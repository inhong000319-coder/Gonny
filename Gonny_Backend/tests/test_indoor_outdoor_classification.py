from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.destination_catalog.services.repository import DestinationCatalogRepository

CSV_PATH = PROJECT_ROOT / "local_only" / "data" / "indoor_outdoor_classification.csv"
KOREAN_FOCUS_CITIES = {"seoul", "busan", "jeju"}


def load_csv_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def load_korean_focus_places() -> dict[str, PlaceData]:
    repository = DestinationCatalogRepository()
    places: dict[str, PlaceData] = {}
    for catalog in repository.load_catalogs():
        if catalog.city not in KOREAN_FOCUS_CITIES:
            continue
        for place in catalog.places:
            places[place.id] = place
    return places


def test_setting_and_rain_sensitive_light_fields_exist_on_place_data() -> None:
    place = PlaceData(
        id="sample-place",
        name="Sample Place",
        activity_type=["sightseeing"],
        budget_level=["low"],
        suitable_for=["solo"],
        time_fit=["morning"],
        area="city-center",
        duration_hours=2,
        priority=5,
        pace=["easy"],
        mobility=["walkable"],
        summary="sample summary",
        setting="outdoor",
        rain_sensitive_light=True,
    )

    assert place.setting == "outdoor"
    assert place.rain_sensitive_light is True


def test_setting_defaults_to_none_for_catalogs_without_classification_data() -> None:
    # Only the 109 Seoul/Busan/Jeju places have been classified so far -
    # every other catalog (e.g. bangkok, tokyo, paris) must still load
    # without error rather than failing validation, so setting has to stay
    # optional (rain_sensitive_light still defaults to False either way).
    repository = DestinationCatalogRepository()
    catalogs = repository.load_catalogs()
    non_korean_catalogs = [catalog for catalog in catalogs if catalog.city not in KOREAN_FOCUS_CITIES]
    assert non_korean_catalogs, "expected at least one non-Korean-focus catalog to exist"

    for catalog in non_korean_catalogs:
        for place in catalog.places:
            assert place.setting is None
            assert place.rain_sensitive_light is False


def test_csv_and_seoul_busan_jeju_place_ids_match_exactly() -> None:
    csv_ids = {row["place_id"] for row in load_csv_rows()}
    catalog_ids = set(load_korean_focus_places().keys())

    only_in_csv = csv_ids - catalog_ids
    only_in_catalog = catalog_ids - csv_ids

    assert not only_in_csv, f"CSV has place_id(s) not found in seoul/busan/jeju catalogs: {sorted(only_in_csv)}"
    assert not only_in_catalog, f"seoul/busan/jeju catalogs have place_id(s) missing from the CSV: {sorted(only_in_catalog)}"


def test_all_109_korean_focus_places_are_classified_and_match_csv() -> None:
    csv_rows = load_csv_rows()
    assert len(csv_rows) == 109

    places = load_korean_focus_places()
    assert len(places) == 109

    setting_counts: dict[str, int] = {}
    rain_sensitive_light_true_count = 0

    for row in csv_rows:
        place = places[row["place_id"]]
        expected_rain_sensitive_light = row["rain_sensitive_light"].strip().lower() == "true"

        assert place.setting == row["setting"], f"{row['place_id']}: setting mismatch"
        assert place.rain_sensitive_light == expected_rain_sensitive_light, f"{row['place_id']}: rain_sensitive_light mismatch"

        setting_counts[place.setting] = setting_counts.get(place.setting, 0) + 1
        if place.rain_sensitive_light:
            rain_sensitive_light_true_count += 1

    assert setting_counts == {"outdoor": 50, "indoor": 40, "mixed": 19}
    assert rain_sensitive_light_true_count == 23
