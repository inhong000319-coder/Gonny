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

from add_tour_api_restaurants_jeju import (  # noqa: E402
    DEDUP_DISTANCE_KM,
    EXCLUDED_CANDIDATES,
    NEW_ID_PREFIX,
    NEW_RESTAURANTS,
    RESTAURANT_ID_PREFIX,
    build_new_place,
    compute_reference_fields,
    find_dedup_match,
    nearest_area,
    resolve_additions,
)

from app.domains.destination_catalog.schemas import PlaceData  # noqa: E402

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"


def build_place(**overrides) -> dict:
    place = {
        "id": "jeju-restaurant-sample",
        "name": "샘플식당",
        "activity_type": ["미식"],
        "budget_level": ["medium"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["evening"],
        "area": "east-jeju",
        "duration_hours": 1,
        "priority": 6,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": "샘플 요약",
        "latitude": 33.5,
        "longitude": 126.5,
        "is_active": True,
        "mood": [],
        "visual_feature": [],
    }
    place.update(overrides)
    return place


def build_candidate(**overrides) -> dict:
    candidate = {
        "name": "신규식당",
        "content_id": "9999999",
        "latitude": 33.5001,
        "longitude": 126.5001,
        "firstmenu": "대표메뉴",
        "fills_gap_place": "근처명소",
        "google_rating": 4.5,
        "google_rating_count": 100,
        "price_level": "medium",
    }
    candidate.update(overrides)
    return candidate


# --- the embedded data itself -------------------------------------------------


def test_31_candidates_pass_the_quality_bar() -> None:
    assert len(NEW_RESTAURANTS) == 31
    for candidate in NEW_RESTAURANTS:
        assert candidate["google_rating"] >= 3.8
        assert candidate["google_rating_count"] >= 20


def test_excluded_candidates_are_not_among_the_31() -> None:
    excluded_names = {c["name"] for c in EXCLUDED_CANDIDATES}
    new_names = {c["name"] for c in NEW_RESTAURANTS}
    assert len(EXCLUDED_CANDIDATES) == 4
    assert excluded_names.isdisjoint(new_names)


def test_31_candidates_have_unique_content_ids() -> None:
    content_ids = [c["content_id"] for c in NEW_RESTAURANTS]
    assert len(content_ids) == len(set(content_ids))


# --- compute_reference_fields() -----------------------------------------------


def test_compute_reference_fields_uses_most_common_and_median_values() -> None:
    places = [
        build_place(id="jeju-restaurant-a", suitable_for=["solo", "couple"], time_fit=["evening"], pace=["easy"], mobility=["walkable"], duration_hours=1, priority=6),
        build_place(id="jeju-restaurant-b", suitable_for=["solo", "couple"], time_fit=["evening"], pace=["easy"], mobility=["walkable"], duration_hours=1, priority=8),
        build_place(id="jeju-restaurant-c", suitable_for=["friend"], time_fit=["afternoon"], pace=["easy"], mobility=["walkable"], duration_hours=3, priority=4),
        build_place(id="jeju-other-place", suitable_for=["family"], time_fit=["morning"], pace=["hard"], mobility=["taxi-needed"], duration_hours=5, priority=2),
    ]
    reference = compute_reference_fields(places)

    assert reference["suitable_for"] == ["solo", "couple"]
    assert reference["time_fit"] == ["evening"]
    assert reference["pace"] == ["easy"]
    assert reference["mobility"] == ["walkable"]
    assert reference["duration_hours"] == 1
    assert reference["priority"] == 6


# --- nearest_area() -------------------------------------------------------------


def test_nearest_area_picks_the_closest_single_place() -> None:
    places = [
        build_place(id="jeju-restaurant-near", area="east-jeju", latitude=33.50, longitude=126.50),
        build_place(id="jeju-restaurant-far", area="west-jeju", latitude=33.30, longitude=126.20),
    ]
    area, distance_km = nearest_area(33.501, 126.501, places)
    assert area == "east-jeju"
    assert distance_km < 1.0


# --- find_dedup_match() ---------------------------------------------------------


def test_find_dedup_match_flags_close_and_similar_name() -> None:
    restaurants = [build_place(id="jeju-restaurant-existing", name="제주흑돼지맛집", latitude=33.5, longitude=126.5)]
    candidate = build_candidate(name="제주흑돼지맛집", latitude=33.5005, longitude=126.5005)  # ~0.06km
    match = find_dedup_match(candidate, restaurants)
    assert match is not None
    assert match["existing_id"] == "jeju-restaurant-existing"


def test_find_dedup_match_ignores_far_away_same_name() -> None:
    restaurants = [build_place(id="jeju-restaurant-existing", name="제주흑돼지맛집", latitude=33.5, longitude=126.5)]
    candidate = build_candidate(name="제주흑돼지맛집", latitude=33.9, longitude=126.9)
    assert find_dedup_match(candidate, restaurants) is None


def test_find_dedup_match_ignores_close_but_dissimilar_name() -> None:
    restaurants = [build_place(id="jeju-restaurant-existing", name="전혀다른이름식당", latitude=33.5, longitude=126.5)]
    candidate = build_candidate(name="제주흑돼지맛집", latitude=33.5005, longitude=126.5005)
    assert find_dedup_match(candidate, restaurants) is None


def test_dedup_distance_threshold_is_300_meters() -> None:
    assert DEDUP_DISTANCE_KM == 0.3


# --- build_new_place() ----------------------------------------------------------


def test_build_new_place_uses_tour_prefix_and_embeds_facts_verbatim() -> None:
    candidate = build_candidate()
    reference = {"suitable_for": ["solo", "couple", "friend", "family"], "time_fit": ["evening"], "pace": ["easy"], "mobility": ["walkable"], "duration_hours": 1, "priority": 6}
    place = build_new_place(candidate, reference, "east-jeju")

    assert place["id"] == f"{NEW_ID_PREFIX}9999999"
    assert place["activity_type"] == ["미식"]
    assert place["budget_level"] == ["medium"]
    assert place["summary"] == "근처명소 인근, 대표 메뉴는 대표메뉴"
    assert place["mood"] == []
    assert place["visual_feature"] == []
    assert place["google_rating"] == 4.5
    assert place["google_rating_count"] == 100
    assert place["content_id"] == "9999999"
    assert PlaceData.model_validate(place).id == place["id"]


# --- resolve_additions(): idempotency and dedup on a synthetic catalog ---------


def test_resolve_additions_adds_all_candidates_when_catalog_is_clean() -> None:
    places = [build_place(id=f"jeju-restaurant-base-{i}", area="east-jeju", latitude=33.5, longitude=126.5) for i in range(3)]
    catalog = {"places": places}
    to_add, already_merged, dedup_skipped = resolve_additions(catalog)

    assert len(to_add) == len(NEW_RESTAURANTS)
    assert already_merged == []
    assert dedup_skipped == []


def test_resolve_additions_is_idempotent_on_rerun() -> None:
    places = [build_place(id=f"jeju-restaurant-base-{i}", area="east-jeju", latitude=33.5, longitude=126.5) for i in range(3)]
    catalog = {"places": places}
    to_add, _, _ = resolve_additions(catalog)
    catalog["places"].extend(to_add)

    to_add_second, already_merged_second, _ = resolve_additions(catalog)
    assert to_add_second == []
    assert len(already_merged_second) == len(NEW_RESTAURANTS)


def test_resolve_additions_skips_a_close_similarly_named_duplicate() -> None:
    sample = NEW_RESTAURANTS[0]
    places = [
        build_place(id="jeju-restaurant-base", area="east-jeju", latitude=33.5, longitude=126.5),
        build_place(id="jeju-restaurant-dup", name=sample["name"], area="east-jeju", latitude=sample["latitude"], longitude=sample["longitude"]),
    ]
    catalog = {"places": places}
    to_add, already_merged, dedup_skipped = resolve_additions(catalog)

    assert len(to_add) == len(NEW_RESTAURANTS) - 1
    assert len(dedup_skipped) == 1
    assert dedup_skipped[0]["name"] == sample["name"]


# --- real catalog sanity (addition already applied) ----------------------------


def test_real_jeju_catalog_has_120_places_including_31_new_restaurants() -> None:
    payload = json.loads((DESTINATIONS_DIR / "jeju.json").read_text(encoding="utf-8"))
    places = [PlaceData.model_validate(p) for p in payload["places"]]
    assert len(places) == 120
    assert len({p.id for p in places}) == 120

    new_restaurants = [p for p in places if p.id.startswith(NEW_ID_PREFIX)]
    assert len(new_restaurants) == 31

    area_set = {p.area for p in places}
    excluded_names = {c["name"] for c in EXCLUDED_CANDIDATES}
    for place in new_restaurants:
        assert place.activity_type == ["미식"]
        assert place.google_rating is not None and place.google_rating >= 3.8
        assert place.google_rating_count is not None and place.google_rating_count >= 20
        assert place.area in area_set
        assert place.mood == []
        assert place.visual_feature == []
        assert place.name not in excluded_names


def test_real_jeju_catalog_excluded_names_are_absent() -> None:
    payload = json.loads((DESTINATIONS_DIR / "jeju.json").read_text(encoding="utf-8"))
    names = {p["name"] for p in payload["places"]}
    for candidate in EXCLUDED_CANDIDATES:
        assert candidate["name"] not in names


def test_real_jeju_catalog_rerunning_main_adds_nothing_more() -> None:
    """additive-only/idempotent at the real-catalog level too: resolving
    against the already-updated catalog finds all 31 already merged."""
    payload = json.loads((DESTINATIONS_DIR / "jeju.json").read_text(encoding="utf-8"))
    to_add, already_merged, dedup_skipped = resolve_additions(payload)
    assert to_add == []
    assert len(already_merged) == len(NEW_RESTAURANTS)
    assert dedup_skipped == []
