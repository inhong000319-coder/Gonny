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


def test_priced_accommodation_is_never_added_to_the_cost_range() -> None:
    # 숙박비는 시기별 편차가 커 예상 비용에 더하지 않는다(가격이 확인된
    # 경우도 마찬가지) - accommodation_scoring/숙소 추천 로직은 건드리지
    # 않으므로 AccommodationData.average_price_krw 자체는 그대로 둔다.
    estimate = estimate_trip_cost_range([build_place("a", 10000)], build_accommodation(90000), travelers=2, nights=3)

    assert estimate is not None
    assert estimate.accommodation_included is False
    assert estimate.min_krw == estimate.max_krw == 10000 * 2


def test_unpriced_accommodation_is_still_excluded() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], build_accommodation(None), travelers=2, nights=3)

    assert estimate is not None
    assert estimate.accommodation_included is False
    assert estimate.min_krw == estimate.max_krw == 10000 * 2


def test_missing_accommodation_is_still_excluded() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], None, travelers=2, nights=3)

    assert estimate is not None
    assert estimate.accommodation_included is False


def test_accommodation_included_is_always_false_regardless_of_price() -> None:
    for accommodation in (build_accommodation(90000), build_accommodation(None), None):
        estimate = estimate_trip_cost_range([build_place("a", 10000)], accommodation, travelers=2, nights=3)
        assert estimate is not None
        assert estimate.accommodation_included is False


def test_travelers_multiply_places_but_accommodation_never_counts() -> None:
    estimate = estimate_trip_cost_range([build_place("a", 10000)], build_accommodation(50000), travelers=4, nights=2)

    assert estimate is not None
    assert estimate.min_krw == 10000 * 4


def test_returns_none_when_no_places_even_with_a_priced_accommodation() -> None:
    # 조기 반환은 장소 유무만으로 판단한다 - 숙소만 있고 장소가 없는 경우도
    # (가격이 있든 없든) None이어야 한다.
    assert estimate_trip_cost_range([], None, travelers=2, nights=2) is None
    assert estimate_trip_cost_range([], build_accommodation(None), travelers=2, nights=2) is None
    assert estimate_trip_cost_range([], build_accommodation(90000), travelers=2, nights=2) is None
