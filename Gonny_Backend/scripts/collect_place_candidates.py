"""부산(기본) TourAPI 관광 활동 후보 장소를 읽기 전용으로 수집해 중간
산출물(JSON)을 local_only/reports/에 만든다 - destinations/*.json
카탈로그는 이 스크립트에서 전혀 수정하지 않는다. 수집·중간 산출물
생성까지만 하는 1단계 스크립트다.

배경: 부산 활동 후보가 25곳뿐이라 recommended_max_days가 8일로 짧다
(compute_recommended_max_days 참고). 이 스크립트가 만든 결과(신규 후보/
기존 중복/제외 사유/area 제안/품질 플래그)는 사람이 검토한 뒤 실제
카탈로그 반영 여부를 결정하는 원재료다.

지역 파라미터: areaCode가 아니라 lDongRegnCd(법정동 시도 코드)를 쓴다 -
scripts/diagnose_area_based_list.py로 실제 호출해 확인한 결과, 부산
areaCode=6은 contentTypeId별 totalCount가 15/4/12/3 수준으로 극히
일부만 반환하지만 lDongRegnCd=26은 348/129/61/987을 반환한다(areaCode는
areacode 필드가 빈 레코드를 조용히 빠뜨리는 기존에 알려진 문제).

수집 대상: contentTypeId 12(관광지)·14(문화시설)·28(레포츠)·38(쇼핑).
39(음식점)·32(숙박)는 수집하지 않는다. 관광지/문화시설/레포츠는 totalCount
전체를, 쇼핑은 조회순 상위 60건을 목표로 한다 - totalCount를 먼저 알아낸
뒤 한 번의 큰 호출로 받고, 응답이 목표보다 적으면(서버 상한 가능성)
작은 페이지 크기로 페이지네이션 폴백한다. arrange="P" 정렬이 페이지를
넘기면 불안정해 같은 항목이 여러 페이지에 또 나올 수 있어, 어느 경로든
수집 후 contentid 기준 중복 제거를 항상 적용한다.

2단계 구조:
  1단계(목록): areaBasedList2 수집 + 좌표/범위 필터 + 기존 카탈로그 중복
    판정 + 품질 플래그 부여 + suggested_area 제안. 상세 호출 없음.
  2단계(상세): 중복·제외·품질 플래그가 있는 후보를 제외한 나머지에
    대해서만 detailIntro2/detailCommon2를 호출한다. 응답은
    local_only/reports/place_detail_cache_busan.json에 contentid별로
    캐시해 재실행 시 이미 받은 건 다시 호출하지 않는다(재개 가능).

Usage:
    python scripts/diagnose_area_based_list.py --help
    python scripts/collect_place_candidates.py --city busan
    python scripts/collect_place_candidates.py --city busan --list-only
    python scripts/collect_place_candidates.py --city busan --out local_only/reports/my_run.json
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
    TOUR_API_LDONG_REGN_CD_BY_CITY,
    TourApiClient,
    _collapse_whitespace,
    _normalize_tour_api_title,
)

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
ENV_FILE = REPO_ROOT / ".env"
DEFAULT_OUT_PATH = PROJECT_ROOT / "local_only" / "reports" / "place_candidates_busan_raw.json"
DETAIL_CACHE_PATH = PROJECT_ROOT / "local_only" / "reports" / "place_detail_cache_busan.json"

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

# 쇼핑(38)만 totalCount 전체가 아니라 조회순 상위 N건을 목표로 한다 -
# 987건 대부분이 약국·이불가게 같은 동네 상점이라(그중 상당수는 아래
# LCLS_SYSTM2_FLAG_RULES로도 걸러진다) 전체를 받을 필요가 없다.
SHOPPING_FIXED_TARGET = 60

# totalCount 확인 호출이 재시도까지 전부 실패했을 때만 쓰는 안전망 - 이
# 값이 실제 목표가 아니라, "totalCount를 아예 모를 때 그래도 뭔가는
# 받아야 한다"는 최후의 수단이다(쇼핑은 SHOPPING_FIXED_TARGET 자체가
# 이미 이 역할을 하므로 여기 없다).
FALLBACK_TARGET_IF_PROBE_FAILS: dict[str, int] = {
    "12": 120,
    "14": 60,
    "28": 40,
}

# 부산 대략 범위(작업 지시 Context 기준) - 이 범위 밖 좌표는 주소 오류나
# 다른 지역 체인점 등 실제로는 부산이 아닌 레코드로 보고 제외한다.
BUSAN_BOUNDS = {"lat_min": 34.9, "lat_max": 35.4, "lng_min": 128.7, "lng_max": 129.4}

# addr1 키워드 -> 기존 destinations/busan.json의 6개 area(nampo/songdo/
# haeundae/gwangalli/centum/dongnae) 제안용 매핑표 - lDongSignguCd가 없을
# 때만 쓰는 폴백이다(주 판정 기준은 아래 SIGUNGU_CODE_TO_AREA). scripts/
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

# lDongSignguCd(시군구 코드) -> 한글 구/군 이름 - 작업 지시 Context의 16개
# 전부를 담아, area 매핑 성공 여부와 무관하게 sigungu_name에 항상 사람이
# 읽을 수 있는 이름을 남긴다.
SIGUNGU_NAME_BY_CODE: dict[str, str] = {
    "110": "중구",
    "140": "서구",
    "170": "동구",
    "200": "영도구",
    "230": "부산진구",
    "260": "동래구",
    "290": "남구",
    "320": "북구",
    "350": "해운대구",
    "380": "사하구",
    "410": "금정구",
    "440": "강서구",
    "470": "연제구",
    "500": "수영구",
    "530": "사상구",
    "710": "기장군",
}

# lDongSignguCd -> 기존 6개 area(구 단위 추정 - suggest_area가 돌려주는
# area_mapping="sigungu"로도 표시한다). "centum"은 해운대구(350) 안에
# 있지만 "haeundae"와 같은 구라서 시군구 코드만으로는 구분하지 않는다
# (요구사항 6: "센텀 vs 해운대처럼 나뉘는 경우는 판단하지 말고 구 단위
# 후보만 표시"). centum은 lDongSignguCd가 없을 때의 주소 키워드 폴백
# (BUSAN_AREA_SUGGESTION_KEYWORDS)에서만 쓰인다. 나머지 구(230 부산진구·
# 710 기장군·320 북구·440 강서구·530 사상구·470 연제구 등)는 이 표에
# 없으므로 suggested_area=None, area_note=AREA_NEEDS_REVIEW_NOTE로 남는다.
SIGUNGU_CODE_TO_AREA: dict[str, str] = {
    "110": "nampo",  # 중구 - 남포동
    "140": "songdo",  # 서구 - 송도해수욕장
    "170": "nampo",  # 동구
    "200": "nampo",  # 영도구
    "290": "gwangalli",  # 남구
    "350": "haeundae",  # 해운대구(센텀시티 포함, 구분하지 않음)
    "380": "songdo",  # 사하구
    "260": "dongnae",  # 동래구
    "410": "dongnae",  # 금정구
    "500": "gwangalli",  # 수영구 - 광안리해수욕장
}

# 품질 플래그 판정용 제목 패턴 - 삭제하지 않고 flags 배열로만 표시한다
# (요구사항 5). "등"으로 열려 있던 목록이라 같은 범주의 가까운 동의어를
# 몇 개 더 넣었지만, 의도적으로 좁게 유지했다 - 과도하게 넓히면 진짜
# 관광 후보까지 오검출할 수 있어서다.
NON_TOURIST_SUSPECT_PATTERNS = ["주식회사", "(주)", "약국", "안경", "부동산", "의원", "병원", "치과", "한의원", "공인중개사"]
LODGING_LIKE_PATTERNS = ["캠핑", "글램핑", "카라반", "펜션", "오토캠핑", "민박"]
FOOD_STREET_LIKE_PATTERNS = ["먹자골목", "맛집", "식당가", "포장마차"]
SPORTS_FACILITY_LIKE_PATTERNS = ["골프", "컨트리클럽", "수련원", "수련관", "야영장"]

QUALITY_FLAG_PATTERNS: dict[str, list[str]] = {
    "non_tourist_suspect": NON_TOURIST_SUSPECT_PATTERNS,
    "lodging_like": LODGING_LIKE_PATTERNS,
    "food_street_like": FOOD_STREET_LIKE_PATTERNS,
    "sports_facility_like": SPORTS_FACILITY_LIKE_PATTERNS,
}

# (contentTypeId, lclsSystm2) -> 플래그. 제목 패턴과 달리 TourAPI의 새
# 분류 코드로 판정한다(요구사항 2) - 쇼핑 27곳 중 17곳이 SH04(백화점 내
# 브랜드 매장)였던 걸 확인하고 추가했다. SH05(지하도상가)·SH06(거리·시장)은
# 유용하다고 판단해 플래그를 붙이지 않는다.
LCLS_SYSTM2_FLAG_RULES: list[tuple[str, str, str]] = [
    ("38", "SH04", "brand_store"),  # 쇼핑 - 백화점 내 브랜드 매장
    ("28", "AC05", "campground"),  # 레포츠 - 캠핑장
    ("28", "VE10", "public_facility"),  # 레포츠 - 수련관·경기장
    ("14", "VE09", "public_facility"),  # 문화시설 - 도서관
]


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


def compute_lcls_systm2_flags(content_type_id: str | None, lcls_systm2: str | None) -> list[str]:
    """(요구사항 2) 제목이 아니라 TourAPI의 새 분류 코드(lclsSystm2)로
    판정하는 플래그. content_type_id나 lcls_systm2가 없으면 아무것도
    매치하지 않는다(KeyError 없이 그냥 빈 목록)."""
    if not content_type_id or not lcls_systm2:
        return []
    return [flag for ctid, code, flag in LCLS_SYSTM2_FLAG_RULES if ctid == content_type_id and lcls_systm2 == code]


def compute_quality_flags(title: str, content_type_id: str | None = None, lcls_systm2: str | None = None) -> list[str]:
    """(요구사항 2·5) 제목 패턴 플래그 + lclsSystm2 플래그를 합친다. 삭제
    하지 않고 그대로 두되, 2단계 상세 보강 대상에서는 제외하는 용도로
    쓴다. 한 항목이 여러 플래그에 동시에 걸릴 수 있다(중복 없이, 처음
    매치된 순서대로)."""
    flags = [flag for flag, patterns in QUALITY_FLAG_PATTERNS.items() if any(pattern in title for pattern in patterns)]
    for flag in compute_lcls_systm2_flags(content_type_id, lcls_systm2):
        if flag not in flags:
            flags.append(flag)
    return flags


def suggest_area_by_address(addr1: str) -> tuple[str | None, str | None]:
    """lDongSignguCd가 없을 때만 쓰는 폴백 - BUSAN_AREA_SUGGESTION_KEYWORDS 중
    addr1에 포함된 첫 키워드의 area를 제안한다. 아무 키워드도 맞지 않으면
    suggested_area=None, area_note=AREA_NEEDS_REVIEW_NOTE로 남긴다."""
    for area, keywords in BUSAN_AREA_SUGGESTION_KEYWORDS.items():
        if any(keyword in addr1 for keyword in keywords):
            return area, None
    return None, AREA_NEEDS_REVIEW_NOTE


def suggest_area(ldong_signgu_cd: str | None, addr1: str) -> tuple[str | None, str | None, str | None, str | None]:
    """(요구사항 3·6) (suggested_area, area_note, sigungu_name, area_mapping).
    lDongSignguCd를 1차 근거로 쓰고, 없을 때만 주소 키워드 폴백
    (suggest_area_by_address)을 쓴다. 시군구 코드가 있어도 기존 6개
    area표(SIGUNGU_CODE_TO_AREA)에 없으면(기장군·강서구 등)
    suggested_area=None, area_note로 남기고, sigungu_name에는 어느 경우든
    알고 있는 한글 구/군 이름을 보존한다. area_mapping은 suggested_area가
    실제로 어떤 방식으로 나왔는지 표시한다 - "sigungu"(구 단위 추정),
    "address_keyword"(주소 키워드 폴백), 또는 None(둘 다 실패)."""
    sigungu_name = SIGUNGU_NAME_BY_CODE.get(ldong_signgu_cd) if ldong_signgu_cd else None

    if ldong_signgu_cd:
        area = SIGUNGU_CODE_TO_AREA.get(ldong_signgu_cd)
        if area is not None:
            return area, None, sigungu_name, "sigungu"
        return None, AREA_NEEDS_REVIEW_NOTE, sigungu_name, None

    area, note = suggest_area_by_address(addr1)
    area_mapping = "address_keyword" if area is not None else None
    return area, note, sigungu_name, area_mapping


def is_within_busan_bounds(lat: float, lng: float) -> bool:
    return (
        BUSAN_BOUNDS["lat_min"] <= lat <= BUSAN_BOUNDS["lat_max"]
        and BUSAN_BOUNDS["lng_min"] <= lng <= BUSAN_BOUNDS["lng_max"]
    )


def normalize_raw_item(raw: dict, content_type_id: str) -> dict:
    """요구사항 3이 보존하라고 한 값만 꺼내고, 원본 응답 전체는 "raw"에
    그대로 둔다. lDongSignguCd·lclsSystm1~3은 가공 없이 그대로 복사한다
    (요구사항 5·6 - 이후 분류/지역 판정에 쓴다). 좌표/범위 필터는 여기서
    적용하지 않는다(필터 여부는 filter_by_coordinates가 결정) - 이 함수는
    아무것도 제외하지 않는다."""
    mapx = raw.get("mapx")
    mapy = raw.get("mapy")
    try:
        longitude = float(mapx) if mapx not in (None, "") else None
        latitude = float(mapy) if mapy not in (None, "") else None
    except (TypeError, ValueError):
        longitude = latitude = None

    title = str(raw.get("title", "")).strip()
    effective_content_type_id = str(raw.get("contenttypeid", "")).strip() or content_type_id
    lcls_systm2 = raw.get("lclsSystm2") or None

    return {
        "contentid": str(raw.get("contentid", "")).strip() or None,
        "contenttypeid": effective_content_type_id,
        "title": title,
        "addr1": str(raw.get("addr1", "")).strip(),
        "addr2": str(raw.get("addr2", "")).strip(),
        "latitude": latitude,
        "longitude": longitude,
        "cat1": raw.get("cat1") or None,
        "cat2": raw.get("cat2") or None,
        "cat3": raw.get("cat3") or None,
        "has_firstimage": bool(str(raw.get("firstimage", "")).strip()),
        "ldong_signgu_cd": str(raw.get("lDongSignguCd", "")).strip() or None,
        "lcls_systm1": raw.get("lclsSystm1") or None,
        "lcls_systm2": lcls_systm2,
        "lcls_systm3": raw.get("lclsSystm3") or None,
        "flags": compute_quality_flags(title, effective_content_type_id, lcls_systm2),
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


def probe_total_count(
    client: TourApiClient,
    ldong_regn_cd: str,
    content_type_id: str,
    call_counter: list[int],
) -> int | None:
    """(요구사항 1) totalCount만 싸게 알아보는 호출(numOfRows=1). 재시도까지
    전부 실패하면 None(그래도 수집 자체는 FALLBACK_TARGET_IF_PROBE_FAILS로
    계속 진행한다 - resolve_target_count 참고)."""
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        call_counter[0] += 1
        _, total_count, status = client.fetch_area_based_list2(content_type_id, None, 1, 1, ldong_regn_cd=ldong_regn_cd)
        if status == "quota_exceeded":
            raise QuotaExceeded(call_counter[0])
        if status == "ok":
            time.sleep(REQUEST_INTERVAL_SECONDS)
            return total_count
        print(
            f"    [{content_type_id}] totalCount 확인 호출 실패(api_error) - 재시도 {attempt + 1}/{MAX_RETRIES_ON_API_ERROR}",
            flush=True,
        )
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    time.sleep(REQUEST_INTERVAL_SECONDS)
    return None


def resolve_target_count(content_type_id: str, total_count: int | None, max_cap: int | None) -> int:
    """쇼핑(38)은 SHOPPING_FIXED_TARGET(조회순 상위 N건)이 목표고, 나머지는
    totalCount 전체가 목표다. totalCount를 못 알아냈으면
    FALLBACK_TARGET_IF_PROBE_FAILS로 대신한다. max_cap이 주어지면(기존
    --max-per-type 옵션의 의미를 이어받은 "타입별 상한") 그 값과 자연
    목표값 중 작은 쪽을 쓴다."""
    if content_type_id == "38":
        natural = SHOPPING_FIXED_TARGET if total_count is None else min(SHOPPING_FIXED_TARGET, total_count)
    else:
        natural = total_count if total_count is not None else FALLBACK_TARGET_IF_PROBE_FAILS.get(content_type_id, 0)
    if max_cap is not None:
        return min(natural, max_cap)
    return natural


def fetch_type_candidates_single_call(
    client: TourApiClient,
    ldong_regn_cd: str,
    content_type_id: str,
    num_rows: int,
    call_counter: list[int],
) -> list[dict]:
    """(요구사항 1) "한 번의 호출로 크게 받는다" - numOfRows=num_rows,
    pageNo=1 딱 한 번. 실패 시 기존과 같은 백오프 재시도."""
    items: list[dict] = []
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        call_counter[0] += 1
        items, _, status = client.fetch_area_based_list2(content_type_id, None, 1, num_rows, ldong_regn_cd=ldong_regn_cd)
        if status == "quota_exceeded":
            raise QuotaExceeded(call_counter[0])
        if status == "ok":
            break
        print(
            f"    [{content_type_id}] 한 번에 받기(numOfRows={num_rows}) 호출 실패(api_error) - "
            f"재시도 {attempt + 1}/{MAX_RETRIES_ON_API_ERROR}",
            flush=True,
        )
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    else:
        items = []
    time.sleep(REQUEST_INTERVAL_SECONDS)
    return items


def fetch_type_candidates_paginated_fallback(
    client: TourApiClient,
    ldong_regn_cd: str,
    content_type_id: str,
    target: int,
    call_counter: list[int],
) -> list[dict]:
    """한 번에 받기가 목표보다 적게 와서(서버 상한 가능성) 쓰는 폴백 -
    작은 페이지 크기(PAGE_SIZE)로 다시 처음부터 페이지네이션한다. arrange=
    "P" 정렬이 페이지마다 불안정해 겹치는 항목이 섞일 수 있지만, 호출부
    (fetch_type_candidates)가 끝에 항상 contentid 중복 제거를 적용한다."""
    collected: list[dict] = []
    page = 1
    while len(collected) < target:
        page_size = min(PAGE_SIZE, target - len(collected))
        items: list[dict] = []
        for attempt in range(MAX_RETRIES_ON_API_ERROR):
            call_counter[0] += 1
            items, _, status = client.fetch_area_based_list2(
                content_type_id, None, page, page_size, ldong_regn_cd=ldong_regn_cd
            )
            if status == "quota_exceeded":
                raise QuotaExceeded(call_counter[0])
            if status == "ok":
                break
            print(
                f"    [{content_type_id}] 폴백 page {page} 호출 실패(api_error) - 재시도 {attempt + 1}/{MAX_RETRIES_ON_API_ERROR}",
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
            f"    [{content_type_id}] 폴백 page {page}: {len(items)}건 (누적 {len(collected)}, 총 API 호출 {call_counter[0]}회)",
            flush=True,
        )
        page += 1
    return collected


def dedupe_by_contentid(items: list[dict]) -> tuple[list[dict], int]:
    """(요구사항 1) contentid 기준 중복 제거(첫 항목 유지). contentid가
    없는 항목은 서로 절대 중복 처리하지 않는다(비교할 식별자가 없으므로).
    Returns (deduped_items, removed_count)."""
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        content_id = str(item.get("contentid") or "")
        if content_id:
            if content_id in seen:
                continue
            seen.add(content_id)
        deduped.append(item)
    return deduped, len(items) - len(deduped)


def fetch_type_candidates(
    client: TourApiClient,
    ldong_regn_cd: str,
    content_type_id: str,
    call_counter: list[int],
    *,
    max_cap: int | None = None,
) -> tuple[list[dict], int | None, int]:
    """contentTypeId 하나에 대해: ① totalCount를 알아내고 ② 그걸 목표로
    한 번의 큰 호출로 받은 뒤 ③ 부족하면 페이지네이션으로 폴백하고 ④
    contentid 기준 중복을 제거한다(요구사항 1). areaCode는 쓰지 않는다
    (모듈 docstring 참고). call_counter[0]는 실제 API 호출마다 늘어나며
    collect_place_candidates 전체에서 공유된다. quota_exceeded는 즉시
    QuotaExceeded로 올린다.

    Returns (deduped_items, total_count, duplicates_removed)."""
    total_count = probe_total_count(client, ldong_regn_cd, content_type_id, call_counter)
    target = resolve_target_count(content_type_id, total_count, max_cap)

    items = fetch_type_candidates_single_call(client, ldong_regn_cd, content_type_id, target, call_counter) if target > 0 else []
    if target > 0 and len(items) < target:
        print(
            f"!! [{content_type_id}] 한 번에 받은 건수({len(items)})가 목표({target})보다 적습니다 - "
            "서버 상한일 수 있어 페이지네이션으로 폴백합니다.",
            flush=True,
        )
        items = fetch_type_candidates_paginated_fallback(client, ldong_regn_cd, content_type_id, target, call_counter)

    deduped, duplicates_removed = dedupe_by_contentid(items)
    return deduped, total_count, duplicates_removed


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


def load_detail_cache(path: Path = DETAIL_CACHE_PATH) -> dict[str, dict]:
    """(요구사항 4) contentid -> {detail_intro, detail_common, open_hours,
    closed_days} 캐시를 읽는다. 파일이 없거나 깨져 있으면 빈 캐시로
    시작한다(캐시는 재개 가능성을 위한 최적화일 뿐, 없어도 정상 동작)."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_detail_cache(cache: dict[str, dict], path: Path = DETAIL_CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def enrich_candidate(client: TourApiClient, item: dict, call_counter: list[int], cache: dict[str, dict]) -> dict:
    """(요구사항 4) detailIntro2/detailCommon2를 호출해 원문 그대로
    detail_intro/detail_common에 담는다(파싱·가공 금지). open_hours/
    closed_days는 이미 검증된 매핑만 재사용한 편의 추출(아래 함수 참고).
    content_id가 cache에 이미 있으면 호출 자체를 생략하고 캐시 값을
    그대로 쓴다(재개 가능성). content_id/content_type_id가 없으면 호출
    하지 않고 전부 None."""
    content_id = item.get("contentid")
    content_type_id = item.get("contenttypeid")

    if content_id and content_id in cache:
        return {**item, **cache[content_id]}

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
    detail_fields = {
        "detail_intro": detail_intro,
        "detail_common": detail_common,
        "open_hours": open_hours,
        "closed_days": closed_days,
    }
    if content_id:
        cache[content_id] = detail_fields
    return {**item, **detail_fields}


def load_existing_places(city: str) -> list[dict]:
    path = DESTINATIONS_DIR / f"{city}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["places"]


def build_summary(
    *,
    per_type_collected: dict[str, int],
    per_type_total_count: dict[str, int | None],
    per_type_duplicates_removed: dict[str, int],
    excluded: list[dict],
    already_in_catalog: list[dict],
    new_candidates: list[dict],
    stage1_api_call_count: int,
    stage2_api_call_count: int,
    partial: bool,
) -> dict:
    exclude_reason_counts = Counter(item["exclude_reason"] for item in excluded)
    suggested_area_counts = Counter((item.get("suggested_area") or "(미정)") for item in new_candidates)
    sigungu_counts = Counter((item.get("sigungu_name") or "(미상)") for item in new_candidates)
    lcls_systm2_counts = Counter((item.get("lcls_systm2") or "(미상)") for item in new_candidates)
    flag_counts: Counter = Counter()
    for item in new_candidates:
        for flag in item.get("flags") or []:
            flag_counts[flag] += 1

    return {
        "collected_by_type": per_type_collected,
        "total_count_by_type": per_type_total_count,
        "duplicates_removed_by_type": per_type_duplicates_removed,
        "duplicates_removed_total": sum(per_type_duplicates_removed.values()),
        "excluded_total": len(excluded),
        "excluded_by_reason": dict(exclude_reason_counts),
        "already_in_catalog_total": len(already_in_catalog),
        "new_candidates_total": len(new_candidates),
        "new_candidates_by_suggested_area": dict(suggested_area_counts),
        "new_candidates_by_sigungu": dict(sigungu_counts),
        "new_candidates_by_lcls_systm2": dict(lcls_systm2_counts),
        "new_candidates_by_flag": dict(flag_counts),
        "stage1_api_call_count": stage1_api_call_count,
        "stage2_api_call_count": stage2_api_call_count,
        "api_call_count_total": stage1_api_call_count + stage2_api_call_count,
        "partial_due_to_quota": partial,
    }


def collect_place_candidates(
    client: TourApiClient,
    city: str,
    *,
    skip_detail: bool = False,
    max_per_type_by_content_type: dict[str, int] | None = None,
) -> dict:
    """전체 오케스트레이션:
      1단계 - 수집(lDongRegnCd) -> 좌표 필터 -> 중복 판정 -> 품질 플래그
        (이미 normalize_raw_item에서 부여됨) -> area 제안.
      2단계 - 품질 플래그가 없는 신규 후보만 상세 보강(캐시 재사용).
        skip_detail=True면 2단계를 아예 건너뛴다(요구사항 3의
        --list-only/--skip-detail).
    어느 단계에서든 QuotaExceeded가 나면 그 단계까지 모은 결과로
    partial_due_to_quota=True를 세팅해 돌려준다 - 예외를 바깥으로 올리지
    않는다(요구사항 8)."""
    max_per_type = max_per_type_by_content_type or {}
    ldong_regn_cd = TOUR_API_LDONG_REGN_CD_BY_CITY[city]
    existing_places = load_existing_places(city)

    call_counter = [0]
    per_type_collected: dict[str, int] = {}
    per_type_total_count: dict[str, int | None] = {}
    per_type_duplicates_removed: dict[str, int] = {}
    all_kept: list[dict] = []
    all_excluded: list[dict] = []
    partial = False

    for content_type_id, label in COLLECT_CONTENT_TYPE_LABELS.items():
        max_cap = max_per_type.get(content_type_id)
        print(f"=== {label}(contentTypeId={content_type_id}) 수집 시작 ===", flush=True)
        try:
            raw_items, total_count, duplicates_removed = fetch_type_candidates(
                client, ldong_regn_cd, content_type_id, call_counter, max_cap=max_cap
            )
        except QuotaExceeded:
            partial = True
            print("!! 요청 한도 초과 - 수집을 중단합니다.", flush=True)
            break
        per_type_total_count[label] = total_count
        per_type_duplicates_removed[label] = duplicates_removed
        normalized = [normalize_raw_item(raw, content_type_id) for raw in raw_items]
        kept, excluded = filter_by_coordinates(normalized)
        per_type_collected[label] = len(kept)
        all_kept.extend(kept)
        all_excluded.extend(excluded)
        print(
            f"{label}: totalCount={total_count}, 중복 제거 {duplicates_removed}건, "
            f"{len(kept)}건 통과, {len(excluded)}건 좌표 제외",
            flush=True,
        )

    stage1_api_call_count = call_counter[0]

    new_candidates, already_in_catalog = partition_duplicates(all_kept, existing_places)
    for item in new_candidates:
        item["suggested_area"], item["area_note"], item["sigungu_name"], item["area_mapping"] = suggest_area(
            item["ldong_signgu_cd"], item["addr1"]
        )

    print(
        f"\n1단계 완료: 기존 카탈로그 중복 {len(already_in_catalog)}건, 신규 후보 {len(new_candidates)}건 "
        f"(1단계 API 호출 {stage1_api_call_count}회)",
        flush=True,
    )

    stage2_api_call_count = 0
    if skip_detail:
        print("--list-only/--skip-detail 지정됨 - 상세 보강(2단계)을 건너뜁니다.", flush=True)
    elif not partial:
        # DETAIL_CACHE_PATH를 매번 모듈 전역에서 다시 읽는다(기본 인자로
        # 한 번만 바인딩하지 않음) - 테스트가 이 경로를 monkeypatch로
        # 바꿔치기할 수 있게 하기 위함이며, 실제 운영 동작은 그대로다.
        cache = load_detail_cache(DETAIL_CACHE_PATH)
        cache_hits = 0
        enrichable_count = sum(1 for item in new_candidates if not item["flags"])
        enriched_so_far = 0
        for index, item in enumerate(new_candidates):
            if item["flags"]:
                continue  # 의심 플래그가 있는 후보는 상세 호출을 하지 않는다(요구사항 3).
            enriched_so_far += 1
            if item.get("contentid") in cache:
                cache_hits += 1
            print(
                f"상세 보강 {enriched_so_far}/{enrichable_count}: {item['title']} "
                f"(총 API 호출 {call_counter[0]}회, 캐시 적중 {cache_hits}건)",
                flush=True,
            )
            try:
                new_candidates[index] = enrich_candidate(client, item, call_counter, cache)
                save_detail_cache(cache, DETAIL_CACHE_PATH)
            except QuotaExceeded:
                partial = True
                print(
                    "!! 상세 보강 중 요청 한도 초과 - 지금까지 모은 결과와 상세 캐시를 저장했습니다. "
                    "다시 실행하면 이어서 진행됩니다.",
                    flush=True,
                )
                break
        stage2_api_call_count = call_counter[0] - stage1_api_call_count

    # 어느 경로를 거쳤든(건너뜀/정상 완료/quota 중단) 모든 후보가 같은
    # 스키마를 갖도록 빠진 상세 필드를 None으로 채운다.
    for item in new_candidates:
        item.setdefault("detail_intro", None)
        item.setdefault("detail_common", None)
        item.setdefault("open_hours", None)
        item.setdefault("closed_days", None)

    summary = build_summary(
        per_type_collected=per_type_collected,
        per_type_total_count=per_type_total_count,
        per_type_duplicates_removed=per_type_duplicates_removed,
        excluded=all_excluded,
        already_in_catalog=already_in_catalog,
        new_candidates=new_candidates,
        stage1_api_call_count=stage1_api_call_count,
        stage2_api_call_count=stage2_api_call_count,
        partial=partial,
    )

    return {
        "city": city,
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
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="1단계(목록 수집·좌표 필터·중복 판정·품질 플래그·area 제안)만 하고 상세 보강(2단계)은 건너뜀",
    )
    parser.add_argument(
        "--skip-detail",
        action="store_true",
        help="--list-only와 동일 - 상세 보강(2단계)을 건너뜀",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help="결과 JSON 저장 경로 (기본: local_only/reports/place_candidates_busan_raw.json)",
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
    skip_detail = args.list_only or args.skip_detail

    result = collect_place_candidates(client, args.city, skip_detail=skip_detail)

    out_path = args.out if args.out.is_absolute() else PROJECT_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = result["summary"]
    print(f"\n=== {args.city} 활동 후보 수집 결과 ===")
    print(f"타입별 totalCount: {summary['total_count_by_type']}")
    print(f"타입별 수집(좌표 필터 통과): {summary['collected_by_type']}")
    print(
        f"contentid 중복 제거: 총 {summary['duplicates_removed_total']}건 "
        f"{summary['duplicates_removed_by_type']}"
    )
    print(f"좌표 제외: {summary['excluded_total']}건 {summary['excluded_by_reason']}")
    print(f"기존 카탈로그 중복: {summary['already_in_catalog_total']}건")
    print(f"신규 후보: {summary['new_candidates_total']}건")
    print(f"신규 후보 suggested_area 분포: {summary['new_candidates_by_suggested_area']}")
    print(f"신규 후보 시군구 분포: {summary['new_candidates_by_sigungu']}")
    print(f"신규 후보 lclsSystm2 분포: {summary['new_candidates_by_lcls_systm2']}")
    print(f"신규 후보 품질 플래그 분포: {summary['new_candidates_by_flag']}")
    print(
        f"1단계 API 호출 {summary['stage1_api_call_count']}회, "
        f"2단계 API 호출 {summary['stage2_api_call_count']}회, "
        f"합계 {summary['api_call_count_total']}회"
    )
    if summary["partial_due_to_quota"]:
        print("\n!! TourAPI 요청 한도를 초과해 중단했습니다. 다시 실행하면 이어서 진행됩니다.")
    print(f"\n저장 위치: {out_path}")


if __name__ == "__main__":
    main()
