from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pytest

from fill_place_coordinates import apply_coordinates

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"

# The 4 ids the fix script deliberately leaves unfilled (no confirmed source).
EXPECTED_STILL_MISSING = {
    "seoul": {"e-land-hangang-cruise", "s-factory", "daelim-sangga"},
    "busan": set(),
    "jeju": {"delmoondo-gimnyeong"},
}

CITY_BOUNDS = {
    "seoul": (37.4, 37.75, 126.75, 127.25),
    "busan": (34.95, 35.35, 128.8, 129.35),
    "jeju": (33.1, 33.6, 126.1, 127.0),
}


def _load_places(city: str) -> list[dict]:
    payload = json.loads((DESTINATIONS_DIR / f"{city}.json").read_text(encoding="utf-8"))
    return payload["places"]


def _build_payload(places: list[dict]) -> dict:
    return {"city": "testcity", "places": places}


# --- apply_coordinates() (the pure logic behind scripts/fill_place_coordinates.py) ---


def test_unknown_place_id_raises_and_leaves_payload_unmodified() -> None:
    payload = _build_payload([{"id": "known-place", "name": "Known", "latitude": None, "longitude": None}])
    payloads = {"testcity": payload}

    with pytest.raises(RuntimeError):
        apply_coordinates(payloads, [("testcity", "missing-place", 1.0, 2.0)])

    assert payload["places"][0]["latitude"] is None


def test_conflicting_existing_coordinates_raise_instead_of_overwriting() -> None:
    payload = _build_payload([{"id": "p", "name": "P", "latitude": 10.0, "longitude": 20.0}])
    payloads = {"testcity": payload}

    with pytest.raises(RuntimeError):
        apply_coordinates(payloads, [("testcity", "p", 11.0, 20.0)])

    # Untouched - the conflicting original value is still there.
    assert payload["places"][0]["latitude"] == 10.0


def test_rerunning_after_a_successful_fill_is_a_no_op() -> None:
    payload = _build_payload([{"id": "p", "name": "P", "latitude": None, "longitude": None}])
    payloads = {"testcity": payload}
    coordinates = [("testcity", "p", 10.0, 20.0)]

    filled_first, skipped_first, *_ = apply_coordinates(payloads, coordinates)
    assert (filled_first, skipped_first) == (1, 0)
    assert payload["places"][0]["latitude"] == 10.0

    filled_second, skipped_second, *_ = apply_coordinates(payloads, coordinates)
    assert (filled_second, skipped_second) == (0, 1)
    assert payload["places"][0]["latitude"] == 10.0


# --- Real catalog data, after the fill has been applied ---


def test_only_the_four_unresolved_places_still_lack_coordinates() -> None:
    for city, expected_missing in EXPECTED_STILL_MISSING.items():
        places = _load_places(city)
        missing = {place["id"] for place in places if place.get("latitude") is None}
        assert missing == expected_missing, city


def test_every_filled_coordinate_is_within_its_city_bounds() -> None:
    for city, (lat_min, lat_max, lng_min, lng_max) in CITY_BOUNDS.items():
        places = _load_places(city)
        for place in places:
            latitude, longitude = place.get("latitude"), place.get("longitude")
            if latitude is None:
                continue
            assert lat_min <= latitude <= lat_max, (city, place["id"], latitude)
            assert lng_min <= longitude <= lng_max, (city, place["id"], longitude)
