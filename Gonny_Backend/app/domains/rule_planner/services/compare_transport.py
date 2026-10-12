"""Compares a trip's actual itinerary against "what if every day used
transit/car instead" scenarios - see RuleItineraryResponse's sibling
endpoint POST /rule-itinerary/compare-transport.

Deliberately does not touch the catalog, scoring, or place-selection code
at all: every number here comes from re-running RuleItineraryService.generate()
per scenario (injected as `generate`, so this module has no DB/catalog
dependency of its own) and reading its already-computed RuleDaySummary/
RuleItineraryItem/RuleMealRecommendation - no place-selection logic is
duplicated or re-derived here.
"""

from __future__ import annotations

from typing import Callable

from app.domains.rule_planner.schemas import (
    DayTransportMode,
    RuleDaySummary,
    RuleItineraryRequest,
    RuleItineraryResponse,
    RuleTransportComparison,
    RuleTransportComparisonDay,
    RuleTransportComparisonResponse,
    RuleTransportScenarioTotals,
    TransportComparisonScenario,
)

SCENARIO_MODES: dict[TransportComparisonScenario, DayTransportMode] = {
    "all_transit": "transit",
    "all_car": "car",
}

# 가정값: 하루라도 travel_minutes가 None(이동시간 데이터 자체가 없음)이면
# 전체 합계도 None으로 처리한다. 일부만 더해서 "전체 합계"라고 보여주면
# 실제보다 적게 걸리는 것처럼 보일 수 있어, 부분 합산 대신 통째로 모른다고
# 표시하는 쪽을 택했다 - RuleDaySummary.travel_is_partial(하루 안에서 일부
# 구간만 빠진 경우)과는 별개의 기준이다.
def _total_travel_minutes(day_summaries: list[RuleDaySummary]) -> int | None:
    minutes = [summary.travel_minutes for summary in day_summaries]
    if any(value is None for value in minutes):
        return None
    return sum(minutes)


def _any_partial(day_summaries: list[RuleDaySummary]) -> bool:
    return any(summary.travel_is_partial for summary in day_summaries)


def scenarios_to_compare(
    current_transport_by_day: list[DayTransportMode] | None,
    days: int,
) -> list[TransportComparisonScenario]:
    """Every scenario whose uniform mode list isn't already exactly what
    the request used. current_transport_by_day=None (no explicit per-day
    mode in the request) never equals either uniform list, so both
    scenarios are kept in that case - see the compare-transport endpoint's
    docstring."""
    scenarios: list[TransportComparisonScenario] = []
    for scenario, mode in SCENARIO_MODES.items():
        uniform = [mode] * days
        if current_transport_by_day == uniform:
            continue
        scenarios.append(scenario)
    return scenarios


def build_scenario_totals(response: RuleItineraryResponse) -> RuleTransportScenarioTotals:
    return RuleTransportScenarioTotals(
        transport_by_day=response.transport_by_day,
        total_travel_minutes=_total_travel_minutes(response.day_summaries),
        any_partial=_any_partial(response.day_summaries),
    )


def _item_slots_by_day(response: RuleItineraryResponse) -> dict[int, set[tuple[str, str]]]:
    """(time_slot, place_name) pairs per day - the identity key the spec
    calls for ("장소 id/이름 + 날짜 + 슬롯"). RuleItineraryItem carries no
    catalog place id, so place_name is the "id/이름" half of that key."""
    by_day: dict[int, set[tuple[str, str]]] = {}
    for item in response.items:
        by_day.setdefault(item.day_number, set()).add((item.time_slot, item.place_name))
    return by_day


def _meal_place_by_day_and_type(response: RuleItineraryResponse) -> dict[tuple[int, str], str]:
    return {(meal.day_number, meal.meal_type): meal.place_name for meal in response.meal_recommendations}


def compare_days(
    base: RuleItineraryResponse, scenario: RuleItineraryResponse
) -> list[RuleTransportComparisonDay]:
    base_summaries = {summary.day_number: summary for summary in base.day_summaries}
    scenario_summaries = {summary.day_number: summary for summary in scenario.day_summaries}
    base_slots = _item_slots_by_day(base)
    scenario_slots = _item_slots_by_day(scenario)

    days: list[RuleTransportComparisonDay] = []
    for day_number in sorted(set(base_summaries) | set(scenario_summaries)):
        base_summary = base_summaries.get(day_number)
        scenario_summary = scenario_summaries.get(day_number)
        base_day_slots = base_slots.get(day_number, set())
        scenario_day_slots = scenario_slots.get(day_number, set())

        days.append(
            RuleTransportComparisonDay(
                day_number=day_number,
                base_mode=base_summary.transport_mode if base_summary else None,
                scenario_mode=scenario_summary.transport_mode if scenario_summary else None,
                base_travel_minutes=base_summary.travel_minutes if base_summary else None,
                scenario_travel_minutes=scenario_summary.travel_minutes if scenario_summary else None,
                base_partial=base_summary.travel_is_partial if base_summary else False,
                scenario_partial=scenario_summary.travel_is_partial if scenario_summary else False,
                only_in_base=sorted(name for _slot, name in base_day_slots - scenario_day_slots),
                only_in_scenario=sorted(name for _slot, name in scenario_day_slots - base_day_slots),
            )
        )
    return days


def count_meal_changed_days(base: RuleItineraryResponse, scenario: RuleItineraryResponse) -> int:
    base_meals = _meal_place_by_day_and_type(base)
    scenario_meals = _meal_place_by_day_and_type(scenario)
    changed_days = {
        day_number
        for day_number, _meal_type in set(base_meals) | set(scenario_meals)
        if base_meals.get((day_number, _meal_type)) != scenario_meals.get((day_number, _meal_type))
    }
    return len(changed_days)


def build_comparison(
    scenario_name: TransportComparisonScenario,
    *,
    base: RuleItineraryResponse,
    scenario_response: RuleItineraryResponse,
) -> RuleTransportComparison:
    mode = SCENARIO_MODES[scenario_name]
    days = compare_days(base, scenario_response)
    same_places = all(not day.only_in_base and not day.only_in_scenario for day in days)
    base_total = _total_travel_minutes(base.day_summaries)
    scenario_total = _total_travel_minutes(scenario_response.day_summaries)
    delta = scenario_total - base_total if base_total is not None and scenario_total is not None else None

    return RuleTransportComparison(
        scenario=scenario_name,
        transport_by_day=[mode] * scenario_response.days,
        total_travel_minutes=scenario_total,
        any_partial=_any_partial(scenario_response.day_summaries),
        travel_minutes_delta=delta,
        same_places=same_places,
        days=days,
        meal_changes=count_meal_changed_days(base, scenario_response),
    )


def build_transport_comparison(
    request: RuleItineraryRequest,
    *,
    generate: Callable[[RuleItineraryRequest], RuleItineraryResponse],
) -> RuleTransportComparisonResponse:
    """generate is injected (rather than importing RuleItineraryService
    here) so this module stays a pure function of its inputs - easy to
    unit test with a fake generate(), and so the only place that decides
    "skip the weather lookup for scenario re-runs" is the caller
    (RuleItineraryService.compare_transport), not this module."""
    base_response = generate(request)
    scenarios = scenarios_to_compare(base_response.transport_by_day, base_response.days)

    comparisons: list[RuleTransportComparison] = []
    for scenario_name in scenarios:
        mode = SCENARIO_MODES[scenario_name]
        scenario_request = request.model_copy(update={"transport_by_day": [mode] * base_response.days})
        scenario_response = generate(scenario_request)
        comparisons.append(
            build_comparison(scenario_name, base=base_response, scenario_response=scenario_response)
        )

    return RuleTransportComparisonResponse(
        base=build_scenario_totals(base_response),
        comparisons=comparisons,
    )
