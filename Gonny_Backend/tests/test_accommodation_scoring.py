from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.rule_planner.services.accommodation_scoring import (
    accommodation_score,
    compute_reference_point,
    load_city_accommodations,
    select_accommodation_recommendation,
)
from app.schemas.place_catalog import CityPlaceCatalog, PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest, RuleItineraryRequest
from app.services.rule_itinerary_service import RuleItineraryService

# Roughly central Seoul, used as a stand-in "reference point" in tests
# that don't need a real itinerary to derive one.
SEOUL_REFERENCE_POINT = (37.5665, 126.9780)


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "sample-hotel",
        "name": "Sample Hotel",
        "city": "seoul",
        "area": "gangnam",
        "accommodation_type": "호텔",
        "budget_level": ["medium"],
        "suitable_for": ["solo", "couple"],
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)


def build_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "seoul",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
        "companion_type": "couple",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["sightseeing"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "gangnam",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample summary",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


# accommodation_score()


def test_budget_match_scores_higher_than_mismatch() -> None:
    request = build_request(budget_band="high")
    matching = build_accommodation(budget_level=["high"])
    mismatched = build_accommodation(id="other", budget_level=["low"])

    assert accommodation_score(matching, request, None) > accommodation_score(mismatched, request, None)


def test_companion_match_scores_higher_than_mismatch() -> None:
    request = build_request(companion_type="family")
    matching = build_accommodation(suitable_for=["family"])
    mismatched = build_accommodation(id="other", suitable_for=["solo"])

    assert accommodation_score(matching, request, None) > accommodation_score(mismatched, request, None)


def test_closer_accommodation_scores_higher_than_farther_one() -> None:
    request = build_request()
    # ~200m from the reference point.
    nearby = build_accommodation(id="nearby", latitude=37.5680, longitude=126.9790)
    # ~40km away (well past FAR_DISTANCE_KM).
    far = build_accommodation(id="far", latitude=37.9000, longitude=127.3000)

    nearby_score = accommodation_score(nearby, request, SEOUL_REFERENCE_POINT)
    far_score = accommodation_score(far, request, SEOUL_REFERENCE_POINT)

    assert nearby_score > far_score


def test_accommodation_type_does_not_affect_score() -> None:
    request = build_request()
    hotel = build_accommodation(accommodation_type="호텔")
    hostel = build_accommodation(id="other", accommodation_type="호스텔")

    assert accommodation_score(hotel, request, None) == accommodation_score(hostel, request, None)


def test_missing_coordinates_contribute_no_location_bonus_or_penalty() -> None:
    request = build_request()
    without_coords = build_accommodation(latitude=None, longitude=None)

    with_reference = accommodation_score(without_coords, request, SEOUL_REFERENCE_POINT)
    without_reference = accommodation_score(without_coords, request, None)

    assert with_reference == without_reference


# select_accommodation_recommendation()


def test_select_prefers_coordinate_having_candidates_when_any_exist() -> None:
    request = build_request(budget_band="low", companion_type="solo")
    # Scores better on budget/companion fit but has no coordinates.
    no_coords_but_better_fit = build_accommodation(
        id="no-coords",
        budget_level=["low"],
        suitable_for=["solo"],
        latitude=None,
        longitude=None,
    )
    # Worse fit on budget/companion but does have coordinates.
    with_coords_worse_fit = build_accommodation(
        id="with-coords",
        budget_level=["high"],
        suitable_for=["family"],
        latitude=37.5665,
        longitude=126.9780,
    )

    selected = select_accommodation_recommendation(
        [no_coords_but_better_fit, with_coords_worse_fit], request, None
    )

    assert selected.id == "with-coords"


def test_select_falls_back_to_full_pool_when_nobody_has_coordinates() -> None:
    request = build_request(budget_band="low", companion_type="solo")
    better_fit = build_accommodation(id="better", budget_level=["low"], suitable_for=["solo"], latitude=None, longitude=None)
    worse_fit = build_accommodation(id="worse", budget_level=["high"], suitable_for=["family"], latitude=None, longitude=None)

    selected = select_accommodation_recommendation([better_fit, worse_fit], request, None)

    assert selected.id == "better"


def test_select_returns_none_for_empty_list() -> None:
    assert select_accommodation_recommendation([], build_request(), None) is None


# compute_reference_point()


def test_reference_point_uses_most_visited_area() -> None:
    catalog = CityPlaceCatalog(
        continent="asia",
        country="korea",
        city="seoul",
        places=[
            build_place(id="a", area="gangnam", latitude=37.50, longitude=127.02),
            build_place(id="b", area="gangnam", latitude=37.52, longitude=127.04),
            build_place(id="c", area="hongdae", latitude=37.55, longitude=126.92),
        ],
    )
    day_place_map = {
        1: [catalog.places[0], catalog.places[1]],
        2: [catalog.places[0]],  # gangnam visited 3 times total, hongdae once
        3: [catalog.places[2]],
    }

    reference_point = compute_reference_point(day_place_map, catalog)

    assert reference_point == pytest.approx((37.51, 127.03))  # average of the two gangnam places


def test_reference_point_none_when_no_places_visited() -> None:
    catalog = CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=[])

    assert compute_reference_point({}, catalog) is None


# load_city_accommodations()


def test_load_city_accommodations_returns_empty_list_for_unknown_city() -> None:
    assert load_city_accommodations("nonexistent-city") == []


def test_load_city_accommodations_reads_real_seoul_data() -> None:
    accommodations = load_city_accommodations("seoul")

    assert 10 <= len(accommodations) <= 15
    assert all(isinstance(item, AccommodationData) for item in accommodations)


# End-to-end integration


def test_generate_includes_an_accommodation_recommendation() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(city="seoul", concepts=["culture", "food"], nights=2, days=3)
    )

    assert response.accommodation_recommendation is not None
    assert response.accommodation_recommendation.city == "seoul"


def test_generate_recommends_different_accommodation_for_different_budget_and_companion() -> None:
    service = RuleItineraryService()
    low_solo_response = service.generate(
        RuleItineraryRequest(
            city="seoul", concepts=["culture", "food"], nights=2, days=3, budget_band="low", companion_type="solo"
        )
    )
    high_family_response = service.generate(
        RuleItineraryRequest(
            city="seoul", concepts=["culture", "food"], nights=2, days=3, budget_band="high", companion_type="family"
        )
    )

    assert low_solo_response.accommodation_recommendation is not None
    assert high_family_response.accommodation_recommendation is not None
    assert low_solo_response.accommodation_recommendation.id != high_family_response.accommodation_recommendation.id
