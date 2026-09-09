from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.accommodation_catalog.schemas import AccommodationData, CityAccommodationCatalog
from app.services.external_clients import extract_lodging_amenities

ACCOMMODATIONS_DIR = PROJECT_ROOT / "app" / "data" / "accommodations"
MIN_SELECTED_PER_CITY = 10
MAX_SELECTED_PER_CITY = 15


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "sample-hotel",
        "name": "Sample Hotel",
        "city": "seoul",
        "area": "gangnam",
        "accommodation_type": "호텔",
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)


def test_accommodation_data_requires_only_id_name_city_area_and_type() -> None:
    accommodation = build_accommodation()

    assert accommodation.latitude is None
    assert accommodation.content_id is None
    assert accommodation.amenities == []
    assert accommodation.budget_level == []
    assert accommodation.budget_level_estimated is True
    assert accommodation.suitable_for == []
    assert accommodation.checkin_time is None
    assert accommodation.checkout_time is None
    assert accommodation.view is None


def test_accommodation_data_stores_checkin_checkout_verbatim() -> None:
    # Same principle as PlaceData.open_hours/closed_days: raw TourAPI text,
    # not parsed - "익일 12:00" is not a plain HH:MM value and must survive
    # untouched.
    accommodation = build_accommodation(checkin_time="15:00", checkout_time="익일 12:00")

    assert accommodation.checkin_time == "15:00"
    assert accommodation.checkout_time == "익일 12:00"


def test_city_accommodation_catalog_wraps_a_list() -> None:
    catalog = CityAccommodationCatalog(
        city="seoul",
        accommodations=[build_accommodation(), build_accommodation(id="sample-hotel-2")],
    )

    assert catalog.city == "seoul"
    assert len(catalog.accommodations) == 2


def test_extract_lodging_amenities_reads_only_available_flags() -> None:
    detail = {
        "parkinglodging": "가능",
        "chkcooking": "불가능",  # must not be misread as available via a naive "가능" substring check
        "fitness": "1",
        "sauna": "0",
        "seminar": "",
    }

    amenities = extract_lodging_amenities(detail)

    assert "주차가능" in amenities
    assert "취사가능" not in amenities
    assert "피트니스" in amenities
    assert "사우나" not in amenities
    assert "세미나실" not in amenities


def test_extract_lodging_amenities_empty_when_nothing_available() -> None:
    detail = {"parkinglodging": "불가", "chkcooking": "", "fitness": "0"}

    assert extract_lodging_amenities(detail) == []


def _load_city_catalog(city: str) -> CityAccommodationCatalog:
    path = ACCOMMODATIONS_DIR / f"{city}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CityAccommodationCatalog.model_validate(payload)


def test_each_city_has_between_min_and_max_accommodations() -> None:
    for city in ["seoul", "busan", "jeju"]:
        catalog = _load_city_catalog(city)
        assert MIN_SELECTED_PER_CITY <= len(catalog.accommodations) <= MAX_SELECTED_PER_CITY, city


def test_accommodation_types_are_not_dominated_by_a_single_type() -> None:
    # No single accommodation_type should make up more than ~60% of a
    # city's selection - the round-robin selection in
    # fetch_accommodation_catalog.py is designed to prevent 호텔 (the most
    # common registered category) from crowding out everything else.
    for city in ["seoul", "busan", "jeju"]:
        catalog = _load_city_catalog(city)
        type_counts: dict[str, int] = {}
        for accommodation in catalog.accommodations:
            type_counts[accommodation.accommodation_type] = type_counts.get(accommodation.accommodation_type, 0) + 1

        assert len(type_counts) >= 2, f"{city}: only one accommodation_type present"
        most_common_share = max(type_counts.values()) / len(catalog.accommodations)
        assert most_common_share <= 0.6, f"{city}: {type_counts}"


def test_accommodation_areas_overlap_existing_destination_catalog_areas() -> None:
    destinations_dir = PROJECT_ROOT / "app" / "data" / "destinations"
    for city in ["seoul", "busan", "jeju"]:
        destination_payload = json.loads((destinations_dir / f"{city}.json").read_text(encoding="utf-8"))
        known_areas = {place["area"] for place in destination_payload["places"]}

        catalog = _load_city_catalog(city)
        for accommodation in catalog.accommodations:
            assert accommodation.area in known_areas, (city, accommodation.id, accommodation.area)


def test_accommodations_have_coordinates_and_content_id() -> None:
    for city in ["seoul", "busan", "jeju"]:
        catalog = _load_city_catalog(city)
        for accommodation in catalog.accommodations:
            assert accommodation.latitude is not None, accommodation.id
            assert accommodation.longitude is not None, accommodation.id
            assert accommodation.content_id is not None, accommodation.id


def test_most_accommodations_have_checkin_checkout_populated() -> None:
    # Not asserting 100%: a handful of detailIntro2 responses can come back
    # with the field genuinely empty (same "TourAPI data itself is blank"
    # situation seen with PlaceData.open_hours), but the large majority
    # should be populated given checkintime/checkouttime were confirmed
    # available for contentTypeId=32 in general.
    for city in ["seoul", "busan", "jeju"]:
        catalog = _load_city_catalog(city)
        with_checkin = sum(1 for accommodation in catalog.accommodations if accommodation.checkin_time)
        assert with_checkin >= len(catalog.accommodations) * 0.7, city
