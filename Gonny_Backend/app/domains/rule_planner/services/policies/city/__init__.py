from __future__ import annotations

from types import ModuleType

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest

from ...travel_estimate import haversine_distance_km
from . import busan, jeju, seoul


CITY_POLICIES: dict[str, ModuleType] = {
    "busan": busan,
    "jeju": jeju,
    "seoul": seoul,
}


def _policy_for(request: NormalizedRuleRequest) -> ModuleType | None:
    return CITY_POLICIES.get(request.city)


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    ranked_areas = [area for area, _ in sorted(area_scores.items(), key=lambda item: item[1], reverse=True)]
    policy = _policy_for(request)
    if policy is not None:
        return policy.preferred_area_order(request, area_scores)
    return ranked_areas


def preferred_area_match_bonus(
    request: NormalizedRuleRequest,
    preferred_area: str | None,
    place_area: str,
) -> int:
    if not preferred_area or preferred_area != place_area:
        return 0
    policy = _policy_for(request)
    if policy is not None:
        return policy.preferred_area_match_bonus()
    return 9


def same_area_continuity_bonus(
    request: NormalizedRuleRequest,
    previous_area: str | None,
    place_area: str,
) -> int:
    if not previous_area or previous_area != place_area:
        return 0
    policy = _policy_for(request)
    if policy is not None:
        return policy.same_area_continuity_bonus()
    return 10


def neighbor_area_bonus(
    request: NormalizedRuleRequest,
    previous_area: str | None,
    place_area: str,
) -> int:
    policy = _policy_for(request)
    if policy is not None:
        return policy.neighbor_area_bonus(previous_area, place_area)
    return 0


def evening_food_bonus(
    request: NormalizedRuleRequest,
    time_slot: str,
    categories: set[str],
) -> int:
    policy = _policy_for(request)
    if policy is not None:
        return policy.evening_food_bonus(time_slot, categories)
    return 0


def extreme_distance_penalty(
    request: NormalizedRuleRequest,
    other_place: PlaceData | None,
    place: PlaceData,
) -> int:
    """Extra penalty for a transition whose real straight-line distance is
    large enough that no city's existing coordinate_area_transition_bonus
    FAR tier (capped at -6, see travel_estimate.py) meaningfully deters it
    - see policies/city/jeju.py's own threshold/penalty constants for why
    Jeju specifically needs this on top of the shared bonus.

    0 for any city whose policy module doesn't define
    extreme_distance_penalty(distance_km) - today that's every city except
    Jeju, so Seoul/Busan (and any city with no policy module at all) are
    completely unaffected by construction, not just by convention.
    """
    if other_place is None:
        return 0
    policy = _policy_for(request)
    if policy is None or not hasattr(policy, "extreme_distance_penalty"):
        return 0
    if (
        other_place.latitude is None
        or other_place.longitude is None
        or place.latitude is None
        or place.longitude is None
    ):
        return 0
    distance_km = haversine_distance_km(other_place.latitude, other_place.longitude, place.latitude, place.longitude)
    return policy.extreme_distance_penalty(distance_km)


def accommodation_distance_score(
    request: NormalizedRuleRequest,
    accommodation: AccommodationData,
    day_endpoints: list[tuple[float, float]],
) -> float | None:
    """Accommodation score based on the accommodation's distance to every
    day's first/last place, used INSTEAD OF (not in addition to) the
    single reference_point tiered bonus in accommodation_scoring.py - see
    the if/elif there. A city opts in simply by defining
    accommodation_distance_score(distances_km) on its policy module
    (seoul.py, busan.py, jeju.py all do; jeju rounds to an int, seoul/busan
    don't - see each module for why).

    None - meaning "this city has no such scoring, use the existing
    reference_point path unchanged" - for any city whose policy module
    doesn't define accommodation_distance_score(distances_km).
    """
    policy = _policy_for(request)
    if policy is None or not hasattr(policy, "accommodation_distance_score"):
        return None
    if accommodation.latitude is None or accommodation.longitude is None or not day_endpoints:
        return None
    distances_km = [
        haversine_distance_km(accommodation.latitude, accommodation.longitude, lat, lng)
        for lat, lng in day_endpoints
    ]
    return policy.accommodation_distance_score(distances_km)
