from __future__ import annotations

from datetime import timedelta

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import (
    LocalJsonPlaceCatalogProvider,
    PlaceCatalogProvider,
)
from app.domains.rule_planner.schemas import (
    CatalogCityOption,
    NormalizedRuleRequest,
    RuleClosedDayExclusion,
    RuleDayDurationWarning,
    RuleItineraryItem,
    RuleItineraryRequest,
    RuleItineraryResponse,
)

from .accommodation_scoring import (
    compute_reference_point,
    load_city_accommodations,
    select_accommodation_recommendation,
)
from .closed_days import WEEKDAY_LABEL_KO, is_confirmed_closed_on
from .community_feedback import PlaceFeedbackSignal, load_place_feedback_signals
from .constants import (
    ACTIVITY_CATEGORIES,
    AREA_LABEL_KO,
    DAY_DURATION_WARNING_THRESHOLD_HOURS,
    PLACE_NAME_KO,
    TIME_SLOTS,
)
from .note_generator import RuleNoteContext, build_rule_note_generator
from .policies.city import preferred_area_order
from .request_normalizer import normalize_budget, normalize_duration, normalize_rule_request
from .slot_scoring import (
    base_score,
    day_phase,
    duration_slot_score,
    phase_score,
    slot_bias_score,
    slot_score,
    style_slot_score,
)
from .travel_estimate import estimate_day_total_minutes


class RuleItineraryService:
    def __init__(self, catalog_provider: PlaceCatalogProvider | None = None):
        self.catalog_provider = catalog_provider or LocalJsonPlaceCatalogProvider()
        self.note_generator = build_rule_note_generator()

    def list_catalog_options(self) -> list[CatalogCityOption]:
        return self.catalog_provider.list_city_options(visible_only=True)

    def generate(self, request: RuleItineraryRequest) -> RuleItineraryResponse:
        normalized = self._normalize_request(request)
        city_catalog = self.catalog_provider.get_city_catalog(
            continent=normalized.continent,
            country=normalized.country,
            city=normalized.city,
            visible_only=True,
        )
        items, day_place_map, closed_day_exclusions = self._build_items(normalized, city_catalog)
        accommodation_recommendation = self._recommend_accommodation(normalized, city_catalog, day_place_map)
        day_duration_warnings = self._build_day_duration_warnings(day_place_map, accommodation_recommendation)

        return RuleItineraryResponse(
            continent=city_catalog.continent,
            country=city_catalog.country,
            city=city_catalog.city,
            travelers=normalized.travelers,
            nights=normalized.nights,
            days=normalized.days,
            budget_band=normalized.budget_band,
            concepts=normalized.concepts,
            style=normalized.style,
            companion_type=normalized.companion_type,
            featured_video=city_catalog.featured_video,
            items=items,
            day_duration_warnings=day_duration_warnings,
            closed_day_exclusions=closed_day_exclusions,
            accommodation_recommendation=accommodation_recommendation,
        )

    def _normalize_request(self, request: RuleItineraryRequest) -> NormalizedRuleRequest:
        return normalize_rule_request(request)

    def _normalize_duration(
        self,
        *,
        nights: int | None,
        days: int | None,
        duration_label: str | None,
    ) -> tuple[int, int]:
        return normalize_duration(nights=nights, days=days, duration_label=duration_label)

    def _normalize_budget(self, budget_value: int | None, budget_band: str | None) -> str:
        return normalize_budget(budget_value, budget_band)

    def _build_items(
        self,
        request: NormalizedRuleRequest,
        city_catalog: CityPlaceCatalog,
    ) -> tuple[list[RuleItineraryItem], dict[int, list[PlaceData]], list[RuleClosedDayExclusion]]:
        scored_places = sorted(
            [place for place in city_catalog.places if place.is_active],
            key=lambda place: self._base_score(place, request),
            reverse=True,
        )

        area_scores = self._group_area_scores(scored_places, request)
        preferred_areas = self._preferred_area_order(request=request, area_scores=area_scores)
        feedback_signals = load_place_feedback_signals([place.id for place in scored_places])
        used_ids: set[str] = set()
        used_day_areas: set[str] = set()
        items: list[RuleItineraryItem] = []
        day_place_map: dict[int, list[PlaceData]] = {}
        closed_day_exclusions: list[RuleClosedDayExclusion] = []
        seen_exclusion_keys: set[tuple[int, str]] = set()
        full_day_used = False

        for day_number in range(1, request.days + 1):
            day_weekday = self._day_weekday(request, day_number)
            full_day_place = self._pick_full_day_place(
                scored_places=scored_places,
                request=request,
                used_ids=used_ids,
                day_number=day_number,
                allow_full_day=not full_day_used,
                day_weekday=day_weekday,
                closed_day_exclusions=closed_day_exclusions,
                seen_exclusion_keys=seen_exclusion_keys,
            )
            if full_day_place is not None:
                for slot in TIME_SLOTS:
                    items.append(
                        RuleItineraryItem(
                            day_number=day_number,
                            time_slot=slot,
                            place_name=self._localize_place_name(full_day_place),
                            category=(
                                full_day_place.activity_type_codes[0]
                                if full_day_place.activity_type_codes
                                else "activity"
                            ),
                            area=self._localize_area(full_day_place.area),
                            notes=self._build_note(
                                place=full_day_place,
                                request=request,
                                time_slot=slot,
                                day_number=day_number,
                                day_area=full_day_place.area,
                                previous_place=full_day_place if slot != "morning" else None,
                            ),
                        )
                    )
                used_ids.add(full_day_place.id)
                day_place_map[day_number] = [full_day_place]
                full_day_used = True
                continue

            day_area = self._pick_day_area(preferred_areas, scored_places, used_ids, used_day_areas)
            if day_area:
                used_day_areas.add(day_area)
            day_places: list[PlaceData] = []

            for slot in TIME_SLOTS:
                previous_place = day_places[-1] if day_places else None
                chosen = self._pick_place_for_slot(
                    scored_places=scored_places,
                    request=request,
                    time_slot=slot,
                    day_number=day_number,
                    used_ids=used_ids,
                    preferred_area=day_area,
                    previous_place=previous_place,
                    feedback_signals=feedback_signals,
                    day_weekday=day_weekday,
                    closed_day_exclusions=closed_day_exclusions,
                    seen_exclusion_keys=seen_exclusion_keys,
                )
                if chosen is None:
                    continue

                used_ids.add(chosen.id)
                main_category = self._resolve_item_category(chosen, request)
                items.append(
                    RuleItineraryItem(
                        day_number=day_number,
                        time_slot=slot,
                        place_name=self._localize_place_name(chosen),
                        category=main_category,
                        area=self._localize_area(chosen.area),
                        notes=self._build_note(
                            place=chosen,
                            request=request,
                            time_slot=slot,
                            day_number=day_number,
                            day_area=day_area,
                            previous_place=previous_place,
                        ),
                    )
                )
                day_places.append(chosen)

            if day_places:
                day_place_map[day_number] = day_places

        return items, day_place_map, closed_day_exclusions

    def _day_weekday(self, request: NormalizedRuleRequest, day_number: int) -> int | None:
        """0=Monday ... 6=Sunday for this day_number, or None if the
        request has no start_date (closed-day exclusion never triggers
        without it - see RuleItineraryRequest.start_date)."""
        if request.start_date is None:
            return None
        return (request.start_date + timedelta(days=day_number - 1)).weekday()

    def _select_first_open_candidate(
        self,
        *,
        ranked_candidates: list[PlaceData],
        day_number: int,
        day_weekday: int | None,
        closed_day_exclusions: list[RuleClosedDayExclusion] | None,
        seen_exclusion_keys: set[tuple[int, str]] | None,
    ) -> PlaceData | None:
        """Returns the highest-ranked candidate that isn't confirmed closed
        on day_weekday, skipping (and recording) any confirmed-closed ones
        ahead of it. When day_weekday is None (no start_date on the
        request), this is a no-op passthrough to ranked_candidates[0]."""
        if day_weekday is None:
            return ranked_candidates[0] if ranked_candidates else None

        for candidate in ranked_candidates:
            if not is_confirmed_closed_on(candidate.closed_days, day_weekday):
                return candidate

            key = (day_number, candidate.id)
            if closed_day_exclusions is not None and seen_exclusion_keys is not None and key not in seen_exclusion_keys:
                seen_exclusion_keys.add(key)
                place_name = self._localize_place_name(candidate)
                closed_day_exclusions.append(
                    RuleClosedDayExclusion(
                        day_number=day_number,
                        place_name=place_name,
                        message=(
                            f"{place_name}은(는) {WEEKDAY_LABEL_KO[day_weekday]}에 휴무로 확인되어 "
                            f"{day_number}일차 일정에서 제외했습니다."
                        ),
                    )
                )
        return None

    def _build_day_duration_warnings(
        self,
        day_place_map: dict[int, list[PlaceData]],
        accommodation: AccommodationData | None = None,
    ) -> list[RuleDayDurationWarning]:
        threshold_minutes = DAY_DURATION_WARNING_THRESHOLD_HOURS * 60
        warnings: list[RuleDayDurationWarning] = []
        for day_number, places in sorted(day_place_map.items()):
            total_minutes = estimate_day_total_minutes(places, accommodation)
            if total_minutes > threshold_minutes:
                warnings.append(
                    RuleDayDurationWarning(
                        day_number=day_number,
                        estimated_total_minutes=total_minutes,
                        message=(
                            f"{day_number}일차 예상 총 소요시간이 약 {total_minutes / 60:.1f}시간으로 "
                            f"{DAY_DURATION_WARNING_THRESHOLD_HOURS}시간을 초과합니다."
                        ),
                    )
                )
        return warnings

    def _recommend_accommodation(
        self,
        request: NormalizedRuleRequest,
        city_catalog: CityPlaceCatalog,
        day_place_map: dict[int, list[PlaceData]],
    ) -> AccommodationData | None:
        accommodations = load_city_accommodations(city_catalog.city)
        reference_point = compute_reference_point(day_place_map, city_catalog)
        return select_accommodation_recommendation(accommodations, request, reference_point)

    def _pick_full_day_place(
        self,
        *,
        scored_places: list[PlaceData],
        request: NormalizedRuleRequest,
        used_ids: set[str],
        day_number: int,
        allow_full_day: bool,
        day_weekday: int | None = None,
        closed_day_exclusions: list[RuleClosedDayExclusion] | None = None,
        seen_exclusion_keys: set[tuple[int, str]] | None = None,
    ) -> PlaceData | None:
        if not allow_full_day or "activity" not in request.concepts:
            return None
        if self._day_phase(request, day_number) != "middle":
            return None

        candidates = [
            place
            for place in scored_places
            if place.id not in used_ids
            and place.full_day_recommended
            and set(place.activity_type_codes) & ACTIVITY_CATEGORIES
        ]
        if not candidates:
            return None

        ranked = sorted(candidates, key=lambda place: self._base_score(place, request) + 20, reverse=True)
        return self._select_first_open_candidate(
            ranked_candidates=ranked,
            day_number=day_number,
            day_weekday=day_weekday,
            closed_day_exclusions=closed_day_exclusions,
            seen_exclusion_keys=seen_exclusion_keys,
        )

    def _group_area_scores(self, places: list[PlaceData], request: NormalizedRuleRequest) -> dict[str, int]:
        area_scores: dict[str, int] = {}
        for place in places:
            area_scores[place.area] = area_scores.get(place.area, 0) + self._base_score(place, request)
        return area_scores

    def _preferred_area_order(self, *, request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
        return preferred_area_order(request, area_scores)

    def _pick_day_area(
        self,
        preferred_areas: list[str],
        places: list[PlaceData],
        used_ids: set[str],
        used_day_areas: set[str],
    ) -> str | None:
        if preferred_areas:
            fresh_areas = [area for area in preferred_areas if area not in used_day_areas]
            area_pool = fresh_areas or preferred_areas
            for candidate_area in area_pool:
                if any(place.area == candidate_area and place.id not in used_ids for place in places):
                    return candidate_area
        return None

    def _resolve_item_category(self, place: PlaceData, request: NormalizedRuleRequest) -> str:
        categories = set(place.activity_type_codes)
        if "activity" in request.concepts and categories & ACTIVITY_CATEGORIES:
            return "activity"
        return place.activity_type_codes[0] if place.activity_type_codes else "sightseeing"

    def _pick_place_for_slot(
        self,
        *,
        scored_places: list[PlaceData],
        request: NormalizedRuleRequest,
        time_slot: str,
        day_number: int,
        used_ids: set[str],
        preferred_area: str | None,
        previous_place: PlaceData | None,
        feedback_signals: dict[str, PlaceFeedbackSignal] | None = None,
        day_weekday: int | None = None,
        closed_day_exclusions: list[RuleClosedDayExclusion] | None = None,
        seen_exclusion_keys: set[tuple[int, str]] | None = None,
    ) -> PlaceData | None:
        available_places = [place for place in scored_places if place.id not in used_ids]
        slot_fitting_places = [place for place in available_places if time_slot in place.time_fit]
        candidate_pool = slot_fitting_places or available_places
        candidate_pool = self._filter_phase_candidates(
            places=candidate_pool,
            request=request,
            day_number=day_number,
        )

        ranked_candidates = sorted(
            candidate_pool,
            key=lambda place: self._slot_score(
                place=place,
                request=request,
                time_slot=time_slot,
                day_number=day_number,
                preferred_area=preferred_area,
                previous_place=previous_place,
                community_signal=(feedback_signals or {}).get(place.id),
            ),
            reverse=True,
        )
        return self._select_first_open_candidate(
            ranked_candidates=ranked_candidates,
            day_number=day_number,
            day_weekday=day_weekday,
            closed_day_exclusions=closed_day_exclusions,
            seen_exclusion_keys=seen_exclusion_keys,
        )

    def _filter_phase_candidates(
        self,
        *,
        places: list[PlaceData],
        request: NormalizedRuleRequest,
        day_number: int,
    ) -> list[PlaceData]:
        if self._day_phase(request, day_number) not in {"arrival", "departure"}:
            return places
        if "activity" not in request.concepts:
            return places

        non_activity_places = [
            place for place in places if not (set(place.activity_type_codes) & ACTIVITY_CATEGORIES)
        ]
        return non_activity_places or places

    def _day_phase(self, request: NormalizedRuleRequest, day_number: int) -> str:
        return day_phase(request, day_number)

    def _localize_place_name(self, place: PlaceData) -> str:
        return PLACE_NAME_KO.get(place.id, place.name)

    def _localize_area(self, area: str) -> str:
        return AREA_LABEL_KO.get(area, area)

    def _base_score(self, place: PlaceData, request: NormalizedRuleRequest) -> int:
        return base_score(place, request)

    def _slot_score(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        time_slot: str,
        day_number: int,
        preferred_area: str | None,
        previous_place: PlaceData | None = None,
        community_signal: PlaceFeedbackSignal | None = None,
    ) -> int:
        return slot_score(
            place=place,
            request=request,
            time_slot=time_slot,
            day_number=day_number,
            preferred_area=preferred_area,
            previous_place=previous_place,
            community_signal=community_signal,
        )

    def _duration_slot_score(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        time_slot: str,
    ) -> int:
        return duration_slot_score(place=place, request=request, time_slot=time_slot)

    def _style_slot_score(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        time_slot: str,
    ) -> int:
        return style_slot_score(place=place, request=request, time_slot=time_slot)

    def _slot_bias_score(
        self,
        *,
        place: PlaceData,
        time_slot: str,
    ) -> int:
        return slot_bias_score(place=place, time_slot=time_slot)

    def _phase_score(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        day_number: int,
        time_slot: str,
    ) -> int:
        return phase_score(place=place, request=request, day_number=day_number, time_slot=time_slot)

    def _build_note(
        self,
        *,
        place: PlaceData,
        request: NormalizedRuleRequest,
        time_slot: str,
        day_number: int,
        day_area: str | None = None,
        previous_place: PlaceData | None = None,
    ) -> str:
        return self.note_generator.generate(
            RuleNoteContext(
                place=place,
                request=request,
                time_slot=time_slot,
                day_number=day_number,
                localized_place_name=self._localize_place_name(place),
                localized_area_name=self._localize_area(place.area),
                day_area_name=self._localize_area(day_area) if day_area else None,
                previous_place_name=self._localize_place_name(previous_place) if previous_place else None,
                previous_area_name=self._localize_area(previous_place.area) if previous_place else None,
            )
        )


rule_itinerary_service = RuleItineraryService()
