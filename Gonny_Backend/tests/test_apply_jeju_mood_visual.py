from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from apply_jeju_mood_visual import apply_rows, validate_rows  # noqa: E402


def build_row(**overrides) -> dict:
    row = {"id": "sample-place", "mood": "", "visual_feature": "야경|포토스팟"}
    row.update(overrides)
    return row


# --- validate_rows() ----------------------------------------------------


def test_validate_rows_accepts_a_well_formed_row() -> None:
    assert validate_rows([build_row()], existing_ids={"sample-place"}) == []


def test_validate_rows_rejects_an_id_missing_from_the_catalog() -> None:
    errors = validate_rows([build_row(id="not-in-catalog")], existing_ids={"sample-place"})
    assert any("not-in-catalog" in error and "not found" in error for error in errors)


def test_validate_rows_rejects_blank_id() -> None:
    errors = validate_rows([build_row(id="")], existing_ids={"sample-place"})
    assert any("blank id" in error for error in errors)


def test_validate_rows_rejects_duplicate_id() -> None:
    errors = validate_rows([build_row(), build_row()], existing_ids={"sample-place"})
    assert any("duplicate id" in error for error in errors)


def test_validate_rows_rejects_a_mood_value_outside_the_vocabulary() -> None:
    errors = validate_rows([build_row(mood="신남", visual_feature="")], existing_ids={"sample-place"})
    assert any("mood value(s) outside allowed vocabulary" in error for error in errors)


def test_validate_rows_rejects_a_visual_feature_value_outside_the_vocabulary() -> None:
    errors = validate_rows([build_row(visual_feature="웅장함")], existing_ids={"sample-place"})
    assert any("visual_feature value(s) outside allowed vocabulary" in error for error in errors)


def test_validate_rows_accepts_every_allowed_value() -> None:
    row = build_row(mood="활기참|조용함", visual_feature="포토스팟|야경")
    assert validate_rows([row], existing_ids={"sample-place"}) == []


# --- apply_rows() --------------------------------------------------------


def test_apply_rows_writes_only_non_blank_csv_fields() -> None:
    catalog = {"places": [{"id": "sample-place", "mood": [], "visual_feature": []}]}
    applied, skipped = apply_rows(catalog, [build_row(mood="", visual_feature="야경")])

    place = catalog["places"][0]
    assert place["visual_feature"] == ["야경"]
    assert place["mood"] == []  # blank CSV cell - left untouched
    assert applied == {"sample-place": ["visual_feature"]}
    assert skipped == []


def test_apply_rows_strips_whitespace_and_splits_on_pipe() -> None:
    catalog = {"places": [{"id": "sample-place", "mood": [], "visual_feature": []}]}
    apply_rows(catalog, [build_row(visual_feature=" 야경 | 포토스팟 ")])

    assert catalog["places"][0]["visual_feature"] == ["야경", "포토스팟"]


def test_apply_rows_skips_and_reports_a_field_that_already_has_a_value() -> None:
    catalog = {"places": [{"id": "sample-place", "mood": [], "visual_feature": ["야경"]}]}
    applied, skipped = apply_rows(catalog, [build_row(visual_feature="포토스팟")])

    assert catalog["places"][0]["visual_feature"] == ["야경"]  # unchanged
    assert applied == {}
    assert skipped == [("sample-place", "visual_feature", ["야경"])]


def test_apply_rows_is_idempotent() -> None:
    catalog = {"places": [{"id": "sample-place", "mood": [], "visual_feature": []}]}
    row = build_row(mood="조용함", visual_feature="야경")

    apply_rows(catalog, [row])
    first_pass_place = dict(catalog["places"][0])
    applied_second, skipped_second = apply_rows(catalog, [row])

    assert catalog["places"][0] == first_pass_place
    assert applied_second == {}
    assert len(skipped_second) == 2


def test_apply_rows_leaves_other_places_untouched() -> None:
    other_place = {"id": "other-place", "mood": [], "visual_feature": []}
    catalog = {"places": [{"id": "sample-place", "mood": [], "visual_feature": []}, other_place]}

    apply_rows(catalog, [build_row(visual_feature="야경")])

    assert catalog["places"][1]["mood"] == []
    assert catalog["places"][1]["visual_feature"] == []


# --- real catalog sanity (script already applied) -----------------------


def test_real_jeju_catalog_has_the_applied_mood_visual_values() -> None:
    import json

    payload = json.loads(
        (PROJECT_ROOT / "app" / "data" / "destinations" / "jeju.json").read_text(encoding="utf-8")
    )
    by_id = {p["id"]: p for p in payload["places"]}

    assert by_id["saeyeongyo-saeseom"]["visual_feature"] == ["야경", "포토스팟"]
    assert "mood" not in by_id["saeyeongyo-saeseom"]  # blank CSV cell - left untouched

    assert by_id["jeju-mokgwana"]["visual_feature"] == ["야경"]
    assert "mood" not in by_id["jeju-mokgwana"]

    assert by_id["namwon-keuneong"]["mood"] == ["조용함"]
    assert "visual_feature" not in by_id["namwon-keuneong"]

    # The other 21 new places stay untouched (no evidence available).
    other_new_place = by_id["soesokkak"]
    assert other_new_place.get("mood") in (None, [])
    assert other_new_place.get("visual_feature") in (None, [])
