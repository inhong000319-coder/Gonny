"""부산 확장 2단계(#158): 새 구역 5개(seomyeon/gijang/gupo/gangseo/gadeok)를
엔진 설정에 추가하고, 센텀 지역 장소 6곳을 haeundae에서 centum으로 옮기고,
2단계 장소 131곳을 busan.json에 is_active=false로 추가한 변경의 테스트.

constants.py 레벨 테스트(순서·이웃·라벨)는 실제 카탈로그 데이터와 무관하게
항상 통과한다. 실제 busan.json 상태를 확인하는 테스트(센텀 이동·2단계
장소 비활성·활동 후보 수 불변)는 이 PR의 데이터 반영 커밋이 모두 적용된
뒤에만 통과한다(전체 pytest는 브랜치 최종 상태 기준으로 한 번만 돈다).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import ALTERNATE_TIER  # noqa: E402
from app.domains.destination_catalog.services.repository import (  # noqa: E402
    DestinationCatalogRepository,
    compute_recommended_max_days,
)
from app.domains.rule_planner.services.constants import (  # noqa: E402
    AREA_LABEL_KO,
    BUSAN_AREA_NEIGHBORS,
    BUSAN_AREA_ROUTE_ORDER,
)

ORIGINAL_SIX_AREAS = ["nampo", "songdo", "gwangalli", "centum", "haeundae", "dongnae"]
NEW_FIVE_AREAS = ["seomyeon", "gijang", "gupo", "gangseo", "gadeok"]

# 요구사항 1에 명시된 정확한 이웃 집합 (양방향 반대쪽은 기존 구역에 추가됨).
EXPECTED_NEW_AREA_NEIGHBORS = {
    "seomyeon": {"nampo", "dongnae", "gwangalli", "gupo"},
    "gupo": {"seomyeon", "gangseo"},
    "gangseo": {"gupo", "gadeok"},
    "gadeok": {"gangseo"},
    "gijang": {"haeundae", "centum"},
}

CENTUM_MOVED_PLACE_IDS = [
    "busan-yeonghwaui-jeondang",
    "sinsegyebaekhwajeom-senteomsitijeom",
    "senteom-apecnarugongwon",
    "bekseuko-sangsangcheheom-kijeuwoldeu",
    "senteomsiti-aiseuringkeu",
    "busanyeonghwachwaryeongseutyudio",
]

PHASE2_INPUT_PATH = PROJECT_ROOT / "scripts" / "data" / "busan_expansion_places_phase2.json"
PHASE2_EXPECTED_TOTAL = 131
PHASE2_EXPECTED_TIER_COUNTS = {"standard": 32, ALTERNATE_TIER: 99}
PHASE2_EXPECTED_AREA_COUNTS = {"gijang": 46, "seomyeon": 32, "gangseo": 22, "gupo": 19, "gadeok": 12}


# --- constants.py: 새 구역이 ROUTE_ORDER·NEIGHBORS·AREA_LABEL_KO에 있는지 ---


def test_busan_area_route_order_keeps_original_six_order_and_indices():
    assert BUSAN_AREA_ROUTE_ORDER[:6] == ORIGINAL_SIX_AREAS


def test_busan_area_route_order_appends_new_five_in_given_order():
    assert BUSAN_AREA_ROUTE_ORDER[6:] == NEW_FIVE_AREAS


def test_busan_area_route_order_has_exactly_eleven_areas():
    assert len(BUSAN_AREA_ROUTE_ORDER) == 11
    assert len(set(BUSAN_AREA_ROUTE_ORDER)) == 11


def test_busan_new_areas_have_korean_labels():
    expected = {
        "seomyeon": "서면",
        "gupo": "구포·화명",
        "gangseo": "강서",
        "gadeok": "가덕도",
        "gijang": "기장",
    }
    for area, label in expected.items():
        assert AREA_LABEL_KO[area] == label


def test_busan_new_area_neighbor_sets_match_spec():
    for area, expected_neighbors in EXPECTED_NEW_AREA_NEIGHBORS.items():
        assert BUSAN_AREA_NEIGHBORS[area] == expected_neighbors, area


def test_busan_original_areas_gained_the_expected_reverse_links():
    assert "seomyeon" in BUSAN_AREA_NEIGHBORS["nampo"]
    assert "seomyeon" in BUSAN_AREA_NEIGHBORS["dongnae"]
    assert "seomyeon" in BUSAN_AREA_NEIGHBORS["gwangalli"]
    assert "gijang" in BUSAN_AREA_NEIGHBORS["haeundae"]
    assert "gijang" in BUSAN_AREA_NEIGHBORS["centum"]


def test_busan_original_six_areas_keep_their_original_links_too():
    # 역방향 추가가 기존 연결을 지우지 않았는지 - 원래 BUSAN_AREA_NEIGHBORS 값 그대로 남아있는지.
    assert BUSAN_AREA_NEIGHBORS["nampo"] >= {"songdo"}
    assert BUSAN_AREA_NEIGHBORS["songdo"] >= {"nampo"}
    assert BUSAN_AREA_NEIGHBORS["gwangalli"] >= {"haeundae", "centum"}
    assert BUSAN_AREA_NEIGHBORS["haeundae"] >= {"gwangalli", "centum", "dongnae"}
    assert BUSAN_AREA_NEIGHBORS["centum"] >= {"haeundae", "gwangalli"}
    assert BUSAN_AREA_NEIGHBORS["dongnae"] >= {"haeundae"}


def test_busan_area_neighbors_are_fully_bidirectional():
    # 모든 구역 쌍에 대해, a가 b를 이웃으로 가지면 b도 a를 이웃으로 가져야 한다.
    for area, neighbors in BUSAN_AREA_NEIGHBORS.items():
        for neighbor in neighbors:
            assert neighbor in BUSAN_AREA_NEIGHBORS, (area, neighbor)
            assert area in BUSAN_AREA_NEIGHBORS[neighbor], (area, neighbor)


def test_busan_area_neighbors_only_reference_known_areas():
    for area, neighbors in BUSAN_AREA_NEIGHBORS.items():
        assert area in BUSAN_AREA_ROUTE_ORDER
        for neighbor in neighbors:
            assert neighbor in BUSAN_AREA_ROUTE_ORDER, (area, neighbor)


# --- 2단계 입력 파일: 개수·티어·구역별 분포 ---------------------------------


def test_phase2_input_file_exists():
    assert PHASE2_INPUT_PATH.exists(), PHASE2_INPUT_PATH


def test_phase2_input_file_counts_and_tier_and_area_distribution():
    with PHASE2_INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    places = data["places"]

    assert len(places) == PHASE2_EXPECTED_TOTAL

    tier_counts: dict[str, int] = {}
    area_counts: dict[str, int] = {}
    for place in places:
        tier_counts[place["mvp_tier"]] = tier_counts.get(place["mvp_tier"], 0) + 1
        area_counts[place["area"]] = area_counts.get(place["area"], 0) + 1

    assert tier_counts == PHASE2_EXPECTED_TIER_COUNTS
    assert area_counts == PHASE2_EXPECTED_AREA_COUNTS


def test_phase2_input_places_are_all_inactive():
    with PHASE2_INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    assert all(place["is_active"] is False for place in data["places"])


def test_phase2_input_areas_are_all_new_areas_not_original_six():
    with PHASE2_INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    areas = {place["area"] for place in data["places"]}
    assert areas == set(NEW_FIVE_AREAS)
    assert areas.isdisjoint(ORIGINAL_SIX_AREAS)


# --- 실제 busan.json 반영 후 상태 (이 브랜치의 데이터 반영 커밋 적용 후) ----


def _load_real_busan_catalog():
    repository = DestinationCatalogRepository()
    return repository.get_city_catalog(continent=None, country=None, city="busan", visible_only=True)


def test_centum_places_have_moved_from_haeundae_to_centum():
    catalog = _load_real_busan_catalog()
    places_by_id = {place.id: place for place in catalog.places}
    for place_id in CENTUM_MOVED_PLACE_IDS:
        assert places_by_id[place_id].area == "centum", place_id


def test_nurimaru_and_busan_film_street_were_not_moved():
    # 과제에서 "그대로 둔다"고 명시한 두 곳(누리마루 APEC하우스, 부산 영화의
    # 거리) - 혹시 실수로 같이 옮기지 않았는지.
    catalog = _load_real_busan_catalog()
    places_by_id = {place.id: place for place in catalog.places}
    assert places_by_id["nurimaru-apechauseu"].area == "haeundae"
    assert places_by_id["busan-yeonghwaui-geori"].area == "haeundae"


def test_gijang_places_are_present_but_still_inactive():
    # #160 - 2단계 131곳 중 기장(gijang) 46곳은 식당 데이터 보강 전까지
    # --exclude-areas gijang으로 활성화에서 뺐다. 나머지 85곳
    # (seomyeon/gupo/gangseo/gadeok)은 활성화됐다.
    catalog = _load_real_busan_catalog()
    places_by_id = {place.id: place for place in catalog.places}

    with PHASE2_INPUT_PATH.open(encoding="utf-8") as f:
        phase2_places = json.load(f)["places"]
    gijang_ids = {p["id"] for p in phase2_places if p["area"] == "gijang"}
    non_gijang_ids = {p["id"] for p in phase2_places if p["area"] != "gijang"}

    assert len(gijang_ids) == 46
    assert len(non_gijang_ids) == 85
    for place_id in gijang_ids:
        assert places_by_id[place_id].is_active is False, place_id
    for place_id in non_gijang_ids:
        assert places_by_id[place_id].is_active is True, place_id


def test_gijang_places_are_not_in_the_active_candidate_pool():
    # 기장은 여전히 비활성이므로, 어떤 활성 후보 풀에도 안 들어온다 -
    # is_active 필터를 쓰는 모든 real pool이 같은 방식으로 걸러진다.
    catalog = _load_real_busan_catalog()
    with PHASE2_INPUT_PATH.open(encoding="utf-8") as f:
        gijang_ids = {p["id"] for p in json.load(f)["places"] if p["area"] == "gijang"}

    active_ids = {place.id for place in catalog.places if place.is_active}
    assert active_ids.isdisjoint(gijang_ids)


def test_busan_activity_candidate_count_and_recommended_max_days_after_partial_activation():
    # #160으로 85곳(메인 32 포함)이 추가로 활성화됐다: 활동 후보
    # 130 -> 146, recommended_max_days 43 -> 48(146 // 3).
    catalog = _load_real_busan_catalog()
    active_count = sum(
        1
        for place in catalog.places
        if place.is_active and place.is_activity_candidate and place.mvp_tier != ALTERNATE_TIER
    )
    assert active_count == 146
    assert compute_recommended_max_days(active_count) == 48


def test_busan_catalog_has_exactly_494_places_with_448_active():
    catalog = _load_real_busan_catalog()
    assert len(catalog.places) == 494
    assert sum(1 for place in catalog.places if place.is_active) == 448
