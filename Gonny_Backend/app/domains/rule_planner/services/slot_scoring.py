from __future__ import annotations

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest

from .community_feedback import PlaceFeedbackSignal, community_feedback_bonus
from .constants import (
    ACTIVITY_CATEGORIES,
    ARRIVAL_DAY_CATEGORIES,
    DEPARTURE_DAY_CATEGORIES,
    MIDDLE_DAY_CATEGORIES,
    SLOT_CATEGORY_PREFERENCE,
)
from .fitness_model import get_fitness_scorer
from .policies.city import (
    evening_food_bonus,
    neighbor_area_bonus,
    preferred_area_match_bonus,
    same_area_continuity_bonus,
)
from .travel_estimate import coordinate_area_transition_bonus, coordinate_next_place_transition_bonus


# Assumed values, not measured - tune once there's real signal on how much
# a transit day actually penalizes a taxi-needed place or rewards a
# subway-friendly one. Only applied on a day whose transport mode is
# explicitly "transit" (request.transport_by_day) - see slot_score().
TRANSIT_TAXI_NEEDED_PENALTY = -8
TRANSIT_SUBWAY_FRIENDLY_BONUS = 3


def day_phase(request: NormalizedRuleRequest, day_number: int) -> str:
    if request.days <= 1:
        return "arrival"
    if day_number == 1:
        return "arrival"
    if day_number == request.days:
        return "departure"
    return "middle"


def legacy_base_score(place: PlaceData, request: NormalizedRuleRequest) -> int:
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


def base_score(place: PlaceData, request: NormalizedRuleRequest) -> int:
    prediction = get_fitness_scorer().predict(place, request)
    return round(prediction)


def slot_score(
    *,
    place: PlaceData,
    request: NormalizedRuleRequest,
    time_slot: str,
    day_number: int,
    preferred_area: str | None,
    previous_place: PlaceData | None = None,
    next_place: PlaceData | None = None,
    community_signal: PlaceFeedbackSignal | None = None,
) -> int:
    categories = set(place.concept_tags)
    # That day's picked transport mode, or None if the request didn't
    # specify one (request.transport_by_day) - None preserves every
    # mode-aware branch below exactly as it behaved before this feature.
    mode = request.transport_by_day[day_number - 1] if request.transport_by_day else None
    score = base_score(place, request)
    score += phase_score(place=place, request=request, day_number=day_number, time_slot=time_slot, mode=mode)
    score += duration_slot_score(place=place, request=request, time_slot=time_slot)
    score += style_slot_score(place=place, request=request, time_slot=time_slot, mode=mode)

    if time_slot in place.time_fit:
        score += 12
    score += slot_bias_score(place=place, time_slot=time_slot)
    score += preferred_area_match_bonus(request, preferred_area, place.area)
    coordinate_bonus = coordinate_area_transition_bonus(previous_place, place, mode=mode, city=request.city)
    if coordinate_bonus is not None:
        score += coordinate_bonus
    else:
        score += same_area_continuity_bonus(request, previous_place.area if previous_place else None, place.area)
        if previous_place and previous_place.area != place.area:
            score += neighbor_area_bonus(request, previous_place.area, place.area)
    # Forward-looking counterpart to coordinate_bonus above - only ever
    # non-None once a day's slots have already been placed once and the
    # refinement pass re-scores against the now-known next place (see
    # RuleItineraryService._refine_day_with_next_place_lookahead). No
    # string-based fallback here (unlike previous_place): this is a
    # secondary nudge signal, not the primary continuity bonus.
    next_place_bonus = coordinate_next_place_transition_bonus(next_place, place, mode=mode, city=request.city)
    if next_place_bonus is not None:
        score += next_place_bonus
    if mode == "transit":
        if "taxi-needed" in place.mobility:
            score += TRANSIT_TAXI_NEEDED_PENALTY
        if "subway-friendly" in place.mobility:
            score += TRANSIT_SUBWAY_FRIENDLY_BONUS
    feedback_bonus = community_feedback_bonus(community_signal, time_slot, request.companion_type)
    if feedback_bonus is not None:
        score += feedback_bonus
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
    score += google_rating_bonus_score(place)

    return score


# Google rating thresholds/bonuses for the researched restaurant entities
# (see scripts/merge_restaurant_data.py) - deliberately small next to the
# other bonuses here (coordinate transitions alone swing +/-14) so a good
# rating nudges ranking among similar candidates without letting it
# override real fit/continuity signals.
GOOGLE_RATING_HIGH_CONFIDENCE_THRESHOLD = 4.5
GOOGLE_RATING_HIGH_CONFIDENCE_MIN_COUNT = 30
GOOGLE_RATING_HIGH_CONFIDENCE_BONUS = 6
GOOGLE_RATING_GOOD_THRESHOLD = 4.0
GOOGLE_RATING_GOOD_BONUS = 3


def google_rating_bonus_score(place: PlaceData) -> int:
    """Small bonus for places with a strong Google rating.

    Returns 0 (neutral, never a penalty) whenever google_rating is missing,
    which is true for most of the catalog (only the CSV-researched
    restaurants have this field populated) - places without the data must
    never be scored worse than before this bonus existed.
    """
    if place.google_rating is None:
        return 0
    if (
        place.google_rating >= GOOGLE_RATING_HIGH_CONFIDENCE_THRESHOLD
        and (place.google_rating_count or 0) >= GOOGLE_RATING_HIGH_CONFIDENCE_MIN_COUNT
    ):
        return GOOGLE_RATING_HIGH_CONFIDENCE_BONUS
    if place.google_rating >= GOOGLE_RATING_GOOD_THRESHOLD:
        return GOOGLE_RATING_GOOD_BONUS
    return 0


def meal_candidate_score(
    place: PlaceData,
    request: NormalizedRuleRequest,
    *,
    previous_place: PlaceData | None,
    next_place: PlaceData | None,
) -> int:
    """Lightweight scoring for the independent lunch/dinner recommendation
    (see RuleItineraryService._recommend_meals) - deliberately NOT the
    full slot_score(): meals no longer compete for a morning/afternoon/
    evening slot (see SLOT_CATEGORY_PREFERENCE), so slot_score()'s
    slot-fit/phase/duration/style bonuses - all tuned for that 3-way
    activity competition - don't apply to a meal pick. Reuses base_score()
    (trip concept/budget/style/companion fit) plus the same coordinate-
    based continuity bonuses and rating-aware bonus slot_score() uses, so
    a meal is still picked to sit conveniently between the surrounding
    activity places and to favor well-rated restaurants - no new scoring
    logic invented for this.
    """
    score = base_score(place, request)
    previous_bonus = coordinate_area_transition_bonus(previous_place, place)
    if previous_bonus is not None:
        score += previous_bonus
    next_bonus = coordinate_next_place_transition_bonus(next_place, place)
    if next_bonus is not None:
        score += next_bonus
    score += google_rating_bonus_score(place)
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
    mode: str | None = None,
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
        # Skipped on a car day (mode == "car"): a car removes the taxi-
        # access problem this penalty models - see slot_score()'s
        # TRANSIT_TAXI_NEEDED_PENALTY for the separate transit-day signal.
        if mode != "car" and "taxi-needed" in place.mobility:
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
    mode: str | None = None,
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
        # Skipped on a car day: a car removes the taxi/train access
        # problem this penalty models.
        if mode != "car" and ("taxi-needed" in place.mobility or "train-friendly" in place.mobility):
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
    # Skipped on a car day - see the matching comment in the arrival branch above.
    if mode != "car" and ("taxi-needed" in place.mobility or "train-friendly" in place.mobility):
        score -= 6
    if time_slot == "morning" and ("shopping" in categories or "food" in categories or "culture" in categories):
        score += 4
    if time_slot == "evening" and "food" in categories:
        score += 6
    return score
