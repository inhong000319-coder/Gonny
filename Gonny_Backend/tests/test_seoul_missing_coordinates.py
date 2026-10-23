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

from apply_seoul_missing_coordinates import NEW_COORDINATES, validate  # noqa: E402

from app.domains.destination_catalog.schemas import PlaceData  # noqa: E402


def _load_real_seoul_places() -> dict[str, dict]:
    data = json.loads((PROJECT_ROOT / "app" / "data" / "destinations" / "seoul.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["places"]}


# --- real catalog sanity (script already applied) --------------------------


def test_the_3_places_have_their_google_maps_coordinates() -> None:
    by_id = _load_real_seoul_places()
    for place_id, lat, lon in NEW_COORDINATES:
        place = PlaceData.model_validate(by_id[place_id])
        assert place.latitude == lat, place_id
        assert place.longitude == lon, place_id


def test_a_place_with_preexisting_coordinates_is_unaffected() -> None:
    by_id = _load_real_seoul_places()
    place = PlaceData.model_validate(by_id["sewoon-plaza"])
    assert place.latitude == 37.5693347773
    assert place.longitude == 126.9952555258


def test_rerunning_validate_on_the_real_catalog_finds_no_problems() -> None:
    by_id = _load_real_seoul_places()
    problems = validate(list(by_id.values()))
    assert problems == []


# --- validate() never overwrites a differing pre-existing coordinate -------


def test_validate_reports_a_problem_for_a_conflicting_preexisting_coordinate() -> None:
    by_id = _load_real_seoul_places()
    places = list(by_id.values())
    places = [dict(p, latitude=0.0, longitude=0.0) if p["id"] == "daelim-sangga" else p for p in places]
    problems = validate(places)
    assert any("daelim-sangga" in p and "덮어쓰지" in p for p in problems)
