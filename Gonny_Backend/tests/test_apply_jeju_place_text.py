from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from apply_jeju_place_text import apply_rows, validate_rows  # noqa: E402

from app.domains.destination_catalog.schemas import PlaceData  # noqa: E402


def build_row(**overrides) -> dict:
    row = {
        "id": "sample-place",
        "name": "샘플 장소",
        "summary": "샘플 지역의 자연 명소로, 입장료는 무료다.",
        "note_template": "{place_name}은(는) 샘플 지역을 가볍게 둘러보고 싶을 때 좋아요.",
        "highlight_tags": "자연 경관|무료 입장",
        "evidence_basis": "테스트용 근거",
    }
    row.update(overrides)
    return row


def build_place_dict(**overrides) -> dict:
    place = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["자연·트레킹"],
        "budget_level": ["low", "medium"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon"],
        "area": "east-jeju",
        "duration_hours": 2,
        "priority": 8,
        "pace": ["easy"],
        "mobility": ["taxi-needed"],
        "summary": "서귀포 서부에 있는 자연·트레킹 장소다.",
        "note_templates": ["{place_name}은(는) 서귀포 서부 일정에 넣을 수 있는 자연·트레킹 장소예요."],
        "latitude": 33.5,
        "longitude": 126.5,
    }
    place.update(overrides)
    return place


# --- validate_rows() ----------------------------------------------------


def test_validate_rows_accepts_a_well_formed_row() -> None:
    rows = [build_row()]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert errors == []


def test_validate_rows_rejects_an_id_missing_from_the_catalog() -> None:
    rows = [build_row(id="not-in-catalog")]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert any("not-in-catalog" in error and "not found" in error for error in errors)


def test_validate_rows_rejects_duplicate_ids_within_the_csv() -> None:
    rows = [build_row(), build_row()]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert any("duplicate id" in error for error in errors)


def test_validate_rows_rejects_blank_required_fields() -> None:
    for column in ("id", "name", "summary", "note_template", "highlight_tags"):
        rows = [build_row(**{column: ""})]
        errors = validate_rows(rows, existing_ids={"sample-place"})
        assert any(f"blank '{column}'" in error for error in errors), (column, errors)


def test_validate_rows_rejects_a_disallowed_placeholder_in_note_template() -> None:
    rows = [build_row(note_template="{place_name}은(는) {area} 쪽에 있어요.")]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert any("disallowed placeholder" in error for error in errors)


def test_validate_rows_accepts_place_name_placeholder_in_note_template() -> None:
    rows = [build_row(note_template="{place_name}은(는) 좋은 곳이에요.")]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert errors == []


def test_validate_rows_rejects_a_placeholder_in_summary() -> None:
    rows = [build_row(summary="{place_name}은 자연 명소다.")]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert any("summary must not contain placeholders" in error for error in errors)


def test_validate_rows_reports_every_problem_at_once() -> None:
    rows = [build_row(id="", summary="")]
    errors = validate_rows(rows, existing_ids={"sample-place"})
    assert len(errors) >= 2


# --- apply_rows() --------------------------------------------------------


def test_apply_rows_updates_only_the_three_text_fields() -> None:
    catalog = {"places": [build_place_dict()]}
    rows = [build_row()]

    updated_count = apply_rows(catalog, rows)

    place = catalog["places"][0]
    assert updated_count == 1
    assert place["summary"] == "샘플 지역의 자연 명소로, 입장료는 무료다."
    assert place["note_templates"] == ["{place_name}은(는) 샘플 지역을 가볍게 둘러보고 싶을 때 좋아요."]
    assert place["highlight_tags"] == ["자연 경관", "무료 입장"]
    # Every other field is untouched.
    assert place["area"] == "east-jeju"
    assert place["latitude"] == 33.5
    assert place["duration_hours"] == 2
    assert place["mobility"] == ["taxi-needed"]


def test_apply_rows_strips_whitespace_around_highlight_tags() -> None:
    catalog = {"places": [build_place_dict()]}
    rows = [build_row(highlight_tags=" 자연 경관 | 무료 입장 |  ")]

    apply_rows(catalog, rows)

    assert catalog["places"][0]["highlight_tags"] == ["자연 경관", "무료 입장"]


def test_apply_rows_is_idempotent() -> None:
    catalog = {"places": [build_place_dict()]}
    rows = [build_row()]

    apply_rows(catalog, rows)
    first_pass = dict(catalog["places"][0])
    apply_rows(catalog, rows)
    second_pass = catalog["places"][0]

    assert first_pass == second_pass


def test_apply_rows_leaves_other_places_untouched() -> None:
    other_place = build_place_dict(id="other-place", summary="다른 장소 요약")
    catalog = {"places": [build_place_dict(), other_place]}
    rows = [build_row()]

    apply_rows(catalog, rows)

    assert catalog["places"][1]["summary"] == "다른 장소 요약"


# --- real catalog sanity (apply already run) -----------------------------


def test_real_jeju_catalog_has_the_new_text_for_a_sample_place() -> None:
    import json

    payload = json.loads(
        (PROJECT_ROOT / "app" / "data" / "destinations" / "jeju.json").read_text(encoding="utf-8")
    )
    by_id = {p["id"]: p for p in payload["places"]}
    place = PlaceData.model_validate(by_id["soesokkak"])

    assert place.summary == "하효동의 계곡과 바위 경관을 볼 수 있는 자연 명소로, 입장료 없이 상시 개방된다."
    assert place.note_templates == ["{place_name}은(는) 하효동의 계곡과 바위 경관을 가볍게 둘러보고 싶을 때 넣기 좋아요."]
    assert place.highlight_tags == ["자연 경관", "무료 입장", "상시 개방"]
    # Untouched fields stay exactly as scripts/merge_jeju_places.py set them.
    assert place.area == "seogwipo-west"
    assert place.duration_hours == 2
