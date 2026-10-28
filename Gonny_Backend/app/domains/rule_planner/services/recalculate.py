"""Validation for POST /rule-itinerary/recalculate's fixed_slots - turns
the request's flat list of (day_number, time_slot, place_id) pins into the
dict[(day_number, time_slot), PlaceData] shape RuleItineraryService.
_build_items's fixed_slots parameter expects, raising HTTPException(422)
on the first rule violated. See RuleItineraryService.recalculate.

Every check here is a *structural* validation of the user's pinning
itself (does this place exist / fit this slot structurally / repeat in a
way that's never allowed) - it never re-scores or second-guesses whether
a pinned place is a *good* choice. That's deliberate: recalculate's whole
point is to accept the caller's placement as given.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleFixedSlotAssignment

from .arrival_departure import day_slot_rules
from .closed_days import is_confirmed_closed_on


def _day_weekday(request: NormalizedRuleRequest, day_number: int) -> int | None:
    """Mirrors RuleItineraryService._day_weekday exactly - duplicated
    rather than imported, same reasoning as slot_alternatives.py's own
    duplicated helpers (this module never imports service.py, since
    service.py imports this module)."""
    if request.start_date is None:
        return None
    return (request.start_date + timedelta(days=day_number - 1)).weekday()


def build_fixed_slots_lookup(
    *,
    fixed_slots: list[RuleFixedSlotAssignment],
    request: NormalizedRuleRequest,
    city_catalog: CityPlaceCatalog,
) -> dict[tuple[int, str], PlaceData]:
    places_by_id = {place.id: place for place in city_catalog.places}

    # --- per-entry structural checks (place identity, day/slot validity,
    # duplicates) -------------------------------------------------------
    seen_day_slots: set[tuple[int, str]] = set()
    resolved: dict[tuple[int, str], PlaceData] = {}
    allowed_slots_by_day: dict[int, list[str]] = {}

    for entry in fixed_slots:
        place = places_by_id.get(entry.place_id)
        if place is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"알 수 없는 장소 id입니다: {entry.place_id}",
            )
        if not place.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"비활성 장소는 지정할 수 없습니다: {entry.place_id}",
            )
        if "food" in place.concept_tags:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"식당은 활동 슬롯에 지정할 수 없습니다: {entry.place_id}",
            )

        if entry.day_number < 1 or entry.day_number > request.days:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"일정에 없는 일차입니다: {entry.day_number}일차",
            )

        if entry.day_number not in allowed_slots_by_day:
            allowed_slots_by_day[entry.day_number] = day_slot_rules(
                arrival_period=request.arrival_period,
                departure_period=request.departure_period,
                days=request.days,
                day_number=entry.day_number,
            ).allowed_slots
        if entry.time_slot not in allowed_slots_by_day[entry.day_number]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"허용되지 않은 슬롯입니다: {entry.day_number}일차 {entry.time_slot}",
            )

        key = (entry.day_number, entry.time_slot)
        if key in seen_day_slots:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"같은 슬롯이 중복 지정되었습니다: {entry.day_number}일차 {entry.time_slot}",
            )
        seen_day_slots.add(key)
        resolved[key] = place

    # --- completeness: every allowed (day, slot) must be pinned exactly
    # once - no partial fixing --------------------------------------------
    for day_number in range(1, request.days + 1):
        allowed_slots = allowed_slots_by_day.get(day_number)
        if allowed_slots is None:
            allowed_slots = day_slot_rules(
                arrival_period=request.arrival_period,
                departure_period=request.departure_period,
                days=request.days,
                day_number=day_number,
            ).allowed_slots
        for time_slot in allowed_slots:
            if (day_number, time_slot) not in resolved:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"모든 슬롯을 지정해야 합니다: {day_number}일차 {time_slot}이(가) 빠졌습니다",
                )

    # --- per-day repeated-place pattern: a day's pinned places must be
    # either all distinct, or (only when the day has exactly 3 allowed
    # slots) all the same place (full-day) - never a partial repeat. A day
    # with fewer than 3 allowed slots can never be "full-day" because the
    # only place _build_items ever builds a repeated-place item from fills
    # all of TIME_SLOTS (morning/afternoon/evening), which would fabricate
    # an item for a slot this day never actually allowed - see
    # RuleItineraryService._build_items's fixed_slots branch. ---------
    for day_number in range(1, request.days + 1):
        allowed_slots = allowed_slots_by_day.get(day_number) or []
        day_place_ids = [resolved[(day_number, slot)].id for slot in allowed_slots]
        distinct_count = len(set(day_place_ids))
        is_all_distinct = distinct_count == len(day_place_ids)
        is_full_day = distinct_count == 1 and len(day_place_ids) == 3
        if not (is_all_distinct or is_full_day):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"{day_number}일차 안에서 일부 슬롯만 같은 장소로 지정됐습니다 - "
                    "세 슬롯 모두 같은 장소(하루 전체)이거나 전부 다른 장소여야 합니다."
                ),
            )

    # --- cross-day: the same place can never be pinned on two different
    # days (a same-day repeat is only ever the all-3 full-day case above,
    # already validated) --------------------------------------------------
    day_numbers_by_place_id: dict[str, set[int]] = {}
    for (day_number, _time_slot), place in resolved.items():
        day_numbers_by_place_id.setdefault(place.id, set()).add(day_number)
    for place_id, day_numbers in day_numbers_by_place_id.items():
        if len(day_numbers) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"같은 장소를 서로 다른 일차에 지정할 수 없습니다: {place_id}",
            )

    # --- closed-day check (only meaningful with a start_date) -----------
    for (day_number, _time_slot), place in resolved.items():
        day_weekday = _day_weekday(request, day_number)
        if day_weekday is not None and is_confirmed_closed_on(place.closed_days, day_weekday):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"휴무로 확인된 요일의 장소입니다: {day_number}일차 {place.id}",
            )

    return resolved
