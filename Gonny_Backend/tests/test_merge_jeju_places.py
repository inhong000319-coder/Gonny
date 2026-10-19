from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from merge_jeju_places import (  # noqa: E402
    _budget_level,
    _rain_sensitive_light,
    _resolve_average_cost_krw,
    _time_fit,
    merge_rows_into_catalog,
    row_to_place_data,
)

from app.domains.destination_catalog.schemas import PlaceData  # noqa: E402


def build_row(**overrides) -> dict:
    row = {
        "id": "sample-place",
        "name": "샘플 장소",
        "city": "jeju",
        "area_suggestion": "east-jeju",
        "zone": "jeju-city",
        "content_id": "12345",
        "activity_type": "자연·트레킹",
        "setting": "outdoor",
        "average_cost_krw": "",
        "is_free": "",
        "open_hours": "09:00~18:00",
        "closed_days": "연중무휴",
        "latitude": "33.5",
        "longitude": "126.5",
        "address": "제주시 어딘가",
        "confidence": "high",
        "evidence_note": "테스트용 근거",
        "source": "https://example.com",
    }
    row.update(overrides)
    return row


# --- _resolve_average_cost_krw / _budget_level ------------------------------


def test_resolve_average_cost_krw_uses_the_numeric_value_when_present() -> None:
    row = build_row(average_cost_krw="2000", is_free="")
    assert _resolve_average_cost_krw(row) == 2000


def test_resolve_average_cost_krw_is_zero_when_is_free_true() -> None:
    row = build_row(average_cost_krw="", is_free="true")
    assert _resolve_average_cost_krw(row) == 0


def test_resolve_average_cost_krw_is_none_when_neither_is_set() -> None:
    row = build_row(average_cost_krw="", is_free="")
    assert _resolve_average_cost_krw(row) is None


def test_budget_level_tiers_by_resolved_cost() -> None:
    assert _budget_level(0) == ["low", "medium"]
    assert _budget_level(10000) == ["low", "medium"]
    assert _budget_level(10001) == ["medium", "high"]
    assert _budget_level(None) == ["low", "medium", "high"]


# --- _time_fit boundary cases ------------------------------------------------


def test_time_fit_always_open_includes_evening() -> None:
    assert _time_fit("상시 개방") == ["morning", "afternoon", "evening"]
    # A trailing note after the always-open marker doesn't change the result.
    assert _time_fit("상시 개방 ※ 일몰 전 이용 권장") == ["morning", "afternoon", "evening"]


def test_time_fit_closing_at_exactly_18_is_morning_afternoon_only() -> None:
    assert _time_fit("09:00~18:00") == ["morning", "afternoon"]


def test_time_fit_closing_at_exactly_21_includes_evening() -> None:
    assert _time_fit("09:00~21:00") == ["morning", "afternoon", "evening"]


def test_time_fit_closing_past_21_includes_evening() -> None:
    assert _time_fit("09:00~22:00 (입장 마감 21:20)") == ["morning", "afternoon", "evening"]


def test_time_fit_gap_between_18_and_21_falls_back() -> None:
    # 19:00 is neither <= 18:00 nor >= 21:00 - the spec only gives those two
    # rules, so this (and any other unparseable case) uses the same
    # fallback it defines for "can't parse at all".
    assert _time_fit("09:00~19:00") == ["morning", "afternoon"]


def test_time_fit_takes_the_latest_closing_time_across_a_seasonal_schedule() -> None:
    # [하절기] closes 21:00 (evening-inclusive), [동절기] closes 20:00 (gap) -
    # the later of the two should govern.
    assert _time_fit("[하절기] 07:00~21:00 / [동절기] 07:00~20:00") == ["morning", "afternoon", "evening"]


def test_time_fit_falls_back_when_no_pattern_is_found() -> None:
    assert _time_fit("문의 필요") == ["morning", "afternoon"]


# --- _rain_sensitive_light ----------------------------------------------------


def test_rain_sensitive_light_true_for_outdoor_beach_by_name() -> None:
    assert _rain_sensitive_light("outdoor", "표선 해비치 해변") is True
    assert _rain_sensitive_light("outdoor", "협재해수욕장") is True


def test_rain_sensitive_light_false_for_outdoor_non_beach() -> None:
    assert _rain_sensitive_light("outdoor", "산방굴사(산방산)") is False


def test_rain_sensitive_light_false_for_indoor_and_mixed_even_if_name_says_beach() -> None:
    assert _rain_sensitive_light("indoor", "해변 박물관") is False
    assert _rain_sensitive_light("mixed", "해수욕장 전시관") is False


# --- row_to_place_data() field mapping ---------------------------------------


def test_row_to_place_data_produces_a_valid_place() -> None:
    row = build_row()
    place = PlaceData.model_validate(row_to_place_data(row))

    assert place.id == "sample-place"
    assert place.area == "east-jeju"
    assert place.activity_type == ["자연·트레킹"]
    assert place.duration_hours == 2
    assert place.pace == ["easy"]
    assert place.mobility == ["taxi-needed"]
    assert place.suitable_for == ["solo", "couple", "friend", "family"]
    assert place.mood == []
    assert place.visual_feature == []
    assert place.mood_keywords == []
    assert place.highlight_tags == []
    assert "{place_name}" in place.note_templates[0]


def test_row_to_place_data_splits_pipe_separated_activity_types() -> None:
    row = build_row(activity_type="문화·역사|자연·트레킹")
    place = row_to_place_data(row)
    assert place["activity_type"] == ["문화·역사", "자연·트레킹"]
    # The generated sentence uses only the first type.
    assert "문화·역사" in place["summary"]
    assert "자연·트레킹" not in place["summary"]


def test_row_to_place_data_high_confidence_gets_core_tier_and_top_priority() -> None:
    place = row_to_place_data(build_row(confidence="high"))
    assert place["mvp_tier"] == "core"
    assert place["priority"] == 8


def test_row_to_place_data_medium_confidence_keeps_default_tier() -> None:
    place = row_to_place_data(build_row(confidence="medium"))
    assert "mvp_tier" not in place
    assert place["priority"] == 6


def test_row_to_place_data_blank_optional_strings_become_none() -> None:
    place = row_to_place_data(build_row(content_id="", open_hours="", closed_days=""))
    assert place["content_id"] is None
    assert place["closed_days"] is None


# --- merge_rows_into_catalog() idempotency -----------------------------------


def test_merge_rows_into_catalog_adds_new_rows_once() -> None:
    catalog = {"places": [{"id": "already-there", "name": "Existing"}]}
    rows = [build_row(id="new-1", name="New One"), build_row(id="new-2", name="New Two")]

    added, already_merged = merge_rows_into_catalog(catalog, rows)

    assert (added, already_merged) == (2, 0)
    assert {p["id"] for p in catalog["places"]} == {"already-there", "new-1", "new-2"}


def test_merge_rows_into_catalog_skips_already_merged_ids_on_rerun() -> None:
    catalog = {"places": [{"id": "already-there", "name": "Existing"}]}
    rows = [build_row(id="new-1", name="New One")]

    merge_rows_into_catalog(catalog, rows)
    added_second_run, already_merged_second_run = merge_rows_into_catalog(catalog, rows)

    assert (added_second_run, already_merged_second_run) == (0, 1)
    assert len(catalog["places"]) == 2


def test_merge_rows_into_catalog_raises_on_duplicate_id_within_the_same_run() -> None:
    catalog = {"places": []}
    rows = [build_row(id="dup", name="A"), build_row(id="dup", name="B")]

    try:
        merge_rows_into_catalog(catalog, rows)
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- real catalog sanity (merge already applied) -----------------------------


def test_real_jeju_catalog_has_120_places_with_required_fields() -> None:
    import json

    payload = json.loads(
        (PROJECT_ROOT / "app" / "data" / "destinations" / "jeju.json").read_text(encoding="utf-8")
    )
    places = [PlaceData.model_validate(p) for p in payload["places"]]
    # 89 was the count before scripts/add_tour_api_restaurants_jeju.py added
    # 31 more restaurants (see test_add_tour_api_restaurants_jeju.py).
    assert len(places) == 120
    assert len({p.id for p in places}) == 120
