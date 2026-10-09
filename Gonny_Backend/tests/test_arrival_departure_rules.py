from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app.domains.rule_planner.services.arrival_departure import day_slot_rules, has_any_usable_slot

FULL = ["morning", "afternoon", "evening"]


# --- arrival_period (day_number == 1, days > 1) -----------------------------


@pytest.mark.parametrize(
    "arrival_period,expected_slots,expected_lunch,expected_dinner",
    [
        (None, FULL, True, True),
        ("morning", FULL, True, True),
        ("afternoon", ["afternoon", "evening"], False, True),
        ("evening", ["evening"], False, True),
        ("night", [], False, False),
    ],
)
def test_arrival_period_rules_for_day_one(arrival_period, expected_slots, expected_lunch, expected_dinner) -> None:
    rules = day_slot_rules(arrival_period=arrival_period, departure_period=None, days=3, day_number=1)

    assert rules.allowed_slots == expected_slots
    assert rules.lunch_allowed is expected_lunch
    assert rules.dinner_allowed is expected_dinner
    assert rules.breakfast_allowed == ("morning" in expected_slots)


# --- departure_period (day_number == days, days > 1) ------------------------


@pytest.mark.parametrize(
    "departure_period,expected_slots,expected_lunch,expected_dinner",
    [
        (None, FULL, True, True),
        ("evening_or_later", FULL, True, True),
        ("afternoon", ["morning", "afternoon"], True, False),
        ("before_lunch", ["morning"], False, False),
    ],
)
def test_departure_period_rules_for_last_day(
    departure_period, expected_slots, expected_lunch, expected_dinner
) -> None:
    rules = day_slot_rules(arrival_period=None, departure_period=departure_period, days=3, day_number=3)

    assert rules.allowed_slots == expected_slots
    assert rules.lunch_allowed is expected_lunch
    assert rules.dinner_allowed is expected_dinner
    assert rules.breakfast_allowed == ("morning" in expected_slots)


# --- middle days are always unrestricted -------------------------------------


@pytest.mark.parametrize("day_number", [2, 3])
def test_middle_days_are_never_restricted_by_arrival_or_departure(day_number) -> None:
    rules = day_slot_rules(
        arrival_period="night",
        departure_period="before_lunch",
        days=4,
        day_number=day_number,
    )

    assert rules.allowed_slots == FULL
    assert rules.lunch_allowed is True
    assert rules.dinner_allowed is True
    assert rules.breakfast_allowed is True


# --- days == 1 applies both rules, intersected -------------------------------


def test_single_day_trip_intersects_arrival_and_departure_slots() -> None:
    rules = day_slot_rules(arrival_period="afternoon", departure_period="afternoon", days=1, day_number=1)

    # arrival=afternoon -> {afternoon, evening}; departure=afternoon -> {morning, afternoon}
    assert rules.allowed_slots == ["afternoon"]
    # lunch: arrival(False) and departure(True) -> False
    assert rules.lunch_allowed is False
    # dinner: arrival(True) and departure(False) -> False
    assert rules.dinner_allowed is False
    assert rules.breakfast_allowed is False


def test_single_day_trip_with_before_lunch_departure_still_allows_breakfast() -> None:
    # Explicitly called out in the spec: before_lunch has no lunch/dinner,
    # but still "아침 가능" because morning is still a usable slot.
    rules = day_slot_rules(arrival_period=None, departure_period="before_lunch", days=1, day_number=1)

    assert rules.allowed_slots == ["morning"]
    assert rules.lunch_allowed is False
    assert rules.dinner_allowed is False
    assert rules.breakfast_allowed is True


def test_single_day_trip_with_incompatible_periods_has_no_usable_slot() -> None:
    rules = day_slot_rules(arrival_period="evening", departure_period="before_lunch", days=1, day_number=1)

    assert rules.allowed_slots == []
    assert rules.breakfast_allowed is False


# --- has_any_usable_slot ------------------------------------------------------


def test_has_any_usable_slot_false_for_single_day_night_arrival() -> None:
    assert has_any_usable_slot(arrival_period="night", departure_period=None, days=1) is False


def test_has_any_usable_slot_true_when_only_day_one_is_restricted_on_a_longer_trip() -> None:
    # day 1 has nothing, but days 2-3 are unrestricted middle/departure days.
    assert has_any_usable_slot(arrival_period="night", departure_period=None, days=3) is True


def test_has_any_usable_slot_true_by_default() -> None:
    assert has_any_usable_slot(arrival_period=None, departure_period=None, days=1) is True
