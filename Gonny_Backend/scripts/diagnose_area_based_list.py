"""areaBasedList2가 부산에서 기대보다 훨씬 적은/엉뚱한 결과를 주는 원인을
찾기 위한 진단 스크립트 - 읽기 전용, API만 호출하고 아무 파일도 고치지
않는다(collect_place_candidates.py가 쓰는 수집 로직은 전혀 건드리지
않음).

배경(PR #147·#148): arrange="P", areaCode=6으로 호출했더니 contentTypeId별
totalCount가 15/4/12/3 수준으로 작고, 감천문화마을·해운대 해수욕장 등
이미 카탈로그에 있는 대표 관광지가 하나도 안 나왔다. 가설은 ① arrange="P"가
결과를 좁힌다 ② areaCode 대신 lDongRegnCd=26(부산)을 써야 한다 ③ 두
파라미터의 조합 문제 - 이 스크립트는 그 조합들을 하나씩 실제로 호출해
totalCount/resultCode를 비교한다.

Usage:
    python scripts/diagnose_area_based_list.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings  # noqa: E402
from app.services.external_clients import TourApiClient  # noqa: E402

ENV_FILE = REPO_ROOT / ".env"
OUT_PATH = PROJECT_ROOT / "local_only" / "reports" / "area_based_list_diagnosis.txt"
REQUEST_INTERVAL_SECONDS = 0.2
PAGE_NO = 1
NUM_ROWS = 10

CONTENT_TYPE_IDS = ["12", "14", "28", "38"]

# (표시용 라벨, 실제 요청 파라미터) - 둘 다 부산을 가리키지만 서로 다른
# TourAPI 지역 식별 체계다.
REGION_PARAM_VARIANTS: list[tuple[str, dict[str, str]]] = [
    ("areaCode=6", {"areaCode": "6"}),
    ("lDongRegnCd=26", {"lDongRegnCd": "26"}),
]

# None은 arrange 파라미터 자체를 생략한다는 뜻 - "기본 정렬이 뭔지"도
# 같이 확인하기 위함.
ARRANGE_VALUES: list[str | None] = [None, "A", "C", "D", "O", "P", "Q", "R"]


def load_tour_api_key_from_env_file() -> str | None:
    """기존 스크립트들과 같은 방식: 저장소 루트 .env를 직접 읽는다. 이
    함수는 사용자가 스크립트를 실행할 때만 호출되고, 테스트는 가짜
    클라이언트로 진행해 이 함수를 호출하지 않는다."""
    if not ENV_FILE.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def mask_service_key(text: str) -> str:
    """serviceKey 값을 어떤 문자열에서든 지운다 - 요청 URL이 그대로 섞여
    나올 수 있는 예외 메시지(httpx 에러 등)까지 포함해, 출력/로그/저장
    파일 어디에도 실제 키가 남지 않게 한다."""
    return re.sub(r"(serviceKey=)[^&\s]*", r"\1***", text)


def format_arrange_label(arrange: str | None) -> str:
    return arrange if arrange is not None else "(생략)"


def run_one_combination(
    client: TourApiClient,
    content_type_id: str,
    region_label: str,
    region_params: dict[str, str],
    arrange: str | None,
) -> dict:
    """한 조합(contentTypeId x 지역 파라미터 x arrange)을 실제로 한 번
    호출해, 표에 쓸 필드를 더해 돌려준다."""
    result = client.fetch_area_based_list2_raw(
        content_type_id, region_params, arrange, page_no=PAGE_NO, num_rows=NUM_ROWS
    )
    return {
        "content_type_id": content_type_id,
        "region_label": region_label,
        "arrange_label": format_arrange_label(arrange),
        **result,
    }


def format_row(row: dict) -> str:
    """한 조합의 결과를 한 줄짜리 표 형태 문자열로 만든다. serviceKey가
    섞여 나올 수 있는 모든 텍스트 필드(resultMsg, 예외 메시지)는 출력
    직전에 마스킹한다."""
    prefix = f"{row['content_type_id']:<4} {row['region_label']:<16} {row['arrange_label']:<8}"
    if "error" in row:
        return f"{prefix} 오류: {mask_service_key(str(row['error']))}"

    items = row.get("items") or []
    top3_titles = ", ".join(str(item.get("title", "")) for item in items[:3])
    result_code = str(row.get("resultCode") or "")
    result_msg = mask_service_key(str(row.get("resultMsg") or ""))
    total_count = row.get("total_count")
    return (
        f"{prefix} resultCode={result_code:<6} resultMsg={result_msg:<30} "
        f"totalCount={total_count!s:<8} 받은항목수={len(items):<4} 상위3개={top3_titles}"
    )


def build_summary(rows: list[dict]) -> list[str]:
    """요구사항 3: totalCount가 가장 큰 조합 상위 5개, 그리고 같은
    contentTypeId·지역 조합에서 "arrange 생략"과 "P"의 totalCount 차이."""
    lines: list[str] = []

    ranked = sorted(
        (row for row in rows if row.get("total_count") is not None),
        key=lambda row: row["total_count"],
        reverse=True,
    )
    lines.append("=== totalCount가 가장 큰 조합 상위 5개 ===")
    if not ranked:
        lines.append("  (유효한 totalCount를 받은 조합이 없음)")
    for row in ranked[:5]:
        lines.append(
            f"  contentTypeId={row['content_type_id']} {row['region_label']} "
            f"arrange={row['arrange_label']} totalCount={row['total_count']}"
        )

    lines.append("")
    lines.append('=== "arrange 생략" vs "P" totalCount 비교 ===')
    by_key = {(row["content_type_id"], row["region_label"], row["arrange_label"]): row for row in rows}
    for content_type_id in CONTENT_TYPE_IDS:
        for region_label, _ in REGION_PARAM_VARIANTS:
            none_row = by_key.get((content_type_id, region_label, format_arrange_label(None)))
            p_row = by_key.get((content_type_id, region_label, "P"))
            none_count = none_row.get("total_count") if none_row else None
            p_count = p_row.get("total_count") if p_row else None
            lines.append(f"  contentTypeId={content_type_id} {region_label}: 생략={none_count} vs P={p_count}")

    return lines


def main() -> None:
    api_key = load_tour_api_key_from_env_file()
    if not api_key:
        print("TOUR_API_KEY not found in .env - aborting without calling TourAPI.")
        return

    settings = Settings(tour_api_key=api_key)
    client = TourApiClient(settings)

    output_lines: list[str] = []

    def emit(line: str) -> None:
        print(line, flush=True)
        output_lines.append(line)

    rows: list[dict] = []
    emit("=== areaBasedList2 arrange/지역 파라미터 진단 ===")
    call_count = 0
    for content_type_id in CONTENT_TYPE_IDS:
        for region_label, region_params in REGION_PARAM_VARIANTS:
            for arrange in ARRANGE_VALUES:
                row = run_one_combination(client, content_type_id, region_label, region_params, arrange)
                rows.append(row)
                emit(format_row(row))
                call_count += 1
                time.sleep(REQUEST_INTERVAL_SECONDS)

    emit(f"\n총 호출 횟수: {call_count}")
    emit("")
    for line in build_summary(rows):
        emit(line)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    emit(f"\n저장 위치: {OUT_PATH}")


if __name__ == "__main__":
    main()
