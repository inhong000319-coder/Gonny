from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import diagnose_area_based_list as dbl  # noqa: E402


class FakeTourApiClient:
    """TourApiClient를 흉내 내는 가짜 - 실제 네트워크 호출을 하지 않는다.
    responses: (content_type_id, region_label_key, arrange) -> 반환할 dict.
    region_label_key는 테스트 편의상 region_params를 그대로 쓴다(dict는
    해시 불가하므로 frozenset으로 변환해 키로 쓴다)."""

    def __init__(self, responses: dict) -> None:
        self._responses = responses
        self.calls: list[tuple] = []

    def fetch_area_based_list2_raw(self, content_type_id, region_params, arrange, page_no, num_rows):
        self.calls.append((content_type_id, region_params, arrange, page_no, num_rows))
        key = (content_type_id, frozenset(region_params.items()), arrange)
        return self._responses.get(key, {"resultCode": "0000", "resultMsg": "OK", "items": [], "total_count": 0})


def build_ok_result(total_count: int, titles: list[str]) -> dict:
    return {
        "resultCode": "0000",
        "resultMsg": "OK",
        "items": [{"title": title} for title in titles],
        "total_count": total_count,
    }


# --- mask_service_key --------------------------------------------------------


def test_mask_service_key_removes_the_key_value() -> None:
    masked = dbl.mask_service_key("https://example.com/x?serviceKey=SECRET123&pageNo=1")
    assert "SECRET123" not in masked
    assert "serviceKey=***" in masked


def test_mask_service_key_masks_key_embedded_in_an_exception_message() -> None:
    # httpx 예외 메시지에 요청 URL 전체가 그대로 포함되는 경우를 흉내낸다.
    exc_text = "ConnectError: failed for url 'https://apis.data.go.kr/...?serviceKey=ABCDEFG&contentTypeId=12'"
    masked = dbl.mask_service_key(exc_text)
    assert "ABCDEFG" not in masked
    assert "serviceKey=***" in masked


# --- format_arrange_label -----------------------------------------------------


def test_format_arrange_label_none_is_omitted_label() -> None:
    assert dbl.format_arrange_label(None) == "(생략)"


def test_format_arrange_label_passes_through_a_value() -> None:
    assert dbl.format_arrange_label("P") == "P"


# --- run_one_combination / format_row ----------------------------------------


def test_run_one_combination_merges_result_fields() -> None:
    client = FakeTourApiClient(
        {("12", frozenset({"areaCode": "6"}.items()), "P"): build_ok_result(15, ["감천문화마을"])}
    )
    row = dbl.run_one_combination(client, "12", "areaCode=6", {"areaCode": "6"}, "P")
    assert row["content_type_id"] == "12"
    assert row["region_label"] == "areaCode=6"
    assert row["arrange_label"] == "P"
    assert row["total_count"] == 15
    assert client.calls == [("12", {"areaCode": "6"}, "P", 1, 10)]


def test_format_row_shows_result_fields_and_top3_titles() -> None:
    row = {
        "content_type_id": "12",
        "region_label": "areaCode=6",
        "arrange_label": "P",
        **build_ok_result(235, ["감천문화마을", "해운대 해수욕장", "용두산공원", "네번째장소"]),
    }
    line = dbl.format_row(row)
    assert "totalCount=235" in line
    assert "받은항목수=4" in line
    assert "감천문화마을" in line
    assert "해운대 해수욕장" in line
    assert "용두산공원" in line
    assert "네번째장소" not in line  # 상위 3개만


def test_format_row_masks_service_key_inside_result_msg() -> None:
    row = {
        "content_type_id": "12",
        "region_label": "areaCode=6",
        "arrange_label": "P",
        "resultCode": "99",
        "resultMsg": "오류 (serviceKey=SECRET999 포함된 메시지 가정)",
        "items": [],
        "total_count": None,
    }
    line = dbl.format_row(row)
    assert "SECRET999" not in line
    assert "serviceKey=***" in line


def test_format_row_shows_masked_error_text_when_request_failed() -> None:
    row = {
        "content_type_id": "12",
        "region_label": "areaCode=6",
        "arrange_label": "P",
        "error": "ConnectError at ...?serviceKey=TOPSECRET",
    }
    line = dbl.format_row(row)
    assert "TOPSECRET" not in line
    assert "오류:" in line
    assert "serviceKey=***" in line


# --- build_summary -------------------------------------------------------------


def test_build_summary_ranks_top_5_by_total_count() -> None:
    rows = [
        {"content_type_id": "12", "region_label": "areaCode=6", "arrange_label": "P", "total_count": 15},
        {"content_type_id": "12", "region_label": "lDongRegnCd=26", "arrange_label": "P", "total_count": 235},
        {"content_type_id": "14", "region_label": "areaCode=6", "arrange_label": "P", "total_count": 4},
    ]
    lines = dbl.build_summary(rows)
    summary_text = "\n".join(lines)
    assert "totalCount=235" in summary_text
    # 235가 15보다 먼저(위에) 나와야 한다 - 내림차순 정렬.
    assert summary_text.index("totalCount=235") < summary_text.index("totalCount=15")


def test_build_summary_handles_no_valid_total_counts() -> None:
    rows = [{"content_type_id": "12", "region_label": "areaCode=6", "arrange_label": "P", "error": "api_error"}]
    lines = dbl.build_summary(rows)
    assert any("유효한 totalCount" in line for line in lines)


def test_build_summary_compares_omitted_arrange_vs_p() -> None:
    rows = [
        {
            "content_type_id": "12",
            "region_label": "areaCode=6",
            "arrange_label": dbl.format_arrange_label(None),
            "total_count": 300,
        },
        {"content_type_id": "12", "region_label": "areaCode=6", "arrange_label": "P", "total_count": 15},
    ]
    lines = dbl.build_summary(rows)
    matching = [line for line in lines if "contentTypeId=12 areaCode=6:" in line]
    assert len(matching) == 1
    assert "생략=300" in matching[0]
    assert "P=15" in matching[0]


def test_build_summary_reports_none_when_a_combination_is_missing() -> None:
    rows: list[dict] = []
    lines = dbl.build_summary(rows)
    assert any("생략=None vs P=None" in line for line in lines)


# --- 조합 개수 (요구사항 1: 4 x 2 x 8 = 64회 이내) ---------------------------


def test_combination_count_is_64() -> None:
    assert len(dbl.CONTENT_TYPE_IDS) == 4
    assert len(dbl.REGION_PARAM_VARIANTS) == 2
    assert len(dbl.ARRANGE_VALUES) == 8
    assert len(dbl.CONTENT_TYPE_IDS) * len(dbl.REGION_PARAM_VARIANTS) * len(dbl.ARRANGE_VALUES) == 64
