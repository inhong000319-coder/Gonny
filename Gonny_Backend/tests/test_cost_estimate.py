from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.services.cost_estimate import UNPRICED_PLACE_MAX_KRW, estimate_trip_cost_range


def build_place(place_id: str, average_cost_krw: int | None) -> PlaceData:
    return PlaceData.model_validate(
        {
            "id": place_id,
            "name": place_id,
            "activity_type": ["sightseeing"],
            "budget_level": ["medium"],
            "suitable_for": ["couple"],
            "time_fit": ["morning"],
            "area": "gangnam",
            "duration_hours": 2,
            "priority": 7,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "sample",
            "average_cost_krw": average_cost_krw,
        }
    )


def build_accommodation(average_price_krw: int | None) -> AccommodationData:
    return AccommodationData.model_validate(
        {
            "id": "stay",
            "name": "Stay",
            "city": "busan",
            "area": "haeundae",
            "accommodation_type": "호텔",
            "budget_level": ["medium"],
            "suitable_for": ["couple"],
            "average_price_krw": average_price_krw,
        }
    )


def test_all_priced_places_produce_min_equal_max() -> None:
    places = [build_place("a", 10000), build_place("b", 0), build_place("c", 25000)]

    estimate = estimate_trip_cost_range(places, None, travelers=2, nights=2)

    assert estimate is not None
    assert estimate.min_krw == estimate.max_krw == (10000 + 0 + 25000) * 2
    assert estimate.priced_place_count == 3
    assert estimate.unpriced_place_count == 0


def test_unpriced_place_adds_capped_amount_only_to_max() -> None:
    places = [build_place("a", 10000), build_place("b", None), build_place("c", None)]

    estimate = estimate_trip_cost_range(places, None, travelers=3, nights=1)

    assert estimate is not None
    assert estimate.min_krw == 10000 * 3
    assert estimate.max_krw == estimate.min_krw + UNPRICED_PLACE_MAX_KRW * 3 * 2
    assert estimate.priced_place_count == 1
    assert estimate.unpriced_place_count == 2


def test_same_place_repeated_across_slots_is_counted_once() -> None:
    full_day = build_place("full-day", 15000)

    estimate = estimate_trip_cost_range([full_day, full_day, full_day], None, travelers=2, nights=1)

    assert estimate is not None
    assert estimate.min_krw == estimate.max_krw == 15000 * 2
    assert estimate.priced_place_count == 1


def test_priced_accommodation_is_multiplied_by_nights_and_included() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], build_accommodation(90000), travelers=2, nights=3)

    assert estimate is not None
    assert estimate.accommodation_included is True
    assert estimate.min_krw == 10000 * 2 + 90000 * 3
    assert estimate.max_krw == estimate.min_krw


def test_unpriced_accommodation_is_excluded_and_flagged() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], build_accommodation(None), travelers=2, nights=3)

    assert estimate is not None
    assert estimate.accommodation_included is False
    assert estimate.min_krw == estimate.max_krw == 10000 * 2


def test_missing_accommodation_is_excluded_and_flagged() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], None, travelers=2, nights=3)

    assert estimate is not None
    assert estimate.accommodation_included is False


def test_travelers_multiply_places_but_not_accommodation() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], build_accommodation(50000), travelers=4, nights=2)

    assert estimate is not None
    assert estimate.min_krw == 10000 * 4 + 50000 * 2


def test_returns_none_when_no_places_and_no_accommodation_cost() -> None:
    assert estimate_trip_cost_range([], None, travelers=2, nights=2) is None
    assert estimate_trip_cost_range([], build_accommodation(None), travelers=2, nights=2) is None
