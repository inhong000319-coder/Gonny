"""F04 weather-alert suggestions - see RuleItineraryResponse.weather_alerts.

This module only proposes indoor alternatives for outdoor/mixed places on
rainy/snowy days; it never changes the itinerary's actual placed items
(RuleItineraryResponse.items) - that stays a follow-up step the user (or a
later feature) can act on, same as day_duration_warnings and
closed_day_exclusions.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleWeatherAlert
from app.services.external_clients import OpenWeatherClient

from .constants import PLACE_NAME_KO

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


def build_weather_alerts(
    *,
    request: NormalizedRuleRequest,
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
    weather_client: OpenWeatherClient,
) -> list[RuleWeatherAlert]:
    """Best-effort, never raises - any failure (no start_date, unmapped
    city, no API key, network error, unexpected client bug) degrades to
    an empty list rather than breaking itinerary generation, same
    contract as load_place_feedback_signals()."""
    try:
        return _build_weather_alerts(
            request=request,
            day_place_map=day_place_map,
            city_catalog=city_catalog,
            weather_client=weather_client,
        )
    except Exception:
        return []


def _build_weather_alerts(
    *,
    request: NormalizedRuleRequest,
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
    weather_client: OpenWeatherClient,
) -> list[RuleWeatherAlert]:
    if request.start_date is None or not day_place_map:
        return []

    query_city = WEATHER_QUERY_CITY_BY_CODE.get(request.city)
    if query_city is None:
        return []

    # allow_mock_fallback=False: a missing key or failed call must mean
    # "no alerts", never fabricated mock weather (see fetch_5day_forecast).
    forecasts = weather_client.fetch_5day_forecast(query_city, allow_mock_fallback=False)
    if not forecasts:
        return []

    forecast_by_date = {forecast["forecast_date"]: forecast for forecast in forecasts}

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

        alerts.append(
            RuleWeatherAlert(
                day_number=day_number,
                condition=condition,
                precipitation_mm=precipitation_mm,
                affected_place_names=[_localize_place_name(place) for place in affected],
                suggested_alternatives=suggested_alternatives,
            )
        )

    return alerts
