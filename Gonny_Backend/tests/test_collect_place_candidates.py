from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import collect_place_candidates as cpc  # noqa: E402


# --- fake TourApiClient (no network) ----------------------------------------


class FakeTourApiClient:
    """TourApiClient를 흉내 내는 가짜 - 실제 네트워크 호출을 하지 않는다.
    pages_by_type: {content_type_id: [(items, total_count, status), ...]}
      -> fetch_area_based_list2가 호출될 때마다 리스트에서 하나씩 꺼낸다.
    detail_intro_by_id / detail_common_by_id: {content_id: (item, status)}
    """

    def __init__(self, pages_by_type=None, detail_intro_by_id=None, detail_common_by_id=None):
        self._pages_by_type = {k: list(v) for k, v in (pages_by_type or {}).items()}
        self._detail_intro_by_id = detail_intro_by_id or {}
        self._detail_common_by_id = detail_common_by_id or {}
        self.area_based_list_calls: list[tuple] = []
        self.detail_intro_calls: list[tuple] = []
        self.detail_common_calls: list[str] = []

    def fetch_area_based_list2(self, content_type_id, area_code, page_no, num_rows, *, ldong_regn_cd=None):
        self.area_based_list_calls.append((content_type_id, area_code, page_no, num_rows, ldong_regn_cd))
        queue = self._pages_by_type.get(content_type_id, [])
        if not queue:
            return [], 0, "ok"
        return queue.pop(0)

    def fetch_detail_intro2(self, content_id, content_type_id):
        self.detail_intro_calls.append((content_id, content_type_id))
        return self._detail_intro_by_id.get(content_id, (None, "ok"))

    def fetch_detail_common2(self, content_id):
        self.detail_common_calls.append(content_id)
        return self._detail_common_by_id.get(content_id, (None, "ok"))


def build_raw_item(**overrides) -> dict:
    item = {
        "contentid": "9000001",
        "contenttypeid": "12",
        "title": "샘플 관광지",
        "addr1": "부산광역시 해운대구 어딘가 1",
        "addr2": "",
        "mapx": "129.1600000",
        "mapy": "35.1590000",
        "cat1": "A01",
        "cat2": "A0101",
        "cat3": "A01010100",
        "firstimage": "https://example.com/image.jpg",
        "lDongSignguCd": "350",
        "lclsSystm1": "NA",
        "lclsSystm2": "NA01",
        "lclsSystm3": "NA010200",
    }
    item.update(overrides)
    return item


def no_sleep(monkeypatch) -> None:
    monkeypatch.setattr(cpc.time, "sleep", lambda seconds: None)


def disable_detail_cache_io(monkeypatch) -> None:
    """상세 캐시 파일 I/O를 완전히 꺼서(빈 캐시로 시작, 저장은 아무 것도
    안 함) 오케스트레이션 테스트가 진짜 local_only/reports/ 파일을 절대
    건드리지 않게 한다. 캐시 자체의 동작(재개 가능성)은 별도 테스트에서
    tmp_path로 검증한다."""
    monkeypatch.setattr(cpc, "load_detail_cache", lambda path=None: {})
    monkeypatch.setattr(cpc, "save_detail_cache", lambda cache, path=None: None)


# --- mask_service_key --------------------------------------------------------


def test_mask_service_key_removes_the_key_value() -> None:
    url = "https://apis.data.go.kr/B551011/KorService2/areaBasedList2?serviceKey=SECRET123%3D%3D&pageNo=1"
    masked = cpc.mask_service_key(url)
    assert "SECRET123" not in masked
    assert "serviceKey=***" in masked


def test_mask_service_key_leaves_other_params_untouched() -> None:
    url = "https://example.com/x?a=1&serviceKey=abc&b=2"
    masked = cpc.mask_service_key(url)
    assert "a=1" in masked
    assert "b=2" in masked
    assert "abc" not in masked


# --- normalize_raw_item / filter_by_coordinates (좌표 없음·범위 밖) ---------


def test_normalize_raw_item_keeps_required_fields_and_raw() -> None:
    raw = build_raw_item()
    item = cpc.normalize_raw_item(raw, "12")
    assert item["contentid"] == "9000001"
    assert item["contenttypeid"] == "12"
    assert item["title"] == "샘플 관광지"
    assert item["latitude"] == 35.159
    assert item["longitude"] == 129.16
    assert item["has_firstimage"] is True
    assert item["ldong_signgu_cd"] == "350"
    assert item["lcls_systm1"] == "NA"
    assert item["lcls_systm2"] == "NA01"
    assert item["lcls_systm3"] == "NA010200"
    assert item["flags"] == []
    assert item["raw"] == raw


def test_normalize_raw_item_missing_optional_fields_defaults_to_none_without_raising() -> None:
    raw = build_raw_item(cat1="", cat2="", cat3="", firstimage="", lDongSignguCd="")
    del raw["mapx"]
    del raw["mapy"]
    item = cpc.normalize_raw_item(raw, "12")
    assert item["latitude"] is None
    assert item["longitude"] is None
    assert item["cat1"] is None
    assert item["has_firstimage"] is False
    assert item["ldong_signgu_cd"] is None


def test_normalize_raw_item_sets_quality_flags_from_title() -> None:
    item = cpc.normalize_raw_item(build_raw_item(title="행복약국"), "12")
    assert "non_tourist_suspect" in item["flags"]


def test_filter_by_coordinates_excludes_missing_coordinates() -> None:
    item = cpc.normalize_raw_item(build_raw_item(mapx="", mapy=""), "12")
    kept, excluded = cpc.filter_by_coordinates([item])
    assert kept == []
    assert excluded[0]["exclude_reason"] == "좌표 없음"


def test_filter_by_coordinates_excludes_out_of_busan_bounds() -> None:
    # 서울 좌표 (부산 범위 밖)
    item = cpc.normalize_raw_item(build_raw_item(mapx="126.9780", mapy="37.5665"), "12")
    kept, excluded = cpc.filter_by_coordinates([item])
    assert kept == []
    assert excluded[0]["exclude_reason"] == "부산 대략 범위 밖"


def test_filter_by_coordinates_keeps_a_valid_busan_item() -> None:
    item = cpc.normalize_raw_item(build_raw_item(), "12")
    kept, excluded = cpc.filter_by_coordinates([item])
    assert len(kept) == 1
    assert excluded == []


# --- compute_quality_flags ----------------------------------------------------


def test_compute_quality_flags_detects_non_tourist_suspect() -> None:
    assert "non_tourist_suspect" in cpc.compute_quality_flags("동래부동산")


def test_compute_quality_flags_detects_lodging_like() -> None:
    assert "lodging_like" in cpc.compute_quality_flags("해운대 오토캠핑장")


def test_compute_quality_flags_detects_food_street_like() -> None:
    assert "food_street_like" in cpc.compute_quality_flags("국제시장 먹자골목")


def test_compute_quality_flags_detects_sports_facility_like() -> None:
    assert "sports_facility_like" in cpc.compute_quality_flags("동래 컨트리클럽")


def test_compute_quality_flags_empty_for_a_plain_tourist_spot() -> None:
    assert cpc.compute_quality_flags("용두산공원") == []


def test_compute_quality_flags_can_return_multiple_flags() -> None:
    flags = cpc.compute_quality_flags("약국 옆 포장마차")
    assert "non_tourist_suspect" in flags
    assert "food_street_like" in flags


# --- suggest_area (lDongSignguCd 우선, 주소 폴백) ----------------------------


def test_suggest_area_uses_sigungu_code_when_it_maps_to_a_known_area() -> None:
    area, note, sigungu_name = cpc.suggest_area("500", "부산광역시 수영구 광안동 1")
    assert area == "gwangalli"
    assert note is None
    assert sigungu_name == "수영구"


def test_suggest_area_does_not_disambiguate_centum_vs_haeundae_by_sigungu_code() -> None:
    # 센텀시티도 행정구역상 해운대구(350)라서, 시군구 코드만으로는 "haeundae"로
    # 묶인다 - 더 세밀한 구분은 하지 않는다(요구사항 6).
    area, note, sigungu_name = cpc.suggest_area("350", "부산광역시 해운대구 우동 센텀로 1")
    assert area == "haeundae"
    assert sigungu_name == "해운대구"


def test_suggest_area_flags_sigungu_code_not_in_the_six_areas_for_review() -> None:
    area, note, sigungu_name = cpc.suggest_area("710", "부산광역시 기장군 기장읍 123")
    assert area is None
    assert note == cpc.AREA_NEEDS_REVIEW_NOTE
    assert sigungu_name == "기장군"


def test_suggest_area_falls_back_to_address_keywords_when_sigungu_code_missing() -> None:
    area, note, sigungu_name = cpc.suggest_area(None, "부산광역시 모름구 센텀로 1")
    assert area == "centum"
    assert note is None
    assert sigungu_name is None


def test_suggest_area_by_address_matches_a_known_keyword() -> None:
    area, note = cpc.suggest_area_by_address("부산광역시 해운대구 우동 123")
    assert area == "haeundae"
    assert note is None


def test_suggest_area_by_address_flags_unmatched_address_for_review() -> None:
    area, note = cpc.suggest_area_by_address("부산광역시 기장군 기장읍 123")
    assert area is None
    assert note == cpc.AREA_NEEDS_REVIEW_NOTE


# --- find_catalog_duplicate / partition_duplicates (중복 판정) -------------


EXISTING_PLACES = [
    {
        "id": "haeundae-beach",
        "name": "해운대 해수욕장",
        "content_id": "126081",
        "latitude": 35.1590840227225,
        "longitude": 129.160278564827,
    },
]


def test_find_catalog_duplicate_matches_same_content_id() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contentid="126081", title="완전히 다른 이름"), "12")
    duplicate = cpc.find_catalog_duplicate(item, EXISTING_PLACES)
    assert duplicate is not None
    assert duplicate["matched_id"] == "haeundae-beach"
    assert duplicate["reason"] == "같은 content_id"


def test_find_catalog_duplicate_matches_by_name_and_nearby_coordinates() -> None:
    item = cpc.normalize_raw_item(
        build_raw_item(contentid="9999999", title="해운대해수욕장", mapx="129.1603", mapy="35.1592"),
        "12",
    )
    duplicate = cpc.find_catalog_duplicate(item, EXISTING_PLACES)
    assert duplicate is not None
    assert duplicate["matched_id"] == "haeundae-beach"
    assert "이름 일치" in duplicate["reason"]


def test_find_catalog_duplicate_does_not_match_same_name_far_away() -> None:
    # 이름은 같지만 300m보다 훨씬 먼 좌표 - 중복이 아니다.
    item = cpc.normalize_raw_item(
        build_raw_item(contentid="9999999", title="해운대 해수욕장", mapx="129.20", mapy="35.20"),
        "12",
    )
    duplicate = cpc.find_catalog_duplicate(item, EXISTING_PLACES)
    assert duplicate is None


def test_find_catalog_duplicate_returns_none_for_a_genuinely_new_place() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contentid="8888888", title="전혀 새로운 장소"), "12")
    assert cpc.find_catalog_duplicate(item, EXISTING_PLACES) is None


def test_partition_duplicates_splits_candidates_correctly() -> None:
    dup_item = cpc.normalize_raw_item(build_raw_item(contentid="126081", title="해운대 해수욕장"), "12")
    new_item = cpc.normalize_raw_item(build_raw_item(contentid="8888888", title="전혀 새로운 장소"), "12")
    new_candidates, already_in_catalog = cpc.partition_duplicates([dup_item, new_item], EXISTING_PLACES)
    assert [c["contentid"] for c in new_candidates] == ["8888888"]
    assert [c["contentid"] for c in already_in_catalog] == ["126081"]
    assert already_in_catalog[0]["already_in_catalog"]["reason"] == "같은 content_id"


# --- extract_known_hours_fields (필드 누락 방어) -----------------------------


def test_extract_known_hours_fields_reads_the_mapped_field_for_content_type() -> None:
    detail_intro = {"usetime": "09:00~18:00", "restdate": "매주 월요일"}
    open_hours, closed_days = cpc.extract_known_hours_fields(detail_intro, "12")
    assert open_hours == "09:00~18:00"
    assert closed_days == "매주 월요일"


def test_extract_known_hours_fields_missing_field_is_none_not_a_crash() -> None:
    detail_intro = {"some_other_field": "x"}
    open_hours, closed_days = cpc.extract_known_hours_fields(detail_intro, "12")
    assert open_hours is None
    assert closed_days is None


def test_extract_known_hours_fields_unmapped_content_type_is_none() -> None:
    open_hours, closed_days = cpc.extract_known_hours_fields({"usetime": "x"}, "99")
    assert (open_hours, closed_days) == (None, None)


def test_extract_known_hours_fields_none_detail_intro_is_none() -> None:
    assert cpc.extract_known_hours_fields(None, "12") == (None, None)


# --- load_detail_cache / save_detail_cache (파일 I/O) -----------------------


def test_detail_cache_round_trips_through_a_file(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    cache = {"123": {"detail_intro": {"usetime": "09:00~18:00"}, "detail_common": None, "open_hours": "09:00~18:00", "closed_days": None}}
    cpc.save_detail_cache(cache, cache_path)
    loaded = cpc.load_detail_cache(cache_path)
    assert loaded == cache


def test_load_detail_cache_missing_file_returns_empty_dict(tmp_path) -> None:
    assert cpc.load_detail_cache(tmp_path / "does_not_exist.json") == {}


def test_load_detail_cache_corrupt_file_returns_empty_dict(tmp_path) -> None:
    cache_path = tmp_path / "corrupt.json"
    cache_path.write_text("{not valid json", encoding="utf-8")
    assert cpc.load_detail_cache(cache_path) == {}


# --- enrich_candidate (상세 보강, 방어적 읽기, 캐시) --------------------------


def test_enrich_candidate_attaches_raw_detail_dicts_verbatim(monkeypatch) -> None:
    no_sleep(monkeypatch)
    item = cpc.normalize_raw_item(build_raw_item(contentid="9000001"), "12")
    client = FakeTourApiClient(
        detail_intro_by_id={"9000001": ({"usetime": "09:00~18:00", "parking": "가능"}, "ok")},
        detail_common_by_id={"9000001": ({"homepage": "<a>site</a>", "overview": "설명"}, "ok")},
    )
    enriched = cpc.enrich_candidate(client, item, [0], {})
    assert enriched["detail_intro"] == {"usetime": "09:00~18:00", "parking": "가능"}
    assert enriched["detail_common"] == {"homepage": "<a>site</a>", "overview": "설명"}
    assert enriched["open_hours"] == "09:00~18:00"


def test_enrich_candidate_without_content_id_skips_calls_and_stays_none() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contentid=""), "12")
    client = FakeTourApiClient()
    enriched = cpc.enrich_candidate(client, item, [0], {})
    assert enriched["detail_intro"] is None
    assert enriched["detail_common"] is None


def test_enrich_candidate_raises_quota_exceeded_and_stops_calling(monkeypatch) -> None:
    no_sleep(monkeypatch)
    item = cpc.normalize_raw_item(build_raw_item(contentid="9000001"), "12")

    class QuotaClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            return None, "quota_exceeded"

    call_counter = [0]
    try:
        cpc.enrich_candidate(QuotaClient(), item, call_counter, {})
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0]


def test_enrich_candidate_populates_the_cache_after_a_fresh_fetch() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contentid="9000001"), "12")
    client = FakeTourApiClient(detail_intro_by_id={"9000001": ({"usetime": "09:00~18:00"}, "ok")})
    cache: dict = {}
    cpc.enrich_candidate(client, item, [0], cache)
    assert "9000001" in cache
    assert cache["9000001"]["open_hours"] == "09:00~18:00"


def test_enrich_candidate_uses_cache_and_never_calls_the_client_again() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contentid="9000001"), "12")
    cache = {
        "9000001": {
            "detail_intro": {"usetime": "캐시된 시간"},
            "detail_common": None,
            "open_hours": "캐시된 시간",
            "closed_days": None,
        }
    }

    class PoisonClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            raise AssertionError("캐시 적중이면 호출되면 안 된다")

        def fetch_detail_common2(self, content_id):
            raise AssertionError("캐시 적중이면 호출되면 안 된다")

    enriched = cpc.enrich_candidate(PoisonClient(), item, [0], cache)
    assert enriched["open_hours"] == "캐시된 시간"


# --- fetch_type_candidates (페이지네이션 + 재시도, lDongRegnCd) -------------


def test_fetch_type_candidates_sends_ldong_regn_cd_not_area_code(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": [([build_raw_item(contentid="1")], 1, "ok")]})
    cpc.fetch_type_candidates(client, "26", "12", max_items=80, call_counter=[0])
    content_type_id, area_code, page_no, num_rows, ldong_regn_cd = client.area_based_list_calls[0]
    assert ldong_regn_cd == "26"
    assert area_code is None


def test_fetch_type_candidates_paginates_until_total_count(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(
        pages_by_type={
            "12": [
                ([build_raw_item(contentid="1"), build_raw_item(contentid="2")], 3, "ok"),
                ([build_raw_item(contentid="3")], 3, "ok"),
            ]
        }
    )
    items, total_count = cpc.fetch_type_candidates(client, "26", "12", max_items=80, call_counter=[0])
    assert [item["contentid"] for item in items] == ["1", "2", "3"]
    assert total_count == 3
    assert len(client.area_based_list_calls) == 2


def test_fetch_type_candidates_stops_at_max_items() -> None:
    client = FakeTourApiClient(
        pages_by_type={"12": [([build_raw_item(contentid=str(i)) for i in range(10)], 10, "ok")]}
    )
    items, _ = cpc.fetch_type_candidates(client, "26", "12", max_items=5, call_counter=[0])
    assert len(items) == 5


def test_fetch_type_candidates_retries_on_api_error_then_succeeds(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(
        pages_by_type={
            "12": [
                ([], None, "api_error"),
                ([build_raw_item(contentid="1")], 1, "ok"),
            ]
        }
    )
    items, total_count = cpc.fetch_type_candidates(client, "26", "12", max_items=80, call_counter=[0])
    assert [item["contentid"] for item in items] == ["1"]
    assert total_count == 1


def test_fetch_type_candidates_raises_quota_exceeded_immediately(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": [([], None, "quota_exceeded")]})
    call_counter = [0]
    try:
        cpc.fetch_type_candidates(client, "26", "12", max_items=80, call_counter=call_counter)
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0] == 1


# --- collect_place_candidates (전체 오케스트레이션 + 요약 집계) -------------


def four_empty_types(**overrides) -> dict:
    pages = {"12": [([], 0, "ok")], "14": [([], 0, "ok")], "28": [([], 0, "ok")], "38": [([], 0, "ok")]}
    pages.update(overrides)
    return pages


def test_collect_place_candidates_builds_summary_and_separates_candidates(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{"12": [([build_raw_item(contentid="8888888", title="새로운 장소", addr1="부산광역시 해운대구")], 1, "ok")]}
    )
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["new_candidates_total"] == 1
    assert result["summary"]["partial_due_to_quota"] is False
    assert result["candidates"][0]["contentid"] == "8888888"
    assert result["candidates"][0]["suggested_area"] == "haeundae"
    assert result["already_in_catalog"] == []


def test_collect_place_candidates_marks_already_in_catalog_items(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(**{"12": [([build_raw_item(contentid="126081", title="해운대 해수욕장")], 1, "ok")]})
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["new_candidates_total"] == 0
    assert result["summary"]["already_in_catalog_total"] == 1
    assert result["already_in_catalog"][0]["contentid"] == "126081"


def test_collect_place_candidates_reports_total_count_by_type(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(**{"12": [([build_raw_item(contentid="1")], 348, "ok")]})
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    result = cpc.collect_place_candidates(client, "busan", max_per_type_by_content_type={"12": 1, "14": 1, "28": 1, "38": 1})

    assert result["summary"]["total_count_by_type"]["관광지"] == 348


def test_collect_place_candidates_skips_stage2_detail_calls_for_flagged_candidates(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{
            "12": [
                (
                    [
                        build_raw_item(contentid="1111111", title="정상 관광지"),
                        build_raw_item(contentid="2222222", title="국제시장 먹자골목"),
                    ],
                    2,
                    "ok",
                )
            ]
        }
    )
    client = FakeTourApiClient(
        pages_by_type=pages_by_type,
        detail_intro_by_id={"1111111": ({"usetime": "x"}, "ok")},
    )
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    result = cpc.collect_place_candidates(client, "busan")

    by_id = {c["contentid"]: c for c in result["candidates"]}
    assert by_id["1111111"]["detail_intro"] == {"usetime": "x"}
    assert by_id["2222222"]["flags"] == ["food_street_like"]
    assert by_id["2222222"]["detail_intro"] is None
    # 플래그 있는 후보는 detailIntro2/detailCommon2 호출 자체가 없어야 한다.
    assert all(call[0] != "2222222" for call in client.detail_intro_calls)
    assert "2222222" not in client.detail_common_calls


def test_collect_place_candidates_list_only_skips_all_stage2_calls(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(**{"12": [([build_raw_item(contentid="1111111", title="정상 관광지")], 1, "ok")]})
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    result = cpc.collect_place_candidates(client, "busan", skip_detail=True)

    assert result["summary"]["stage2_api_call_count"] == 0
    assert client.detail_intro_calls == []
    assert client.detail_common_calls == []
    assert result["candidates"][0]["detail_intro"] is None


def test_collect_place_candidates_saves_partial_results_on_quota_exceeded(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = {
        "12": [([build_raw_item(contentid="8888888", title="첫 타입 신규 장소")], 1, "ok")],
        "14": [([], None, "quota_exceeded")],
        # 28/38은 quota 중단으로 도달하지 않는다.
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["partial_due_to_quota"] is True
    # 12에서 모은 신규 후보는 보존된다.
    assert result["summary"]["new_candidates_total"] == 1
    assert result["candidates"][0]["contentid"] == "8888888"
    assert result["candidates"][0]["detail_intro"] is None


def test_collect_place_candidates_saves_partial_results_on_quota_during_enrichment(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{
            "12": [
                (
                    [
                        build_raw_item(contentid="8888888", title="첫 번째 신규 장소"),
                        build_raw_item(contentid="7777777", title="두 번째 신규 장소"),
                    ],
                    2,
                    "ok",
                )
            ]
        }
    )

    class QuotaOnDetailClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            return None, "quota_exceeded"

    client = QuotaOnDetailClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["partial_due_to_quota"] is True
    # 상세 보강은 못 받았어도 두 후보 모두 결과에 남아있어야 한다.
    assert len(result["candidates"]) == 2
    assert all(c["detail_intro"] is None for c in result["candidates"])


def test_collect_place_candidates_resumes_from_detail_cache_on_second_run(monkeypatch, tmp_path) -> None:
    """요구사항 8: 캐시 재개 - 두 번째 실행에서 상세 호출이 0이어야 한다."""
    no_sleep(monkeypatch)
    cache_path = tmp_path / "place_detail_cache_busan.json"
    monkeypatch.setattr(cpc, "DETAIL_CACHE_PATH", cache_path)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    pages_by_type = four_empty_types(**{"12": [([build_raw_item(contentid="1111111", title="정상 관광지")], 1, "ok")]})

    first_client = FakeTourApiClient(
        pages_by_type=pages_by_type,
        detail_intro_by_id={"1111111": ({"usetime": "09:00~18:00"}, "ok")},
    )
    first_result = cpc.collect_place_candidates(first_client, "busan")
    assert first_result["candidates"][0]["open_hours"] == "09:00~18:00"
    assert len(first_client.detail_intro_calls) == 1
    assert cache_path.exists()

    class PoisonClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            raise AssertionError("캐시가 있으면 두 번째 실행은 상세를 다시 호출하면 안 된다")

        def fetch_detail_common2(self, content_id):
            raise AssertionError("캐시가 있으면 두 번째 실행은 상세를 다시 호출하면 안 된다")

    second_pages_by_type = four_empty_types(**{"12": [([build_raw_item(contentid="1111111", title="정상 관광지")], 1, "ok")]})
    second_client = PoisonClient(pages_by_type=second_pages_by_type)
    second_result = cpc.collect_place_candidates(second_client, "busan")

    assert second_result["candidates"][0]["open_hours"] == "09:00~18:00"
    assert second_result["summary"]["stage2_api_call_count"] == 0


def test_collect_place_candidates_never_touches_the_real_catalog_file(monkeypatch) -> None:
    """읽기 전용 보장: destinations/busan.json 파일 쓰기가 호출되지 않는다."""
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    import json as json_module

    busan_path = cpc.DESTINATIONS_DIR / "busan.json"
    original_mtime = busan_path.stat().st_mtime
    original_text = busan_path.read_text(encoding="utf-8")

    client = FakeTourApiClient(pages_by_type=four_empty_types())
    cpc.collect_place_candidates(client, "busan")

    assert busan_path.stat().st_mtime == original_mtime
    assert busan_path.read_text(encoding="utf-8") == original_text
    json_module.loads(original_text)  # 여전히 유효한 JSON인지도 같이 확인


# --- --help / CLI 플래그 ------------------------------------------------------


def test_help_flag_does_not_raise(capsys) -> None:
    try:
        cpc.parse_args(["--help"])
        assert False, "argparse --help는 SystemExit을 던진다"
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "--list-only" in captured.out
    assert "--skip-detail" in captured.out


def test_parse_args_list_only_and_skip_detail_flags() -> None:
    args = cpc.parse_args(["--list-only"])
    assert args.list_only is True
    assert args.skip_detail is False

    args2 = cpc.parse_args(["--skip-detail"])
    assert args2.skip_detail is True
