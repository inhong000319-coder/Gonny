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

    def fetch_area_based_list2(self, content_type_id, area_code, page_no, num_rows):
        self.area_based_list_calls.append((content_type_id, area_code, page_no, num_rows))
        queue = self._pages_by_type.get(content_type_id, [])
        if not queue:
            return [], 0, "ok"
        return queue.pop(0)

    def fetch_detail_intro2(self, content_id, content_type_id):
        return self._detail_intro_by_id.get(content_id, (None, "ok"))

    def fetch_detail_common2(self, content_id, content_type_id):
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
    }
    item.update(overrides)
    return item


def no_sleep(monkeypatch) -> None:
    monkeypatch.setattr(cpc.time, "sleep", lambda seconds: None)


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
    assert item["raw"] == raw


def test_normalize_raw_item_missing_optional_fields_defaults_to_none_without_raising() -> None:
    raw = build_raw_item(cat1="", cat2="", cat3="", firstimage="")
    del raw["mapx"]
    del raw["mapy"]
    item = cpc.normalize_raw_item(raw, "12")
    assert item["latitude"] is None
    assert item["longitude"] is None
    assert item["cat1"] is None
    assert item["has_firstimage"] is False


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


# --- suggest_area -------------------------------------------------------------


def test_suggest_area_matches_a_known_keyword() -> None:
    area, note = cpc.suggest_area("부산광역시 해운대구 우동 123")
    assert area == "haeundae"
    assert note is None


def test_suggest_area_flags_unmatched_address_for_review() -> None:
    area, note = cpc.suggest_area("부산광역시 기장군 기장읍 123")
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


# --- enrich_candidate (상세 보강, 방어적 읽기) --------------------------------


def test_enrich_candidate_attaches_raw_detail_dicts_verbatim(monkeypatch) -> None:
    no_sleep(monkeypatch)
    item = cpc.normalize_raw_item(build_raw_item(contentid="9000001"), "12")
    client = FakeTourApiClient(
        detail_intro_by_id={"9000001": ({"usetime": "09:00~18:00", "parking": "가능"}, "ok")},
        detail_common_by_id={"9000001": ({"homepage": "<a>site</a>", "overview": "설명"}, "ok")},
    )
    enriched = cpc.enrich_candidate(client, item, [0])
    assert enriched["detail_intro"] == {"usetime": "09:00~18:00", "parking": "가능"}
    assert enriched["detail_common"] == {"homepage": "<a>site</a>", "overview": "설명"}
    assert enriched["open_hours"] == "09:00~18:00"


def test_enrich_candidate_without_content_id_skips_calls_and_stays_none() -> None:
    item = cpc.normalize_raw_item(build_raw_item(contentid=""), "12")
    client = FakeTourApiClient()
    enriched = cpc.enrich_candidate(client, item, [0])
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
        cpc.enrich_candidate(QuotaClient(), item, call_counter)
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0]


# --- fetch_type_candidates (페이지네이션 + 재시도) ---------------------------


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
    items = cpc.fetch_type_candidates(client, "6", "12", max_items=80, call_counter=[0])
    assert [item["contentid"] for item in items] == ["1", "2", "3"]
    assert len(client.area_based_list_calls) == 2


def test_fetch_type_candidates_stops_at_max_items() -> None:
    client = FakeTourApiClient(
        pages_by_type={"12": [([build_raw_item(contentid=str(i)) for i in range(10)], 10, "ok")]}
    )
    items = cpc.fetch_type_candidates(client, "6", "12", max_items=5, call_counter=[0])
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
    items = cpc.fetch_type_candidates(client, "6", "12", max_items=80, call_counter=[0])
    assert [item["contentid"] for item in items] == ["1"]


def test_fetch_type_candidates_raises_quota_exceeded_immediately(monkeypatch) -> None:
    no_sleep(monkeypatch)
    client = FakeTourApiClient(pages_by_type={"12": [([], None, "quota_exceeded")]})
    call_counter = [0]
    try:
        cpc.fetch_type_candidates(client, "6", "12", max_items=80, call_counter=call_counter)
        assert False, "QuotaExceeded가 올라와야 한다"
    except cpc.QuotaExceeded as exc:
        assert exc.api_call_count == call_counter[0] == 1


# --- collect_place_candidates (전체 오케스트레이션 + 요약 집계) -------------


def test_collect_place_candidates_builds_summary_and_separates_candidates(monkeypatch) -> None:
    no_sleep(monkeypatch)
    pages_by_type = {
        "12": [([build_raw_item(contentid="8888888", title="새로운 장소", addr1="부산광역시 해운대구")], 1, "ok")],
        "14": [([], 0, "ok")],
        "28": [([], 0, "ok")],
        "38": [([], 0, "ok")],
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan", max_per_type=80)

    assert result["summary"]["new_candidates_total"] == 1
    assert result["summary"]["partial_due_to_quota"] is False
    assert result["candidates"][0]["contentid"] == "8888888"
    assert result["candidates"][0]["suggested_area"] == "haeundae"
    assert result["already_in_catalog"] == []


def test_collect_place_candidates_marks_already_in_catalog_items(monkeypatch) -> None:
    no_sleep(monkeypatch)
    pages_by_type = {
        "12": [([build_raw_item(contentid="126081", title="해운대 해수욕장")], 1, "ok")],
        "14": [([], 0, "ok")],
        "28": [([], 0, "ok")],
        "38": [([], 0, "ok")],
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan", max_per_type=80)

    assert result["summary"]["new_candidates_total"] == 0
    assert result["summary"]["already_in_catalog_total"] == 1
    assert result["already_in_catalog"][0]["contentid"] == "126081"


def test_collect_place_candidates_saves_partial_results_on_quota_exceeded(monkeypatch) -> None:
    no_sleep(monkeypatch)
    pages_by_type = {
        "12": [([build_raw_item(contentid="8888888", title="첫 타입 신규 장소")], 1, "ok")],
        "14": [([], None, "quota_exceeded")],
        # 28/38은 quota 중단으로 도달하지 않는다.
    }
    client = FakeTourApiClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan", max_per_type=80)

    assert result["summary"]["partial_due_to_quota"] is True
    # 12에서 모은 신규 후보는 보존된다.
    assert result["summary"]["new_candidates_total"] == 1
    assert result["candidates"][0]["contentid"] == "8888888"


def test_collect_place_candidates_saves_partial_results_on_quota_during_enrichment(monkeypatch) -> None:
    no_sleep(monkeypatch)
    pages_by_type = {
        "12": [
            (
                [
                    build_raw_item(contentid="8888888", title="첫 번째 신규 장소"),
                    build_raw_item(contentid="7777777", title="두 번째 신규 장소"),
                ],
                2,
                "ok",
            )
        ],
        "14": [([], 0, "ok")],
        "28": [([], 0, "ok")],
        "38": [([], 0, "ok")],
    }

    class QuotaOnDetailClient(FakeTourApiClient):
        def fetch_detail_intro2(self, content_id, content_type_id):
            return None, "quota_exceeded"

    client = QuotaOnDetailClient(pages_by_type=pages_by_type)
    monkeypatch.setattr(cpc, "load_existing_places", lambda city: list(EXISTING_PLACES))

    result = cpc.collect_place_candidates(client, "busan", max_per_type=80)

    assert result["summary"]["partial_due_to_quota"] is True
    # 상세 보강은 못 받았어도 두 후보 모두 결과에 남아있어야 한다.
    assert len(result["candidates"]) == 2
    assert all(c["detail_intro"] is None for c in result["candidates"])


def test_collect_place_candidates_never_touches_the_real_catalog_file(monkeypatch, tmp_path) -> None:
    """읽기 전용 보장: destinations/busan.json 파일 쓰기가 호출되지 않는다."""
    no_sleep(monkeypatch)
    import json as json_module

    busan_path = cpc.DESTINATIONS_DIR / "busan.json"
    original_mtime = busan_path.stat().st_mtime
    original_text = busan_path.read_text(encoding="utf-8")

    client = FakeTourApiClient(pages_by_type={"12": [([], 0, "ok")], "14": [([], 0, "ok")], "28": [([], 0, "ok")], "38": [([], 0, "ok")]})
    cpc.collect_place_candidates(client, "busan", max_per_type=80)

    assert busan_path.stat().st_mtime == original_mtime
    assert busan_path.read_text(encoding="utf-8") == original_text
    json_module.loads(original_text)  # 여전히 유효한 JSON인지도 같이 확인


# --- --help ------------------------------------------------------------------


def test_help_flag_does_not_raise(capsys) -> None:
    try:
        cpc.parse_args(["--help"])
        assert False, "argparse --help는 SystemExit을 던진다"
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "--max-per-type" in captured.out
