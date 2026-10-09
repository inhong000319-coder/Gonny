from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.weather_alerts import build_weather_report

A_START_DATE = date(2026, 6, 1)  # day_number 1 -> 2026-06-01, day 2 -> 06-02, ...


class CountingFakeWeatherClient:
    """Stand-in for OpenWeatherClient - returns canned forecasts (or
    raises) without real network access, and counts how many times it
    was called so tests can assert the forecast is fetched at most once
    per build_weather_report() call."""

    def __init__(self, forecasts: list[dict] | None = None, raise_error: bool = False):
        self._forecasts = forecasts if forecasts is not None else []
        self._raise_error = raise_error
        self.call_count = 0

    def fetch_5day_forecast(self, destination: str, *, allow_mock_fallback: bool = True) -> list[dict]:
        self.call_count += 1
        if self._raise_error:
            raise RuntimeError("simulated failure")
        return self._forecasts


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["sightseeing"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "city-center",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample summary",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def build_catalog(places: list[PlaceData]) -> CityPlaceCatalog:
    return CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=places)


def build_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "seoul",
        "travelers": 2,
        "nights": 1,
        "days": 1,
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
        "companion_type": "friend",
        "start_date": A_START_DATE,
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


def forecast_for(forecast_date: date, *, condition: str, precipitation_mm: float = 0.0) -> dict:
    return {
        "forecast_date": forecast_date,
        "condition": condition,
        "min_temp_c": 10.0,
        "max_temp_c": 18.0,
        "precipitation_mm": precipitation_mm,
    }


# (a) start_date 없음 -> 모든 일차 no_start_date, date None.
def test_no_start_date_marks_every_day_as_no_start_date() -> None:
    catalog = build_catalog([])
    request = build_request(start_date=None, days=3)
    weather_client = CountingFakeWeatherClient([forecast_for(A_START_DATE, condition="rain", precipitation_mm=12.0)])

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert alerts == []
    assert len(statuses) == 3
    assert all(status.status == "no_start_date" and status.date is None for status in statuses)
    # no start_date is decided before any forecast lookup is even attempted.
    assert weather_client.call_count == 0


# (b) 예보 있는 날짜 -> checked + condition/기온 채워짐, 비 예보면 alerts도 일관되게 채워짐.
def test_forecast_within_range_is_checked_and_consistent_with_alerts() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(days=1)
    weather_client = CountingFakeWeatherClient(
        [forecast_for(A_START_DATE, condition="rain", precipitation_mm=12.0)]
    )

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert len(statuses) == 1
    status = statuses[0]
    assert status.status == "checked"
    assert status.date == A_START_DATE
    assert status.condition == "rain"
    assert status.min_temp_c == 10.0
    assert status.max_temp_c == 18.0
    # same forecast fetch backs both weather_status and weather_alerts.
    assert len(alerts) == 1
    assert alerts[0].day_number == 1
    assert alerts[0].condition == "rain"


# (c) 예보 범위 밖(오늘 기준 5일 이후 시작) -> 해당 일차 out_of_range, weather_alerts 빈 목록.
def test_start_date_beyond_forecast_range_is_out_of_range() -> None:
    today = date(2026, 6, 1)
    far_start = today + timedelta(days=10)
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(start_date=far_start, days=1)
    # The forecast client only ever covers the next 5 days from "today" -
    # none of which reach far_start.
    weather_client = CountingFakeWeatherClient(
        [forecast_for(today + timedelta(days=offset), condition="clear") for offset in range(5)]
    )

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=today,
    )

    assert alerts == []
    assert len(statuses) == 1
    assert statuses[0].status == "out_of_range"
    assert statuses[0].date == far_start


# (d) 시작일이 과거 -> past (예보 호출 결과와 무관, "checked"보다도 우선한다).
def test_past_start_date_is_past_even_when_forecast_data_exists_for_it() -> None:
    today = date(2026, 6, 10)
    past_start = date(2026, 6, 1)
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(start_date=past_start, days=1)
    # A forecast entry exists for the past date too - past must still win.
    weather_client = CountingFakeWeatherClient([forecast_for(past_start, condition="rain", precipitation_mm=12.0)])

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=today,
    )

    assert len(statuses) == 1
    assert statuses[0].status == "past"
    assert statuses[0].date == past_start
    assert statuses[0].condition is None


# (e) 예보 조회 실패(빈 목록) -> unavailable.
def test_empty_forecast_response_is_unavailable() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(days=1)
    weather_client = CountingFakeWeatherClient([])

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert alerts == []
    assert len(statuses) == 1
    assert statuses[0].status == "unavailable"
    assert statuses[0].date == A_START_DATE


# (f) 일부 일차만 범위 안(오늘 시작 7일 일정) -> 앞 5일은 checked, 뒤는 out_of_range.
def test_only_days_within_the_5day_window_are_checked() -> None:
    today = A_START_DATE
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(start_date=today, days=7)
    weather_client = CountingFakeWeatherClient(
        [forecast_for(today + timedelta(days=offset), condition="clear") for offset in range(5)]
    )

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={day: [outdoor_place] for day in range(1, 8)},
        city_catalog=catalog,
        weather_client=weather_client,
        today=today,
    )

    assert [status.status for status in statuses] == [
        "checked",
        "checked",
        "checked",
        "checked",
        "checked",
        "out_of_range",
        "out_of_range",
    ]


# (g) 지원하지 않는 도시 -> unavailable.
def test_unsupported_city_is_unavailable() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(city="incheon", days=1)
    weather_client = CountingFakeWeatherClient(
        [forecast_for(A_START_DATE, condition="rain", precipitation_mm=12.0)]
    )

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert alerts == []
    assert len(statuses) == 1
    assert statuses[0].status == "unavailable"
    # an unsupported city never even queries the forecast client.
    assert weather_client.call_count == 0


# (h) 예보 호출이 요청당 1회만 일어난다.
def test_forecast_is_fetched_at_most_once_per_request() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(start_date=A_START_DATE, days=7)
    weather_client = CountingFakeWeatherClient(
        [forecast_for(A_START_DATE + timedelta(days=offset), condition="clear") for offset in range(5)]
    )

    build_weather_report(
        request=request,
        day_place_map={day: [outdoor_place] for day in range(1, 8)},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert weather_client.call_count == 1


# (i) 응답 weather_status 길이 == days (day_place_map에 없는 날도 포함).
def test_weather_status_length_matches_days_even_with_sparse_day_place_map() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(start_date=A_START_DATE, days=3)
    weather_client = CountingFakeWeatherClient(
        [forecast_for(A_START_DATE + timedelta(days=offset), condition="clear") for offset in range(5)]
    )

    # day 2 has no entry in day_place_map (e.g. a closed-day exclusion),
    # same shape as the existing test_weather_alerts_skips_days_outside_...
    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place], 3: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert len(statuses) == 3
    assert [status.day_number for status in statuses] == [1, 2, 3]
    assert all(status.status == "checked" for status in statuses)


# Exception safety net: build_weather_report() must never propagate, and
# degrades to "unavailable" (start_date present) same as the existing
# build_weather_alerts() raise-safety test.
def test_build_weather_report_falls_back_to_unavailable_on_unexpected_error() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(days=2)
    weather_client = CountingFakeWeatherClient(raise_error=True)

    alerts, statuses = build_weather_report(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
        today=A_START_DATE,
    )

    assert alerts == []
    assert len(statuses) == 2
    assert all(status.status == "unavailable" for status in statuses)
