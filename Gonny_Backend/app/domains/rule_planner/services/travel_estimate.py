from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.domains.destination_catalog.schemas import PlaceData

EARTH_RADIUS_KM = 6371.0

# Average adult walking pace on flat urban terrain.
WALK_SPEED_KMH = 4.0
# Blended "door to door" transit speed: subway/bus cruising speed averaged
# with wait times, transfers, and station walk-up, not raw vehicle speed.
# Seoul subway typically cruises ~30-35km/h between stations, but the
# door-to-door effective speed factoring in waiting/transfers is commonly
# cited around 18-22km/h for short-to-medium urban trips.
TRANSIT_EFFECTIVE_SPEED_KMH = 20.0
# Below this distance most people just walk rather than wait for transit.
WALK_DISTANCE_THRESHOLD_KM = 1.2
# Straight-line ("as the crow flies") distance underestimates real route
# distance because roads/rail don't run in straight lines. A detour index
# of ~1.3 is a commonly cited rule of thumb for dense urban street grids.
ROUTE_DETOUR_FACTOR = 1.3


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometers."""
    lat1_rad, lng1_rad, lat2_rad, lng2_rad = map(radians, (lat1, lng1, lat2, lng2))
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def estimate_straight_line_travel_minutes(distance_km: float) -> int:
    """Rough travel-time estimate from straight-line distance alone.

    This is NOT a routed estimate - it doesn't know about roads, transit
    lines, or transfers. It exists as a placeholder until real routing
    (e.g. ODSay) is wired in; see estimate_travel_minutes_between() below
    for the swap point.
    """
    routed_distance_km = distance_km * ROUTE_DETOUR_FACTOR
    speed_kmh = WALK_SPEED_KMH if distance_km <= WALK_DISTANCE_THRESHOLD_KM else TRANSIT_EFFECTIVE_SPEED_KMH
    return round((routed_distance_km / speed_kmh) * 60)


def estimate_travel_minutes_between(place_a: PlaceData, place_b: PlaceData) -> int | None:
    """Estimated travel time between two places, or None if either is missing coordinates.

    This is the seam for swapping in a real routing provider later (e.g.
    ODSayClient.estimate_duration_min): callers only depend on this
    function's (place_a, place_b) -> int | None signature, not on how the
    estimate is computed. Today it's straight-line distance; later it can
    call out to ODSay for places with coordinates and keep the same
    None-on-missing-data contract.
    """
    if place_a.latitude is None or place_a.longitude is None:
        return None
    if place_b.latitude is None or place_b.longitude is None:
        return None
    distance_km = haversine_distance_km(place_a.latitude, place_a.longitude, place_b.latitude, place_b.longitude)
    return estimate_straight_line_travel_minutes(distance_km)


def estimate_day_total_minutes(places: list[PlaceData]) -> int:
    """Total estimated minutes for one day's plan: each place's own
    duration plus estimated travel between consecutive places.

    A pair without coordinates on both ends contributes 0 travel time (not
    an error) - the total simply reflects duration_hours only for that
    pair, same as before coordinates existed.
    """
    total_minutes = sum(place.duration_hours * 60 for place in places)
    for previous_place, place in zip(places, places[1:]):
        travel_minutes = estimate_travel_minutes_between(previous_place, place)
        if travel_minutes is not None:
            total_minutes += travel_minutes
    return total_minutes


# Bonus tiers are calibrated to sit within the range of the existing
# string-based same_area_continuity_bonus (12-18 across city policies) and
# neighbor_area_bonus (5-8), so swapping between coordinate-based and
# string-based scoring for a given transition doesn't create a visible
# discontinuity in itinerary scores.
CLOSE_TRAVEL_MINUTES_THRESHOLD = 8
NEARBY_TRAVEL_MINUTES_THRESHOLD = 20
FAR_TRAVEL_MINUTES_THRESHOLD = 40
CLOSE_TRANSITION_BONUS = 14
NEARBY_TRANSITION_BONUS = 6
FAR_TRANSITION_PENALTY = -6


def coordinate_area_transition_bonus(previous_place: PlaceData | None, place: PlaceData) -> int | None:
    """Distance-based continuity bonus for a slot transition.

    Returns None when previous_place is missing or either place lacks
    coordinates - the caller should fall back to the string-based
    same_area_continuity_bonus()/neighbor_area_bonus() in that case, per
    the gradual per-pair transition described in this feature's scope.
    """
    if previous_place is None:
        return None
    travel_minutes = estimate_travel_minutes_between(previous_place, place)
    if travel_minutes is None:
        return None
    if travel_minutes <= CLOSE_TRAVEL_MINUTES_THRESHOLD:
        return CLOSE_TRANSITION_BONUS
    if travel_minutes <= NEARBY_TRAVEL_MINUTES_THRESHOLD:
        return NEARBY_TRANSITION_BONUS
    if travel_minutes <= FAR_TRAVEL_MINUTES_THRESHOLD:
        return 0
    return FAR_TRANSITION_PENALTY
