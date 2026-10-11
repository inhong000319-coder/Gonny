from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.rule_planner.schemas import RuleItineraryRequest
from app.domains.rule_planner.services.reasons import MAX_REASONS_PER_PLACE
from app.domains.rule_planner.services.service import RuleItineraryService


def _build_request(**overrides) -> RuleItineraryRequest:
    data = {
        "city": "seoul",
        "nights": 2,
        "days": 3,
        "travelers": 2,
        "companion_type": "friend",
        "budget_band": "medium",
        "concepts": ["sightseeing", "culture"],
        "style": "easy",
    }
    data.update(overrides)
    return RuleItineraryRequest(**data)


# --- (5) day_summaries covers every day 1..days, including empty ones ------


def test_day_summaries_covers_every_day_including_an_empty_arrival_day() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request(arrival_period="night"))

    assert [summary.day_number for summary in response.day_summaries] == [1, 2, 3]
    day1 = response.day_summaries[0]
    assert day1.place_count == 0
    assert day1.area_count == 0
    assert day1.activity_minutes == 0
    assert day1.travel_minutes is None
    assert day1.travel_is_partial is False

    # Days 2-3 are unrestricted, so they should have real content.
    assert response.day_summaries[1].place_count > 0
    assert response.day_summaries[2].place_count > 0


def test_day_summaries_place_and_area_counts_exclude_meals() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request(include_breakfast=True))

    for summary in response.day_summaries:
        day_items = [item for item in response.items if item.day_number == summary.day_number]
        assert summary.place_count == len(day_items)
        assert summary.area_count == len({item.area for item in day_items})
        # meal_recommendations existing for this day must not have inflated place_count.
        day_meals = [m for m in response.meal_recommendations if m.day_number == summary.day_number]
        if day_meals:
            assert summary.place_count == len(day_items)  # unchanged by meals


# --- (6) travel_is_partial / travel_minutes None handling -------------------


def test_travel_minutes_is_none_exactly_when_no_day_travel_data_exists() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request(arrival_period="night"))

    day_travel_by_day = {dt.day_number: dt for dt in response.day_travel}
    for summary in response.day_summaries:
        travel_entry = day_travel_by_day.get(summary.day_number)
        if travel_entry is None or not travel_entry.legs:
            assert summary.travel_minutes is None
            assert summary.travel_is_partial is False
        else:
            assert summary.travel_minutes is not None
            assert summary.travel_is_partial == (travel_entry.missing_leg_count > 0)


def test_transport_mode_echoes_request_or_none() -> None:
    service = RuleItineraryService()
    modes = ["transit", "car", "transit"]
    response = service.generate(_build_request(transport_by_day=modes))
    assert [summary.transport_mode for summary in response.day_summaries] == modes

    response_unset = service.generate(_build_request())
    assert all(summary.transport_mode is None for summary in response_unset.day_summaries)


def test_travel_minutes_resolves_with_default_mode_when_unset() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request())

    day_travel_by_day = {dt.day_number: dt for dt in response.day_travel}
    for summary in response.day_summaries:
        if summary.transport_mode is not None:
            continue
        travel_entry = day_travel_by_day.get(summary.day_number)
        if travel_entry is not None and travel_entry.legs:
            # Default mode is "transit" (see service._DEFAULT_DAY_SUMMARY_TRANSPORT_MODE).
            assert summary.travel_minutes == travel_entry.transit_total_minutes


# --- reasons wired into generate() end to end -------------------------------


def test_items_and_meals_have_at_most_three_reasons_each() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request(include_breakfast=True))

    for item in response.items:
        assert len(item.reasons) <= MAX_REASONS_PER_PLACE
    for meal in response.meal_recommendations:
        assert len(meal.reasons) <= MAX_REASONS_PER_PLACE


def test_breakfast_reasons_never_mention_opening_hours() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request(nights=9, days=10, include_breakfast=True))

    breakfasts = [meal for meal in response.meal_recommendations if meal.meal_type == "breakfast"]
    assert breakfasts, "expected at least one breakfast recommendation for this fixture"
    for meal in breakfasts:
        assert meal.hours_unverified is True
        for reason in meal.reasons:
            assert "영업" not in reason.label


def test_meal_reasons_use_only_travel_or_time_fit_codes() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request(include_breakfast=True))

    for meal in response.meal_recommendations:
        for reason in meal.reasons:
            assert reason.code in {"near_previous", "time_fit"}


def test_no_reason_label_contains_a_raw_score_number_or_internal_code() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request())

    forbidden_substrings = ["score", "weight", "base_score", "slot_score"]
    for item in response.items:
        for reason in item.reasons:
            for forbidden in forbidden_substrings:
                assert forbidden not in reason.label.lower()
                assert forbidden not in reason.code.lower()


# --- (7) reasons/day_summaries never change item selection or ordering -----


def test_generation_is_deterministic_aside_from_the_new_fields() -> None:
    service = RuleItineraryService()
    request = _build_request(include_breakfast=True, transport_by_day=["transit", "car", "transit"])

    first = service.generate(request).model_dump(mode="json")
    second = service.generate(request).model_dump(mode="json")

    def strip_new_fields(dump: dict) -> dict:
        stripped = dict(dump)
        stripped["items"] = [{k: v for k, v in item.items() if k != "reasons"} for item in stripped["items"]]
        stripped["meal_recommendations"] = [
            {k: v for k, v in meal.items() if k != "reasons"} for meal in stripped["meal_recommendations"]
        ]
        stripped.pop("day_summaries", None)
        return stripped

    assert strip_new_fields(first) == strip_new_fields(second)
    # The new fields themselves must also be deterministic.
    assert first == second
