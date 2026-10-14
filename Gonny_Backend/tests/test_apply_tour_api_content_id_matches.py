from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from apply_tour_api_content_id_matches import (  # noqa: E402
    TARGET_CANDIDATE_TITLE_BY_PLACE_ID,
    apply_content_ids,
    find_place,
    resolve_content_id,
)

from app.domains.destination_catalog.schemas import PlaceData  # noqa: E402


def build_place_dict(**overrides) -> dict:
    place = {
        "id": "sample-place",
        "name": "샘플 가게",
        "activity_type": ["미식"],
        "budget_level": ["low", "medium"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["evening"],
        "area": "jongno",
        "duration_hours": 1,
        "priority": 7,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": "sample summary",
    }
    place.update(overrides)
    return place


def build_catalogs(**city_places: list[dict]) -> dict[str, dict]:
    return {city: {"places": places} for city, places in city_places.items()}


# --- resolve_content_id() -------------------------------------------------


def test_resolve_content_id_finds_a_unique_exact_title_match() -> None:
    report = {"샘플 가게": [{"title": "샘플 가게 본점", "content_id": "111"}]}
    content_id, reason = resolve_content_id("샘플 가게", "샘플 가게 본점", report)
    assert content_id == "111"
    assert reason == ""


def test_resolve_content_id_fails_when_place_not_in_report() -> None:
    content_id, reason = resolve_content_id("없는 가게", "아무거나", {})
    assert content_id is None
    assert "찾지 못함" in reason


def test_resolve_content_id_fails_when_title_does_not_match() -> None:
    report = {"샘플 가게": [{"title": "다른 이름", "content_id": "111"}]}
    content_id, reason = resolve_content_id("샘플 가게", "샘플 가게 본점", report)
    assert content_id is None
    assert "일치하는 후보가 없음" in reason


def test_resolve_content_id_fails_when_same_title_maps_to_different_ids() -> None:
    report = {"샘플 가게": [{"title": "샘플 가게 본점", "content_id": "111"}, {"title": "샘플 가게 본점", "content_id": "222"}]}
    content_id, reason = resolve_content_id("샘플 가게", "샘플 가게 본점", report)
    assert content_id is None
    assert "여러 개" in reason


def test_resolve_content_id_succeeds_when_same_title_and_id_appear_twice() -> None:
    report = {"샘플 가게": [{"title": "샘플 가게 본점", "content_id": "111"}, {"title": "샘플 가게 본점", "content_id": "111"}]}
    content_id, reason = resolve_content_id("샘플 가게", "샘플 가게 본점", report)
    assert content_id == "111"


# --- find_place() ----------------------------------------------------------


def test_find_place_locates_a_place_across_cities() -> None:
    catalogs = build_catalogs(
        seoul=[build_place_dict(id="a")],
        busan=[build_place_dict(id="b")],
        jeju=[build_place_dict(id="c")],
    )
    city, place = find_place(catalogs, "b")
    assert city == "busan"
    assert place["id"] == "b"


def test_find_place_returns_none_for_an_unknown_id() -> None:
    catalogs = build_catalogs(seoul=[build_place_dict(id="a")])
    city, place = find_place(catalogs, "not-there")
    assert city is None
    assert place is None


# --- apply_content_ids() ----------------------------------------------------


def test_apply_content_ids_writes_only_places_with_a_resolved_match() -> None:
    catalogs = build_catalogs(seoul=[build_place_dict(id="seoul-restaurant-jongno-xiaobao", name="샤오바오우육면")])
    report = {"샤오바오우육면": [{"title": "샤오바오우육면 종로본점", "content_id": "3094138"}]}

    original_targets = dict(TARGET_CANDIDATE_TITLE_BY_PLACE_ID)
    try:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID["seoul-restaurant-jongno-xiaobao"] = "샤오바오우육면 종로본점"

        result = apply_content_ids(catalogs, report)

        assert len(result["applied"]) == 1
        assert result["applied"][0]["content_id"] == "3094138"
        assert catalogs["seoul"]["places"][0]["content_id"] == "3094138"
        assert result["skipped"] == []
    finally:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.update(original_targets)


def test_apply_content_ids_never_overwrites_an_existing_content_id() -> None:
    catalogs = build_catalogs(
        seoul=[build_place_dict(id="p1", name="샘플 가게", content_id="already-set")]
    )
    report = {"샘플 가게": [{"title": "approved title", "content_id": "999"}]}

    original_targets = dict(TARGET_CANDIDATE_TITLE_BY_PLACE_ID)
    try:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID["p1"] = "approved title"

        result = apply_content_ids(catalogs, report)

        assert result["applied"] == []
        assert len(result["skipped"]) == 1
        assert "이미 content_id" in result["skipped"][0]["reason"]
        assert catalogs["seoul"]["places"][0]["content_id"] == "already-set"  # unchanged
    finally:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.update(original_targets)


def test_apply_content_ids_is_idempotent() -> None:
    catalogs = build_catalogs(seoul=[build_place_dict(id="p1", name="샘플 가게")])
    report = {"샘플 가게": [{"title": "approved title", "content_id": "999"}]}

    original_targets = dict(TARGET_CANDIDATE_TITLE_BY_PLACE_ID)
    try:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID["p1"] = "approved title"

        first = apply_content_ids(catalogs, report)
        second = apply_content_ids(catalogs, report)

        assert len(first["applied"]) == 1
        assert second["applied"] == []
        assert len(second["skipped"]) == 1
        assert catalogs["seoul"]["places"][0]["content_id"] == "999"
    finally:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.update(original_targets)


def test_apply_content_ids_skips_and_reports_an_unresolvable_title() -> None:
    catalogs = build_catalogs(seoul=[build_place_dict(id="p1", name="샘플 가게")])
    report = {"샘플 가게": [{"title": "전혀 다른 제목", "content_id": "999"}]}

    original_targets = dict(TARGET_CANDIDATE_TITLE_BY_PLACE_ID)
    try:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID["p1"] = "approved title"

        result = apply_content_ids(catalogs, report)

        assert result["applied"] == []
        assert len(result["skipped"]) == 1
        assert catalogs["seoul"]["places"][0].get("content_id") is None
    finally:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.update(original_targets)


def test_apply_content_ids_reports_a_target_id_missing_from_the_catalog() -> None:
    catalogs = build_catalogs(seoul=[build_place_dict(id="other-place")])

    original_targets = dict(TARGET_CANDIDATE_TITLE_BY_PLACE_ID)
    try:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID["missing-id"] = "whatever"

        result = apply_content_ids(catalogs, {})

        assert result["applied"] == []
        assert len(result["skipped"]) == 1
        assert "찾지 못함" in result["skipped"][0]["reason"]
    finally:
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.clear()
        TARGET_CANDIDATE_TITLE_BY_PLACE_ID.update(original_targets)


# --- real catalog sanity (script already applied) --------------------------


def test_real_catalogs_have_the_23_approved_content_ids() -> None:
    import json

    expected = {
        "seoul-restaurant-euljiro-mugyodong-bugeoguk": "403044",
        "jungmun-saekdal": "126449",
        "sea-life-busan-aquarium": "229912",
        "seoul-restaurant-gangnam-apgujeong-gadam": "2869760",
    }
    catalogs = {
        city: json.loads((PROJECT_ROOT / "app" / "data" / "destinations" / f"{city}.json").read_text(encoding="utf-8"))
        for city in ("seoul", "busan", "jeju")
    }
    by_id = {p["id"]: p for catalog in catalogs.values() for p in catalog["places"]}

    for place_id, content_id in expected.items():
        place = PlaceData.model_validate(by_id[place_id])
        assert place.content_id == content_id

    # 섭지코지's own existing content_id/coordinates are untouched by this script.
    seopjikoji = PlaceData.model_validate(by_id["seopjikoji"])
    assert seopjikoji.content_id == "127813"
