from __future__ import annotations

import json
from pathlib import Path

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest

from .travel_estimate import haversine_distance_km

ACCOMMODATIONS_DIR = Path(__file__).resolve().parents[4] / "app" / "data" / "accommodations"

# Rule-based only - deliberately not using get_fitness_scorer(). The ML
# model was trained on destination_catalog.PlaceData's feature space
# (activity_type/mood/visual_feature/...), which accommodations don't
# have; AccommodationData has a completely different shape
# (accommodation_type/amenities/budget_level/suitable_for), so there's no
# valid way to feed it through the same model.
BUDGET_MATCH_BONUS = 6
BUDGET_MISMATCH_PENALTY = -4
COMPANION_MATCH_BONUS = 5
COMPANION_MISMATCH_PENALTY = -3

# Distance tiers mirror travel_estimate.coordinate_area_transition_bonus's
# magnitudes (14/6/0/-6) for consistency with the rest of the scoring
# system, expressed directly in km rather than estimated travel minutes -
# there's no "next slot" transit-mode nuance for "how close is this hotel
# to where the trip actually happens", just plain proximity.
CLOSE_DISTANCE_KM = 1.0
NEARBY_DISTANCE_KM = 3.0
FAR_DISTANCE_KM = 7.0
CLOSE_LOCATION_BONUS = 14
NEARBY_LOCATION_BONUS = 6
FAR_LOCATION_PENALTY = -6


def load_city_accommodations(city: str) -> list[AccommodationData]:
    """Best-effort load of app/data/accommodations/{city}.json. Returns []
    if the file doesn't exist (e.g. a city outside the 3 covered so far) -
    callers should treat that as "no recommendation available", not an
    error."""
    path = ACCOMMODATIONS_DIR / f"{city}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [AccommodationData.model_validate(item) for item in payload.get("accommodations", [])]


def compute_reference_point(
    day_place_map: dict[int, list[PlaceData]],
    city_catalog: CityPlaceCatalog,
) -> tuple[float, float] | None:
    """MVP reference point for location-fitness scoring: the average
    coordinates of every catalog place in the itinerary's single
    most-visited area (by raw area code, not the localized display label).

    This deliberately ignores day-by-day structure - a more precise
    reference (e.g. each day's last-visited place, or a per-night
    recommendation) is a natural next step but out of scope for this MVP,
    which recommends exactly one accommodation for the whole trip.
    """
    area_visit_counts: dict[str, int] = {}
    for places in day_place_map.values():
        for place in places:
            area_visit_counts[place.area] = area_visit_counts.get(place.area, 0) + 1
    if not area_visit_counts:
        return None
    most_visited_area = max(area_visit_counts.items(), key=lambda entry: entry[1])[0]

    area_coordinates = [
        (place.latitude, place.longitude)
        for place in city_catalog.places
        if place.area == most_visited_area and place.latitude is not None and place.longitude is not None
    ]
    if not area_coordinates:
        return None
    average_latitude = sum(lat for lat, _ in area_coordinates) / len(area_coordinates)
    average_longitude = sum(lng for _, lng in area_coordinates) / len(area_coordinates)
    return average_latitude, average_longitude


def accommodation_score(
    accommodation: AccommodationData,
    request: NormalizedRuleRequest,
    reference_point: tuple[float, float] | None,
) -> int:
    """Rule-based accommodation fitness score.

    accommodation_type deliberately does not affect this score (per this
    feature's scope) - it's surfaced in the response for the user to see,
    not used to rank candidates. view is not read here either (data
    quality too low for this round - see AccommodationData.view).
    """
    score = 0

    if request.budget_band in accommodation.budget_level:
        score += BUDGET_MATCH_BONUS
    else:
        score += BUDGET_MISMATCH_PENALTY

    if request.companion_type in accommodation.suitable_for:
        score += COMPANION_MATCH_BONUS
    else:
        score += COMPANION_MISMATCH_PENALTY

    if reference_point is not None and accommodation.latitude is not None and accommodation.longitude is not None:
        distance_km = haversine_distance_km(
            reference_point[0], reference_point[1], accommodation.latitude, accommodation.longitude
        )
        if distance_km <= CLOSE_DISTANCE_KM:
            score += CLOSE_LOCATION_BONUS
        elif distance_km <= NEARBY_DISTANCE_KM:
            score += NEARBY_LOCATION_BONUS
        elif distance_km <= FAR_DISTANCE_KM:
            score += 0
        else:
            score += FAR_LOCATION_PENALTY
    # No coordinates (on the accommodation or the reference point): the
    # location component simply contributes 0, per this feature's "exclude
    # from location fitness, score on the rest" rule - see
    # select_accommodation_recommendation for how coordinate-having
    # candidates are still preferred overall.

    return score


def select_accommodation_recommendation(
    accommodations: list[AccommodationData],
    request: NormalizedRuleRequest,
    reference_point: tuple[float, float] | None,
) -> AccommodationData | None:
    """Picks the single best accommodation for the whole trip (this MVP's
    scope - no per-night reassignment).

    If at least one candidate has coordinates, candidates without
    coordinates are dropped entirely rather than merely scored lower: a
    recommendation we can't place on a map is a materially worse
    suggestion than one we can, so it shouldn't be able to outrank a
    coordinate-having candidate just by winning on budget/companion fit
    alone. Only when *no* candidate has coordinates does the full pool
    get scored on budget/companion fit alone.
    """
    if not accommodations:
        return None

    with_coordinates = [
        accommodation
        for accommodation in accommodations
        if accommodation.latitude is not None and accommodation.longitude is not None
    ]
    candidate_pool = with_coordinates or accommodations

    ranked = sorted(
        candidate_pool,
        key=lambda accommodation: accommodation_score(accommodation, request, reference_point),
        reverse=True,
    )
    return ranked[0]
