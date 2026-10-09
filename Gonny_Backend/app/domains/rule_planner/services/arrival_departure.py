"""Day-1 arrival / last-day departure time-of-day -> which activity slots
and meals are usable that day. See RuleItineraryRequest.arrival_period /
departure_period / include_breakfast.

Both rule tables are keyed by the raw request value (None included) so a
caller never has to special-case "no restriction" separately from an
explicit value that happens to mean the same thing (arrival None and
"morning" are the same rule; departure None and "evening_or_later" are the
same rule).
"""

from __future__ import annotations

from typing import NamedTuple

from app.domains.rule_planner.schemas import ArrivalPeriod, DeparturePeriod, TimeSlot

from .constants import TIME_SLOTS

# day_number == 1 (and days == 1, see day_slot_rules).
ARRIVAL_PERIOD_RULES: dict[ArrivalPeriod | None, dict] = {
    None: {"slots": {"morning", "afternoon", "evening"}, "lunch": True, "dinner": True},
    "morning": {"slots": {"morning", "afternoon", "evening"}, "lunch": True, "dinner": True},
    "afternoon": {"slots": {"afternoon", "evening"}, "lunch": False, "dinner": True},
    "evening": {"slots": {"evening"}, "lunch": False, "dinner": True},
    "night": {"slots": set(), "lunch": False, "dinner": False},
}

# day_number == request.days (and days == 1, see day_slot_rules).
DEPARTURE_PERIOD_RULES: dict[DeparturePeriod | None, dict] = {
    None: {"slots": {"morning", "afternoon", "evening"}, "lunch": True, "dinner": True},
    "evening_or_later": {"slots": {"morning", "afternoon", "evening"}, "lunch": True, "dinner": True},
    "afternoon": {"slots": {"morning", "afternoon"}, "lunch": True, "dinner": False},
    "before_lunch": {"slots": {"morning"}, "lunch": False, "dinner": False},
}

_UNRESTRICTED_SLOTS = {"morning", "afternoon", "evening"}


class DaySlotRules(NamedTuple):
    # In TIME_SLOTS order (morning, afternoon, evening), never reordered.
    allowed_slots: list[TimeSlot]
    lunch_allowed: bool
    dinner_allowed: bool
    # True iff "morning" is in allowed_slots - breakfast happens in the
    # morning, so a day with no usable morning slot can never have one,
    # and a day with a usable morning slot always can (independent of
    # whether include_breakfast is even set - that's the caller's job).
    breakfast_allowed: bool


def day_slot_rules(
    *,
    arrival_period: ArrivalPeriod | None,
    departure_period: DeparturePeriod | None,
    days: int,
    day_number: int,
) -> DaySlotRules:
    is_first = day_number == 1
    is_last = day_number == days

    if is_first and is_last:
        arrival = ARRIVAL_PERIOD_RULES[arrival_period]
        departure = DEPARTURE_PERIOD_RULES[departure_period]
        slots = arrival["slots"] & departure["slots"]
        lunch = arrival["lunch"] and departure["lunch"]
        dinner = arrival["dinner"] and departure["dinner"]
    elif is_first:
        rule = ARRIVAL_PERIOD_RULES[arrival_period]
        slots, lunch, dinner = rule["slots"], rule["lunch"], rule["dinner"]
    elif is_last:
        rule = DEPARTURE_PERIOD_RULES[departure_period]
        slots, lunch, dinner = rule["slots"], rule["lunch"], rule["dinner"]
    else:
        slots, lunch, dinner = _UNRESTRICTED_SLOTS, True, True

    ordered_slots = [slot for slot in TIME_SLOTS if slot in slots]
    return DaySlotRules(
        allowed_slots=ordered_slots,
        lunch_allowed=lunch,
        dinner_allowed=dinner,
        breakfast_allowed="morning" in slots,
    )


def has_any_usable_slot(
    *,
    arrival_period: ArrivalPeriod | None,
    departure_period: DeparturePeriod | None,
    days: int,
) -> bool:
    """False means the whole trip has not one single usable activity
    slot on any day (e.g. a 1-day trip with arrival_period="night") -
    callers should reject the request rather than generate an empty
    itinerary."""
    return any(
        day_slot_rules(
            arrival_period=arrival_period,
            departure_period=departure_period,
            days=days,
            day_number=day_number,
        ).allowed_slots
        for day_number in range(1, days + 1)
    )
