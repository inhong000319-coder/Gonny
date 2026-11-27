from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import collect_restaurant_candidates_busan as crcb  # noqa: E402


# --- fake TourApiClient (no network) ----------------------------------------


class FakeTourApiClient:
    """TourApiClient를 흉내 내는 가짜 - 실제 네트워크 호출을 하지 않는다.
    pages: fetch_area_based_list2가 호출될 때마다 순서대로 하나씩 꺼내는
    (items, total_count, status) 리스트. detail_intro_by_id:
    {content_id: (item, status)}."""

    def __init__(self, pages=None, detail_intro_by_id=None):
        self._pages = list(pages or [])
        self._detail_intro_by_id = detail_intro_by_id or {}
        self.area_based_list_calls: list[tuple] = []
        self.detail_intro_calls: list[tuple] = []

    def fetch_area_based_list2(self, content_type_id, area_code, page_no, num_rows, *, ldong_regn_cd=None):
        self.area_based_list_calls.append((content_type_id, area_code, page_no, num_rows, ldong_regn_cd))
        if not self._pages:
            return [], 0, "ok"
        return self._pages.pop(0)

    def fetch_detail_intro2(self, content_id, content_type_id):
        self.detail_intro_calls.append((content_id, content_type_id))
        return self._detail_intro_by_id.get(content_id, (None, "ok"))


def no_sleep(monkeypatch) -> None:
    monkeypatch.setattr(crcb.time, "sleep", lambda seconds: None)


def fake_distance_by_latitude_diff(monkeypatch) -> None:
    """선정 알고리즘 테스트를 실제 위경도 수학이 아니라 숫자로 다루기 위한
    유틸 - 이 모듈이 import한 haversine_distance_km을 "위도 차이의 절대값
    (km)"으로 바꿔치기한다. haversine_distance_km 자체의 정확성은
    travel_estimate 쪽 테스트가 이미 검증하므로, 이 파일의 관심사(중복
    판정·공백 판정·후보 선정 로직)와는 분리한다."""
    monkeypatch.setattr(crcb, "haversine_distance_km", lambda lat1, lon1, lat2, lon2: abs(lat1 - lat2))


def existing_restaurant(**overrides) -> dict:
    data = {
        "id": "existing-1",
        "name": "기존식당",
        "content_id": "100001",
        "latitude": 0.0,
        "longitude": 0.0,
        "activity_type": ["미식"],
    }
    data.update(overrides)
    return data


def new_candidate(**overrides) -> dict:
    data = {
        "contentid": "200001",
        "contenttypeid": "39",
        "title": "새 식당",
        "addr1": "부산광역시 기장군 어딘가",
        "latitude": 0.0,
        "longitude": 0.0,
        "lcls_systm1": "FD",
        "lcls_systm2": "FD01",
        "lcls_systm3": "FD010100",
    }
    data.update(overrides)
    return data


def gap_place(**overrides) -> dict:
    data = {
        "id": "gap-place-1",
        "name": "공백 장소",
        "area": "gijang",
        "latitude": 0.0,
        "longitude": 0.0,
        "gap_distance_km": 5.0,
    }
    data.update(overrides)
    return data


# --- find_existing_restaurant_duplicate / partition (요구사항 3) -----------


def test_find_existing_restaurant_duplicate_matches_same_content_id(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    item = new_candidate(contentid="100001", title="완전히 다른 이름", latitude=99.0)
    duplicate = crcb.find_existing_restaurant_duplicate(item, [existing_restaurant(content_id="100001")])
    assert duplicate is not None
    assert duplicate["reason"] == "같은 content_id"


def test_find_existing_restaurant_duplicate_matches_by_distance_and_name_similarity(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    item = new_candidate(contentid="200001", title="기존식당 본점", latitude=0.0001)  # 300m 이내
    duplicate = crcb.find_existing_restaurant_duplicate(item, [existing_restaurant(name="기존식당")])
    assert duplicate is not None
    assert "이름 유사도" in duplicate["reason"]


def test_find_existing_restaurant_duplicate_far_away_is_not_a_match_even_with_same_name(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    item = new_candidate(contentid="200001", title="기존식당", latitude=1.0)  # 1km, 300m 밖
    duplicate = crcb.find_existing_restaurant_duplicate(item, [existing_restaurant(name="기존식당")])
    assert duplicate is None


def test_find_existing_restaurant_duplicate_nearby_but_dissimilar_name_is_not_a_match(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    item = new_candidate(contentid="200001", title="전혀 다른 상호", latitude=0.0001)
    duplicate = crcb.find_existing_restaurant_duplicate(item, [existing_restaurant(name="기존식당")])
    assert duplicate is None


def test_find_existing_restaurant_duplicate_returns_none_for_a_genuinely_new_place(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    item = new_candidate(contentid="999999", title="새로운 맛집", latitude=10.0)
    assert crcb.find_existing_restaurant_duplicate(item, [existing_restaurant()]) is None


def test_partition_existing_restaurant_duplicates_splits_and_tags_reason(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    dup = new_candidate(contentid="100001", title="중복")
    new = new_candidate(contentid="999999", title="새 맛집", latitude=10.0)
    new_items, duplicates = crcb.partition_existing_restaurant_duplicates(
        [dup, new], [existing_restaurant(content_id="100001")]
    )
    assert [c["contentid"] for c in new_items] == ["999999"]
    assert [c["contentid"] for c in duplicates] == ["100001"]
    assert duplicates[0]["exclude_reason"] == "existing_restaurant_duplicate"
    assert duplicates[0]["matched"]["reason"] == "같은 content_id"


# --- analyze_gap_places / build_gap_summary (요구사항 4) --------------------


def test_analyze_gap_places_flags_places_farther_than_threshold_as_gap(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    target_places = [
        {"id": "p-far", "name": "먼 곳", "area": "gijang", "latitude": 5.0, "longitude": 0.0},
        {"id": "p-near", "name": "가까운 곳", "area": "gijang", "latitude": 1.0, "longitude": 0.0},
    ]
    existing = [existing_restaurant(latitude=0.0)]
    gap_analysis = crcb.analyze_gap_places(target_places, existing)
    gap_ids = {p["id"] for p in gap_analysis["gijang"]["gap_places"]}
    assert gap_ids == {"p-far"}
    assert len(gap_analysis["gijang"]["places"]) == 2


def test_analyze_gap_places_ignores_places_outside_target_areas(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    target_places = [{"id": "p-other", "name": "기타", "area": "nampo", "latitude": 5.0, "longitude": 0.0}]
    gap_analysis = crcb.analyze_gap_places(target_places, [existing_restaurant()])
    assert gap_analysis["gijang"]["places"] == []
    assert gap_analysis["gijang"]["gap_places"] == []


def test_build_gap_summary_reports_median_and_max_distance(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    target_places = [
        {"id": "p1", "name": "a", "area": "gijang", "latitude": 1.0, "longitude": 0.0},
        {"id": "p2", "name": "b", "area": "gijang", "latitude": 4.0, "longitude": 0.0},
        {"id": "p3", "name": "c", "area": "gijang", "latitude": 5.0, "longitude": 0.0},
    ]
    gap_analysis = crcb.analyze_gap_places(target_places, [existing_restaurant(latitude=0.0)])
    summary = crcb.build_gap_summary(gap_analysis)
    assert summary["gijang"]["place_count"] == 3
    assert summary["gijang"]["gap_place_count"] == 2  # 4km, 5km > 3km
    assert summary["gijang"]["nearest_restaurant_distance_km_median"] == 4.0
    assert summary["gijang"]["nearest_restaurant_distance_km_max"] == 5.0


# --- select_candidates_for_gap_places (요구사항 5) --------------------------


def test_select_candidates_excludes_candidates_outside_the_search_radius(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    gap_analysis = {"gijang": {"gap_places": [gap_place(latitude=0.0, gap_distance_km=5.0)]}}
    far_candidate = new_candidate(contentid="200001", latitude=crcb.CANDIDATE_SEARCH_RADIUS_KM + 0.5)
    client = FakeTourApiClient()
    selected, excluded = crcb.select_candidates_for_gap_places(client, gap_analysis, [far_candidate], [0], {})
    assert selected == []
    assert client.detail_intro_calls == []  # 반경 밖이면 상세 조회도 안 한다


def test_select_candidates_picks_at_most_two_per_gap_place(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    gap_analysis = {"gijang": {"gap_places": [gap_place(gap_distance_km=5.0)]}}
    candidates = [
        new_candidate(contentid=f"20000{i}", latitude=0.1 * i)
        for i in range(1, 5)  # 0.1, 0.2, 0.3, 0.4km - 전부 반경 안
    ]
    client = FakeTourApiClient()
    selected, excluded = crcb.select_candidates_for_gap_places(client, gap_analysis, candidates, [0], {})
    assert len(selected) == crcb.FINAL_PICKS_PER_GAP_PLACE == 2


def test_select_candidates_prefers_firstmenu_over_a_closer_candidate_without_it(monkeypatch) -> None:
    # 예비 풀(3곳) 중 firstmenu가 있는 후보가 더 가까운 "firstmenu 없는"
    # 후보를 최종 2곳에서 밀어낸다 - 모듈 docstring에서 설명한 설계.
    fake_distance_by_latitude_diff(monkeypatch)
    gap_analysis = {"gijang": {"gap_places": [gap_place(gap_distance_km=5.0)]}}
    c_nearest_no_menu = new_candidate(contentid="c1", latitude=0.10)
    c_second_no_menu = new_candidate(contentid="c2", latitude=0.15)
    c_third_has_menu = new_candidate(contentid="c3", latitude=0.20)
    client = FakeTourApiClient(
        detail_intro_by_id={
            "c1": ({}, "ok"),
            "c2": ({}, "ok"),
            "c3": ({"firstmenu": "낙지볶음"}, "ok"),
        }
    )
    selected, excluded = crcb.select_candidates_for_gap_places(
        client, gap_analysis, [c_nearest_no_menu, c_second_no_menu, c_third_has_menu], [0], {}
    )
    selected_ids = {c["contentid"] for c in selected}
    assert selected_ids == {"c1", "c3"}  # c2(0.15, 메뉴 없음)가 c3(0.20, 메뉴 있음)에 밀려 탈락
    assert excluded == []  # 공백 장소 하나뿐이라 구역 한도로 잘리지 않음


def test_select_candidates_does_not_reselect_a_candidate_for_another_gap_place(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    gap_analysis = {
        "gijang": {
            "gap_places": [
                gap_place(id="gp-high", name="공백 큰 곳", gap_distance_km=5.0),
                gap_place(id="gp-low", name="공백 작은 곳", gap_distance_km=3.5),
            ]
        }
    }
    candidates = [new_candidate(contentid=f"c{i}", latitude=0.1 * i) for i in range(1, 5)]  # c1..c4
    client = FakeTourApiClient()  # firstmenu 없음 -> 순수 거리 순
    selected, excluded = crcb.select_candidates_for_gap_places(client, gap_analysis, candidates, [0], {})

    by_gap_place = {}
    for item in selected:
        by_gap_place.setdefault(item["fills_gap_place_id"], set()).add(item["contentid"])

    assert by_gap_place["gp-high"] == {"c1", "c2"}  # 더 심한 공백(gp-high)이 먼저 처리돼 가장 가까운 2곳을 가져감
    assert by_gap_place["gp-low"] == {"c3", "c4"}  # 남은 후보 중에서만 고름 - c1/c2 재선택 없음


def test_select_candidates_truncates_by_area_limit_keeping_the_worst_gap_places(monkeypatch) -> None:
    fake_distance_by_latitude_diff(monkeypatch)
    monkeypatch.setitem(crcb.AREA_CANDIDATE_LIMITS, "gijang", 2)  # 한 공백 장소 몫만 남도록 한도를 낮춤
    gap_analysis = {
        "gijang": {
            "gap_places": [
                gap_place(id="gp-high", name="공백 큰 곳", latitude=0.0, gap_distance_km=10.0),
                gap_place(id="gp-low", name="공백 작은 곳", latitude=100.0, gap_distance_km=4.0),
            ]
        }
    }
    candidates_for_high = [new_candidate(contentid=f"h{i}", latitude=0.1 * i) for i in range(1, 3)]
    candidates_for_low = [new_candidate(contentid=f"l{i}", latitude=100.0 + 0.1 * i) for i in range(1, 3)]
    client = FakeTourApiClient()

    selected, excluded = crcb.select_candidates_for_gap_places(
        client, gap_analysis, candidates_for_high + candidates_for_low, [0], {}
    )

    assert {c["contentid"] for c in selected} == {"h1", "h2"}  # 한도(2)까지 공백이 큰 gp-high 몫만 남음
    assert {c["contentid"] for c in excluded} == {"l1", "l2"}
    assert all(c["exclude_reason"] == "area_limit_exceeded" for c in excluded)


def test_select_candidates_resumes_detail_lookups_from_the_shared_cache(monkeypatch) -> None:
    # (d) 캐시 재사용 - 이미 캐시에 있는 content_id는 detailIntro2를 다시
    # 호출하지 않는다(재개 가능).
    fake_distance_by_latitude_diff(monkeypatch)
    gap_analysis = {"gijang": {"gap_places": [gap_place(gap_distance_km=5.0)]}}
    candidate = new_candidate(contentid="c1", latitude=0.1)
    cache = {"c1": {"detail_intro": {"firstmenu": "캐시된메뉴"}}}

    class PoisonClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            raise AssertionError("캐시 적중이면 호출되면 안 된다")

    selected, _ = crcb.select_candidates_for_gap_places(PoisonClient(), gap_analysis, [candidate], [0], cache)
    assert selected[0]["firstmenu"] == "캐시된메뉴"


# --- fetch_restaurant_detail (캐시 적재, 요구사항 5) -------------------------


def test_fetch_restaurant_detail_populates_the_cache_after_a_fresh_fetch(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(detail_intro_by_id={"c1": ({"firstmenu": "낙지볶음"}, "ok")})
    cache: dict = {}
    detail = crcb.fetch_restaurant_detail(client, new_candidate(contentid="c1"), [0], cache)
    assert detail == {"firstmenu": "낙지볶음"}
    assert cache["c1"]["detail_intro"] == {"firstmenu": "낙지볶음"}


def test_fetch_restaurant_detail_raises_quota_exceeded(monkeypatch) -> None:
    no_sleep(monkeypatch)

    class QuotaClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            return None, "quota_exceeded"

    call_counter = [0]
    try:
        crcb.fetch_restaurant_detail(QuotaClient(), new_candidate(contentid="c1"), call_counter, {})
        assert False, "QuotaExceeded가 올라와야 한다"
    except crcb.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0]


# --- build_csv_rows / write_shortlist_csv (요구사항 6) ----------------------


def test_build_csv_rows_maps_fields_and_leaves_human_review_columns_blank() -> None:
    item = new_candidate(
        contentid="2845099",
        title="바보낙지",
        addr1="부산광역시 기장군 기장읍 동암해안길 6",
        latitude=35.1949130176,
        longitude=129.2218930329,
        firstmenu="낙지볶음",
        dist_to_nearest_existing_restaurant_gap_km=0.16,
        fills_gap_place="Skyline Luge Busan",
    )
    rows = crcb.build_csv_rows([item])
    row = rows[0]
    assert row["candidate_id"] == "busan-new-restaurant-2845099"
    assert row["name"] == "바보낙지"
    assert row["lclsSystm1"] == "FD"
    assert row["firstmenu"] == "낙지볶음"
    assert row["dist_to_nearest_existing_restaurant_gap_km"] == 0.16
    assert row["fills_gap_place"] == "Skyline Luge Busan"
    for blank_column in ["google_rating", "google_rating_count", "price_level", "evidence_source", "confidence"]:
        assert row[blank_column] == ""


def test_write_shortlist_csv_uses_the_required_header_and_utf8_sig_encoding(tmp_path) -> None:
    item = new_candidate(
        contentid="2845099",
        title="바보낙지",
        firstmenu="낙지볶음",
        dist_to_nearest_existing_restaurant_gap_km=0.16,
        fills_gap_place="Skyline Luge Busan",
    )
    csv_path = tmp_path / "shortlist.csv"
    crcb.write_shortlist_csv(crcb.build_csv_rows([item]), csv_path)

    raw_bytes = csv_path.read_bytes()
    assert raw_bytes.startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        data_row = next(reader)

    assert header == crcb.CSV_FIELDNAMES
    assert data_row[header.index("name")] == "바보낙지"
    assert data_row[header.index("candidate_id")] == "busan-new-restaurant-2845099"


# --- --help / CLI 플래그 -------------------------------------------------------


def test_help_flag_does_not_raise(capsys) -> None:
    try:
        crcb.parse_args(["--help"])
        assert False, "argparse --help는 SystemExit을 던진다"
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "--list-only" in captured.out
    assert "--out" in captured.out


def test_parse_args_list_only_flag_and_default_out_path() -> None:
    args = crcb.parse_args([])
    assert args.list_only is False
    assert args.out == crcb.DEFAULT_OUT_PATH

    args2 = crcb.parse_args(["--list-only"])
    assert args2.list_only is True


# --- collect_restaurant_candidates (오케스트레이션 통합 - list-only/full) ---


def _four_places_two_gap(area="gijang"):
    return [
        {"id": "gap-1", "name": "공백 장소 1", "area": area, "latitude": 5.0, "longitude": 0.0},
        {"id": "gap-2", "name": "공백 장소 2", "area": area, "latitude": 4.0, "longitude": 0.0},
        {"id": "near-1", "name": "가까운 장소", "area": area, "latitude": 1.0, "longitude": 0.0},
    ]


def test_collect_restaurant_candidates_list_only_skips_selection_and_detail_calls(monkeypatch) -> None:
    no_sleep(monkeypatch)
    fake_distance_by_latitude_diff(monkeypatch)
    monkeypatch.setattr(crcb, "load_existing_places", lambda city: [existing_restaurant(latitude=0.0)])
    places = _four_places_two_gap()
    monkeypatch.setattr(crcb, "load_target_area_places", lambda: places)

    client = FakeTourApiClient(pages=[([], 0, "ok"), ([], 0, "ok")])
    result = crcb.collect_restaurant_candidates(client, list_only=True)

    assert result["mode"] == "list-only"
    assert result["gap_place_summary"]["gijang"]["gap_place_count"] == 2
    assert client.detail_intro_calls == []


def test_collect_restaurant_candidates_full_mode_selects_and_saves_cache(monkeypatch, tmp_path) -> None:
    # 실제 haversine_distance_km을 그대로 쓴다(단위 테스트들과 달리 여기서는
    # is_within_busan_bounds도 같이 작동해야 하므로 실제 부산 범위 안의
    # 좌표를 쓴다) - 공백 장소(35.050)는 기존 식당(35.000)에서 약 5.5km
    # 떨어져 있어 공백(>3km)이고, 신규 후보(35.051)는 그 공백 장소에서
    # 약 0.1km로 반경(2km) 안에 든다.
    no_sleep(monkeypatch)
    cache_path = tmp_path / "restaurant_detail_cache_busan.json"
    monkeypatch.setattr(crcb, "DETAIL_CACHE_PATH", cache_path)
    monkeypatch.setattr(
        crcb,
        "load_existing_places",
        lambda city: [existing_restaurant(latitude=35.000, longitude=129.000)],
    )
    monkeypatch.setattr(
        crcb,
        "load_target_area_places",
        lambda: [{"id": "gap-1", "name": "공백 장소", "area": "gijang", "latitude": 35.050, "longitude": 129.000}],
    )

    raw_items = [
        {
            "contentid": "300001",
            "title": "새 식당",
            "addr1": "부산광역시 기장군",
            "addr2": "",
            "mapx": "129.000",
            "mapy": "35.051",
            "lclsSystm1": "FD",
            "lclsSystm2": "FD01",
            "lclsSystm3": "FD010100",
        }
    ]
    client = FakeTourApiClient(
        pages=[(raw_items, 1, "ok"), (raw_items, 1, "ok")],
        detail_intro_by_id={"300001": ({"firstmenu": "낙지볶음"}, "ok")},
    )

    result = crcb.collect_restaurant_candidates(client, list_only=False)

    assert result["mode"] == "full"
    assert result["gap_place_summary"]["gijang"]["gap_place_count"] == 1
    assert result["summary"]["selected_candidate_count"] == 1
    assert result["selected_candidates"][0]["contentid"] == "300001"
    assert result["selected_candidates"][0]["firstmenu"] == "낙지볶음"
    assert result["partial_due_to_quota"] is False
    assert cache_path.exists()  # 상세 캐시 파일이 실제로 저장됐는지(재개 가능성)


def test_collect_restaurant_candidates_never_touches_the_real_catalog_file(monkeypatch) -> None:
    """읽기 전용 보장: destinations/busan.json 파일 쓰기가 호출되지 않는다."""
    no_sleep(monkeypatch)
    import json as json_module

    busan_path = PROJECT_ROOT / "app" / "data" / "destinations" / "busan.json"
    original_mtime = busan_path.stat().st_mtime
    original_text = busan_path.read_text(encoding="utf-8")

    client = FakeTourApiClient(pages=[([], 0, "ok"), ([], 0, "ok")])
    crcb.collect_restaurant_candidates(client, list_only=True)

    assert busan_path.stat().st_mtime == original_mtime
    assert busan_path.read_text(encoding="utf-8") == original_text
    json_module.loads(original_text)
