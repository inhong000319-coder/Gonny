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
      -> fetch_area_based_list2가 호출될 때마다(probe든 한 번에 받기든
      폴백 페이지든 구분 없이) 리스트에서 하나씩 순서대로 꺼낸다.
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


def type_page(items: list[dict], total_count: int | None = None) -> list[tuple]:
    """한 contentTypeId에 대해 (probe, 한 번에 받기) 두 호출을 스크립트
    한다 - 둘 다 같은 total_count를 보고하게 해 폴백이 트리거되지 않게
    한다(기본은 len(items), max_per_type_by_content_type으로 target을
    더 작게 깎는 테스트에서는 total_count를 더 크게 명시할 수 있다)."""
    resolved_total = len(items) if total_count is None else total_count
    return [(items, resolved_total, "ok"), (items, resolved_total, "ok")]


def four_empty_types(**overrides) -> dict:
    pages = {"12": [([], 0, "ok")], "14": [([], 0, "ok")], "28": [([], 0, "ok")], "38": [([], 0, "ok")]}
    pages.update(overrides)
    return pages


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


def test_normalize_raw_item_sets_quality_flags_from_lcls_systm2() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contenttypeid="38", lclsSystm2="SH04", title="어떤 브랜드 매장"), "38")
    assert item["flags"] == ["brand_store"]


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


# --- compute_quality_flags (제목 패턴) ---------------------------------------


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


# --- compute_lcls_systm2_flags / compute_quality_flags (새 분류 코드) -------


def test_compute_lcls_systm2_flags_detects_brand_store() -> None:
    assert cpc.compute_lcls_systm2_flags("38", "SH04") == ["brand_store"]


def test_compute_lcls_systm2_flags_detects_campground() -> None:
    assert cpc.compute_lcls_systm2_flags("28", "AC05") == ["campground"]


def test_compute_lcls_systm2_flags_detects_public_facility_for_leports_and_culture() -> None:
    assert cpc.compute_lcls_systm2_flags("28", "VE10") == ["public_facility"]
    assert cpc.compute_lcls_systm2_flags("14", "VE09") == ["public_facility"]


def test_compute_lcls_systm2_flags_does_not_cross_apply_to_wrong_content_type() -> None:
    # SH04은 쇼핑(38) 전용 규칙 - 다른 타입에 같은 코드가 와도 매치하지 않는다.
    assert cpc.compute_lcls_systm2_flags("12", "SH04") == []


def test_compute_lcls_systm2_flags_missing_args_returns_empty_without_raising() -> None:
    assert cpc.compute_lcls_systm2_flags(None, "SH04") == []
    assert cpc.compute_lcls_systm2_flags("38", None) == []


def test_compute_quality_flags_combines_title_and_lcls_systm2_without_duplicates() -> None:
    flags = cpc.compute_quality_flags("동래 컨트리클럽", "28", "AC05")
    assert "sports_facility_like" in flags
    assert "campground" in flags
    assert len(flags) == len(set(flags))


# --- suggest_area (lDongSignguCd 우선, 주소 폴백, area_mapping) -------------


def test_suggest_area_uses_sigungu_code_when_it_maps_to_a_known_area() -> None:
    area, note, sigungu_name, area_mapping = cpc.suggest_area("500", "부산광역시 수영구 광안동 1")
    assert area == "gwangalli"
    assert note is None
    assert sigungu_name == "수영구"
    assert area_mapping == "sigungu"


def test_suggest_area_does_not_disambiguate_centum_vs_haeundae_by_sigungu_code() -> None:
    # 센텀시티도 행정구역상 해운대구(350)라서, 시군구 코드만으로는 "haeundae"로
    # 묶인다 - 더 세밀한 구분은 하지 않는다(요구사항 6).
    area, note, sigungu_name, area_mapping = cpc.suggest_area("350", "부산광역시 해운대구 우동 센텀로 1")
    assert area == "haeundae"
    assert sigungu_name == "해운대구"
    assert area_mapping == "sigungu"


def test_suggest_area_flags_sigungu_code_not_in_the_six_areas_for_review() -> None:
    area, note, sigungu_name, area_mapping = cpc.suggest_area("710", "부산광역시 기장군 기장읍 123")
    assert area is None
    assert note == cpc.AREA_NEEDS_REVIEW_NOTE
    assert sigungu_name == "기장군"
    assert area_mapping is None


def test_suggest_area_falls_back_to_address_keywords_when_sigungu_code_missing() -> None:
    area, note, sigungu_name, area_mapping = cpc.suggest_area(None, "부산광역시 모름구 센텀로 1")
    assert area == "centum"
    assert note is None
    assert sigungu_name is None
    assert area_mapping == "address_keyword"


def test_suggest_area_fallback_with_no_keyword_match_has_no_area_mapping() -> None:
    area, note, sigungu_name, area_mapping = cpc.suggest_area(None, "부산광역시 어딘지 모를 동네")
    assert area is None
    assert note == cpc.AREA_NEEDS_REVIEW_NOTE
    assert area_mapping is None


# 요구사항 3이 새로 보강한 시군구 매핑 5개
def test_suggest_area_new_sigungu_mappings() -> None:
    assert cpc.suggest_area("170", "부산 동구")[0] == "nampo"
    assert cpc.suggest_area("200", "부산 영도구")[0] == "nampo"
    assert cpc.suggest_area("290", "부산 남구")[0] == "gwangalli"
    assert cpc.suggest_area("380", "부산 사하구")[0] == "songdo"
    assert cpc.suggest_area("410", "부산 금정구")[0] == "dongnae"


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


# --- resolve_target_count / dedupe_by_contentid (순수 함수) ------------------


def test_resolve_target_count_uses_total_count_for_non_shopping_types() -> None:
    assert cpc.resolve_target_count("12", 348, None) == 348
    assert cpc.resolve_target_count("14", 129, None) == 129


def test_resolve_target_count_caps_shopping_at_fixed_target() -> None:
    assert cpc.resolve_target_count("38", 987, None) == cpc.SHOPPING_FIXED_TARGET
    assert cpc.resolve_target_count("38", 10, None) == 10  # totalCount가 목표보다 적으면 그만큼만


def test_resolve_target_count_uses_fallback_when_total_count_unknown() -> None:
    assert cpc.resolve_target_count("12", None, None) == cpc.FALLBACK_TARGET_IF_PROBE_FAILS["12"]
    assert cpc.resolve_target_count("38", None, None) == cpc.SHOPPING_FIXED_TARGET


def test_resolve_target_count_max_cap_overrides_when_smaller() -> None:
    assert cpc.resolve_target_count("12", 500, 50) == 50
    assert cpc.resolve_target_count("12", 10, 50) == 10  # 자연 목표가 더 작으면 그대로


def test_dedupe_by_contentid_keeps_first_occurrence_and_counts_removed() -> None:
    items = [
        build_raw_item(contentid="1", title="첫번째"),
        build_raw_item(contentid="2", title="두번째"),
        build_raw_item(contentid="1", title="첫번째(중복)"),
    ]
    deduped, removed = cpc.dedupe_by_contentid(items)
    assert [item["title"] for item in deduped] == ["첫번째", "두번째"]
    assert removed == 1


def test_dedupe_by_contentid_never_merges_items_without_a_contentid() -> None:
    items = [build_raw_item(contentid=""), build_raw_item(contentid="")]
    deduped, removed = cpc.dedupe_by_contentid(items)
    assert len(deduped) == 2
    assert removed == 0


# --- probe_total_count --------------------------------------------------------


def test_probe_total_count_raises_quota_exceeded_immediately(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": [([], None, "quota_exceeded")]})
    call_counter = [0]
    try:
        cpc.probe_total_count(client, "26", "12", call_counter)
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0] == 1


def test_probe_total_count_returns_none_after_exhausting_retries(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": [([], None, "api_error")] * cpc.MAX_RETRIES_ON_API_ERROR})
    assert cpc.probe_total_count(client, "26", "12", [0]) is None


# --- fetch_type_candidates (totalCount 확인 -> 한 번에 받기 -> 폴백 -> 중복 제거) ---


def test_fetch_type_candidates_sends_ldong_regn_cd_not_area_code(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": type_page([build_raw_item(contentid="1")])})
    cpc.fetch_type_candidates(client, "26", "12", call_counter=[0])
    content_type_id, area_code, page_no, num_rows, ldong_regn_cd = client.area_based_list_calls[0]
    assert ldong_regn_cd == "26"
    assert area_code is None


def test_fetch_type_candidates_probes_then_fetches_once_when_big_call_matches_target(monkeypatch) -> None:
    no_sleep(monkeypatch)
    items = [build_raw_item(contentid=str(i)) for i in range(5)]
    client = FakeTourApiClient(pages_by_type={"12": type_page(items)})

    result_items, total_count, duplicates_removed = cpc.fetch_type_candidates(client, "26", "12", call_counter=[0])

    assert len(result_items) == 5
    assert total_count == 5
    assert duplicates_removed == 0
    assert len(client.area_based_list_calls) == 2  # probe + 한 번에 받기


def test_fetch_type_candidates_falls_back_to_pagination_when_big_call_returns_fewer_than_target(monkeypatch) -> None:
    no_sleep(monkeypatch)
    pages_by_type = {
        "12": [
            ([build_raw_item(contentid="probe")], 10, "ok"),  # probe: totalCount=10
            ([build_raw_item(contentid=str(i)) for i in range(6)], 10, "ok"),  # 한 번에 받기: 6건뿐(서버 상한)
            ([build_raw_item(contentid=str(i)) for i in range(5)], 10, "ok"),  # 폴백 page1: 5건
            ([build_raw_item(contentid=str(i)) for i in range(5, 10)], 10, "ok"),  # 폴백 page2: 나머지 5건
        ]
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)

    result_items, total_count, duplicates_removed = cpc.fetch_type_candidates(client, "26", "12", call_counter=[0])

    assert total_count == 10
    assert len(result_items) == 10
    assert duplicates_removed == 0
    assert len(client.area_based_list_calls) == 4  # probe + 한 번에 받기(부족) + 폴백 2페이지


def test_fetch_type_candidates_dedupes_overlapping_fallback_pages(monkeypatch) -> None:
    no_sleep(monkeypatch)
    # 폴백 page1이 id 1/2/3을, page2가 불안정한 arrange="P" 정렬 때문에
    # id 3/4로 다시 겹쳐서 돌아오는 상황을 재현한다.
    pages_by_type = {
        "12": [
            ([build_raw_item(contentid="probe")], 4, "ok"),
            ([build_raw_item(contentid="x")], 4, "ok"),  # 한 번에 받기: 1건뿐 -> 폴백
            ([build_raw_item(contentid="1"), build_raw_item(contentid="2"), build_raw_item(contentid="3")], 4, "ok"),
            ([build_raw_item(contentid="3"), build_raw_item(contentid="4")], 4, "ok"),
        ]
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)

    result_items, total_count, duplicates_removed = cpc.fetch_type_candidates(client, "26", "12", call_counter=[0])

    assert sorted(item["contentid"] for item in result_items) == ["1", "2", "3", "4"]
    assert duplicates_removed == 1


def test_fetch_type_candidates_shopping_target_is_capped_even_with_a_larger_total_count(monkeypatch) -> None:
    no_sleep(monkeypatch)
    items = [build_raw_item(contentid=str(i), contenttypeid="38") for i in range(cpc.SHOPPING_FIXED_TARGET)]
    pages_by_type = {
        "38": [
            ([build_raw_item(contentid="probe", contenttypeid="38")], 987, "ok"),
            (items, 987, "ok"),
        ]
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)

    result_items, total_count, duplicates_removed = cpc.fetch_type_candidates(client, "26", "38", call_counter=[0])

    assert total_count == 987
    assert len(result_items) == cpc.SHOPPING_FIXED_TARGET
    # 한 번에 받기에서 목표(60)를 정확히 채웠으니 폴백은 없다 - 호출은 probe+한 번뿐.
    assert len(client.area_based_list_calls) == 2


def test_fetch_type_candidates_respects_max_cap(monkeypatch) -> None:
    no_sleep(monkeypatch)
    probe_and_call = [([build_raw_item(contentid="1")], 348, "ok"), ([build_raw_item(contentid="1")], 348, "ok")]
    client = FakeTourApiClient(pages_by_type={"12": probe_and_call})

    result_items, total_count, _ = cpc.fetch_type_candidates(client, "26", "12", call_counter=[0], max_cap=1)

    assert total_count == 348
    assert len(result_items) == 1
    # 한 번에 받기 호출의 num_rows가 min(348,1)=1로 깎여서 전달됐는지 확인.
    assert client.area_based_list_calls[1][3] == 1


def test_fetch_type_candidates_raises_quota_exceeded_from_probe(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": [([], None, "quota_exceeded")]})
    call_counter = [0]
    try:
        cpc.fetch_type_candidates(client, "26", "12", call_counter=call_counter)
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0] == 1


def test_fetch_type_candidates_raises_quota_exceeded_from_big_call(monkeypatch) -> None:
    no_sleep(monkeypatch)
    pages_by_type = {"12": [([build_raw_item()], 5, "ok"), ([], None, "quota_exceeded")]}
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    try:
        cpc.fetch_type_candidates(client, "26", "12", call_counter=[0])
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded:
        pass


# --- collect_place_candidates (전체 오케스트레이션 + 요약 집계) -------------


def test_collect_place_candidates_builds_summary_and_separates_candidates(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{"12": type_page([build_raw_item(contentid="8888888", title="새로운 장소", addr1="부산광역시 해운대구")])}
    )
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["new_candidates_total"] == 1
    assert result["summary"]["partial_due_to_quota"] is False
    assert result["candidates"][0]["contentid"] == "8888888"
    assert result["candidates"][0]["suggested_area"] == "haeundae"
    assert result["candidates"][0]["area_mapping"] == "sigungu"
    assert result["already_in_catalog"] == []


def test_collect_place_candidates_marks_already_in_catalog_items(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(**{"12": type_page([build_raw_item(contentid="126081", title="해운대 해수욕장")])})
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["new_candidates_total"] == 0
    assert result["summary"]["already_in_catalog_total"] == 1
    assert result["already_in_catalog"][0]["contentid"] == "126081"


def test_collect_place_candidates_reports_total_count_and_duplicates_removed_by_type(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{"12": type_page([build_raw_item(contentid="1")], total_count=348)}
    )
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    result = cpc.collect_place_candidates(client, "busan", max_per_type_by_content_type={"12": 1, "14": 1, "28": 1, "38": 1})

    assert result["summary"]["total_count_by_type"]["관광지"] == 348
    assert result["summary"]["duplicates_removed_by_type"]["관광지"] == 0
    assert result["summary"]["duplicates_removed_total"] == 0


def test_collect_place_candidates_reports_nonzero_duplicates_removed(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{
            "12": [
                ([build_raw_item(contentid="probe")], 1, "ok"),
                (
                    [
                        build_raw_item(contentid="1", title="같은장소"),
                        build_raw_item(contentid="1", title="같은장소(중복)"),
                    ],
                    1,
                    "ok",
                ),
            ]
        }
    )
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    result = cpc.collect_place_candidates(client, "busan", max_per_type_by_content_type={"12": 2, "14": 1, "28": 1, "38": 1})

    assert result["summary"]["duplicates_removed_by_type"]["관광지"] == 1
    assert result["summary"]["duplicates_removed_total"] == 1
    assert result["summary"]["new_candidates_total"] == 1


def test_collect_place_candidates_skips_stage2_detail_calls_for_flagged_candidates(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{
            "12": type_page(
                [
                    build_raw_item(contentid="1111111", title="정상 관광지"),
                    build_raw_item(contentid="2222222", title="국제시장 먹자골목"),
                ]
            )
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
    assert all(call[0] != "2222222" for call in client.detail_intro_calls)
    assert "2222222" not in client.detail_common_calls


def test_collect_place_candidates_list_only_skips_all_stage2_calls(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(**{"12": type_page([build_raw_item(contentid="1111111", title="정상 관광지")])})
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
        "12": type_page([build_raw_item(contentid="8888888", title="첫 타입 신규 장소")]),
        "14": [([], None, "quota_exceeded")],
        # 28/38은 quota 중단으로 도달하지 않는다.
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["partial_due_to_quota"] is True
    assert result["summary"]["new_candidates_total"] == 1
    assert result["candidates"][0]["contentid"] == "8888888"
    assert result["candidates"][0]["detail_intro"] is None


def test_collect_place_candidates_saves_partial_results_on_quota_during_enrichment(monkeypatch) -> None:
    no_sleep(monkeypatch)
    disable_detail_cache_io(monkeypatch)
    pages_by_type = four_empty_types(
        **{
            "12": type_page(
                [
                    build_raw_item(contentid="8888888", title="첫 번째 신규 장소"),
                    build_raw_item(contentid="7777777", title="두 번째 신규 장소"),
                ]
            )
        }
    )

    class QuotaOnDetailClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            return None, "quota_exceeded"

    client = QuotaOnDetailClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan")

    assert result["summary"]["partial_due_to_quota"] is True
    assert len(result["candidates"]) == 2
    assert all(c["detail_intro"] is None for c in result["candidates"])


def test_collect_place_candidates_resumes_from_detail_cache_on_second_run(monkeypatch, tmp_path) -> None:
    """요구사항(이전 작업) 재확인: 두 번째 실행에서 상세 호출이 0이어야 한다."""
    no_sleep(monkeypatch)
    cache_path = tmp_path / "place_detail_cache_busan.json"
    monkeypatch.setattr(cpc, "DETAIL_CACHE_PATH", cache_path)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: [])

    pages_by_type = four_empty_types(**{"12": type_page([build_raw_item(contentid="1111111", title="정상 관광지")])})

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

    second_pages_by_type = four_empty_types(**{"12": type_page([build_raw_item(contentid="1111111", title="정상 관광지")])})
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
