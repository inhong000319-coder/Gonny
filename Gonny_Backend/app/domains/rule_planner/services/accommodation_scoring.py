from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import BudgetBand, NormalizedRuleRequest

from .policies.city import accommodation_distance_score, price_exact_match_bonus
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
# When a real nightly rate is known (AccommodationData.average_price_krw), the
# budget check uses it instead of the coarse budget_level tag - hence a
# slightly larger exact-match bonus, since it's grounded in data rather than
# a tag. Adjacent/far penalties scale with how many bands apart the stay and
# the requested band are.
#
# PRICE_EXACT_MATCH_BONUS is the shared default - _budget_fit_score() no
# longer reads it directly for the exact-match case; it goes through
# policies.city.price_exact_match_bonus(accommodation.city) instead, which
# falls back to this same value (10) for any city that doesn't override it
# (today: busan). Kept here (not removed) since it's still that fallback's
# source of truth and existing callers/tests import it.
PRICE_EXACT_MATCH_BONUS = 10
PRICE_ADJACENT_PENALTY = -2
PRICE_FAR_PENALTY = -6
# Tertile cut-offs over the 27 priced accommodations (min 42,862, median
# 109,000, max 880,000 KRW): low <= 70,000 < medium <= 200,000 < high.
LOW_PRICE_MAX_KRW = 70000
MEDIUM_PRICE_MAX_KRW = 200000
_PRICE_BAND_ORDER = {"low": 0, "medium": 1, "high": 2}
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

# Assumed values, not measured - tune once there's real signal on how much
# parking matters relative to the other factors here. Never a penalty for
# lacking "주차가능": only applies when the trip has at least one car day
# (request.transport_by_day), and only rewards having it.
PARKING_AMENITY_LABEL = "주차가능"
PARKING_BONUS_ALL_CAR = 6
PARKING_BONUS_SOME_CAR = 3


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


def compute_day_endpoints(day_place_map: dict[int, list[PlaceData]]) -> list[tuple[float, float]]:
    """Each day's first and last place coordinates (deduplicated when a
    day has only one place), for accommodation_distance_score - see
    policies/city/jeju.py. Places without coordinates are skipped rather
    than guessed at."""
    endpoints: list[tuple[float, float]] = []
    for places in day_place_map.values():
        with_coordinates = [place for place in places if place.latitude is not None and place.longitude is not None]
        if not with_coordinates:
            continue
        first, last = with_coordinates[0], with_coordinates[-1]
        endpoints.append((first.latitude, first.longitude))
        if last is not first:
            endpoints.append((last.latitude, last.longitude))
    return endpoints


def classify_price_band(price_krw: int) -> BudgetBand:
    if price_krw <= LOW_PRICE_MAX_KRW:
        return "low"
    if price_krw <= MEDIUM_PRICE_MAX_KRW:
        return "medium"
    return "high"


def count_accommodation_types(city: str) -> dict[str, int]:
    return dict(Counter(accommodation.accommodation_type for accommodation in load_city_accommodations(city)))


def _budget_fit_score(accommodation: AccommodationData, requested_band: BudgetBand) -> int:
    if accommodation.average_price_krw is not None:
        band_distance = abs(
            _PRICE_BAND_ORDER[classify_price_band(accommodation.average_price_krw)]
            - _PRICE_BAND_ORDER[requested_band]
        )
        if band_distance == 0:
            return price_exact_match_bonus(accommodation.city)
        if band_distance == 1:
            return PRICE_ADJACENT_PENALTY
        return PRICE_FAR_PENALTY

    if requested_band in accommodation.budget_level:
        return BUDGET_MATCH_BONUS
    return BUDGET_MISMATCH_PENALTY


def _parking_bonus(accommodation: AccommodationData, request: NormalizedRuleRequest) -> int:
    if not request.transport_by_day:
        return 0
    car_day_count = sum(1 for mode in request.transport_by_day if mode == "car")
    if car_day_count == 0:
        return 0
    if PARKING_AMENITY_LABEL not in accommodation.amenities:
        return 0
    if car_day_count == len(request.transport_by_day):
        return PARKING_BONUS_ALL_CAR
    return PARKING_BONUS_SOME_CAR


def accommodation_score(
    accommodation: AccommodationData,
    request: NormalizedRuleRequest,
    reference_point: tuple[float, float] | None,
    day_endpoints: list[tuple[float, float]] | None = None,
) -> float:
    """Rule-based accommodation fitness score.

    Budget fit uses request.accommodation_budget_band (lodging-only budget,
    falling back to the activity budget_band when unset) and two different
    bases, intentionally:
      - If average_price_krw is known, the stay's real nightly rate is
        classified into low/medium/high (see classify_price_band) and compared
        against that band by distance: exact +10, one band off -2,
        two bands off -6.
      - If average_price_krw is None (not researched or not confirmed), the
        coarse budget_level tag is used instead: +6 when it matches, -4 when
        it doesn't. Unknown prices are never guessed at.
    So priced and unpriced accommodations are scored on different bases by
    design - available data is used, missing data isn't inferred.

    accommodation_type does not affect this score - when the user selects
    types, select_accommodation_recommendation narrows the pool to them first.
    view is not read here (data quality too low for this round - see
    AccommodationData.view).

    When the trip has at least one car day (request.transport_by_day), a
    stay with the "주차가능" amenity gets PARKING_BONUS_ALL_CAR (every day is
    a car day) or PARKING_BONUS_SOME_CAR (only some are) - see
    _parking_bonus(). Never a penalty for lacking it, and never applied at
    all when transport_by_day is unset or has no car day.
    """
    score = _budget_fit_score(accommodation, request.accommodation_budget_band)

    if request.companion_type in accommodation.suitable_for:
        score += COMPANION_MATCH_BONUS
    else:
        score += COMPANION_MISMATCH_PENALTY

    score += _parking_bonus(accommodation, request)

    # Seoul/busan/jeju all define this (see each policies/city/*.py module) -
    # score by distance to every day's first/last place INSTEAD OF the
    # single reference_point tiered bonus below. None only for a city whose
    # policy module doesn't define accommodation_distance_score(distances_km) -
    # see policies/city/__init__.py.accommodation_distance_score.
    per_day_endpoint_distance_score = accommodation_distance_score(request, accommodation, day_endpoints or [])
    if per_day_endpoint_distance_score is not None:
        score += per_day_endpoint_distance_score
    elif reference_point is not None and accommodation.latitude is not None and accommodation.longitude is not None:
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


def _tie_break_distance_km(
    accommodation: AccommodationData,
    reference_point: tuple[float, float] | None,
    day_endpoints: list[tuple[float, float]] | None,
) -> float:
    """Distance used ONLY to break an exact accommodation_score() tie
    deterministically - never fed into the score itself. Mirrors whichever
    distance the score's own distance term would have used (the per-day-
    endpoint average when the city defines accommodation_distance_score,
    else the single reference_point distance), so the tie-break stays
    consistent with "closer is better" instead of an unrelated metric.
    A candidate with no coordinates (or no reference at all) sorts last
    among ties via float("inf") - it was already excluded upstream in
    select_accommodation_recommendation whenever any coordinate-having
    candidate exists, so this only matters in the all-candidates-lack-
    coordinates fallback pool.
    """
    if accommodation.latitude is None or accommodation.longitude is None:
        return float("inf")
    if day_endpoints:
        distances_km = [
            haversine_distance_km(accommodation.latitude, accommodation.longitude, lat, lng)
            for lat, lng in day_endpoints
        ]
        return sum(distances_km) / len(distances_km)
    if reference_point is not None:
        return haversine_distance_km(reference_point[0], reference_point[1], accommodation.latitude, accommodation.longitude)
    return float("inf")


def select_accommodation_recommendation(
    accommodations: list[AccommodationData],
    request: NormalizedRuleRequest,
    reference_point: tuple[float, float] | None,
    day_endpoints: list[tuple[float, float]] | None = None,
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

    When the user selected accommodation_types, the coordinate-filtered pool
    is narrowed to those types first, so only those stays are considered. If
    none of the pool matches, the type filter is skipped and the pool above
    is used unchanged, so a selection never empties the recommendation.
    """
    if not accommodations:
        return None

    with_coordinates = [
        accommodation
        for accommodation in accommodations
        if accommodation.latitude is not None and accommodation.longitude is not None
    ]
    candidate_pool = with_coordinates or accommodations
    if request.accommodation_types:
        typed_pool = [
            accommodation
            for accommodation in candidate_pool
            if accommodation.accommodation_type in request.accommodation_types
        ]
        if typed_pool:
            candidate_pool = typed_pool

    # Explicit, deterministic tie-break - never rely on candidate_pool's
    # incoming (catalog file) order. On an exact accommodation_score() tie,
    # prefer the closer-to-the-itinerary candidate (_tie_break_distance_km);
    # if that's ALSO tied, prefer the lexicographically smaller id. Ascending
    # sort on (-score, distance_km, id) reproduces "score desc, distance asc,
    # id asc" in one pass without mixing sort directions.
    ranked = sorted(
        candidate_pool,
        key=lambda accommodation: (
            -accommodation_score(accommodation, request, reference_point, day_endpoints),
            _tie_break_distance_km(accommodation, reference_point, day_endpoints),
            accommodation.id,
        ),
    )
    return ranked[0]
