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

from apply_slot_bias_s4_real import (  # noqa: E402
    EXPECTED_TABLE,
    FROZEN_TARGET_IDS,
    build_plan,
    compute_group_stats,
    fill_value_for,
    is_non_restaurant_active,
    is_slot_bias_empty,
    target_places,
    verify_table,
)

from app.domains.destination_catalog.schemas import PlaceData  # noqa: E402


def build_place(**overrides) -> dict:
    place = {
        "id": "sample-place",
        "name": "샘플 장소",
        "activity_type": ["문화·역사"],
        "budget_level": ["low", "medium"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon"],
        "area": "jongno",
        "duration_hours": 2,
        "priority": 5,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": "sample summary",
    }
    place.update(overrides)
    return place


# --- is_non_restaurant_active / is_slot_bias_empty -------------------------


def test_is_non_restaurant_active_excludes_restaurants() -> None:
    restaurant = build_place(activity_type=["미식"])
    assert is_non_restaurant_active(restaurant) is False


def test_is_non_restaurant_active_excludes_inactive_places() -> None:
    inactive = build_place(is_active=False)
    assert is_non_restaurant_active(inactive) is False


def test_is_slot_bias_empty_treats_missing_key_and_empty_dict_as_empty() -> None:
    assert is_slot_bias_empty(build_place()) is True
    assert is_slot_bias_empty(build_place(slot_bias={})) is True
    assert is_slot_bias_empty(build_place(slot_bias={"morning": 3})) is False


# --- target_places() --------------------------------------------------------


def test_target_places_only_returns_empty_non_restaurant_active_places() -> None:
    places = [
        build_place(id="a"),  # target
        build_place(id="b", slot_bias={"morning": 3}),  # already filled, not a target
        build_place(id="c", activity_type=["미식"]),  # restaurant, not a target
        build_place(id="d", is_active=False),  # inactive, not a target
    ]
    ids = {p["id"] for p in target_places(places)}
    assert ids == {"a"}


# --- compute_group_stats() excludes the frozen target ids -------------------


def test_compute_group_stats_excludes_frozen_target_ids_from_the_reference_population() -> None:
    places = [
        build_place(id="real-1", time_fit=["morning"], slot_bias={"morning": 4}),
        build_place(id="real-2", time_fit=["morning"], slot_bias={"morning": 6}),
        # this one is in the frozen target set and has a (synthetic) nonzero
        # slot_bias, as it would after a prior apply run - must NOT feed
        # back into the "has" group's mean.
        build_place(id="gyeongbokgung", time_fit=["morning"], slot_bias={"morning": 999}),
    ]
    stats = compute_group_stats(places, FROZEN_TARGET_IDS["seoul"])
    assert stats["morning"]["has_n"] == 2
    assert stats["morning"]["has_fill"] == 5  # mean(4, 6) = 5, not pulled toward 999


def test_compute_group_stats_skips_restaurants_and_inactive_places() -> None:
    places = [
        build_place(id="r1", time_fit=["morning"], slot_bias={"morning": 10}, activity_type=["미식"]),
        build_place(id="i1", time_fit=["morning"], slot_bias={"morning": 10}, is_active=False),
    ]
    stats = compute_group_stats(places, set())
    assert stats["morning"]["has_n"] == 0
    assert stats["morning"]["has_fill"] is None


# --- verify_table() ----------------------------------------------------------


def test_verify_table_passes_when_computed_matches_the_hardcoded_table() -> None:
    computed = {
        city: {slot: {"has_fill": EXPECTED_TABLE[city][slot]["has"], "not_has_fill": EXPECTED_TABLE[city][slot]["not_has"]}
               for slot in ("morning", "afternoon", "evening")}
        for city in ("seoul", "busan", "jeju")
    }
    assert verify_table(computed) == []


def test_verify_table_reports_a_mismatch() -> None:
    computed = {
        city: {slot: {"has_fill": EXPECTED_TABLE[city][slot]["has"], "not_has_fill": EXPECTED_TABLE[city][slot]["not_has"]}
               for slot in ("morning", "afternoon", "evening")}
        for city in ("seoul", "busan", "jeju")
    }
    computed["seoul"]["morning"]["has_fill"] = 999
    mismatches = verify_table(computed)
    assert len(mismatches) == 1
    assert "seoul morning has" in mismatches[0]


# --- fill_value_for() / build_plan() ----------------------------------------


def test_fill_value_for_busan_afternoon_not_has_is_manually_skipped() -> None:
    value, reason = fill_value_for("busan", "afternoon", ["morning", "evening"])  # afternoon not in time_fit -> not_has
    assert value is None
    assert reason == "skip_manual"


def test_fill_value_for_seoul_afternoon_not_has_has_no_sample() -> None:
    value, reason = fill_value_for("seoul", "afternoon", ["morning", "evening"])
    assert value is None
    assert reason == "skip_no_sample"


def test_fill_value_for_returns_the_has_fill_when_slot_is_in_time_fit() -> None:
    value, reason = fill_value_for("seoul", "morning", ["morning", "afternoon"])
    assert value == 5
    assert reason == "has"


def test_fill_value_for_skips_a_place_with_no_time_fit_at_all() -> None:
    value, reason = fill_value_for("seoul", "morning", [])
    assert value is None
    assert reason == "skip_no_time_fit"


def test_build_plan_never_proposes_a_value_for_an_already_filled_place() -> None:
    places = [build_place(id="gyeongbokgung", time_fit=["morning"], slot_bias={"morning": 3})]
    plan = build_plan("seoul", places)
    assert plan == []  # not a target - already filled


def test_build_plan_fills_busan_haeundae_beach_skipping_afternoon() -> None:
    places = [build_place(id="haeundae-beach", time_fit=["morning", "evening"])]
    plan = build_plan("busan", places)
    assert len(plan) == 1
    assert plan[0]["new_slot_bias"] == {"morning": 5, "evening": 7}
    assert "afternoon" not in plan[0]["new_slot_bias"]


# --- real catalog sanity (script already applied) --------------------------


def _load_real_catalogs() -> dict[str, dict]:
    return {
        city: json.loads((PROJECT_ROOT / "app" / "data" / "destinations" / f"{city}.json").read_text(encoding="utf-8"))
        for city in ("seoul", "busan", "jeju")
    }


def test_all_52_target_places_are_filled_in_the_real_catalogs() -> None:
    catalogs = _load_real_catalogs()
    by_id = {p["id"]: p for catalog in catalogs.values() for p in catalog["places"]}

    for city, ids in FROZEN_TARGET_IDS.items():
        for place_id in ids:
            place = by_id[place_id]
            assert place.get("slot_bias"), f"{city}/{place_id}: slot_bias가 비어 있음"


def test_real_catalog_fill_matches_the_s4_real_rule_for_a_sample_of_places() -> None:
    catalogs = _load_real_catalogs()
    by_id = {p["id"]: p for catalog in catalogs.values() for p in catalog["places"]}

    # busan haeundae-beach: time_fit=['morning','evening'] -> morning has(+5),
    # afternoon manually skipped, evening has(+7).
    haeundae = PlaceData.model_validate(by_id["haeundae-beach"])
    assert haeundae.slot_bias == {"morning": 5, "evening": 7}

    # seoul gyeongbokgung: time_fit=['morning','afternoon'] -> morning
    # has(+5), afternoon has(+5), evening not_has(-4).
    gyeongbokgung = PlaceData.model_validate(by_id["gyeongbokgung"])
    assert gyeongbokgung.slot_bias == {"morning": 5, "afternoon": 5, "evening": -4}

    # jeju bijarim: time_fit=['morning'] only -> morning has(+5); afternoon
    # has no sample (skipped); evening not_has(-5).
    bijarim = PlaceData.model_validate(by_id["bijarim"])
    assert bijarim.slot_bias == {"morning": 5, "evening": -5}
    assert "afternoon" not in bijarim.slot_bias


def test_a_preexisting_nonzero_slot_bias_place_is_unchanged() -> None:
    catalogs = _load_real_catalogs()
    by_id = {p["id"]: p for catalog in catalogs.values() for p in catalog["places"]}

    place = PlaceData.model_validate(by_id["e-land-hangang-cruise"])
    assert place.slot_bias == {"afternoon": 4, "evening": 10}


def test_no_restaurant_in_the_real_catalogs_has_a_newly_added_slot_bias() -> None:
    catalogs = _load_real_catalogs()
    for catalog in catalogs.values():
        for p in catalog["places"]:
            if "미식" in p.get("activity_type", []):
                assert p["id"] not in FROZEN_TARGET_IDS.get("seoul", set()) | FROZEN_TARGET_IDS.get("busan", set()) | FROZEN_TARGET_IDS.get("jeju", set())


def test_rerunning_build_plan_on_the_real_catalogs_is_a_no_op() -> None:
    catalogs = _load_real_catalogs()
    for city in ("seoul", "busan", "jeju"):
        plan = build_plan(city, catalogs[city]["places"])
        assert plan == [], f"{city}: 이미 적용된 상태에서 build_plan이 빈 목록을 반환해야 함"
