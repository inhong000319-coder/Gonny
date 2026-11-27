"""부산에서 식당 데이터가 부족한 5개 구역(기장 gijang·가덕도 gadeok·강서
gangseo·구포 gupo·서면 seomyeon) 주변의 TourAPI 음식점(contentTypeId=39)
후보를 읽기 전용으로 수집해, 사람이 Google 평점·리뷰 수·가격대를 채울
shortlist CSV를 만든다. destinations/*.json 카탈로그는 전혀 수정하지
않는다. 네트워크 호출 외에는 local_only/reports/에만 파일을 쓴다.

배경: 2단계 장소 반영 후 기장 46곳은 식당 부족 때문에 비활성으로 보류
중이다(기장 일정의 식사가 최대 24km 떨어지는 문제) - 활성 상태인
가덕도·강서 장소에서도 식사 이동이 10~21km로 길고, 서면에는 식당이
0곳이다. 이 스크립트의 결과(scripts/add_tour_api_restaurants_jeju.py가
제주에서 한 것과 같은 절차 - shortlist CSV -> 사람이 평점 확인 -> 평점
3.8/리뷰 20개 이상만 별도 스크립트로 추가)는 그 식당 공백을 메우기
위한 원재료다.

collect_place_candidates.py의 공통 부분(TourApiClient, lDongRegnCd 기반
수집·한 번에 받기+페이지네이션 폴백·contentid 중복 제거·좌표 필터·
상세 캐시)은 import해서 그대로 쓰고 복사하지 않는다. 이 스크립트가 새로
만드는 부분은: contentTypeId=39 자체 수집, 기존 식당과의 fuzzy 중복
판정(이름 유사도+거리 - add_tour_api_restaurants_jeju.py의
find_dedup_match와 같은 기준), 식당 공백 구역/장소 판정, 공백 장소별
후보 선정, shortlist CSV 작성.

후보 선정(요구사항 5)의 "가까운 순 최대 2곳" + "firstmenu 있는 후보
우선"은 선정 시점에는 firstmenu를 모른다(areaBasedList2 응답에는 없고
detailIntro2에만 있다) - 둘을 동시에 만족시키려고, 공백 장소마다 2km
이내 미배정 후보 중 가장 가까운 DETAIL_POOL_SIZE_PER_GAP_PLACE(3)곳의
상세를 먼저 조회하고, 그 결과로 (firstmenu 있음 여부, 거리) 순으로
재정렬해 최종 FINAL_PICKS_PER_GAP_PLACE(2)곳만 남긴다(나머지 1곳은
다른 공백 장소가 다시 고를 수 있게 미배정으로 되돌린다). "상세 조회는
선정된 후보에 대해서만"이라는 요구사항의 "선정"을 이 3곳 예비 선정까지
포함하는 것으로 해석했다 - 순수 거리만으로 2곳을 먼저 확정하면
firstmenu를 아예 못 써보므로, 가장 가까운 소수(3곳)로 범위를 좁혀 상세
호출 비용을 작게 유지하면서도 firstmenu 우선순위를 실제로 적용했다.
firstmenu가 진짜 TourAPI detailIntro2 필드인지는 이 저장소에
DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE 같은 검증된 상수가 없어
직접 실행으로 확인하지 못했다 - 다만 local_only/data/
restaurant_shortlist_busan.csv(이전에 사람이 만든 것으로 보이는 기존
부산 식당 shortlist)에 firstmenu 열이 실제 값("낙지볶음" 등)으로 차 있어
근거가 있다고 보고 그대로 썼다. 실행 결과가 다르면(필드가 없거나 다른
이름이면) 보고해 달라.

Usage:
    python scripts/collect_restaurant_candidates_busan.py --help
    python scripts/collect_restaurant_candidates_busan.py --list-only
    python scripts/collect_restaurant_candidates_busan.py
    python scripts/collect_restaurant_candidates_busan.py --out local_only/reports/my_run.json
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import median

# Windows 콘솔은 리다이렉트 시 cp949로 기본 인코딩되어 한글이 깨진다.
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from app.core.settings import Settings  # noqa: E402
from app.domains.rule_planner.services.travel_estimate import haversine_distance_km  # noqa: E402
from app.services.external_clients import TOUR_API_LDONG_REGN_CD_BY_CITY, TourApiClient  # noqa: E402

from collect_place_candidates import (  # noqa: E402
    QuotaExceeded,
    fetch_type_candidates,
    filter_by_coordinates,
    load_detail_cache,
    load_existing_places,
    load_tour_api_key_from_env_file,
    normalize_raw_item,
    save_detail_cache,
)

DEFAULT_OUT_PATH = PROJECT_ROOT / "local_only" / "reports" / "restaurant_candidates_busan_raw.json"
DEFAULT_CSV_PATH = PROJECT_ROOT / "local_only" / "reports" / "restaurant_shortlist_busan_expansion.csv"
DETAIL_CACHE_PATH = PROJECT_ROOT / "local_only" / "reports" / "restaurant_detail_cache_busan.json"

REQUEST_INTERVAL_SECONDS = 0.2
MAX_RETRIES_ON_API_ERROR = 5
RETRY_BACKOFF_SECONDS = 2.0

RESTAURANT_CONTENT_TYPE_ID = "39"

# 기존 카탈로그와의 중복 판정(find_catalog_duplicate, collect_place_
# candidates.py)과 달리, 이름 "정규화 후 완전 일치"가 아니라 difflib
# 유사도를 쓴다 - scripts/add_tour_api_restaurants_jeju.py의
# find_dedup_match와 같은 기준(300m, 유사도 0.45)을 그대로 따른다.
EXISTING_RESTAURANT_DEDUP_DISTANCE_KM = 0.3
EXISTING_RESTAURANT_DEDUP_SIMILARITY_THRESHOLD = 0.45

# 식당 공백 판정 대상 구역 - 2단계에서 새로 추가된 구역들(#158). 비활성
# 포함(요구사항 4) - 활성화 여부와 무관하게 "이 구역에 식당이 얼마나
# 가까이 있는가"를 본다.
TARGET_AREAS = ["gijang", "gadeok", "gangseo", "gupo", "seomyeon"]
GAP_DISTANCE_KM_THRESHOLD = 3.0

# 공백 장소 하나당 찾는 후보 반경과 최종 픽 수.
CANDIDATE_SEARCH_RADIUS_KM = 2.0
FINAL_PICKS_PER_GAP_PLACE = 2
# firstmenu 우선순위를 실제로 적용하기 위한 예비 후보 풀 크기 - 모듈
# docstring의 설계 설명 참고.
DETAIL_POOL_SIZE_PER_GAP_PLACE = 3

# 구역별 최종 후보 수 한도(요구사항 5) - 합 56, "50곳 안팎" 목표에 맞춘
# 고정값. 넘으면 공백 거리가 큰 장소의 후보부터 남긴다.
AREA_CANDIDATE_LIMITS: dict[str, int] = {
    "gijang": 24,
    "gangseo": 8,
    "gadeok": 6,
    "gupo": 6,
    "seomyeon": 10,
}

CSV_FIELDNAMES = [
    "candidate_id",
    "name",
    "addr1",
    "latitude",
    "longitude",
    "content_id",
    "lclsSystm1",
    "lclsSystm2",
    "lclsSystm3",
    "firstmenu",
    "dist_to_nearest_existing_restaurant_gap_km",
    "fills_gap_place",
    "google_rating",
    "google_rating_count",
    "price_level",
    "evidence_source",
    "confidence",
]


def load_existing_busan_restaurants() -> list[dict]:
    """activity_type에 "미식"이 있는 모든 장소(비활성 포함 - 요구사항 3이
    "비활성 제외 안 함"이라고 명시) - load_existing_places(collect_place_
    candidates.py)를 그대로 재사용한다(읽기 전용, destinations/busan.json을
    쓰지 않는다)."""
    return [place for place in load_existing_places("busan") if "미식" in (place.get("activity_type") or [])]


def load_target_area_places() -> list[dict]:
    """TARGET_AREAS에 속한 모든 장소(비활성 포함)."""
    return [place for place in load_existing_places("busan") if place.get("area") in TARGET_AREAS]


def find_existing_restaurant_duplicate(item: dict, existing_restaurants: list[dict]) -> dict | None:
    """(요구사항 3) content_id가 같거나, 300m 이내 + 이름 유사도(difflib)
    0.45 이상이면 중복으로 본다 - add_tour_api_restaurants_jeju.py의
    find_dedup_match와 같은 기준."""
    content_id = item.get("contentid")
    if content_id:
        for existing in existing_restaurants:
            if str(existing.get("content_id") or "") == content_id:
                return {"matched_id": existing["id"], "matched_name": existing["name"], "reason": "같은 content_id"}

    if item.get("latitude") is None or item.get("longitude") is None:
        return None
    for existing in existing_restaurants:
        if existing.get("latitude") is None or existing.get("longitude") is None:
            continue
        distance_km = haversine_distance_km(
            item["latitude"], item["longitude"], existing["latitude"], existing["longitude"]
        )
        if distance_km > EXISTING_RESTAURANT_DEDUP_DISTANCE_KM:
            continue
        similarity = difflib.SequenceMatcher(None, item["title"], existing["name"]).ratio()
        if similarity >= EXISTING_RESTAURANT_DEDUP_SIMILARITY_THRESHOLD:
            return {
                "matched_id": existing["id"],
                "matched_name": existing["name"],
                "reason": f"이름 유사도 {round(similarity, 3)} + 거리 {round(distance_km * 1000)}m 이내",
            }
    return None


def partition_existing_restaurant_duplicates(
    items: list[dict], existing_restaurants: list[dict]
) -> tuple[list[dict], list[dict]]:
    new_candidates: list[dict] = []
    duplicates: list[dict] = []
    for item in items:
        duplicate = find_existing_restaurant_duplicate(item, existing_restaurants)
        if duplicate is None:
            new_candidates.append(item)
        else:
            duplicates.append({**item, "exclude_reason": "existing_restaurant_duplicate", "matched": duplicate})
    return new_candidates, duplicates


def nearest_existing_restaurant_distance_km(
    place: dict, existing_restaurants: list[dict]
) -> float | None:
    if place.get("latitude") is None or place.get("longitude") is None:
        return None
    distances = [
        haversine_distance_km(place["latitude"], place["longitude"], existing["latitude"], existing["longitude"])
        for existing in existing_restaurants
        if existing.get("latitude") is not None and existing.get("longitude") is not None
    ]
    return min(distances) if distances else None


def analyze_gap_places(target_places: list[dict], existing_restaurants: list[dict]) -> dict:
    """(요구사항 4) 구역별 {장소 수, 공백 장소 목록(거리 포함), 거리
    중앙값/최댓값}. 공백 장소 = 가장 가까운 기존 식당까지 거리가
    GAP_DISTANCE_KM_THRESHOLD(3km)보다 먼 장소."""
    by_area: dict[str, dict] = {area: {"places": [], "gap_places": []} for area in TARGET_AREAS}
    for place in target_places:
        area = place.get("area")
        if area not in by_area:
            continue
        distance_km = nearest_existing_restaurant_distance_km(place, existing_restaurants)
        by_area[area]["places"].append({"id": place["id"], "name": place["name"], "distance_km": distance_km})
        if distance_km is not None and distance_km > GAP_DISTANCE_KM_THRESHOLD:
            by_area[area]["gap_places"].append(
                {
                    "id": place["id"],
                    "name": place["name"],
                    "area": area,
                    "latitude": place.get("latitude"),
                    "longitude": place.get("longitude"),
                    "gap_distance_km": distance_km,
                }
            )
    return by_area


def build_gap_summary(gap_analysis: dict) -> dict:
    summary = {}
    for area, data in gap_analysis.items():
        distances = [p["distance_km"] for p in data["places"] if p["distance_km"] is not None]
        summary[area] = {
            "place_count": len(data["places"]),
            "gap_place_count": len(data["gap_places"]),
            "nearest_restaurant_distance_km_median": round(median(distances), 3) if distances else None,
            "nearest_restaurant_distance_km_max": round(max(distances), 3) if distances else None,
        }
    return summary


def select_candidates_for_gap_places(
    client: TourApiClient,
    gap_analysis: dict,
    new_candidates: list[dict],
    call_counter: list[int],
    cache: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    """(요구사항 5) 모든 공백 장소를 구역과 무관하게 공백 거리가 큰
    순서로 정렬해 처리한다 - 희소한 후보를 더 심한 공백부터 우선 배정
    하면서, 구역별 한도 초과 시에도 "뒤에 처리된(공백이 작은) 장소"의
    후보가 먼저 잘려나가게 한다(구역 안에서의 순서도 이미 공백이 큰
    순서이므로).

    Returns (selected, excluded) - selected는 구역 한도까지 통과한 최종
    후보(fills_gap_place 등 포함), excluded는 상세 풀에서 탈락했거나
    구역 한도로 잘린 후보(exclude_reason 포함)."""
    all_gap_places = [
        {**gap_place, "area": area}
        for area, data in gap_analysis.items()
        for gap_place in data["gap_places"]
    ]
    all_gap_places.sort(key=lambda p: p["gap_distance_km"], reverse=True)

    claimed_content_ids: set[str] = set()
    per_area_selected: dict[str, list[dict]] = {area: [] for area in TARGET_AREAS}
    excluded: list[dict] = []

    geocoded_candidates = [c for c in new_candidates if c.get("latitude") is not None and c.get("longitude") is not None]

    for gap_place in all_gap_places:
        if gap_place["latitude"] is None or gap_place["longitude"] is None:
            continue
        nearby = []
        for candidate in geocoded_candidates:
            content_id = candidate.get("contentid")
            if not content_id or content_id in claimed_content_ids:
                continue
            distance_km = haversine_distance_km(
                gap_place["latitude"], gap_place["longitude"], candidate["latitude"], candidate["longitude"]
            )
            if distance_km <= CANDIDATE_SEARCH_RADIUS_KM:
                nearby.append((distance_km, candidate))
        nearby.sort(key=lambda pair: pair[0])
        detail_pool = nearby[:DETAIL_POOL_SIZE_PER_GAP_PLACE]

        enriched_pool = []
        for distance_km, candidate in detail_pool:
            content_id = candidate["contentid"]
            claimed_content_ids.add(content_id)  # 상세 조회 중 다른 공백 장소가 동시에 집어가지 않게 임시 선점
            detail_intro = fetch_restaurant_detail(client, candidate, call_counter, cache)
            firstmenu = (detail_intro or {}).get("firstmenu") or None
            enriched_pool.append((distance_km, candidate, firstmenu))

        # firstmenu 있는 후보 우선, 그 다음 가까운 순.
        enriched_pool.sort(key=lambda row: (row[2] is None, row[0]))
        final_picks = enriched_pool[:FINAL_PICKS_PER_GAP_PLACE]
        losers = enriched_pool[FINAL_PICKS_PER_GAP_PLACE:]

        for distance_km, candidate, _firstmenu in losers:
            claimed_content_ids.discard(candidate["contentid"])  # 다른 공백 장소가 다시 고를 수 있게 되돌림

        for distance_km, candidate, firstmenu in final_picks:
            per_area_selected[gap_place["area"]].append(
                {
                    **candidate,
                    "firstmenu": firstmenu,
                    "fills_gap_place": gap_place["name"],
                    "fills_gap_place_id": gap_place["id"],
                    "dist_to_nearest_existing_restaurant_gap_km": round(distance_km, 3),
                }
            )

    selected: list[dict] = []
    for area, candidates in per_area_selected.items():
        limit = AREA_CANDIDATE_LIMITS[area]
        kept = candidates[:limit]
        dropped = candidates[limit:]
        selected.extend(kept)
        for item in dropped:
            claimed_content_ids.discard(item["contentid"])
            excluded.append({**item, "exclude_reason": "area_limit_exceeded"})

    return selected, excluded


def fetch_restaurant_detail(
    client: TourApiClient, candidate: dict, call_counter: list[int], cache: dict[str, dict]
) -> dict | None:
    """detailIntro2만 호출한다(firstmenu만 필요 - detailCommon2는 쓰지
    않는다). content_id가 캐시에 있으면 호출을 생략한다(재개 가능,
    요구사항 5)."""
    content_id = candidate.get("contentid")
    if not content_id:
        return None
    if content_id in cache:
        return cache[content_id].get("detail_intro")

    detail_intro: dict | None = None
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        call_counter[0] += 1
        detail_intro, status = client.fetch_detail_intro2(content_id, RESTAURANT_CONTENT_TYPE_ID)
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

    cache[content_id] = {"detail_intro": detail_intro}
    return detail_intro


def build_csv_rows(selected: list[dict]) -> list[dict]:
    rows = []
    for item in selected:
        rows.append(
            {
                "candidate_id": f"busan-new-restaurant-{item['contentid']}",
                "name": item["title"],
                "addr1": item["addr1"],
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "content_id": item["contentid"],
                "lclsSystm1": item.get("lcls_systm1") or "",
                "lclsSystm2": item.get("lcls_systm2") or "",
                "lclsSystm3": item.get("lcls_systm3") or "",
                "firstmenu": item.get("firstmenu") or "",
                "dist_to_nearest_existing_restaurant_gap_km": item["dist_to_nearest_existing_restaurant_gap_km"],
                "fills_gap_place": item["fills_gap_place"],
                "google_rating": "",
                "google_rating_count": "",
                "price_level": "",
                "evidence_source": "",
                "confidence": "",
            }
        )
    return rows


def write_shortlist_csv(rows: list[dict], path: Path) -> None:
    """엑셀에서 한글이 깨지지 않도록 utf-8-sig로 쓴다(요구사항 6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def collect_restaurant_candidates(client: TourApiClient, *, list_only: bool = False) -> dict:
    """전체 오케스트레이션. QuotaExceeded는 지금까지 모은 결과로
    partial_due_to_quota=True를 세팅해 돌려준다(예외를 밖으로 올리지
    않는다 - collect_place_candidates.py와 같은 방식)."""
    call_counter = [0]
    ldong_regn_cd = TOUR_API_LDONG_REGN_CD_BY_CITY["busan"]
    partial = False

    existing_restaurants = load_existing_busan_restaurants()
    target_places = load_target_area_places()
    gap_analysis = analyze_gap_places(target_places, existing_restaurants)
    gap_summary = build_gap_summary(gap_analysis)

    try:
        raw_items, total_count, duplicates_removed = fetch_type_candidates(
            client, ldong_regn_cd, RESTAURANT_CONTENT_TYPE_ID, call_counter
        )
    except QuotaExceeded:
        return {
            "city": "busan",
            "mode": "list-only" if list_only else "full",
            "gap_place_summary": gap_summary,
            "partial_due_to_quota": True,
            "api_call_count_total": call_counter[0],
        }

    normalized = [normalize_raw_item(raw, RESTAURANT_CONTENT_TYPE_ID) for raw in raw_items]
    kept, coordinate_excluded = filter_by_coordinates(normalized)
    for item in coordinate_excluded:
        item["exclude_reason"] = item.get("exclude_reason") or "좌표 없음 또는 부산 범위 밖"

    new_candidates, existing_duplicates = partition_existing_restaurant_duplicates(kept, existing_restaurants)

    stage1_api_call_count = call_counter[0]

    if list_only:
        return {
            "city": "busan",
            "mode": "list-only",
            "gap_place_summary": gap_summary,
            "total_count": total_count,
            "duplicates_removed_by_contentid": duplicates_removed,
            "coordinate_excluded_count": len(coordinate_excluded),
            "existing_restaurant_duplicate_count": len(existing_duplicates),
            "new_candidate_count": len(new_candidates),
            "api_call_count_total": stage1_api_call_count,
            "partial_due_to_quota": False,
        }

    cache = load_detail_cache(DETAIL_CACHE_PATH)
    try:
        selected, selection_excluded = select_candidates_for_gap_places(
            client, gap_analysis, new_candidates, call_counter, cache
        )
    except QuotaExceeded:
        partial = True
        selected, selection_excluded = [], []
    finally:
        save_detail_cache(cache, DETAIL_CACHE_PATH)

    stage2_api_call_count = call_counter[0] - stage1_api_call_count

    all_excluded = coordinate_excluded + existing_duplicates + selection_excluded

    return {
        "city": "busan",
        "mode": "full",
        "gap_place_summary": gap_summary,
        "area_candidate_limits": AREA_CANDIDATE_LIMITS,
        "total_count": total_count,
        "duplicates_removed_by_contentid": duplicates_removed,
        "selected_candidates": selected,
        "excluded": all_excluded,
        "summary": {
            "coordinate_excluded_count": len(coordinate_excluded),
            "existing_restaurant_duplicate_count": len(existing_duplicates),
            "new_candidate_count": len(new_candidates),
            "selected_candidate_count": len(selected),
            "selected_by_area": dict(Counter(_area_of_selected(item, gap_analysis) for item in selected)),
            "stage1_api_call_count": stage1_api_call_count,
            "stage2_api_call_count": stage2_api_call_count,
            "api_call_count_total": call_counter[0],
        },
        "partial_due_to_quota": partial,
    }


def _area_of_selected(item: dict, gap_analysis: dict) -> str:
    for area, data in gap_analysis.items():
        for gap_place in data["gap_places"]:
            if gap_place["id"] == item.get("fills_gap_place_id"):
                return area
    return "(미상)"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "부산 식당 공백 구역(기장·가덕도·강서·구포·서면) 주변의 TourAPI 음식점 후보를 "
            "읽기 전용으로 수집해 local_only/reports/에 shortlist CSV를 만든다. "
            "destinations/*.json 카탈로그는 수정하지 않는다."
        )
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="목록 수집과 공백 장소 요약까지만 하고 후보 선정·상세 조회·CSV 작성은 건너뜀",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help=f"결과 JSON 저장 경로 (기본: {DEFAULT_OUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    api_key = load_tour_api_key_from_env_file()
    if not api_key:
        print("TOUR_API_KEY not found in .env - aborting without calling TourAPI.")
        return

    settings = Settings(tour_api_key=api_key)
    client = TourApiClient(settings)

    result = collect_restaurant_candidates(client, list_only=args.list_only)

    out_path = args.out if args.out.is_absolute() else PROJECT_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== busan 식당 공백 구역 후보 수집 결과 ({result['mode']}) ===")
    print("구역별 공백 요약:")
    for area, stats in result["gap_place_summary"].items():
        print(
            f"  {area}: 장소 {stats['place_count']}곳, 공백 장소 {stats['gap_place_count']}곳, "
            f"최근접 식당 거리 중앙값 {stats['nearest_restaurant_distance_km_median']}km, "
            f"최댓값 {stats['nearest_restaurant_distance_km_max']}km"
        )

    if result["mode"] == "list-only":
        print(f"\ntotalCount: {result.get('total_count')}")
        print(f"contentid 중복 제거: {result.get('duplicates_removed_by_contentid')}건")
        print(f"좌표 제외: {result.get('coordinate_excluded_count')}건")
        print(f"기존 식당 중복 제외: {result.get('existing_restaurant_duplicate_count')}건")
        print(f"신규 후보: {result.get('new_candidate_count')}건")
    else:
        summary = result["summary"]
        print(f"\n좌표 제외: {summary['coordinate_excluded_count']}건")
        print(f"기존 식당 중복 제외: {summary['existing_restaurant_duplicate_count']}건")
        print(f"신규 후보: {summary['new_candidate_count']}건")
        print(f"최종 선정: {summary['selected_candidate_count']}건 (구역별 {summary['selected_by_area']})")
        print(
            f"1단계 API 호출 {summary['stage1_api_call_count']}회, "
            f"2단계 API 호출 {summary['stage2_api_call_count']}회, "
            f"합계 {summary['api_call_count_total']}회"
        )
        csv_path = DEFAULT_CSV_PATH
        write_shortlist_csv(build_csv_rows(result["selected_candidates"]), csv_path)
        print(f"shortlist CSV: {csv_path}")

    if result.get("partial_due_to_quota"):
        print("\n!! TourAPI 요청 한도를 초과해 중단했습니다. 다시 실행하면 이어서 진행됩니다.")
    print(f"\n저장 위치: {out_path}")


if __name__ == "__main__":
    main()
