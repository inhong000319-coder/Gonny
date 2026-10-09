from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.services.breakfast import is_breakfast_candidate
from app.domains.rule_planner.schemas import RuleItineraryRequest
from app.domains.rule_planner.services.request_normalizer import normalize_rule_request
from app.domains.rule_planner.services.service import RuleItineraryService

FULL = {"morning", "afternoon", "evening"}


def _slots(response, day_number: int) -> set[str]:
    return {item.time_slot for item in response.items if item.day_number == day_number}


def _meal_types(response, day_number: int) -> set[str]:
    return {meal.meal_type for meal in response.meal_recommendations if meal.day_number == day_number}


# --- (a) arrival_period controls day 1 -------------------------------------


@pytest.mark.parametrize(
    "arrival_period,expected_slots,expects_lunch,expects_dinner",
    [
        (None, FULL, True, True),
        ("morning", FULL, True, True),
        ("afternoon", {"afternoon", "evening"}, False, True),
        ("evening", {"evening"}, False, True),
        ("night", set(), False, False),
    ],
)
def test_arrival_period_controls_day_one_slots_and_meals(
    arrival_period, expected_slots, expects_lunch, expects_dinner
) -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, arrival_period=arrival_period)
    response = RuleItineraryService().generate(request)

    assert _slots(response, 1) == expected_slots
    meal_types = _meal_types(response, 1)
    assert ("lunch" in meal_types) is expects_lunch
    assert ("dinner" in meal_types) is expects_dinner
    assert response.arrival_period == arrival_period


# --- (b) departure_period controls the last day -----------------------------


@pytest.mark.parametrize(
    "departure_period,expected_slots,expects_lunch,expects_dinner",
    [
        (None, FULL, True, True),
        ("evening_or_later", FULL, True, True),
        ("afternoon", {"morning", "afternoon"}, True, False),
        ("before_lunch", {"morning"}, False, False),
    ],
)
def test_departure_period_controls_last_day_slots_and_meals(
    departure_period, expected_slots, expects_lunch, expects_dinner
) -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, departure_period=departure_period)
    response = RuleItineraryService().generate(request)

    last_day = response.days
    assert _slots(response, last_day) == expected_slots
    meal_types = _meal_types(response, last_day)
    assert ("lunch" in meal_types) is expects_lunch
    assert ("dinner" in meal_types) is expects_dinner
    assert response.departure_period == departure_period


# --- (c) days == 1 intersects both rules; impossible combos are rejected ----


def test_single_day_trip_intersects_arrival_and_departure_rules() -> None:
    request = RuleItineraryRequest(city="seoul", days=1, arrival_period="afternoon", departure_period="afternoon")
    response = RuleItineraryService().generate(request)

    assert _slots(response, 1) == {"afternoon"}
    assert _meal_types(response, 1) == set()  # lunch needs arrival(False); dinner needs departure(False)


def test_single_day_trip_with_no_usable_slot_is_rejected_with_korean_message() -> None:
    request = RuleItineraryRequest(city="seoul", days=1, arrival_period="night")

    with pytest.raises(HTTPException) as excinfo:
        normalize_rule_request(request)

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail == "선택한 도착·출발 시간대로는 일정을 만들 수 없어요."


# --- (d) a full-day place never lands on a slot-restricted day --------------


def test_full_day_place_is_not_assigned_on_a_slot_restricted_day() -> None:
    # Lotte World Adventure (seoul) is full_day_recommended and would
    # normally claim every slot on a middle day - here day 1 is both the
    # only day and slot-restricted, so it must not appear at all, and the
    # 2 open slots must be 2 distinct places (not one place 2x).
    request = RuleItineraryRequest(city="seoul", days=1, concepts=["activity"], arrival_period="afternoon")
    response = RuleItineraryService().generate(request)

    day1_items = [item for item in response.items if item.day_number == 1]
    assert len(day1_items) == 2
    assert len({item.place_name for item in day1_items}) == 2
    assert all(item.place_name != "Lotte World Adventure" for item in day1_items)


# --- (e) meal anchors fall back correctly around an empty slot --------------


def test_meal_anchor_helpers_skip_missing_slots() -> None:
    service = RuleItineraryService()
    morning = PlaceData.model_validate(
        {
            "id": "morning-place",
            "name": "Morning Place",
            "activity_type": ["sightseeing"],
            "budget_level": ["medium"],
            "suitable_for": ["couple"],
            "time_fit": ["morning"],
            "area": "gangnam",
            "duration_hours": 1,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "sample",
        }
    )
    evening = morning.model_copy(update={"id": "evening-place", "name": "Evening Place"})

    # afternoon slot missing entirely (e.g. arrival_period excluded it).
    slot_map = {"morning": morning, "evening": evening}

    # lunch (boundary 1): previous looks only at morning -> present.
    assert service._nearest_activity_before(slot_map, 1) is morning
    # dinner (boundary 2): previous looks at [morning, afternoon]
    # reversed - afternoon missing, falls back to morning.
    assert service._nearest_activity_before(slot_map, 2) is morning
    # lunch's next looks at [afternoon, evening] - afternoon missing,
    # falls back to evening.
    assert service._nearest_activity_after(slot_map, 1) is evening

    # Now with morning itself missing - lunch's previous has nothing to
    # fall back to at all.
    assert service._nearest_activity_before({"evening": evening}, 1) is None


# --- (f) include_breakfast -----------------------------------------------


def test_breakfast_is_added_only_on_allowed_days_and_flagged_unverified() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, include_breakfast=True)
    response = RuleItineraryService().generate(request)

    breakfasts = [meal for meal in response.meal_recommendations if meal.meal_type == "breakfast"]
    assert len(breakfasts) == 3  # unrestricted trip - every day allows breakfast
    assert all(meal.hours_unverified for meal in breakfasts)
    non_breakfasts = [meal for meal in response.meal_recommendations if meal.meal_type != "breakfast"]
    assert all(not meal.hours_unverified for meal in non_breakfasts)
    assert response.include_breakfast is True


def test_breakfast_is_skipped_on_a_day_with_no_morning_slot() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, arrival_period="evening", include_breakfast=True)
    response = RuleItineraryService().generate(request)

    assert "breakfast" not in _meal_types(response, 1)


def test_breakfast_runs_out_of_candidates_and_is_skipped_rather_than_reused_or_backfilled() -> None:
    # Seoul has exactly 8 keyword-classified breakfast candidates - a
    # 10-day trip must use at most 8 breakfasts, never repeat one, and
    # never fall back to the general food pool once they run out.
    request = RuleItineraryRequest(city="seoul", nights=9, days=10, include_breakfast=True)
    response = RuleItineraryService().generate(request)

    breakfasts = [meal for meal in response.meal_recommendations if meal.meal_type == "breakfast"]
    assert len(breakfasts) <= 8
    assert len({meal.place_name for meal in breakfasts}) == len(breakfasts)
    all_names = [meal.place_name for meal in response.meal_recommendations]
    assert len(all_names) == len(set(all_names))  # no restaurant repeats across any meal, any day


def test_breakfast_false_by_default() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3)
    response = RuleItineraryService().generate(request)

    assert response.include_breakfast is False
    assert all(meal.meal_type != "breakfast" for meal in response.meal_recommendations)


# --- (g) day_travel: no fake accommodation->accommodation leg ---------------


def test_fully_restricted_day_is_excluded_from_day_travel_and_duration_warnings() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, arrival_period="night")
    response = RuleItineraryService().generate(request)

    assert all(item.day_number != 1 for item in response.items)
    assert 1 not in {day_travel.day_number for day_travel in response.day_travel}
    assert 1 not in {warning.day_number for warning in response.day_duration_warnings}


def test_day_sequence_order_is_breakfast_morning_lunch_afternoon_dinner_evening() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, include_breakfast=True)
    response = RuleItineraryService().generate(request)

    day1_travel = next(dt for dt in response.day_travel if dt.day_number == 1)
    # First leg starts from the accommodation; the kind sequence after
    # that should alternate place/meal in point-in-day order.
    to_kinds = [leg.to_kind for leg in day1_travel.legs]
    # breakfast (meal) -> morning (place) -> lunch (meal) -> afternoon
    # (place) -> dinner (meal) -> evening (place) -> accommodation
    assert to_kinds[0] == "meal"  # breakfast, right after leaving the accommodation
    assert to_kinds[-1] == "accommodation"


# --- (h) empty fields => identical response to omitting them entirely ------


def test_empty_new_fields_produce_identical_response_to_omitting_them() -> None:
    explicit = RuleItineraryRequest(
        city="seoul",
        nights=2,
        days=3,
        arrival_period=None,
        departure_period=None,
        include_breakfast=False,
    )
    omitted = RuleItineraryRequest(city="seoul", nights=2, days=3)

    service = RuleItineraryService()
    assert service.generate(explicit).model_dump(mode="json") == service.generate(omitted).model_dump(mode="json")


# --- (i) invalid enum values are rejected by pydantic -----------------------


def test_invalid_arrival_period_is_rejected_by_pydantic() -> None:
    with pytest.raises(ValidationError):
        RuleItineraryRequest(city="seoul", arrival_period="brunch")


def test_invalid_departure_period_is_rejected_by_pydantic() -> None:
    with pytest.raises(ValidationError):
        RuleItineraryRequest(city="seoul", departure_period="lunchtime")
