from __future__ import annotations

from datetime import timedelta
from typing import Literal

from app.core.settings import settings
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
    RuleMealRecommendation,
    RuleWeatherAlert,
)
from app.services.external_clients import OpenWeatherClient

from .accommodation_scoring import (
    count_accommodation_types,
    compute_reference_point,
    load_city_accommodations,
    select_accommodation_recommendation,
)
from .closed_days import WEEKDAY_LABEL_KO, is_confirmed_closed_on
from .cost_estimate import estimate_trip_cost_range
from .community_feedback import PlaceFeedbackSignal, load_place_feedback_signals
from .constants import (
    ACTIVITY_CATEGORIES,
    AREA_LABEL_KO,
    AREA_NEIGHBORS_BY_CITY,
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
    meal_candidate_score,
    phase_score,
    slot_bias_score,
    slot_score,
    style_slot_score,
)
from .travel_estimate import estimate_day_total_minutes, estimate_travel_minutes_between
from .weather_alerts import build_weather_alerts

# How much higher a next-place-aware refinement candidate's score must be
# than the currently-placed item's before _refine_day_with_next_place_lookahead
# swaps it in - a real margin, not any marginal/noise-level improvement, so
# the refinement pass doesn't just churn picks. Roughly one continuity-bonus
# tier (see travel_estimate.py's NEARBY_TRANSITION_BONUS=6/CLOSE_TRANSITION_BONUS=14).
REFINEMENT_SCORE_MARGIN = 10


class RuleItineraryService:
    def __init__(
        self,
        catalog_provider: PlaceCatalogProvider | None = None,
        weather_client: OpenWeatherClient | None = None,
    ):
        self.catalog_provider = catalog_provider or LocalJsonPlaceCatalogProvider()
        self.note_generator = build_rule_note_generator()
        self.weather_client = weather_client or OpenWeatherClient(settings)

    def list_catalog_options(self) -> list[CatalogCityOption]:
        return [
            option.model_copy(update={"accommodation_type_counts": count_accommodation_types(option.city)})
            for option in self.catalog_provider.list_city_options(visible_only=True)
        ]

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
        meal_recommendations, day_place_map_with_meals = self._recommend_meals(
            normalized, city_catalog, day_place_map
        )
        day_duration_warnings = self._build_day_duration_warnings(
            day_place_map_with_meals, accommodation_recommendation
        )
        weather_alerts = self._build_weather_alerts(normalized, day_place_map, city_catalog)

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
            weather_alerts=weather_alerts,
            accommodation_recommendation=accommodation_recommendation,
            meal_recommendations=meal_recommendations,
            estimated_cost=estimate_trip_cost_range(
                (place for places in day_place_map.values() for place in places),
                accommodation_recommendation,
                travelers=normalized.travelers,
                nights=normalized.nights,
            ),
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
        # "food" places are excluded from the 3-slot activity competition
        # entirely, not merely de-preferred - they're recommended
        # independently per day instead (see _recommend_meals), same
        # separation as accommodation_recommendation never appearing in
        # items. Removing food only from SLOT_CATEGORY_PREFERENCE's
        # preference-match bonus isn't enough on its own: a food place can
        # still win a slot on base_score/coordinate-continuity alone, so
        # it has to be dropped from the candidate pool here too.
        scored_places = sorted(
            [place for place in city_catalog.places if place.is_active and "food" not in place.concept_tags],
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
                            # Every slot is the same place on a full-day
                            # itinerary item, so there's no real transition
                            # to report - see RuleItineraryItem's docstring.
                            travel_minutes_from_previous=None,
                            average_cost_krw=full_day_place.average_cost_krw,
                        )
                    )
                used_ids.add(full_day_place.id)
                day_place_map[day_number] = [full_day_place]
                full_day_used = True
                continue

            day_area = self._pick_day_area(preferred_areas, scored_places, used_ids, used_day_areas)
            if day_area:
                used_day_areas.add(day_area)

            slot_places = self._pick_places_for_day(
                scored_places=scored_places,
                request=request,
                day_number=day_number,
                used_ids=used_ids,
                day_area=day_area,
                feedback_signals=feedback_signals,
                day_weekday=day_weekday,
                closed_day_exclusions=closed_day_exclusions,
                seen_exclusion_keys=seen_exclusion_keys,
            )
            slot_places = self._refine_day_with_next_place_lookahead(
                slot_places,
                scored_places=scored_places,
                request=request,
                day_number=day_number,
                used_ids=used_ids,
                day_area=day_area,
                feedback_signals=feedback_signals,
                day_weekday=day_weekday,
            )

            day_places = [place for _, place in slot_places]
            for index, (slot, chosen) in enumerate(slot_places):
                previous_place = slot_places[index - 1][1] if index > 0 else None
                main_category = self._resolve_item_category(chosen, request)
                travel_minutes_from_previous = (
                    estimate_travel_minutes_between(previous_place, chosen) if previous_place is not None else None
                )
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
                        travel_minutes_from_previous=travel_minutes_from_previous,
                        average_cost_krw=chosen.average_cost_krw,
                    )
                )

            if day_places:
                day_place_map[day_number] = day_places

        return items, day_place_map, closed_day_exclusions

    def _pick_places_for_day(
        self,
        *,
        scored_places: list[PlaceData],
        request: NormalizedRuleRequest,
        day_number: int,
        used_ids: set[str],
        day_area: str | None,
        feedback_signals: dict[str, PlaceFeedbackSignal] | None,
        day_weekday: int | None,
        closed_day_exclusions: list[RuleClosedDayExclusion] | None,
        seen_exclusion_keys: set[tuple[int, str]] | None,
    ) -> list[tuple[str, PlaceData]]:
        """Greedy first pass: one slot at a time, morning -> afternoon ->
        evening. previous_place is known at this point (the prior slot in
        this same pass); next_place never is - the slot loop can't know
        what a later slot will hold before picking it. That's what
        _refine_day_with_next_place_lookahead() is for, run afterward once
        the whole day is confirmed.
        """
        slot_places: list[tuple[str, PlaceData]] = []
        for slot in TIME_SLOTS:
            previous_place = slot_places[-1][1] if slot_places else None
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
            slot_places.append((slot, chosen))
        return slot_places

    def _is_open_on_day(self, place: PlaceData, day_weekday: int | None) -> bool:
        """Silent (no exclusion-recording) closed-day check for the
        speculative re-scoring below - unlike _select_first_open_candidate(),
        this evaluates candidates that mostly never end up placed, so it
        must not add closed_day_exclusions noise implying a real attempt."""
        if day_weekday is None:
            return True
        return not is_confirmed_closed_on(place.closed_days, day_weekday)

    def _refine_day_with_next_place_lookahead(
        self,
        slot_places: list[tuple[str, PlaceData]],
        *,
        scored_places: list[PlaceData],
        request: NormalizedRuleRequest,
        day_number: int,
        used_ids: set[str],
        day_area: str | None,
        feedback_signals: dict[str, PlaceFeedbackSignal] | None,
        day_weekday: int | None,
    ) -> list[tuple[str, PlaceData]]:
        """2nd pass over an already-greedily-placed day: re-score each slot
        (except the day's last, which has no next place) against its now-
        confirmed previous AND next place, and swap in a clearly-better
        unused candidate if one exists (see REFINEMENT_SCORE_MARGIN). This
        is the "refine after the fact" approach recommended for exposing
        next_place-aware scoring without restructuring the greedy slot
        loop into a lookahead search.
        """
        if len(slot_places) < 2:
            return slot_places  # no next_place context exists with 0-1 slots

        for index, (slot, current_place) in enumerate(slot_places):
            if index + 1 >= len(slot_places):
                continue  # day's last slot has no next place to look ahead to

            previous_place = slot_places[index - 1][1] if index > 0 else None
            next_place = slot_places[index + 1][1]

            current_score = self._slot_score(
                place=current_place,
                request=request,
                time_slot=slot,
                day_number=day_number,
                preferred_area=day_area,
                previous_place=previous_place,
                next_place=next_place,
                community_signal=(feedback_signals or {}).get(current_place.id),
            )

            available = [
                place
                for place in scored_places
                if place.id not in used_ids and self._is_open_on_day(place, day_weekday)
            ]
            if not available:
                continue

            best_candidate = max(
                available,
                key=lambda place: self._slot_score(
                    place=place,
                    request=request,
                    time_slot=slot,
                    day_number=day_number,
                    preferred_area=day_area,
                    previous_place=previous_place,
                    next_place=next_place,
                    community_signal=(feedback_signals or {}).get(place.id),
                ),
            )
            best_score = self._slot_score(
                place=best_candidate,
                request=request,
                time_slot=slot,
                day_number=day_number,
                preferred_area=day_area,
                previous_place=previous_place,
                next_place=next_place,
                community_signal=(feedback_signals or {}).get(best_candidate.id),
            )

            if best_score > current_score + REFINEMENT_SCORE_MARGIN:
                used_ids.discard(current_place.id)
                used_ids.add(best_candidate.id)
                slot_places[index] = (slot, best_candidate)

        return slot_places

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

    def _build_weather_alerts(
        self,
        request: NormalizedRuleRequest,
        day_place_map: dict[int, list[PlaceData]],
        city_catalog: CityPlaceCatalog,
    ) -> list[RuleWeatherAlert]:
        return build_weather_alerts(
            request=request,
            day_place_map=day_place_map,
            city_catalog=city_catalog,
            weather_client=self.weather_client,
        )

    def _recommend_accommodation(
        self,
        request: NormalizedRuleRequest,
        city_catalog: CityPlaceCatalog,
        day_place_map: dict[int, list[PlaceData]],
    ) -> AccommodationData | None:
        accommodations = load_city_accommodations(city_catalog.city)
        reference_point = compute_reference_point(day_place_map, city_catalog)
        return select_accommodation_recommendation(accommodations, request, reference_point)

    def _recommend_meals(
        self,
        request: NormalizedRuleRequest,
        city_catalog: CityPlaceCatalog,
        day_place_map: dict[int, list[PlaceData]],
    ) -> tuple[list[RuleMealRecommendation], dict[int, list[PlaceData]]]:
        """Independent lunch/dinner recommendation, one pass per day - same
        spirit as _recommend_accommodation() above (a pick made outside the
        morning/afternoon/evening slot competition), just repeated per day
        instead of once for the whole trip. Runs as its own pass over the
        already-built itinerary (day_place_map) rather than inside
        _build_items()'s slot loop: food no longer competes for a slot
        (see SLOT_CATEGORY_PREFERENCE), so it doesn't belong in that loop
        at all any more - this replaces the old post-hoc food-guarantee
        swap that used to live there.

        Point-in-day order is morning_place -> lunch -> afternoon_place ->
        dinner -> evening_place (a full-day day's single place anchors
        both meals on both sides, since it fills all 3 nominal slots).

        Returns (meal_recommendations, day_place_map_with_meals) - the
        second is day_place_map with the actually-chosen restaurant
        PlaceData spliced into each day's place list at that point-in-day
        position, for _build_day_duration_warnings() to size the day's
        total time correctly (a day with an unaccounted lunch/dinner would
        otherwise look shorter than it really is). The original
        day_place_map (without meals) is still what every other caller
        (weather alerts, the accommodation reference point above) uses -
        see this feature's scope note on why duration warnings alone need
        the augmented version.
        """
        scored_places = sorted(
            [place for place in city_catalog.places if place.is_active],
            key=lambda place: self._base_score(place, request),
            reverse=True,
        )
        # Restaurants must never repeat across days/meals within the same
        # trip, and must never collide with an already-placed activity
        # place - seed this from every activity place already in the
        # itinerary, then grow it as meals get picked below.
        used_ids: set[str] = {place.id for places in day_place_map.values() for place in places}

        meal_recommendations: list[RuleMealRecommendation] = []
        day_place_map_with_meals: dict[int, list[PlaceData]] = {}

        # Iterates every day in the request, not just the days that ended
        # up with an entry in day_place_map: a day where the activity-slot
        # loop somehow placed nothing at all (candidate pool exhaustion -
        # rare, but possible) should still get its own lunch/dinner
        # consideration rather than silently having no meals at all.
        for day_number in range(1, request.days + 1):
            day_places = day_place_map.get(day_number, [])
            day_weekday = self._day_weekday(request, day_number)
            day_area = day_places[0].area if day_places else None

            if len(day_places) <= 1:
                # Full-day (or an edge-case empty/single-item day): the one
                # place anchors both sides of both meals.
                morning_place = afternoon_place = evening_place = day_places[0] if day_places else None
            else:
                morning_place = day_places[0]
                afternoon_place = day_places[1] if len(day_places) > 1 else None
                evening_place = day_places[2] if len(day_places) > 2 else None

            lunch_place = self._pick_meal_place(
                previous_place=morning_place,
                next_place=afternoon_place,
                day_area=day_area,
                city=request.city,
                scored_places=scored_places,
                request=request,
                used_ids=used_ids,
                day_number=day_number,
                day_weekday=day_weekday,
            )
            if lunch_place is not None:
                used_ids.add(lunch_place.id)
                meal_recommendations.append(
                    self._build_meal_recommendation(
                        place=lunch_place,
                        meal_type="lunch",
                        request=request,
                        day_number=day_number,
                        day_area=day_area,
                        previous_place=morning_place,
                    )
                )

            dinner_place = self._pick_meal_place(
                previous_place=afternoon_place,
                next_place=evening_place,
                day_area=day_area,
                city=request.city,
                scored_places=scored_places,
                request=request,
                used_ids=used_ids,
                day_number=day_number,
                day_weekday=day_weekday,
            )
            if dinner_place is not None:
                used_ids.add(dinner_place.id)
                meal_recommendations.append(
                    self._build_meal_recommendation(
                        place=dinner_place,
                        meal_type="dinner",
                        request=request,
                        day_number=day_number,
                        day_area=day_area,
                        previous_place=afternoon_place,
                    )
                )

            augmented_day_places = self._splice_meals_into_day_places(
                day_places, lunch_place=lunch_place, dinner_place=dinner_place
            )
            if augmented_day_places:
                day_place_map_with_meals[day_number] = augmented_day_places

        return meal_recommendations, day_place_map_with_meals

    def _pick_meal_place(
        self,
        *,
        previous_place: PlaceData | None,
        next_place: PlaceData | None,
        day_area: str | None,
        city: str,
        scored_places: list[PlaceData],
        request: NormalizedRuleRequest,
        used_ids: set[str],
        day_number: int,
        day_weekday: int | None,
    ) -> PlaceData | None:
        food_candidates = [
            place for place in scored_places if place.id not in used_ids and "food" in place.concept_tags
        ]
        if not food_candidates:
            return None  # no food entity available for this city - data gap, not a bug

        candidate_pool = self._meal_candidate_pool(food_candidates, day_area=day_area, city=city)
        ranked = sorted(
            candidate_pool,
            key=lambda place: meal_candidate_score(
                place, request, previous_place=previous_place, next_place=next_place
            ),
            reverse=True,
        )
        # Meal closures aren't surfaced as itinerary-level
        # closed_day_exclusions (those cover activity-slot picks) - a
        # restaurant being closed today just quietly moves on to the next
        # candidate, so this passes None/None rather than recording one.
        return self._select_first_open_candidate(
            ranked_candidates=ranked,
            day_number=day_number,
            day_weekday=day_weekday,
            closed_day_exclusions=None,
            seen_exclusion_keys=None,
        )

    def _meal_candidate_pool(
        self, food_candidates: list[PlaceData], *, day_area: str | None, city: str
    ) -> list[PlaceData]:
        """day_area preferred, falling back to a neighboring area, falling
        back to the whole city - never an empty pool as long as
        food_candidates itself is non-empty, so a real (if farther-away)
        recommendation always beats no recommendation."""
        if not day_area:
            return food_candidates

        same_area = [place for place in food_candidates if place.area == day_area]
        if same_area:
            return same_area

        neighbor_areas = AREA_NEIGHBORS_BY_CITY.get(city, {}).get(day_area, set())
        neighbor_area_candidates = [place for place in food_candidates if place.area in neighbor_areas]
        if neighbor_area_candidates:
            return neighbor_area_candidates

        return food_candidates

    def _splice_meals_into_day_places(
        self,
        day_places: list[PlaceData],
        *,
        lunch_place: PlaceData | None,
        dinner_place: PlaceData | None,
    ) -> list[PlaceData]:
        """Rebuilds one day's place list in point-in-day order (morning ->
        lunch -> afternoon -> dinner -> evening) with the chosen meals
        spliced in, for _build_day_duration_warnings() to size the day
        correctly. A full-day day (day_places has a single entry) has no
        "afternoon"/"evening" to splice around, so this naturally reduces
        to [full_day_place, lunch?, dinner?] - the full-day place's own
        duration_hours already accounts for the whole day's activity time,
        so it's included exactly once even though it conceptually spans
        every slot.
        """
        augmented: list[PlaceData] = []
        if day_places:
            augmented.append(day_places[0])
        if lunch_place is not None:
            augmented.append(lunch_place)
        if len(day_places) > 1:
            augmented.append(day_places[1])
        if dinner_place is not None:
            augmented.append(dinner_place)
        if len(day_places) > 2:
            augmented.append(day_places[2])
        return augmented

    def _build_meal_recommendation(
        self,
        *,
        place: PlaceData,
        meal_type: Literal["lunch", "dinner"],
        request: NormalizedRuleRequest,
        day_number: int,
        day_area: str | None,
        previous_place: PlaceData | None,
    ) -> RuleMealRecommendation:
        # Reuses the existing note generator rather than inventing meal-
        # specific templates - "afternoon"/"evening" flavor the copy
        # closely enough to lunch/dinner's real-world timing (note_generator's
        # templates fall back to a neutral generic line for any other
        # time_slot value anyway, so this never produces something odd).
        note_time_slot = "afternoon" if meal_type == "lunch" else "evening"
        return RuleMealRecommendation(
            day_number=day_number,
            meal_type=meal_type,
            place_name=self._localize_place_name(place),
            area=self._localize_area(place.area),
            notes=self._build_note(
                place=place,
                request=request,
                time_slot=note_time_slot,
                day_number=day_number,
                day_area=day_area,
                previous_place=previous_place,
            ),
            travel_minutes_from_previous=(
                estimate_travel_minutes_between(previous_place, place) if previous_place is not None else None
            ),
        )

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
        next_place: PlaceData | None = None,
        community_signal: PlaceFeedbackSignal | None = None,
    ) -> int:
        return slot_score(
            place=place,
            request=request,
            time_slot=time_slot,
            day_number=day_number,
            preferred_area=preferred_area,
            previous_place=previous_place,
            next_place=next_place,
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
