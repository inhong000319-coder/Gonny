from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.destination_catalog.services.repository import DestinationCatalogRepository

KOREAN_FOCUS_CITIES = {"seoul", "busan", "jeju"}


def load_korean_focus_places() -> list[PlaceData]:
    repository = DestinationCatalogRepository()
    places: list[PlaceData] = []
    for catalog in repository.load_catalogs():
        if catalog.city in KOREAN_FOCUS_CITIES:
            places.extend(catalog.places)
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


def test_seoul_busan_jeju_catalogs_have_109_unique_place_ids() -> None:
    # This used to cross-check against local_only/data/indoor_outdoor_
    # classification.csv, but local_only/ isn't committed to git, so that
    # comparison always failed on a fresh clone/CI. The place_id-level
    # match against that CSV was already verified once when the setting/
    # rain_sensitive_light data was applied (see feature/indoor-outdoor-
    # labels) - this just guards the count/uniqueness invariant going forward.
    ids = [place.id for place in load_korean_focus_places()]

    assert len(ids) == 109
    assert len(set(ids)) == len(ids), "duplicate place_id found across seoul/busan/jeju catalogs"


def test_all_109_korean_focus_places_are_classified() -> None:
    # Expected distribution was verified once against local_only/data/
    # indoor_outdoor_classification.csv when the setting/rain_sensitive_
    # light data was applied to the catalog JSON files (see feature/
    # indoor-outdoor-labels). local_only/ isn't committed to git, so this
    # test hardcodes the already-verified expectations instead of
    # re-reading that CSV - otherwise it would always fail on a fresh
    # clone/CI where local_only/ doesn't exist.
    EXPECTED_SETTING_COUNTS = {"outdoor": 50, "indoor": 40, "mixed": 19}
    EXPECTED_RAIN_SENSITIVE_LIGHT_TRUE_COUNT = 23

    places = load_korean_focus_places()
    assert len(places) == 109

    setting_counts: dict[str, int] = {}
    rain_sensitive_light_true_count = 0

    for place in places:
        assert place.setting is not None, f"{place.id} is missing setting classification"
        setting_counts[place.setting] = setting_counts.get(place.setting, 0) + 1
        if place.rain_sensitive_light:
            rain_sensitive_light_true_count += 1

    assert setting_counts == EXPECTED_SETTING_COUNTS
    assert rain_sensitive_light_true_count == EXPECTED_RAIN_SENSITIVE_LIGHT_TRUE_COUNT
