from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException

from app.domains.rule_planner.schemas import (
    RuleDaySummary,
    RuleItineraryItem,
    RuleItineraryRequest,
    RuleItineraryResponse,
    RuleMealRecommendation,
)
from app.domains.rule_planner.services.compare_transport import (
    build_comparison,
    build_scenario_totals,
    build_transport_comparison,
    compare_days,
    count_meal_changed_days,
    scenarios_to_compare,
)
from app.domains.rule_planner.services.request_normalizer import normalize_rule_request
from app.domains.rule_planner.services.service import RuleItineraryService


class CountingFakeWeatherClient:
    """Same pattern as tests/test_weather_status.py's fake - counts calls
    without touching the network, so tests can assert it's never invoked."""

    def __init__(self):
        self.call_count = 0

    def fetch_5day_forecast(self, destination: str, *, allow_mock_fallback: bool = True) -> list[dict]:
        self.call_count += 1
        return []


def build_item(**overrides) -> RuleItineraryItem:
    data = {
        "day_number": 1,
        "time_slot": "morning",
        "place_name": "A",
        "category": "sightseeing",
        "area": "gangnam",
        "notes": "note",
    }
    data.update(overrides)
    return RuleItineraryItem.model_validate(data)


def build_meal(**overrides) -> RuleMealRecommendation:
    data = {
        "day_number": 1,
        "meal_type": "lunch",
        "place_name": "Food A",
        "area": "gangnam",
        "notes": "note",
    }
    data.update(overrides)
    return RuleMealRecommendation.model_validate(data)


def build_day_summary(**overrides) -> RuleDaySummary:
    data = {
        "day_number": 1,
        "place_count": 1,
        "area_count": 1,
        "activity_minutes": 120,
        "travel_minutes": 30,
        "travel_is_partial": False,
        "transport_mode": "transit",
    }
    data.update(overrides)
    return RuleDaySummary.model_validate(data)


def build_response(**overrides) -> RuleItineraryResponse:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "seoul",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
        "companion_type": "friend",
        "items": [],
        "transport_by_day": ["transit", "transit", "transit"],
        "day_summaries": [],
    }
    data.update(overrides)
    return RuleItineraryResponse.model_validate(data)


def build_request(**overrides) -> RuleItineraryRequest:
    data = {
        "city": "seoul",
        "nights": 2,
        "days": 3,
        "travelers": 2,
        "companion_type": "friend",
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
    }
    data.update(overrides)
    return RuleItineraryRequest(**data)


# --- (1) scenario inclusion/exclusion ---------------------------------------


def test_all_transit_current_only_returns_all_car() -> None:
    scenarios = scenarios_to_compare(["transit", "transit", "transit"], 3)
    assert scenarios == ["all_car"]


def test_all_car_current_only_returns_all_transit() -> None:
    scenarios = scenarios_to_compare(["car", "car", "car"], 3)
    assert scenarios == ["all_transit"]


def test_mixed_current_returns_both_scenarios() -> None:
    scenarios = scenarios_to_compare(["transit", "car", "transit"], 3)
    assert scenarios == ["all_transit", "all_car"]


def test_unset_current_returns_both_scenarios() -> None:
    scenarios = scenarios_to_compare(None, 3)
    assert scenarios == ["all_transit", "all_car"]


# --- (2) base/scenario totals match day_summaries ---------------------------


def test_scenario_totals_sum_day_summaries_travel_minutes() -> None:
    response = build_response(
        day_summaries=[
            build_day_summary(day_number=1, travel_minutes=10, travel_is_partial=False),
            build_day_summary(day_number=2, travel_minutes=20, travel_is_partial=True),
            build_day_summary(day_number=3, travel_minutes=30, travel_is_partial=False),
        ]
    )
    totals = build_scenario_totals(response)
    assert totals.total_travel_minutes == 60
    assert totals.any_partial is True
    assert totals.transport_by_day == response.transport_by_day


# --- (4) None propagation ----------------------------------------------------


def test_total_is_none_when_any_day_travel_minutes_is_none() -> None:
    response = build_response(
        day_summaries=[
            build_day_summary(day_number=1, travel_minutes=10),
            build_day_summary(day_number=2, travel_minutes=None),
        ]
    )
    totals = build_scenario_totals(response)
    assert totals.total_travel_minutes is None


def test_delta_is_none_when_either_side_total_is_none() -> None:
    base = build_response(day_summaries=[build_day_summary(day_number=1, travel_minutes=None)])
    scenario = build_response(day_summaries=[build_day_summary(day_number=1, travel_minutes=50)])

    comparison = build_comparison("all_car", base=base, scenario_response=scenario)
    assert comparison.travel_minutes_delta is None

    base2 = build_response(day_summaries=[build_day_summary(day_number=1, travel_minutes=50)])
    comparison2 = build_comparison(
        "all_car",
        base=base2,
        scenario_response=build_response(day_summaries=[build_day_summary(day_number=1, travel_minutes=None)]),
    )
    assert comparison2.travel_minutes_delta is None


def test_delta_is_computed_when_both_sides_known() -> None:
    base = build_response(day_summaries=[build_day_summary(day_number=1, travel_minutes=50)])
    scenario = build_response(day_summaries=[build_day_summary(day_number=1, travel_minutes=30)])
    comparison = build_comparison("all_car", base=base, scenario_response=scenario)
    assert comparison.travel_minutes_delta == -20


# --- (3) same_places / only_in_base / only_in_scenario ----------------------


def test_same_places_true_when_every_day_slot_place_matches() -> None:
    base = build_response(
        items=[build_item(day_number=1, time_slot="morning", place_name="A")],
        day_summaries=[build_day_summary(day_number=1)],
    )
    scenario = build_response(
        items=[build_item(day_number=1, time_slot="morning", place_name="A")],
        day_summaries=[build_day_summary(day_number=1)],
    )
    days = compare_days(base, scenario)
    assert len(days) == 1
    assert days[0].only_in_base == []
    assert days[0].only_in_scenario == []
    comparison = build_comparison("all_car", base=base, scenario_response=scenario)
    assert comparison.same_places is True


def test_only_in_base_and_only_in_scenario_reflect_actual_item_diff() -> None:
    base = build_response(
        items=[
            build_item(day_number=1, time_slot="morning", place_name="A"),
            build_item(day_number=1, time_slot="afternoon", place_name="B"),
        ],
        day_summaries=[build_day_summary(day_number=1)],
    )
    scenario = build_response(
        items=[
            build_item(day_number=1, time_slot="morning", place_name="A"),
            build_item(day_number=1, time_slot="afternoon", place_name="C"),
        ],
        day_summaries=[build_day_summary(day_number=1)],
    )
    days = compare_days(base, scenario)
    assert days[0].only_in_base == ["B"]
    assert days[0].only_in_scenario == ["C"]
    comparison = build_comparison("all_car", base=base, scenario_response=scenario)
    assert comparison.same_places is False


def test_same_place_name_in_a_different_slot_counts_as_a_difference() -> None:
    # Identity key is (time_slot, place_name) per day - a place that moved
    # slots is still a change, not "unchanged".
    base = build_response(
        items=[build_item(day_number=1, time_slot="morning", place_name="A")],
        day_summaries=[build_day_summary(day_number=1)],
    )
    scenario = build_response(
        items=[build_item(day_number=1, time_slot="afternoon", place_name="A")],
        day_summaries=[build_day_summary(day_number=1)],
    )
    days = compare_days(base, scenario)
    assert days[0].only_in_base == ["A"]
    assert days[0].only_in_scenario == ["A"]


def test_meal_changes_counts_days_not_individual_meals() -> None:
    base = build_response(
        meal_recommendations=[
            build_meal(day_number=1, meal_type="lunch", place_name="L1"),
            build_meal(day_number=1, meal_type="dinner", place_name="D1"),
            build_meal(day_number=2, meal_type="lunch", place_name="L2"),
        ],
        day_summaries=[build_day_summary(day_number=1), build_day_summary(day_number=2)],
    )
    scenario = build_response(
        meal_recommendations=[
            build_meal(day_number=1, meal_type="lunch", place_name="L1-changed"),
            build_meal(day_number=1, meal_type="dinner", place_name="D1-changed"),
            build_meal(day_number=2, meal_type="lunch", place_name="L2"),
        ],
        day_summaries=[build_day_summary(day_number=1), build_day_summary(day_number=2)],
    )
    # Day 1 has 2 changed meals but should count as 1 changed day; day 2 unchanged.
    assert count_meal_changed_days(base, scenario) == 1


def test_meal_appearing_only_on_one_side_counts_as_changed() -> None:
    base = build_response(
        meal_recommendations=[build_meal(day_number=1, meal_type="breakfast", place_name="B1")],
        day_summaries=[build_day_summary(day_number=1)],
    )
    scenario = build_response(meal_recommendations=[], day_summaries=[build_day_summary(day_number=1)])
    assert count_meal_changed_days(base, scenario) == 1


# --- build_transport_comparison orchestration (fake generate) --------------


def test_build_transport_comparison_calls_generate_once_per_included_scenario() -> None:
    call_log: list[list[str] | None] = []

    def fake_generate(request: RuleItineraryRequest) -> RuleItineraryResponse:
        call_log.append(request.transport_by_day)
        days = request.days or 3
        mode_list = request.transport_by_day or ["transit"] * days
        return build_response(
            days=days,
            transport_by_day=request.transport_by_day,
            day_summaries=[
                build_day_summary(day_number=i + 1, transport_mode=mode_list[i], travel_minutes=10 * (i + 1))
                for i in range(days)
            ],
        )

    request = build_request(transport_by_day=["transit", "car", "transit"], days=3, nights=2)
    result = build_transport_comparison(request, generate=fake_generate)

    # base + all_transit + all_car = 3 calls.
    assert len(call_log) == 3
    assert call_log[0] == ["transit", "car", "transit"]
    assert {tuple(c) for c in call_log[1:]} == {("transit", "transit", "transit"), ("car", "car", "car")}
    assert {c.scenario for c in result.comparisons} == {"all_transit", "all_car"}


def test_build_transport_comparison_excludes_scenario_matching_current() -> None:
    def fake_generate(request: RuleItineraryRequest) -> RuleItineraryResponse:
        days = request.days or 3
        return build_response(
            days=days,
            transport_by_day=request.transport_by_day,
            day_summaries=[build_day_summary(day_number=i + 1) for i in range(days)],
        )

    request = build_request(transport_by_day=["transit", "transit", "transit"], days=3, nights=2)
    result = build_transport_comparison(request, generate=fake_generate)

    assert [c.scenario for c in result.comparisons] == ["all_car"]


# --- (5) validation errors pass through unchanged ---------------------------


def test_transport_by_day_length_mismatch_raises_422() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, transport_by_day=["transit", "car"])
    with pytest.raises(HTTPException) as excinfo:
        normalize_rule_request(request)
    assert excinfo.value.status_code == 422


def test_compare_transport_endpoint_rejects_bad_transport_by_day_length() -> None:
    service = RuleItineraryService(weather_client=CountingFakeWeatherClient())
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, transport_by_day=["transit", "car"])
    with pytest.raises(HTTPException) as excinfo:
        service.compare_transport(request)
    assert excinfo.value.status_code == 422


def test_compare_transport_endpoint_rejects_impossible_arrival_period() -> None:
    service = RuleItineraryService(weather_client=CountingFakeWeatherClient())
    request = RuleItineraryRequest(city="seoul", days=1, arrival_period="night")
    with pytest.raises(HTTPException) as excinfo:
        service.compare_transport(request)
    assert excinfo.value.status_code == 422


# --- (6) weather client is never called -------------------------------------


def test_compare_transport_never_calls_the_weather_client() -> None:
    fake_weather = CountingFakeWeatherClient()
    service = RuleItineraryService(weather_client=fake_weather)
    request = build_request(transport_by_day=["transit", "car", "transit"])

    result = service.compare_transport(request)

    assert fake_weather.call_count == 0
    assert len(result.comparisons) == 2  # mixed current -> both scenarios


def test_compare_transport_response_never_exposes_weather_fields() -> None:
    # The comparison response schema itself has no weather_alerts/
    # weather_status fields - a structural guarantee, not just "empty".
    from app.domains.rule_planner.schemas import RuleTransportComparisonResponse

    assert "weather_alerts" not in RuleTransportComparisonResponse.model_fields
    assert "weather_status" not in RuleTransportComparisonResponse.model_fields


# --- (7) determinism ---------------------------------------------------------


def test_compare_transport_is_deterministic() -> None:
    service = RuleItineraryService(weather_client=CountingFakeWeatherClient())
    request = build_request(transport_by_day=["transit", "car", "transit"])

    first = service.compare_transport(request)
    second = service.compare_transport(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


# --- end-to-end sanity against real generate() -------------------------------


def test_end_to_end_totals_match_independent_generate_calls() -> None:
    service = RuleItineraryService(weather_client=CountingFakeWeatherClient())
    request = build_request(city="seoul", nights=2, days=3, transport_by_day=["transit", "car", "transit"])

    comparison = service.compare_transport(request)

    base_response = service.generate(request, include_weather=False)
    expected_base_total = sum(s.travel_minutes for s in base_response.day_summaries if s.travel_minutes is not None)
    if any(s.travel_minutes is None for s in base_response.day_summaries):
        assert comparison.base.total_travel_minutes is None
    else:
        assert comparison.base.total_travel_minutes == expected_base_total

    all_transit_request = build_request(city="seoul", nights=2, days=3, transport_by_day=["transit"] * 3)
    all_transit_response = service.generate(all_transit_request, include_weather=False)
    all_transit_comparison = next(c for c in comparison.comparisons if c.scenario == "all_transit")
    if any(s.travel_minutes is None for s in all_transit_response.day_summaries):
        assert all_transit_comparison.total_travel_minutes is None
    else:
        assert all_transit_comparison.total_travel_minutes == sum(
            s.travel_minutes for s in all_transit_response.day_summaries
        )
