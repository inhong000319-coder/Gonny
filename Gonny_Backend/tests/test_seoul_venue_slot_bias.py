from __future__ import annotations

import json
from pathlib import Path

from app.domains.destination_catalog.schemas import PlaceData

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_seoul_place(place_id: str) -> PlaceData:
    data = json.loads((PROJECT_ROOT / "app" / "data" / "destinations" / "seoul.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in data["places"]}
    return PlaceData.model_validate(by_id[place_id])


def test_rolling_hall_evening_slot_bias_is_3() -> None:
    # Lowered from 8 to 3 (scenario B, see local_only/reports/
    # seoul_venue_slot_bias_apply.md) - a data-only, easily reversible
    # adjustment, not a fix backed by a documented design rationale
    # (the original 8 came from a 2026-07-27 checkpoint commit with no
    # explanation - see seoul_venue_sensitivity.md item 4).
    place = _load_seoul_place("rolling-hall")
    assert place.slot_bias == {"afternoon": 2, "evening": 3, "morning": -5}


def test_kbs_hall_evening_slot_bias_is_3() -> None:
    place = _load_seoul_place("kbs-hall")
    assert place.slot_bias == {"afternoon": 3, "evening": 3, "morning": -4}
