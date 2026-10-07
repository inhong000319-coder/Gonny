from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import RuleTravelOption

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


def estimate_accommodation_transition_minutes(
    accommodation: AccommodationData | None, place: PlaceData
) -> int | None:
    """Estimated travel time between the recommended accommodation and a
    place, or None if there's no accommodation or either side is missing
    coordinates. Reuses the same haversine + straight-line estimate as
    estimate_travel_minutes_between(), just for an AccommodationData/
    PlaceData pair instead of two PlaceData."""
    if accommodation is None:
        return None
    if accommodation.latitude is None or accommodation.longitude is None:
        return None
    if place.latitude is None or place.longitude is None:
        return None
    distance_km = haversine_distance_km(
        accommodation.latitude, accommodation.longitude, place.latitude, place.longitude
    )
    return estimate_straight_line_travel_minutes(distance_km)


def estimate_day_total_minutes(
    places: list[PlaceData],
    accommodation: AccommodationData | None = None,
) -> int:
    """Total estimated minutes for one day's plan: each place's own
    duration plus estimated travel between consecutive places.

    A pair without coordinates on both ends contributes 0 travel time (not
    an error) - the total simply reflects duration_hours only for that
    pair, same as before coordinates existed.

    accommodation is optional (defaults to None, preserving prior
    behavior). When given, the accommodation-to-first-place and
    last-place-to-accommodation legs are added too, since the MVP
    recommends a single accommodation for the whole trip and the traveler
    is assumed to return there every night - see
    RuleItineraryService._recommend_accommodation.
    """
    total_minutes = sum(place.duration_hours * 60 for place in places)
    for previous_place, place in zip(places, places[1:]):
        travel_minutes = estimate_travel_minutes_between(previous_place, place)
        if travel_minutes is not None:
            total_minutes += travel_minutes

    if places:
        to_first_place_minutes = estimate_accommodation_transition_minutes(accommodation, places[0])
        if to_first_place_minutes is not None:
            total_minutes += to_first_place_minutes
        from_last_place_minutes = estimate_accommodation_transition_minutes(accommodation, places[-1])
        if from_last_place_minutes is not None:
            total_minutes += from_last_place_minutes

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


def _coordinate_transition_bonus(other_place: PlaceData | None, place: PlaceData) -> int | None:
    """Distance-based continuity bonus for a transition between `place` and
    `other_place` - shared by the previous-place and next-place bonus
    functions below, since haversine distance (and therefore the estimated
    travel time) is symmetric regardless of which direction the leg is
    actually walked.

    Returns None when other_place is missing or either place lacks
    coordinates - callers fall back to something else in that case (the
    string-based same_area_continuity_bonus()/neighbor_area_bonus() for the
    previous-place direction; simply no bonus for the next-place direction).
    """
    if other_place is None:
        return None
    travel_minutes = estimate_travel_minutes_between(other_place, place)
    if travel_minutes is None:
        return None
    if travel_minutes <= CLOSE_TRAVEL_MINUTES_THRESHOLD:
        return CLOSE_TRANSITION_BONUS
    if travel_minutes <= NEARBY_TRAVEL_MINUTES_THRESHOLD:
        return NEARBY_TRANSITION_BONUS
    if travel_minutes <= FAR_TRAVEL_MINUTES_THRESHOLD:
        return 0
    return FAR_TRANSITION_PENALTY


def coordinate_area_transition_bonus(previous_place: PlaceData | None, place: PlaceData) -> int | None:
    """Distance-based continuity bonus for a slot transition, looking
    *backward* to the previous slot's (already-confirmed) place.

    Returns None when previous_place is missing or either place lacks
    coordinates - the caller should fall back to the string-based
    same_area_continuity_bonus()/neighbor_area_bonus() in that case, per
    the gradual per-pair transition described in this feature's scope.
    """
    return _coordinate_transition_bonus(previous_place, place)


def coordinate_next_place_transition_bonus(next_place: PlaceData | None, place: PlaceData) -> int | None:
    """Distance-based continuity bonus looking *forward* to the next slot's
    place, mirroring coordinate_area_transition_bonus's backward-looking
    version (same thresholds/estimate, via _coordinate_transition_bonus()).

    Only meaningful once the day's slots have already been greedily placed
    once - see RuleItineraryService._refine_day_with_next_place_lookahead,
    which re-scores each slot against its now-known next place and swaps in
    a clearly-better unused candidate when one exists.

    Weighted at half of the previous-place bonus: previous_place is a
    transition the traveler will actually walk by the time a slot is
    re-scored in that refinement pass, while next_place is a forward-
    looking signal for nudging the pick, not a confirmed leg (the next
    slot could itself still be swapped in the same pass). Halving it keeps
    the confirmed previous-leg bonus the dominant signal rather than having
    this lookahead bonus override it.
    """
    raw_bonus = _coordinate_transition_bonus(next_place, place)
    if raw_bonus is None:
        return None
    return round(raw_bonus / 2)


# --- Mode-aware travel options (walk/transit/car) -------------------------
#
# Separate from estimate_straight_line_travel_minutes() above, which scoring
# and duration totals keep using unchanged. That single-speed estimate has
# no per-leg fixed cost, so it can invert near its walk/transit distance
# threshold (a 1.2km walk and a 1.3km transit ride land close together even
# though real transit has a wait-and-walk-up overhead a car/bus ride at
# 1.3km wouldn't actually beat by much). The functions below give each mode
# its own fixed cost specifically to avoid that.
#
# All figures below are assumed values, not measured - recalibrate against
# a real routing API (e.g. ODSay for transit) once one is wired in.
WALK_OPTION_MAX_MINUTES = 20

TRANSIT_FIXED_MINUTES = 10
CAR_FIXED_MINUTES = 8
DEFAULT_CITY_TRANSPORT_PROFILE = "seoul"
TRANSIT_SPEED_KMH_BY_CITY: dict[str, float] = {"seoul": 25.0, "busan": 22.0, "jeju": 15.0}
CAR_SPEED_KMH_BY_CITY: dict[str, float] = {"seoul": 20.0, "busan": 25.0, "jeju": 35.0}

TRANSPORT_PROFILES: dict[str, dict[str, object]] = {
    "transit": {"fixed_minutes": TRANSIT_FIXED_MINUTES, "speed_kmh_by_city": TRANSIT_SPEED_KMH_BY_CITY},
    "car": {"fixed_minutes": CAR_FIXED_MINUTES, "speed_kmh_by_city": CAR_SPEED_KMH_BY_CITY},
}


def _mode_speed_kmh(mode: str, city: str) -> float:
    speeds: dict[str, float] = TRANSPORT_PROFILES[mode]["speed_kmh_by_city"]  # type: ignore[assignment]
    return speeds.get(city, speeds[DEFAULT_CITY_TRANSPORT_PROFILE])


def estimate_mode_minutes(mode: str, distance_km: float, city: str) -> int:
    """Fixed time (wait/parking/walk-up) plus routed distance at the mode's
    cruising speed for `city`, falling back to the Seoul profile for any
    other city. mode must be "transit" or "car" - see estimate_walk_option_minutes
    for walking, which has no fixed time."""
    fixed_minutes: int = TRANSPORT_PROFILES[mode]["fixed_minutes"]  # type: ignore[assignment]
    speed_kmh = _mode_speed_kmh(mode, city)
    routed_distance_km = distance_km * ROUTE_DETOUR_FACTOR
    return max(1, round(fixed_minutes + (routed_distance_km / speed_kmh) * 60))


def estimate_walk_option_minutes(distance_km: float) -> int:
    """Walking time for one leg, reusing the same detour factor and walking
    speed as estimate_straight_line_travel_minutes(). No fixed time - unlike
    transit/car there's no wait or parking step."""
    routed_distance_km = distance_km * ROUTE_DETOUR_FACTOR
    return max(1, round((routed_distance_km / WALK_SPEED_KMH) * 60))


def estimate_transport_options(distance_km: float, city: str) -> list[RuleTravelOption]:
    """Every transport option for one leg: transit and car always, walk only
    when it's WALK_OPTION_MAX_MINUTES or under (beyond that, nobody
    realistically walks it, so it's left out rather than shown as a
    technically-valid but useless choice)."""
    options = [
        RuleTravelOption(mode="transit", minutes=estimate_mode_minutes("transit", distance_km, city)),
        RuleTravelOption(mode="car", minutes=estimate_mode_minutes("car", distance_km, city)),
    ]
    walk_minutes = estimate_walk_option_minutes(distance_km)
    if walk_minutes <= WALK_OPTION_MAX_MINUTES:
        options.insert(0, RuleTravelOption(mode="walk", minutes=walk_minutes))
    return options
