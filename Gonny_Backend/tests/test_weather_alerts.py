from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.weather_alerts import build_weather_alerts

A_START_DATE = date(2026, 6, 1)  # day_number 1 -> 2026-06-01, day 2 -> 06-02, ...


class FakeWeatherClient:
    """Stand-in for OpenWeatherClient - returns canned forecasts, or
    raises, without any real network access."""

    def __init__(self, forecasts: list[dict] | None = None, raise_error: bool = False):
        self._forecasts = forecasts if forecasts is not None else []
        self._raise_error = raise_error

    def fetch_5day_forecast(self, destination: str, *, allow_mock_fallback: bool = True) -> list[dict]:
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


def forecast_for(day_offset: int, *, condition: str, precipitation_mm: float) -> dict:
    return {
        "forecast_date": A_START_DATE + timedelta(days=day_offset),
        "condition": condition,
        "min_temp_c": 10.0,
        "max_temp_c": 18.0,
        "precipitation_mm": precipitation_mm,
    }


def test_moderate_rain_flags_all_outdoor_and_mixed_places() -> None:
    # 12mm/3h = 4mm/h, at/above the 3mm/h "보통 비" threshold.
    outdoor_place = build_place(id="outdoor-place", area="area-a", setting="outdoor", rain_sensitive_light=False)
    mixed_place = build_place(id="mixed-place", area="area-a", setting="mixed", rain_sensitive_light=False)
    indoor_place = build_place(id="indoor-place", area="area-a", setting="indoor")
    catalog = build_catalog([outdoor_place, mixed_place, indoor_place])
    request = build_request()
    weather_client = FakeWeatherClient([forecast_for(0, condition="rain", precipitation_mm=12.0)])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place, mixed_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.day_number == 1
    assert alert.condition == "rain"
    assert set(alert.affected_place_names) == {outdoor_place.name, mixed_place.name}


def test_light_rain_only_flags_rain_sensitive_light_places() -> None:
    # 3mm/3h = 1mm/h, below the 3mm/h "보통 비" threshold -> "약한 비".
    sensitive_place = build_place(
        id="sensitive-place", area="area-a", setting="outdoor", rain_sensitive_light=True
    )
    ordinary_outdoor_place = build_place(
        id="ordinary-outdoor-place", area="area-a", setting="outdoor", rain_sensitive_light=False
    )
    catalog = build_catalog([sensitive_place, ordinary_outdoor_place])
    request = build_request()
    weather_client = FakeWeatherClient([forecast_for(0, condition="rain", precipitation_mm=3.0)])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [sensitive_place, ordinary_outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert len(alerts) == 1
    assert alerts[0].affected_place_names == [sensitive_place.name]


def test_weather_alerts_empty_when_forecast_client_returns_nothing() -> None:
    # Represents "no API key" / a handled failure - fetch_5day_forecast()
    # itself already returns [] in that case (allow_mock_fallback=False).
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request()
    weather_client = FakeWeatherClient([])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert alerts == []


def test_weather_alerts_empty_when_forecast_client_raises() -> None:
    # Extra safety net: even if the client misbehaves and raises outright
    # (not just returns []), build_weather_alerts must not propagate it.
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request()
    weather_client = FakeWeatherClient(raise_error=True)

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert alerts == []


def test_weather_alerts_empty_when_no_start_date() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(start_date=None)
    weather_client = FakeWeatherClient([forecast_for(0, condition="rain", precipitation_mm=12.0)])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert alerts == []


def test_weather_alerts_skips_days_outside_the_5day_forecast_range() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request(days=3)
    # Only day 1 has a forecast entry; day 3's date (start_date + 2) isn't
    # covered - simulating a trip date past OpenWeatherMap's 5-day limit.
    weather_client = FakeWeatherClient([forecast_for(0, condition="rain", precipitation_mm=12.0)])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place], 3: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert [alert.day_number for alert in alerts] == [1]


def test_clear_or_cloudy_days_produce_no_alert() -> None:
    outdoor_place = build_place(id="outdoor-place", setting="outdoor")
    catalog = build_catalog([outdoor_place])
    request = build_request()
    weather_client = FakeWeatherClient([forecast_for(0, condition="clear", precipitation_mm=0.0)])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert alerts == []


def test_suggested_alternatives_prefer_same_area_and_respect_budget_and_companion_filters() -> None:
    outdoor_place = build_place(id="outdoor-place", area="area-a", setting="outdoor")
    # Matches budget/companion and is in the same area - should be preferred.
    best_match = build_place(
        id="indoor-same-area",
        name="Indoor Same Area",
        area="area-a",
        setting="indoor",
        budget_level=["medium"],
        suitable_for=["friend"],
        priority=5,
    )
    # Matches budget/companion but a different area.
    other_area_match = build_place(
        id="indoor-other-area",
        name="Indoor Other Area",
        area="area-b",
        setting="indoor",
        budget_level=["medium"],
        suitable_for=["friend"],
        priority=9,
    )
    # Same area but doesn't match budget/companion at all.
    unmatched_same_area = build_place(
        id="indoor-unmatched",
        name="Indoor Unmatched",
        area="area-a",
        setting="indoor",
        budget_level=["high"],
        suitable_for=["solo"],
        priority=10,
    )
    catalog = build_catalog([outdoor_place, best_match, other_area_match, unmatched_same_area])
    request = build_request(budget_band="medium", companion_type="friend")
    weather_client = FakeWeatherClient([forecast_for(0, condition="rain", precipitation_mm=12.0)])

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert len(alerts) == 1
    suggestions = alerts[0].suggested_alternatives
    assert suggestions[0] == best_match.name
    assert unmatched_same_area.name not in suggestions
