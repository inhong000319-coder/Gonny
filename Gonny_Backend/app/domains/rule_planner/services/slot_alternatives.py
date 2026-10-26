"""Post-processing pass that computes up to 3 "instead of this" alternative
places per activity slot, after _build_items has already finalized the
real selection - see RuleItineraryService.generate() and RuleSlotAlternative.

This module never influences which place _build_items picks. It only
re-scores the already-confirmed candidate pool with the real slot_score()
function, using the same previous/next place and day_area that the
winning pick was scored against, and reports the top few runners-up.

Candidate rule (deliberately narrower than _pick_place_for_slot's own
pool): active, non-restaurant, time_fit includes this slot - no fallback
to time_fit-less candidates if that leaves too few (see
_pick_place_for_slot's "slot_fitting_places or available_places" for the
contrast - that fallback exists for the real pick because a slot must
always be filled; an alternative list is allowed to simply be short).
"""
from __future__ import annotations

from typing import Callable

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleItineraryItem, RuleSlotAlternative

from .closed_days import is_confirmed_closed_on
from .community_feedback import PlaceFeedbackSignal
from .constants import ACTIVITY_CATEGORIES, TIME_SLOTS
from .slot_scoring import day_phase, slot_score

MAX_ALTERNATIVES = 3


def _filter_phase_candidates(
    *, places: list[PlaceData], request: NormalizedRuleRequest, day_number: int
) -> list[PlaceData]:
    """Mirrors RuleItineraryService._filter_phase_candidates exactly (same
    inputs, same fallback-to-places-if-empty) - duplicated rather than
    imported because that one is a private method on the service class,
    and this module intentionally never imports service.py (to avoid a
    circular import, since service.py imports this module)."""
    if day_phase(request, day_number) not in {"arrival", "departure"}:
        return places
    if "activity" not in request.concepts:
        return places
    non_activity_places = [place for place in places if not (set(place.activity_type_codes) & ACTIVITY_CATEGORIES)]
    return non_activity_places or places


def _is_open_on_day(place: PlaceData, day_weekday: int | None) -> bool:
    if day_weekday is None:
        return True
    return not is_confirmed_closed_on(place.closed_days, day_weekday)


def _slot_sequence(day_slot_places: dict[str, PlaceData]) -> list[tuple[str, PlaceData]]:
    return [(slot, day_slot_places[slot]) for slot in TIME_SLOTS if slot in day_slot_places]


def compute_item_alternatives(
    *,
    items: list[RuleItineraryItem],
    request: NormalizedRuleRequest,
    city_catalog: CityPlaceCatalog,
    day_place_map: dict[int, list[PlaceData]],
    day_slot_places: dict[int, dict[str, PlaceData]],
    day_areas: dict[int, str | None],
    feedback_signals: dict[str, PlaceFeedbackSignal] | None,
    day_weekdays: dict[int, int | None],
    localize_place_name: Callable[[PlaceData], str],
    localize_area: Callable[[str], str],
    resolve_item_category: Callable[[PlaceData, NormalizedRuleRequest], str],
    build_note: Callable[..., str],
) -> list[RuleItineraryItem]:
    """Returns a NEW list of items (same order, same other fields) with
    `alternatives` filled in on each non-full-day item. Pure function -
    doesn't mutate the input items or any of the _build_items state."""
    full_day_days = {
        day_number
        for day_number, slots in day_slot_places.items()
        if len(slots) == len(TIME_SLOTS) and len({place.id for place in slots.values()}) == 1
    }

    all_used_ids = {place.id for places in day_place_map.values() for place in places}

    scored_places_by_id = {
        place.id: place
        for place in city_catalog.places
        if place.is_active and "food" not in place.concept_tags
    }

    new_items: list[RuleItineraryItem] = []
    for item in items:
        if item.day_number in full_day_days:
            new_items.append(item)
            continue

        slot_places = day_slot_places.get(item.day_number)
        if not slot_places or item.time_slot not in slot_places:
            # Shouldn't happen for a non-full-day item, but never block the
            # response over it - just no alternatives for this one.
            new_items.append(item)
            continue

        sequence = _slot_sequence(slot_places)
        index = next(i for i, (slot, _) in enumerate(sequence) if slot == item.time_slot)
        previous_place = sequence[index - 1][1] if index > 0 else None
        next_place = sequence[index + 1][1] if index + 1 < len(sequence) else None

        day_weekday = day_weekdays.get(item.day_number)
        preferred_area = day_areas.get(item.day_number)

        # all_used_ids already includes this slot's own chosen place, so
        # excluding it also satisfies "현재 선택 장소 제외" for free.
        candidates = [
            place
            for place_id, place in scored_places_by_id.items()
            if place_id not in all_used_ids
            and item.time_slot in place.time_fit
            and _is_open_on_day(place, day_weekday)
        ]
        candidates = _filter_phase_candidates(places=candidates, request=request, day_number=item.day_number)

        ranked = sorted(
            candidates,
            key=lambda place: (
                -slot_score(
                    place=place,
                    request=request,
                    time_slot=item.time_slot,
                    day_number=item.day_number,
                    preferred_area=preferred_area,
                    previous_place=previous_place,
                    next_place=next_place,
                    community_signal=(feedback_signals or {}).get(place.id),
                ),
                place.id,
            ),
        )

        alternatives = [
            RuleSlotAlternative(
                place_id=place.id,
                place_name=localize_place_name(place),
                category=resolve_item_category(place, request),
                area=localize_area(place.area),
                notes=build_note(
                    place=place,
                    request=request,
                    time_slot=item.time_slot,
                    day_number=item.day_number,
                    day_area=preferred_area,
                    previous_place=previous_place,
                ),
                average_cost_krw=place.average_cost_krw,
            )
            for place in ranked[:MAX_ALTERNATIVES]
        ]
        new_items.append(item.model_copy(update={"alternatives": alternatives}))

    return new_items
