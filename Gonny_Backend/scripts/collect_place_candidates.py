"""부산(기본) TourAPI 관광 활동 후보 장소를 읽기 전용으로 수집해 중간
산출물(JSON)을 local_only/reports/에 만든다 - destinations/*.json
카탈로그는 이 스크립트에서 전혀 수정하지 않는다. 수집·중간 산출물
생성까지만 하는 1단계 스크립트다.

배경: 부산 활동 후보가 25곳뿐이라 recommended_max_days가 8일로 짧다
(compute_recommended_max_days 참고). 이 스크립트가 만든 결과(신규 후보/
기존 중복/제외 사유/area 제안)는 사람이 검토한 뒤 실제 카탈로그 반영
여부를 결정하는 원재료다.

수집 대상: contentTypeId 12(관광지)·14(문화시설)·28(레포츠)·38(쇼핑).
39(음식점)·32(숙박)는 수집하지 않는다.

Usage:
    python scripts/collect_place_candidates.py --help
    python scripts/collect_place_candidates.py --city busan
    python scripts/collect_place_candidates.py --city busan --max-per-type 50 \
        --out local_only/reports/my_run.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

# Windows 콘솔은 리다이렉트 시 cp949로 기본 인코딩되어 한글이 깨진다.
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings  # noqa: E402
from app.domains.rule_planner.services.travel_estimate import haversine_distance_km  # noqa: E402
from app.services.external_clients import (  # noqa: E402
    DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE,
    TOUR_API_AREA_CODE_BY_CITY,
    TourApiClient,
    _collapse_whitespace,
    _normalize_tour_api_title,
)

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
ENV_FILE = REPO_ROOT / ".env"
DEFAULT_OUT_PATH = PROJECT_ROOT / "local_only" / "reports" / "place_candidates_busan_raw.json"

REQUEST_INTERVAL_SECONDS = 0.2
MAX_RETRIES_ON_API_ERROR = 5
RETRY_BACKOFF_SECONDS = 2.0
PAGE_SIZE = 100
DUPLICATE_DISTANCE_M = 300.0

# 수집 대상 contentTypeId - 39(음식점)·32(숙박)는 요구사항상 제외한다.
COLLECT_CONTENT_TYPE_LABELS: dict[str, str] = {
    "12": "관광지",
    "14": "문화시설",
    "28": "레포츠",
    "38": "쇼핑",
}

# 부산 대략 범위(작업 지시 Context 기준) - 이 범위 밖 좌표는 주소 오류나
# 다른 지역 체인점 등 실제로는 부산이 아닌 레코드로 보고 제외한다.
BUSAN_BOUNDS = {"lat_min": 34.9, "lat_max": 35.4, "lng_min": 128.7, "lng_max": 129.4}

# addr1 키워드 -> 기존 destinations/busan.json의 6개 area(nampo/songdo/
# haeundae/gwangalli/centum/dongnae) 제안용 매핑표. scripts/
# fetch_accommodation_catalog.py의 AREA_MATCH_KEYWORDS["busan"]과 같은
# 키워드를 쓴다 - 엔진 코드가 아니라 이 스크립트 안의 제안용 표이므로
# 사람이 쉽게 고칠 수 있게 여기 그대로 둔다. 우선순위는 딕셔너리 순서
# (먼저 일치하는 키를 쓴다).
BUSAN_AREA_SUGGESTION_KEYWORDS: dict[str, list[str]] = {
    "nampo": ["남포"],
    "songdo": ["송도"],
    "gwangalli": ["광안리", "광안"],
    "haeundae": ["해운대"],
    "dongnae": ["동래"],
    "centum": ["센텀"],
}
AREA_NEEDS_REVIEW_NOTE = "새 area 필요 여부 검토"


class QuotaExceeded(Exception):
    """TourAPI의 일일/전역 요청 한도를 넘겼을 때 수집 루프를 즉시 빠져
    나오기 위해 쓴다. 지금까지 실제로 호출한 횟수를 들고 있어, 잡는 쪽이
    부분 결과를 그대로 저장하고 명확한 메시지로 중단할 수 있게 한다."""

    def __init__(self, api_call_count: int) -> None:
        super().__init__("TourAPI 요청 한도 초과")
        self.api_call_count = api_call_count


def load_tour_api_key_from_env_file() -> str | None:
    """scripts/fetch_place_operating_hours.py 등과 같은 방식: docker-compose
    env_file을 거치지 않는 스크립트이므로 저장소 루트 .env를 직접 읽는다.
    이 함수는 "사용자가 스크립트를 실행할 때"만 호출되며, 검증(테스트)은
    이 함수를 호출하지 않는 가짜 클라이언트로 진행한다."""
    if not ENV_FILE.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def mask_service_key(url: str) -> str:
    """URL/쿼리 문자열에서 serviceKey 값을 지운다 - 출력·로그·산출물 어디에도
    실제 키 값이 남지 않게 하기 위한 방어적 유틸리티."""
    return re.sub(r"(serviceKey=)[^&]*", r"\1***", url)


def suggest_area(addr1: str) -> tuple[str | None, str | None]:
    """(suggested_area, area_note) - BUSAN_AREA_SUGGESTION_KEYWORDS 중
    addr1에 포함된 첫 키워드의 area를 제안한다. 아무 키워드도 맞지 않으면
    suggested_area=None, area_note=AREA_NEEDS_REVIEW_NOTE로 남겨, 기장군·
    강서구처럼 기존 6개 area에 맞지 않는 곳을 사람이 검토하게 한다."""
    for area, keywords in BUSAN_AREA_SUGGESTION_KEYWORDS.items():
        if any(keyword in addr1 for keyword in keywords):
            return area, None
    return None, AREA_NEEDS_REVIEW_NOTE


def is_within_busan_bounds(lat: float, lng: float) -> bool:
    return (
        BUSAN_BOUNDS["lat_min"] <= lat <= BUSAN_BOUNDS["lat_max"]
        and BUSAN_BOUNDS["lng_min"] <= lng <= BUSAN_BOUNDS["lng_max"]
    )


def normalize_raw_item(raw: dict, content_type_id: str) -> dict:
    """요구사항 3이 보존하라고 한 값만 꺼내고, 원본 응답 전체는 "raw"에
    그대로 둔다. 좌표/범위 필터는 여기서 적용하지 않는다(필터 여부는
    filter_by_coordinates가 결정) - 이 함수는 아무것도 제외하지 않는다."""
    mapx = raw.get("mapx")
    mapy = raw.get("mapy")
    try:
        longitude = float(mapx) if mapx not in (None, "") else None
        latitude = float(mapy) if mapy not in (None, "") else None
    except (TypeError, ValueError):
        longitude = latitude = None

    return {
        "contentid": str(raw.get("contentid", "")).strip() or None,
        "contenttypeid": str(raw.get("contenttypeid", "")).strip() or content_type_id,
        "title": str(raw.get("title", "")).strip(),
        "addr1": str(raw.get("addr1", "")).strip(),
        "addr2": str(raw.get("addr2", "")).strip(),
        "latitude": latitude,
        "longitude": longitude,
        "cat1": raw.get("cat1") or None,
        "cat2": raw.get("cat2") or None,
        "cat3": raw.get("cat3") or None,
        "has_firstimage": bool(str(raw.get("firstimage", "")).strip()),
        "raw": raw,
    }


def filter_by_coordinates(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """정규화된 항목을 (통과, 제외)로 나눈다 - 제외 항목에는
    "exclude_reason"이 붙는다(요구사항 3)."""
    kept: list[dict] = []
    excluded: list[dict] = []
    for item in items:
        if item["latitude"] is None or item["longitude"] is None:
            excluded.append({**item, "exclude_reason": "좌표 없음"})
            continue
        if not is_within_busan_bounds(item["latitude"], item["longitude"]):
            excluded.append({**item, "exclude_reason": "부산 대략 범위 밖"})
            continue
        kept.append(item)
    return kept, excluded


def find_catalog_duplicate(item: dict, existing_places: list[dict]) -> dict | None:
    """(요구사항 5) 기존 destinations/busan.json의 places와 비교만 한다
    (읽기 전용 - 이 스크립트는 그 파일을 절대 쓰지 않는다). 두 방식 중
    하나라도 맞으면 중복으로 본다: ① 같은 content_id, ② 이름 정규화
    (_normalize_tour_api_title 재사용) 일치 + 좌표 거리 300m 이내."""
    content_id = item.get("contentid")
    if content_id:
        for place in existing_places:
            if str(place.get("content_id") or "") == content_id:
                return {
                    "matched_id": place["id"],
                    "matched_name": place["name"],
                    "reason": "같은 content_id",
                }

    candidate_title_collapsed = _collapse_whitespace(_normalize_tour_api_title(item["title"]))
    for place in existing_places:
        if place.get("latitude") is None or place.get("longitude") is None:
            continue
        place_title_collapsed = _collapse_whitespace(_normalize_tour_api_title(place["name"]))
        if place_title_collapsed != candidate_title_collapsed or not candidate_title_collapsed:
            continue
        distance_km = haversine_distance_km(
            item["latitude"], item["longitude"], place["latitude"], place["longitude"]
        )
        if distance_km * 1000 <= DUPLICATE_DISTANCE_M:
            return {
                "matched_id": place["id"],
                "matched_name": place["name"],
                "reason": f"이름 일치 + 좌표 {round(distance_km * 1000)}m 이내",
            }
    return None


def partition_duplicates(items: list[dict], existing_places: list[dict]) -> tuple[list[dict], list[dict]]:
    new_candidates: list[dict] = []
    already_in_catalog: list[dict] = []
    for item in items:
        duplicate = find_catalog_duplicate(item, existing_places)
        if duplicate is None:
            new_candidates.append(item)
        else:
            already_in_catalog.append({**item, "already_in_catalog": duplicate})
    return new_candidates, already_in_catalog


def fetch_type_candidates(
    client: TourApiClient,
    area_code: str,
    content_type_id: str,
    max_items: int,
    call_counter: list[int],
) -> list[dict]:
    """contentTypeId 하나에 대해 areaBasedList2를 페이지네이션으로 호출해
    최대 max_items건을 모은다. call_counter[0]는 실제 API 호출마다 늘어나며
    collect_place_candidates 전체에서 공유된다(요구사항 7의 "호출 횟수").
    quota_exceeded는 즉시 QuotaExceeded로 올리고, 그 외 api_error는 기존
    스크립트들과 같은 백오프 재시도(MAX_RETRIES_ON_API_ERROR)를 쓴다."""
    collected: list[dict] = []
    page = 1
    total_count: int | None = None
    while len(collected) < max_items:
        page_size = min(PAGE_SIZE, max_items - len(collected))
        items: list[dict] = []
        for attempt in range(MAX_RETRIES_ON_API_ERROR):
            call_counter[0] += 1
            items, total_count, status = client.fetch_area_based_list2(content_type_id, area_code, page, page_size)
            if status == "quota_exceeded":
                raise QuotaExceeded(call_counter[0])
            if status == "ok":
                break
            print(
                f"    [{content_type_id}] page {page} 호출 실패(api_error) - 재시도 {attempt + 1}/{MAX_RETRIES_ON_API_ERROR}",
                flush=True,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
        else:
            items = []
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if not items:
            break
        collected.extend(items)
        print(
            f"    [{content_type_id}] page {page}: {len(items)}건 (누적 {len(collected)}"
            f"{f'/{total_count}' if total_count is not None else ''}, 총 API 호출 {call_counter[0]}회)",
            flush=True,
        )
        if total_count is not None and len(collected) >= total_count:
            break
        page += 1
    return collected[:max_items]


def extract_known_hours_fields(detail_intro: dict | None, content_type_id: str | None) -> tuple[str | None, str | None]:
    """이용시간/휴무일만 따로 꺼내는 편의 필드 - 이미 실제 응답으로 검증된
    DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE 매핑만 재사용한다(주차·
    이용요금 필드명은 contentTypeId별로 검증된 매핑이 없어 여기서 추출하지
    않는다 - detail_intro의 raw 안에 그대로 남아있으니 사람이 직접 확인).
    매핑에 없는 contentTypeId나 없는 필드는 그냥 None - KeyError로 죽지
    않는다."""
    if detail_intro is None or content_type_id is None:
        return None, None
    fields = DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE.get(content_type_id)
    if fields is None:
        return None, None
    hours_field, closed_field = fields
    open_hours = str(detail_intro.get(hours_field, "") or "").strip() or None
    closed_days = str(detail_intro.get(closed_field, "") or "").strip() or None
    return open_hours, closed_days


def enrich_candidate(client: TourApiClient, item: dict, call_counter: list[int]) -> dict:
    """(요구사항 4) detailIntro2/detailCommon2를 호출해 원문 그대로
    detail_intro/detail_common에 담는다(파싱·가공 금지). open_hours/
    closed_days는 이미 검증된 매핑만 재사용한 편의 추출(위 함수 참고).
    content_id/content_type_id가 없으면 호출하지 않고 전부 None."""
    content_id = item.get("contentid")
    content_type_id = item.get("contenttypeid")
    detail_intro: dict | None = None
    detail_common: dict | None = None

    if content_id and content_type_id:
        for attempt in range(MAX_RETRIES_ON_API_ERROR):
            call_counter[0] += 1
            detail_intro, status = client.fetch_detail_intro2(content_id, content_type_id)
            if status == "quota_exceeded":
                raise QuotaExceeded(call_counter[0])
            if status == "ok":
                break
            print(
                f"    detailIntro2({content_id}) 호출 실패(api_error) - 재시도 {attempt + 1}/{MAX_RETRIES_ON_API_ERROR}",
                flush=True,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
        time.sleep(REQUEST_INTERVAL_SECONDS)

        for attempt in range(MAX_RETRIES_ON_API_ERROR):
            call_counter[0] += 1
            detail_common, status = client.fetch_detail_common2(content_id)
            if status == "quota_exceeded":
                raise QuotaExceeded(call_counter[0])
            if status == "ok":
                break
            print(
                f"    detailCommon2({content_id}) 호출 실패(api_error) - 재시도 {attempt + 1}/{MAX_RETRIES_ON_API_ERROR}",
                flush=True,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
        time.sleep(REQUEST_INTERVAL_SECONDS)

    open_hours, closed_days = extract_known_hours_fields(detail_intro, content_type_id)
    return {
        **item,
        "detail_intro": detail_intro,
        "detail_common": detail_common,
        "open_hours": open_hours,
        "closed_days": closed_days,
    }


def load_existing_places(city: str) -> list[dict]:
    path = DESTINATIONS_DIR / f"{city}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["places"]


def build_summary(
    *,
    per_type_collected: dict[str, int],
    excluded: list[dict],
    already_in_catalog: list[dict],
    new_candidates: list[dict],
    api_call_count: int,
    partial: bool,
) -> dict:
    exclude_reason_counts = Counter(item["exclude_reason"] for item in excluded)
    suggested_area_counts = Counter((item.get("suggested_area") or "(미정)") for item in new_candidates)
    return {
        "collected_by_type": per_type_collected,
        "excluded_total": len(excluded),
        "excluded_by_reason": dict(exclude_reason_counts),
        "already_in_catalog_total": len(already_in_catalog),
        "new_candidates_total": len(new_candidates),
        "new_candidates_by_suggested_area": dict(suggested_area_counts),
        "api_call_count": api_call_count,
        "partial_due_to_quota": partial,
    }


def collect_place_candidates(client: TourApiClient, city: str, max_per_type: int) -> dict:
    """전체 오케스트레이션: 수집 -> 좌표 필터 -> 중복 판정 -> area 제안 ->
    상세 보강 -> 요약. 어느 단계에서든 QuotaExceeded가 나면 그 단계까지
    모은 결과로 partial_due_to_quota=True를 세팅해 돌려준다 - 예외를
    바깥으로 올리지 않는다(요구사항 8)."""
    area_code = TOUR_API_AREA_CODE_BY_CITY[city]
    existing_places = load_existing_places(city)

    call_counter = [0]
    per_type_collected: dict[str, int] = {}
    all_kept: list[dict] = []
    all_excluded: list[dict] = []
    partial = False

    for content_type_id, label in COLLECT_CONTENT_TYPE_LABELS.items():
        print(f"=== {label}(contentTypeId={content_type_id}) 수집 시작 (최대 {max_per_type}건) ===", flush=True)
        try:
            raw_items = fetch_type_candidates(client, area_code, content_type_id, max_per_type, call_counter)
        except QuotaExceeded:
            partial = True
            print("!! 요청 한도 초과 - 수집을 중단합니다.", flush=True)
            break
        normalized = [normalize_raw_item(raw, content_type_id) for raw in raw_items]
        kept, excluded = filter_by_coordinates(normalized)
        per_type_collected[label] = len(kept)
        all_kept.extend(kept)
        all_excluded.extend(excluded)
        print(f"{label}: {len(kept)}건 통과, {len(excluded)}건 좌표 제외", flush=True)

    new_candidates, already_in_catalog = partition_duplicates(all_kept, existing_places)
    for item in new_candidates:
        item["suggested_area"], item["area_note"] = suggest_area(item["addr1"])

    print(
        f"\n중복 판정 완료: 기존 카탈로그 중복 {len(already_in_catalog)}건, 신규 후보 {len(new_candidates)}건",
        flush=True,
    )

    if not partial:
        enriched: list[dict] = []
        for index, item in enumerate(new_candidates):
            print(
                f"상세 보강 {index + 1}/{len(new_candidates)}: {item['title']} "
                f"(총 API 호출 {call_counter[0]}회)",
                flush=True,
            )
            try:
                enriched.append(enrich_candidate(client, item, call_counter))
            except QuotaExceeded:
                partial = True
                print("!! 상세 보강 중 요청 한도 초과 - 남은 후보는 상세 없이 저장합니다.", flush=True)
                # 상세 보강은 못 받았지만 후보 자체는 그대로 남긴다 - 다음
                # 실행에서 상세만 이어서 받을 수 있게.
                enriched.append({**item, "detail_intro": None, "detail_common": None, "open_hours": None, "closed_days": None})
                enriched.extend(
                    {**remaining, "detail_intro": None, "detail_common": None, "open_hours": None, "closed_days": None}
                    for remaining in new_candidates[index + 1 :]
                )
                break
        new_candidates = enriched

    summary = build_summary(
        per_type_collected=per_type_collected,
        excluded=all_excluded,
        already_in_catalog=already_in_catalog,
        new_candidates=new_candidates,
        api_call_count=call_counter[0],
        partial=partial,
    )

    return {
        "city": city,
        "max_per_type": max_per_type,
        "candidates": new_candidates,
        "excluded": all_excluded,
        "already_in_catalog": already_in_catalog,
        "summary": summary,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "부산(기본) TourAPI 관광 활동 후보 장소(관광지/문화시설/레포츠/쇼핑)를 "
            "읽기 전용으로 수집해 local_only/reports/에 중간 산출물 JSON을 만든다. "
            "destinations/*.json 카탈로그는 수정하지 않는다."
        )
    )
    parser.add_argument("--city", default="busan", choices=["busan"], help="수집할 도시 (이번 단계는 busan만 지원, 기본: busan)")
    parser.add_argument("--max-per-type", type=int, default=80, help="contentTypeId별 최대 수집 건수 (기본: 80)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH, help="결과 JSON 저장 경로 (기본: local_only/reports/place_candidates_busan_raw.json)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    api_key = load_tour_api_key_from_env_file()
    if not api_key:
        print("TOUR_API_KEY not found in .env - aborting without calling TourAPI.")
        return

    settings = Settings(tour_api_key=api_key)
    client = TourApiClient(settings)

    result = collect_place_candidates(client, args.city, args.max_per_type)

    out_path = args.out if args.out.is_absolute() else PROJECT_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = result["summary"]
    print(f"=== {args.city} 활동 후보 수집 결과 ===")
    print(f"타입별 수집(좌표 필터 통과): {summary['collected_by_type']}")
    print(f"좌표 제외: {summary['excluded_total']}건 {summary['excluded_by_reason']}")
    print(f"기존 카탈로그 중복: {summary['already_in_catalog_total']}건")
    print(f"신규 후보: {summary['new_candidates_total']}건")
    print(f"신규 후보의 suggested_area 분포: {summary['new_candidates_by_suggested_area']}")
    print(f"API 호출 횟수: {summary['api_call_count']}")
    if summary["partial_due_to_quota"]:
        print("\n!! TourAPI 요청 한도를 초과해 중단했습니다. 지금까지 모은 결과만 저장했습니다.")
    print(f"\n저장 위치: {out_path}")


if __name__ == "__main__":
    main()
