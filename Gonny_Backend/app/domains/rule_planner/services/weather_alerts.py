"""F04 weather-alert suggestions - see RuleItineraryResponse.weather_alerts.

This module only proposes indoor alternatives for outdoor/mixed places on
rainy/snowy days; it never changes the itinerary's actual placed items
(RuleItineraryResponse.items) - that stays a follow-up step the user (or a
later feature) can act on, same as day_duration_warnings and
closed_day_exclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Literal
from zoneinfo import ZoneInfo

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import (
    NormalizedRuleRequest,
    RuleDayWeatherStatus,
    RuleSlotAlternative,
    RuleWeatherAffectedItem,
    RuleWeatherAlert,
)
from app.services.external_clients import OpenWeatherClient

from .community_feedback import PlaceFeedbackSignal
from .constants import PLACE_NAME_KO, TIME_SLOTS
from .slot_alternatives import neighbors_in_slot_sequence, rank_slot_candidates

# OpenWeatherMap's `q` query param, for the only cities the rule_planner
# actually serves (DestinationCatalogRepository.VISIBLE_CITY_CODES). Any
# other request.city (not one of these) has no forecast lookup and simply
# never produces weather alerts - see build_weather_alerts().
WEATHER_QUERY_CITY_BY_CODE = {
    "seoul": "Seoul,KR",
    "busan": "Busan,KR",
    "jeju": "Jeju,KR",
}

# KMA(기상청) 예보용어해설(https://www.kma.go.kr/kma/biz/forecast05.jsp)의
# 강수강도 분류 - 1시간 강수량 기준: 약한 비 3mm 미만 / 보통 비 3mm 이상
# ~15mm 미만 / 강한 비 15mm 이상 / 매우 강한 비 30mm 이상. 이 기능은
# "약한" vs "보통 이상"만 구분하면 되므로(강한/매우 강한 비도 outdoor
# 전체에 동일하게 경보 대상이라 세분화가 필요 없음) 그 경계값(3mm/h)만
# 사용한다.
#
# 눈은 KMA가 cm(적설 깊이) 단위로 분류하지만(참고: 약한 눈 시간당
# 0.1cm 미만, 강한 눈 시간당 3cm 이상) OpenWeatherMap의 snow.3h는
# mm(수분 환산량)로 온다 - 서로 다른 물리량이고, mm->cm 환산은 눈의
# 밀도(기온에 따라 크게 달라짐)에 의존해 정확한 계수를 추측할 수 없으므로,
# rain과 동일한 mm 기준 강도표를 snow.3h(mm)에도 그대로 적용한다.
MODERATE_OR_ABOVE_THRESHOLD_MM_PER_HOUR = 3.0

# Up to this many indoor alternatives are suggested per affected place.
MAX_ALTERNATIVES_PER_PLACE = 3


def _localize_place_name(place: PlaceData) -> str:
    return PLACE_NAME_KO.get(place.id, place.name)


def _classify_precipitation_intensity(
    precipitation_mm_per_3h: float,
) -> Literal["light", "moderate_or_above"] | None:
    """None means "no meaningful precipitation" (e.g. condition says rain
    but the forecast block's accumulated amount rounds to zero) - callers
    should skip alerting in that case.

    OpenWeatherMap's rain.3h/snow.3h is a 3-hour accumulated total, not an
    hourly rate, so comparing it directly against KMA's hourly thresholds
    would overstate intensity (3mm spread evenly across 3 hours is "약한
    비", not "보통 비"). Dividing by 3 estimates the average hourly rate.
    """
    if precipitation_mm_per_3h <= 0:
        return None
    hourly_rate = precipitation_mm_per_3h / 3.0
    if hourly_rate >= MODERATE_OR_ABOVE_THRESHOLD_MM_PER_HOUR:
        return "moderate_or_above"
    return "light"


def _affected_places(places: list[PlaceData], intensity: Literal["light", "moderate_or_above"]) -> list[PlaceData]:
    if intensity == "moderate_or_above":
        return [place for place in places if place.setting in ("outdoor", "mixed")]
    return [place for place in places if place.rain_sensitive_light]


def _suggest_indoor_alternatives(
    affected_place: PlaceData,
    city_catalog: CityPlaceCatalog,
    request: NormalizedRuleRequest,
) -> list[str]:
    """Same-area first, filtered by budget_band/companion_type like the
    rest of the rule-based scoring (e.g. accommodation_scoring.py) - a
    hard filter that falls back to the unfiltered indoor pool if nothing
    matches, rather than suggesting nothing at all."""
    indoor_candidates = [
        place
        for place in city_catalog.places
        if place.is_active and place.setting == "indoor" and place.id != affected_place.id
    ]
    if not indoor_candidates:
        return []

    matched = [
        place
        for place in indoor_candidates
        if request.budget_band in place.budget_level and request.companion_type in place.suitable_for
    ]
    candidate_pool = matched or indoor_candidates

    same_area = sorted(
        (place for place in candidate_pool if place.area == affected_place.area),
        key=lambda place: place.priority,
        reverse=True,
    )
    other_area = sorted(
        (place for place in candidate_pool if place.area != affected_place.area),
        key=lambda place: place.priority,
        reverse=True,
    )
    ranked = same_area + other_area
    return [_localize_place_name(place) for place in ranked[:MAX_ALTERNATIVES_PER_PLACE]]


@dataclass(frozen=True)
class WeatherSwapContext:
    """Everything RuleWeatherAffectedItem.swap_candidates needs beyond
    what build_weather_report already takes - the same per-trip context
    compute_item_alternatives uses (see RuleItineraryService._assemble_
    response), bundled so build_weather_report/_build_weather_report/
    _build_alerts_from_forecast don't have to thread 8 separate kwargs
    through 3 call layers. Passing None (every pre-existing caller,
    including every test in test_weather_alerts.py/test_weather_status.py)
    means "don't compute affected_items" - see _build_alerts_from_forecast.
    """

    day_slot_places: dict[int, dict[str, PlaceData]]
    day_areas: dict[int, str | None]
    feedback_signals: dict[str, PlaceFeedbackSignal] | None
    day_weekdays: dict[int, int | None]
    localize_place_name: Callable[[PlaceData], str]
    localize_area: Callable[[str], str]
    resolve_item_category: Callable[[PlaceData, NormalizedRuleRequest], str]
    build_note: Callable[..., str]


def build_weather_alerts(
    *,
    request: NormalizedRuleRequest,
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
    weather_client: OpenWeatherClient,
) -> list[RuleWeatherAlert]:
    """Thin wrapper kept for existing callers/tests - see
    build_weather_report() for the full (alerts, statuses) contract.
    affected_items is always [] through this wrapper (no WeatherSwapContext)."""
    alerts, _statuses = build_weather_report(
        request=request,
        day_place_map=day_place_map,
        city_catalog=city_catalog,
        weather_client=weather_client,
    )
    return alerts


def build_weather_report(
    *,
    request: NormalizedRuleRequest,
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
    weather_client: OpenWeatherClient,
    today: date | None = None,
    swap_context: WeatherSwapContext | None = None,
) -> tuple[list[RuleWeatherAlert], list[RuleDayWeatherStatus]]:
    """Best-effort, never raises - any failure (unmapped city, no API
    key, network error, unexpected client bug) degrades to an empty
    alert list plus a best-guess weather_status rather than breaking
    itinerary generation, same contract as load_place_feedback_signals().

    Fetches the forecast at most once per call and derives both the
    alerts (only for days present in day_place_map) and the per-day
    status (for every day 1..request.days, regardless of day_place_map)
    from that single fetch.
    """
    try:
        return _build_weather_report(
            request=request,
            day_place_map=day_place_map,
            city_catalog=city_catalog,
            weather_client=weather_client,
            today=today,
            swap_context=swap_context,
        )
    except Exception:
        if request.start_date is None:
            statuses = [
                RuleDayWeatherStatus(day_number=day_number, date=None, status="no_start_date")
                for day_number in range(1, request.days + 1)
            ]
        else:
            statuses = [
                RuleDayWeatherStatus(
                    day_number=day_number,
                    date=request.start_date + timedelta(days=day_number - 1),
                    status="unavailable",
                )
                for day_number in range(1, request.days + 1)
            ]
        return [], statuses


def _resolve_today(today: date | None) -> date:
    if today is not None:
        return today
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def _build_weather_report(
    *,
    request: NormalizedRuleRequest,
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
    weather_client: OpenWeatherClient,
    today: date | None,
    swap_context: WeatherSwapContext | None = None,
) -> tuple[list[RuleWeatherAlert], list[RuleDayWeatherStatus]]:
    if request.start_date is None:
        statuses = [
            RuleDayWeatherStatus(day_number=day_number, date=None, status="no_start_date")
            for day_number in range(1, request.days + 1)
        ]
        return [], statuses

    resolved_today = _resolve_today(today)
    query_city = WEATHER_QUERY_CITY_BY_CODE.get(request.city)
    # allow_mock_fallback=False: a missing key or failed call must mean
    # "no data", never fabricated mock weather (see fetch_5day_forecast).
    forecasts = weather_client.fetch_5day_forecast(query_city, allow_mock_fallback=False) if query_city else []
    forecast_by_date = {forecast["forecast_date"]: forecast for forecast in forecasts}

    statuses: list[RuleDayWeatherStatus] = []
    for day_number in range(1, request.days + 1):
        day_date = request.start_date + timedelta(days=day_number - 1)
        if day_date < resolved_today:
            statuses.append(RuleDayWeatherStatus(day_number=day_number, date=day_date, status="past"))
            continue
        if query_city is None or not forecasts:
            statuses.append(RuleDayWeatherStatus(day_number=day_number, date=day_date, status="unavailable"))
            continue
        forecast = forecast_by_date.get(day_date)
        if forecast is None:
            # Outside the 5-day forecast window (or otherwise not
            # returned) - the caller can tell this apart from "unavailable".
            statuses.append(RuleDayWeatherStatus(day_number=day_number, date=day_date, status="out_of_range"))
            continue
        statuses.append(
            RuleDayWeatherStatus(
                day_number=day_number,
                date=day_date,
                status="checked",
                condition=forecast["condition"],
                min_temp_c=forecast.get("min_temp_c"),
                max_temp_c=forecast.get("max_temp_c"),
            )
        )

    alerts = _build_alerts_from_forecast(
        request=request,
        day_place_map=day_place_map,
        city_catalog=city_catalog,
        forecast_by_date=forecast_by_date,
        swap_context=swap_context,
    )
    return alerts, statuses


def _build_alerts_from_forecast(
    *,
    request: NormalizedRuleRequest,
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
    forecast_by_date: dict[date, dict],
    swap_context: WeatherSwapContext | None = None,
) -> list[RuleWeatherAlert]:
    if not day_place_map or not forecast_by_date:
        return []

    # swap_context가 있을 때만 쓰는 전역(이 날씨 보고서 전체 공통) 컨텍스트 -
    # compute_item_alternatives와 완전히 같은 "활성·활동 후보" 전체 풀(식당은
    # 빼고, meal_eligible=False인 비식당 food 장소는 포함 - PlaceData.
    # is_activity_candidate 참고), 같은 "트립 전체에서 이미 쓰인 장소" 집합.
    # 매 (날짜, 장소) 쌍마다 다시 계산하지 않고 한 번만 만든다.
    all_used_ids: set[str] | None = None
    scored_places_by_id: dict[str, PlaceData] | None = None
    if swap_context is not None:
        all_used_ids = {place.id for places in day_place_map.values() for place in places}
        scored_places_by_id = {
            place.id: place for place in city_catalog.places if place.is_active and place.is_activity_candidate
        }

    alerts: list[RuleWeatherAlert] = []
    for day_number, places in sorted(day_place_map.items()):
        day_date = request.start_date + timedelta(days=day_number - 1)
        forecast = forecast_by_date.get(day_date)
        if forecast is None:
            # Outside the 5-day forecast window (or otherwise not
            # returned) - skip quietly, per this feature's scope.
            continue

        condition = forecast["condition"]
        if condition not in ("rain", "snow"):
            continue

        precipitation_mm = forecast.get("precipitation_mm", 0.0)
        intensity = _classify_precipitation_intensity(precipitation_mm)
        if intensity is None:
            continue

        affected = _affected_places(places, intensity)
        if not affected:
            continue

        suggested_alternatives: list[str] = []
        for affected_place in affected:
            for suggestion in _suggest_indoor_alternatives(affected_place, city_catalog, request):
                if suggestion not in suggested_alternatives:
                    suggested_alternatives.append(suggestion)

        affected_items = (
            _build_affected_items(
                day_number=day_number,
                affected=affected,
                request=request,
                swap_context=swap_context,
                all_used_ids=all_used_ids,
                scored_places_by_id=scored_places_by_id,
            )
            if swap_context is not None
            else []
        )

        alerts.append(
            RuleWeatherAlert(
                day_number=day_number,
                condition=condition,
                precipitation_mm=precipitation_mm,
                affected_place_names=[_localize_place_name(place) for place in affected],
                suggested_alternatives=suggested_alternatives,
                affected_items=affected_items,
            )
        )

    return alerts


def _build_affected_items(
    *,
    day_number: int,
    affected: list[PlaceData],
    request: NormalizedRuleRequest,
    swap_context: WeatherSwapContext,
    all_used_ids: set[str],
    scored_places_by_id: dict[str, PlaceData],
) -> list[RuleWeatherAffectedItem]:
    """One RuleWeatherAffectedItem per (slot this affected place occupies
    that day) - a full-day place occupies all 3 TIME_SLOTS (see
    RuleItineraryService._build_items' full-day branch: day_slot_places[d]
    maps every slot to the same PlaceData), so it gets 3 entries, each
    with swap_candidates=[] (a full-day item can't be partially swapped -
    see RuleItineraryRecalculateRequest's full-day validation rule in
    services/recalculate.py)."""
    slot_places_for_day = swap_context.day_slot_places.get(day_number, {})
    is_full_day = len(slot_places_for_day) == len(TIME_SLOTS) and len(
        {place.id for place in slot_places_for_day.values()}
    ) == 1
    day_weekday = swap_context.day_weekdays.get(day_number)
    preferred_area = swap_context.day_areas.get(day_number)

    items: list[RuleWeatherAffectedItem] = []
    for affected_place in affected:
        matching_slots = [
            slot
            for slot in TIME_SLOTS
            if slot_places_for_day.get(slot) is not None and slot_places_for_day[slot].id == affected_place.id
        ]
        for slot in matching_slots:
            if is_full_day:
                swap_candidates: list[RuleSlotAlternative] = []
            else:
                previous_place, next_place = neighbors_in_slot_sequence(slot_places_for_day, slot)
                swap_candidates = rank_slot_candidates(
                    scored_places_by_id=scored_places_by_id,
                    exclude_ids=all_used_ids,
                    request=request,
                    time_slot=slot,
                    day_number=day_number,
                    day_weekday=day_weekday,
                    preferred_area=preferred_area,
                    previous_place=previous_place,
                    next_place=next_place,
                    feedback_signals=swap_context.feedback_signals,
                    localize_place_name=swap_context.localize_place_name,
                    localize_area=swap_context.localize_area,
                    resolve_item_category=swap_context.resolve_item_category,
                    build_note=swap_context.build_note,
                    extra_predicate=lambda place: place.setting == "indoor",
                )
            items.append(
                RuleWeatherAffectedItem(
                    time_slot=slot,
                    place_id=affected_place.id,
                    place_name=swap_context.localize_place_name(affected_place),
                    swap_candidates=swap_candidates,
                )
            )
    return items
