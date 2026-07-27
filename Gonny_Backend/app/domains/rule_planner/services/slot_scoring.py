from __future__ import annotations

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest

from .constants import (
    ACTIVITY_CATEGORIES,
    ARRIVAL_DAY_CATEGORIES,
    DEPARTURE_DAY_CATEGORIES,
    MIDDLE_DAY_CATEGORIES,
    SLOT_CATEGORY_PREFERENCE,
)
from .policies.city import (
    evening_food_bonus,
    neighbor_area_bonus,
    preferred_area_match_bonus,
    same_area_continuity_bonus,
)


def day_phase(request: NormalizedRuleRequest, day_number: int) -> str:
    if request.days <= 1:
        return "arrival"
    if day_number == 1:
        return "arrival"
    if day_number == request.days:
        return "departure"
    return "middle"


def base_score(place: PlaceData, request: NormalizedRuleRequest) -> int:
    score = place.priority * 10
    concept_tags = set(place.concept_tags)
    score += len(concept_tags & set(request.concepts)) * 8
    if "activity" in request.concepts and set(place.activity_type_codes) & ACTIVITY_CATEGORIES:
        score += 28
    elif "activity" in request.concepts:
        score -= 6
    if place.mvp_tier == "core":
        score += 10
    elif place.mvp_tier == "hidden":
        score -= 20

    if request.budget_band in place.budget_level:
        score += 6
    if request.companion_type in place.suitable_for:
        score += 5
    if request.style == "easy" and "easy" in place.pace:
        score += 4
    if request.style == "tight" and "tight" in place.pace:
        score += 4
    if request.style in {"near-stay", "mobility-first"} and (
        "walkable" in place.mobility or "nearby" in place.mobility
    ):
        score += 4

    return score


def slot_score(
    *,
    place: PlaceData,
    request: NormalizedRuleRequest,
    time_slot: str,
    day_number: int,
    preferred_area: str | None,
    previous_place: PlaceData | None = None,
) -> int:
    categories = set(place.concept_tags)
    score = base_score(place, request)
    score += phase_score(place=place, request=request, day_number=day_number, time_slot=time_slot)
    score += duration_slot_score(place=place, request=request, time_slot=time_slot)
    score += style_slot_score(place=place, request=request, time_slot=time_slot)

    if time_slot in place.time_fit:
        score += 12
    score += slot_bias_score(place=place, time_slot=time_slot)
    score += preferred_area_match_bonus(request, preferred_area, place.area)
    score += same_area_continuity_bonus(request, previous_place.area if previous_place else None, place.area)
    if previous_place and previous_place.area != place.area:
        score += neighbor_area_bonus(request, previous_place.area, place.area)
    if categories & SLOT_CATEGORY_PREFERENCE[time_slot]:
        score += 5
    if "activity" in request.concepts and categories & ACTIVITY_CATEGORIES:
        score += 10
    if time_slot == "evening" and "food" in categories:
        score += 4
    score += evening_food_bonus(request, time_slot, categories)
    if time_slot == "morning" and ("relax" in categories or "cafe" in categories):
        score += 3
    if request.style == "near-stay" and place.area == preferred_area:
        score += 3

    return score


def duration_slot_score(
    *,
    place: PlaceData,
    request: NormalizedRuleRequest,
    time_slot: str,
) -> int:
    duration = place.duration_hours
    categories = set(place.concept_tags)

    if time_slot == "morning":
        if duration <= 2:
            score = 6
        elif duration <= 4:
            score = 3
        elif duration >= 6:
            score = -10
        else:
            score = -4

        if categories & ACTIVITY_CATEGORIES and duration >= 4 and "activity" in request.concepts:
            score += 4
        return score

    if time_slot == "afternoon":
        if duration <= 1:
            score = -2
        elif duration <= 4:
            score = 4
        else:
            score = 2

        if categories & ACTIVITY_CATEGORIES and duration >= 4:
            score += 6
        return score

    if duration <= 2:
        score = 8
    elif duration == 3:
        score = 3
    elif duration == 4:
        score = -3
    else:
        score = -12

    if categories & {"food", "photo", "shopping", "nightlife"} and duration <= 3:
        score += 3
    return score


def style_slot_score(
    *,
    place: PlaceData,
    request: NormalizedRuleRequest,
    time_slot: str,
) -> int:
    duration = place.duration_hours
    score = 0

    if request.style == "tight":
        if time_slot in {"morning", "afternoon"} and duration >= 3:
            score += 3
        if time_slot == "evening" and duration <= 2:
            score += 2
    elif request.style == "easy":
        if duration <= 3:
            score += 3
        elif duration >= 5:
            score -= 4
    elif request.style == "near-stay":
        if duration <= 3:
            score += 2
    elif request.style == "mobility-first":
        if duration <= 3:
            score += 2
        if "taxi-needed" in place.mobility:
            score -= 3

    return score


def slot_bias_score(
    *,
    place: PlaceData,
    time_slot: str,
) -> int:
    raw_bias = place.slot_bias.get(time_slot, 0)
    normalized_bias = max(min(raw_bias, 8), -8)
    return normalized_bias * 3


def phase_score(
    *,
    place: PlaceData,
    request: NormalizedRuleRequest,
    day_number: int,
    time_slot: str,
) -> int:
    phase = day_phase(request, day_number)
    categories = set(place.concept_tags)
    score = 0

    if phase == "arrival":
        if categories & ARRIVAL_DAY_CATEGORIES:
            score += 12
        if categories & ACTIVITY_CATEGORIES:
            score -= 34
        if time_slot == "morning" and categories & ACTIVITY_CATEGORIES:
            score -= 16
        if place.full_day_recommended:
            score -= 40
        if place.duration_hours >= 4:
            score -= 12
        if time_slot == "morning" and categories & {"relax", "culture", "sightseeing"}:
            score += 6
        if time_slot == "evening" and "food" in categories:
            score += 8
        if "taxi-needed" in place.mobility or "train-friendly" in place.mobility:
            score -= 4
        return score

    if phase == "middle":
        if categories & MIDDLE_DAY_CATEGORIES:
            score += 10
        if "activity" in request.concepts and categories & ACTIVITY_CATEGORIES:
            score += 12
        if "activity" in request.concepts and time_slot in {"morning", "afternoon"}:
            if categories & ACTIVITY_CATEGORIES:
                score += 12
            else:
                score -= 8
        return score

    if categories & DEPARTURE_DAY_CATEGORIES:
        score += 12
    if categories & ACTIVITY_CATEGORIES:
        score -= 44
    if place.full_day_recommended:
        score -= 36
    if place.duration_hours >= 4:
        score -= 14
    elif place.duration_hours <= 2:
        score += 8
    if "taxi-needed" in place.mobility or "train-friendly" in place.mobility:
        score -= 6
    if time_slot == "morning" and ("shopping" in categories or "food" in categories or "culture" in categories):
        score += 4
    if time_slot == "evening" and "food" in categories:
        score += 6
    return score
