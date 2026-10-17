# TourAPI 숙박(contentTypeId=32)은 areaCode 필터를 쓰면 areacode 필드가 빈
# 레코드가 조용히 빠진다 - 기존 카탈로그 21곳(대형 체인 호텔 포함: 파라다이스
# 호텔 부산, 그랜드 하얏트 서울 등)이 이 사각지대에 있었다는 사실을
# local_only/reports/accommodation_areacode_gap_access_paths.* 조사로 확인했다.
# 대신 areaBasedList2에 areaCode 대신 lDongRegnCd(법정동 시/도 코드)를 쓰면
# 같은 지역의 areacode-공백 레코드까지 전부 조회된다(서울 11/부산 26/제주 50).
# 이 스크립트는 그 방식으로 받은 lDongRegnCd 풀에서, 사람이 검토해 승인한
# content_id 허용 목록(ALLOWED_NEW_LODGING_BY_CITY, NAMED_HOTEL_TARGET_TITLES_BY_CITY)
# 에 있는 레코드만 app/data/accommodations/*.json에 추가한다. 허용 목록 밖의
# 레코드는 이유를 불문하고 추가하지 않는다.
#
# 기존 숙소 45곳(도시별 15)은 절대 수정하지 않는다 - id/content_id가 이미
# 있으면 건너뛴다. 두 번 실행해도 결과가 같다(멱등).
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.stdout.reconfigure(encoding="utf-8")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import httpx

from app.core.settings import Settings
from app.domains.accommodation_catalog.schemas import AccommodationData
from app.services.external_clients import ACCOMMODATION_TYPE_LABELS_BY_LCLS2, TourApiClient
from app.domains.rule_planner.services.travel_estimate import haversine_distance_km
from app.domains.rule_planner.services.policies.city.jeju_zones import nearest_zone

from fetch_accommodation_catalog import build_accommodation, match_area  # noqa: E402

ACCOMMODATIONS_DIR = PROJECT_ROOT / "app" / "data" / "accommodations"
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
ENV_FILE = REPO_ROOT / ".env"
REQUEST_INTERVAL_SECONDS = 0.25
MAX_RETRIES_ON_API_ERROR = 5
RETRY_BACKOFF_SECONDS = 2.0
PAGE_SIZE = 100

LDONG_REGN_CD_BY_CITY: dict[str, str] = {"seoul": "11", "busan": "26", "jeju": "50"}

# 승인된 신규 숙소 99곳 (lodging_selection_v4의 선택 목록). 값은 area/zone
# 라벨(서울·부산은 destinations area, 제주는 jeju_zones 코드) - 검토 당시
# 이미 keyword/nearest/zone 근거로 결정됐으므로 이 스크립트에서 다시 계산하지
# 않고 그대로 쓴다. 각 줄의 주석: 이름 | 유형 | 객실수 | 라벨 근거.
ALLOWED_NEW_LODGING_BY_CITY: dict[str, dict[str, str]] = {
    "seoul": {
        "142728": "gwangjin",  # 그랜드 워커힐 서울 | 호텔 | 477실 | keyword
        "142729": "euljiro",  # 더그랜드롯데 서울 | 호텔 | 868실 | keyword
        "142730": "myeongdong",  # 웨스틴 조선 서울 | 호텔 | 462실 | nearest(0.41km)
        "142733": "itaewon",  # 그랜드 하얏트 서울 | 호텔 | 615실 | nearest(0.71km)
        "142734": "euljiro",  # 서울신라호텔 | 호텔 | 464실 | nearest(1.58km)
        "142764": "gangnam",  # 호텔리베라 청담 | 호텔 | 319실 | keyword
        "142765": "hongdae",  # 스위스 그랜드 호텔 | 호텔 | 396실 | nearest(4.0km)
        "143033": "gangnam",  # JW 메리어트 호텔 서울 | 호텔 | 379실 | nearest(2.83km)
        "143107": "gwangjin",  # 비스타 워커힐 서울 | 호텔 | 253실 | keyword
        "2505908": "gwanak",  # 롯데시티호텔 구로 | 호텔 | 283실 | nearest(3.69km)
        "2548198": "gangnam",  # L7 강남 바이 롯데호텔 | 호텔 | 333실 | keyword
        "2573944": "gwanak",  # Cozy Lodge | 호스텔 | 4실 | keyword
        "2602549": "dongdaemun",  # 96번지 트래블러스 롯지 | 호스텔 | 15실 | nearest(0.74km)
        "2603723": "dongdaemun",  # 플랜에이호스텔 | 호스텔 | 6실 | nearest(0.76km)
        "2607806": "hongdae",  # 나비호스텔 | 호스텔 | 16실 | nearest(0.54km)
        "2608038": "euljiro",  # USB하우스 | 호스텔 | 9실 | nearest(1.1km)
        "2610854": "gangnam",  # 야코리아호스텔 강남점 | 호스텔 | 10실 | keyword
        "2639707": "gwanak",  # 포포인츠 바이 쉐라톤 서울 구로 | 호텔 | 202실 | nearest(3.51km)
        "2650639": "gwangjin",  # 리버사이드게스트하우스 | 호스텔 | 4실 | keyword
        "2666430": "gangnam",  # K-그랜드 호스텔 강남 1(K-GRAND HOSTEL GANGNAM1) | 호스텔 | 8실 | keyword
        "2700928": "gangnam",  # 업플로 호스텔 | 호스텔 | 18실 | nearest(2.77km)
        "2706047": "jongno",  # 한옥 게스트하우스 동촌재 | 펜션·민박 | 4실 | keyword
        "2707438": "jongno",  # 하은재 | 펜션·민박 | 4실 | keyword
        "2907142": "hongdae",  # 롯데호텔 L7홍대 | 호텔 | 340실 | keyword
        "2991972": "dongdaemun",  # 소테츠 호텔즈 더 스프라지르 서울 동대문 | 호텔 | 215실 | nearest(0.98km)
        "3023167": "hongdae",  # 브라운스위트 신촌센트럴 | 모텔 | 50실 | nearest(1.33km)
        "3072219": "jongno",  # 북촌빈관 by 락고재 | 펜션·민박 | 4실 | keyword
        "3076176": "dongdaemun",  # 더리센츠동대문호텔 | 호텔 | 207실 | keyword
        "3076237": "jamsil",  # 로사나관광호텔 | 호텔 | 81실 | nearest(0.7km)
        "3079777": "jongno",  # 이비스 앰배서더 서울 인사동 | 호텔 | 363실 | keyword
        "3091243": "gwangjin",  # 에이치에비뉴 건대점 | 호텔 | 미상실 | keyword
        "3337233": "euljiro",  # 노보텔 앰배서더 서울 동대문 호텔 & 레지던스 | 호텔 | 523실 | keyword
        "3337577": "jamsil",  # 소피텔 앰배서더 서울 호텔&서비스드 레지던스 | 호텔 | 563실 | keyword
        "3339644": "jongno",  # 포시즌스 호텔 서울(광화문미래에셋호텔) | 호텔 | 317실 | keyword
        "3379735": "dongdaemun",  # 맹그로브 신설 | 호텔 | 311실 | keyword
        "3387114": "itaewon",  # 노보텔 앰배서더 서울 용산 | 호텔 | 621실 | nearest(2.45km)
        "3387804": "itaewon",  # 이비스 스타일 앰배서더 서울 용산 | 호텔 | 591실 | nearest(2.45km)
        "3395428": "myeongdong",  # 보코 서울 명동 | 호텔 | 576실 | nearest(0.57km)
        "3464755": "jamsil",  # 시그니엘 서울 | 호텔 | 235실 | nearest(0.37km)
        "3464880": "jongno",  # 오라카이 인사동 스위츠 | 콘도미니엄 | 213실 | keyword
        "3465873": "jongno",  # 오라카이 대학로 호텔 | 호텔 | 232실 | keyword
        "3465927": "hongdae",  # 글래드 마포 | 호텔 | 374실 | nearest(2.95km)
        "3484585": "dongdaemun",  # 스테이 패스포트 신당 료칸 | 모텔 | 7실 | nearest(0.91km)
        "3570799": "gwanak",  # 엠디호텔 독산 | 호텔 | 258실 | nearest(4.54km)
        "4041219": "dongdaemun",  # 지후헌 | 펜션·민박 | 미상실 | nearest(2.17km)
    },
    "busan": {
        "1162526": "gwangalli",  # 토요코인호텔 부산서면 | 호텔 | 308실 | nearest(4.95km)
        "1215432": "dongnae",  # 부산 센트럴호텔 | 호텔 | 81실 | nearest(2.84km)
        "138217": "haeundae",  # 부산도시공사 아르피나 | 호스텔 | 110실 | keyword
        "142853": "haeundae",  # 파라다이스 호텔 부산 | 호텔 | 532실 | keyword
        "142998": "gwangalli",  # 롯데호텔 부산 | 호텔 | 650실 | nearest(5.69km)
        "143048": "dongnae",  # 호텔 농심 | 호텔 | 240실 | keyword
        "2595523": "haeundae",  # 센텀프리미어호텔 | 호텔 | 461실 | keyword
        "2637949": "dongnae",  # 녹천호텔 | 호텔 | 80실 | keyword
        "2699332": "gwangalli",  # 더웨이브 | 호스텔 | 4실 | nearest(0.74km)
        "2699563": "gwangalli",  # 옐로우라이트하우스 | 호스텔 | 4실 | keyword
        "2708673": "nampo",  # 라발스호텔 | 호텔 | 381실 | nearest(0.57km)
        "2832276": "nampo",  # 라마다 앙코르 바이윈덤 부산역 호텔 | 호텔 | 439실 | nearest(2.0km)
        "3074655": "gwangalli",  # 어반스테이 서면 | 모텔 | 200실 | nearest(5.23km)
        "3075356": "haeundae",  # 마티에 오시리아 | 콘도미니엄 | 200실 | nearest(5.16km)
        "3386773": "songdo",  # 윈덤 그랜드 부산 | 호텔 | 271실 | nearest(0.81km)
        "3465024": "haeundae",  # 아난티 앳 부산 빌라쥬 | 호텔 | 392실 | nearest(6.49km)
        "3532722": "gwangalli",  # 트래블라이트 | 호스텔 | 10실 | nearest(5.5km)
        "3580404": "gwangalli",  # 아바니 센트럴 부산 | 호텔 | 289실 | nearest(4.98km)
        "583031": "nampo",  # 토요코인호텔 부산역2점 | 호텔 | 491실 | nearest(1.35km)
        "986534": "songdo",  # 부산 비치 관광호텔 | 호텔 | 34실 | nearest(1.35km)
    },
    "jeju": {
        "137814": "bukseo",  # 제주 금강산콘도 | 콘도미니엄 | 미상실 | zone
        "1403482": "jeju-city",  # 오션스위츠 제주호텔 | 호텔 | 350실 | zone
        "142957": "jeju-city",  # 메종 글래드 제주 | 호텔 | 513실 | zone
        "142965": "seogwipo-si",  # 서귀포KAL호텔 | 호텔 | 225실 | zone
        "143025": "jungmun-andeok",  # 롯데호텔 제주 | 호텔 | 500실 | zone
        "1821483": "dongbu",  # 제주올레하우스 | 펜션·민박 | 미상실 | zone
        "1846473": "seogwipo-si",  # 신신호텔 제주오션 | 호텔 | 229실 | zone
        "1887546": "bukseo",  # 프레리아 커플 독채펜션 | 펜션·민박 | 4실 | zone
        "232287": "dongbu",  # 소노벨 제주 | 콘도미니엄 | 396실 | zone
        "2498637": "jungmun-andeok",  # 용산 제주유스호스텔 | 호스텔 | 45실 | zone
        "2561880": "jungmun-andeok",  # 제주신화월드 호텔 앤 리조트 랜딩관 | 호텔 | 615실 | zone
        "2561909": "jungmun-andeok",  # 제주신화월드 호텔 앤 리조트 메리어트관 | 호텔 | 527실 | zone
        "2623014": "jungmun-andeok",  # 브릭216 | 호스텔 | 20실 | zone
        "2623579": "daejeong",  # 틸다하우스 | 펜션·민박 | 6실 | zone
        "2626708": "jungmun-andeok",  # 해성파크텔 | 호스텔 | 6실 | zone
        "2634320": "seogwipo-si",  # 아인스 호스텔 | 호스텔 | 45실 | zone
        "2667498": "jeju-city",  # 에덴호스텔 | 호스텔 | 11실 | zone
        "2847272": "daejeong",  # 제주 항공우주 호텔 | 호텔 | 110실 | zone
        "2876795": "jeju-city",  # 그랜드 하얏트 제주 | 호텔 | 1600실 | zone
        "2940391": "bukseo",  # 광이멀스테이 | 펜션·민박 | 3실 | zone
        "3031581": "namdong",  # 카세로지 | 호텔 | 23실 | zone
        "3076467": "daejeong",  # 담모라 호텔앤리조트 | 호텔 | 58실 | zone
        "3076491": "seongsan",  # 제주티라호텔 | 호텔 | 30실 | zone
        "3079939": "dongbu",  # 라마다제주함덕호텔 | 호텔 | 310실 | zone
        "3079952": "dongbu",  # 제주서우봉비치호텔 | 호텔 | 미상실 | zone
        "3079973": "bukseo",  # 일성리조트 제주비치 | 콘도미니엄 | 177실 | zone
        "3079994": "dongbu",  # MJ리조트 | 콘도미니엄 | 미상실 | zone
        "3089169": "dongbu",  # 호텔스위트캐슬 | 호텔 | 87실 | zone
        "3344565": "seogwipo-si",  # JW 메리어트 제주 리조트 & 스파 | 호텔 | 89실 | zone
        "3520495": "seongsan",  # 취다선 리조트 | 호텔 | 20실 | zone
        "733613": "namdong",  # 아망뜨펜션(제주) | 펜션·민박 | 17실 | zone
        "971331": "daejeong",  # 오션하우스 | 펜션·민박 | 6실 | zone
        "977101": "bukseo",  # 애월해안누리(구 하얀둥지) | 펜션·민박 | 5실 | zone
        "983958": "bukseo",  # 엘리시안 제주 | 콘도미니엄 | 58실 | zone
    },
}

# 대표 호텔 8곳 - content_id를 미리 알지 못해(이름만 검토·승인됨) 런타임에
# lDongRegnCd 풀에서 "정확히 이 제목과 일치하는 레코드가 하나뿐인지" 확인해
# 해석한다. 둘 이상이거나 하나도 없으면 추가하지 않고 건너뜀 목록에 남긴다.
NAMED_HOTEL_TARGET_TITLES_BY_CITY: dict[str, list[str]] = {
    "seoul": ["파크 하얏트 서울", "레스케이프 호텔(L'Escape Hotel)", "글래드 여의도", "콘래드 서울"],
    "busan": ["시그니엘 부산", "웨스틴 조선 부산", "파크 하얏트 부산"],
    "jeju": ["그랜드 조선 제주"],
}


def load_tour_api_key_from_env_file() -> str | None:
    if not ENV_FILE.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def fetch_full_lodging_pool(api_key: str, base_url: str, city: str) -> tuple[list[dict], bool]:
    """Full areaBasedList2(contentTypeId=32) pool for one city using
    lDongRegnCd instead of areaCode, so areacode-blank records aren't
    silently dropped. Paginates until collected == totalCount. Returns
    (items, collected_fully)."""
    collected: list[dict] = []
    page = 1
    total_count: int | None = None
    while True:
        params = {
            "serviceKey": api_key, "numOfRows": PAGE_SIZE, "pageNo": page, "MobileOS": "ETC",
            "MobileApp": "Gonny", "_type": "json", "contentTypeId": "32",
            "lDongRegnCd": LDONG_REGN_CD_BY_CITY[city],
        }
        items = None
        for attempt in range(MAX_RETRIES_ON_API_ERROR):
            try:
                with httpx.Client(timeout=12.0) as client:
                    resp = client.get(f"{base_url}/areaBasedList2", params=params)
                payload = resp.json()["response"]
                if payload["header"]["resultCode"] != "0000":
                    time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                body = payload["body"]
                total_count = body["totalCount"]
                raw = body["items"]["item"] if body["items"] else []
                items = raw if isinstance(raw, list) else [raw]
                break
            except Exception:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
        if items is None:
            return collected, False
        collected.extend(items)
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if not items or len(collected) >= total_count:
            return collected, len(collected) == total_count
        page += 1


def compute_area_centers(city: str) -> dict[str, tuple[float, float]]:
    payload = json.loads((DESTINATIONS_DIR / f"{city}.json").read_text(encoding="utf-8"))
    coords_by_area: dict[str, list[tuple[float, float]]] = {}
    for place in payload["places"]:
        if place.get("latitude") is not None and place.get("longitude") is not None:
            coords_by_area.setdefault(place["area"], []).append((place["latitude"], place["longitude"]))
    return {
        area: (sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords))
        for area, coords in coords_by_area.items()
    }


def resolve_area_label(city: str, addr1: str, lat: float, lng: float, area_centers: dict) -> tuple[str, str]:
    """Only used for the 8 named hotels (their area wasn't pre-decided).
    Returns (area_or_zone, basis)."""
    if city == "jeju":
        return nearest_zone(lat, lng), "zone"
    keyword = match_area(city, addr1)
    if keyword:
        return keyword, "keyword"
    nearest = min(area_centers.items(), key=lambda kv: haversine_distance_km(lat, lng, *kv[1]))
    dist = round(haversine_distance_km(lat, lng, *nearest[1]), 2)
    return nearest[0], f"nearest({dist}km)"


def load_city_catalog_raw(city: str) -> dict:
    return json.loads((ACCOMMODATIONS_DIR / f"{city}.json").read_text(encoding="utf-8"))


def save_city_catalog_raw(city: str, payload: dict) -> None:
    path = ACCOMMODATIONS_DIR / f"{city}.json"
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_item_for_pool_record(record: dict, area_label: str) -> dict:
    accommodation_type = ACCOMMODATION_TYPE_LABELS_BY_LCLS2.get(str(record.get("lclsSystm2", "")))
    item = dict(record)
    item["_area"] = area_label
    item["_accommodation_type"] = accommodation_type
    return item


def resolve_additions_for_city(
    city: str,
    pool: list[dict],
    existing_ids: set[str],
    existing_content_ids: set[str],
    area_centers: dict[str, tuple[float, float]],
) -> tuple[list[tuple[dict, str]], list[dict]]:
    """Pure (no network, no file I/O) resolution of which pool records to
    add for one city, given the already-fetched lDongRegnCd pool and the
    catalog's current ids/content_ids. Returns (to_add, skipped), where
    to_add is a list of (pool_record, area_label) pairs. Used directly by
    main() and by tests (with a synthetic pool, no TourAPI call needed)."""
    pool_by_content_id = {str(item.get("contentid")): item for item in pool}
    to_add: list[tuple[dict, str]] = []
    skipped: list[dict] = []

    # --- allow-listed content_ids (already-decided area label) ---
    for content_id, area_label in ALLOWED_NEW_LODGING_BY_CITY[city].items():
        if content_id in existing_content_ids or content_id in existing_ids:
            skipped.append({"content_id": content_id, "reason": "이미 카탈로그에 존재"})
            continue
        record = pool_by_content_id.get(content_id)
        if record is None:
            skipped.append({"content_id": content_id, "reason": "lDongRegnCd 풀에서 조회 실패(현재 풀에 없음)"})
            continue
        accommodation_type = ACCOMMODATION_TYPE_LABELS_BY_LCLS2.get(str(record.get("lclsSystm2", "")))
        if accommodation_type is None:
            skipped.append({"content_id": content_id, "reason": "유형 미분류", "title": record.get("title")})
            continue
        if not record.get("mapx") or not record.get("mapy"):
            skipped.append({"content_id": content_id, "reason": "좌표 없음", "title": record.get("title")})
            continue
        to_add.append((record, area_label))

    # --- the 8 named hotels: resolve content_id by exact title match ---
    for target_title in NAMED_HOTEL_TARGET_TITLES_BY_CITY.get(city, []):
        matches = [item for item in pool if str(item.get("title", "")).strip() == target_title.strip()]
        if len(matches) != 1:
            skipped.append({
                "content_id": None, "reason": f"풀에서 '{target_title}' 정확히 하나로 확인 안됨 (매칭 {len(matches)}건)",
                "title": target_title,
            })
            continue
        record = matches[0]
        content_id = str(record.get("contentid"))
        if content_id in existing_content_ids or content_id in existing_ids:
            skipped.append({"content_id": content_id, "reason": "이미 카탈로그에 존재", "title": target_title})
            continue
        if any(r.get("contentid") == record.get("contentid") for r, _ in to_add):
            skipped.append({"content_id": content_id, "reason": "허용 목록과 중복", "title": target_title})
            continue
        accommodation_type = ACCOMMODATION_TYPE_LABELS_BY_LCLS2.get(str(record.get("lclsSystm2", "")))
        if accommodation_type is None:
            skipped.append({"content_id": content_id, "reason": "유형 미분류", "title": target_title})
            continue
        if not record.get("mapx") or not record.get("mapy"):
            skipped.append({"content_id": content_id, "reason": "좌표 없음", "title": target_title})
            continue
        area_label, basis = resolve_area_label(city, str(record.get("addr1", "")), float(record["mapy"]), float(record["mapx"]), area_centers)
        to_add.append((record, area_label))

    return to_add, skipped


def main() -> None:
    api_key = load_tour_api_key_from_env_file()
    if not api_key:
        print("TOUR_API_KEY not found in .env - aborting without touching any files.")
        return

    settings = Settings(tour_api_key=api_key)
    client = TourApiClient(settings)
    base_url = settings.tour_api_base_url.rstrip("/")

    report: dict[str, dict] = {}

    for city in ("seoul", "busan", "jeju"):
        print(f"=== {city} ===")
        pool, collected_fully = fetch_full_lodging_pool(api_key, base_url, city)
        print(f"  lDongRegnCd 풀 수집: {len(pool)}건, 전체수집={collected_fully}")
        if not collected_fully:
            print(f"  !! {city}: 풀을 전부 받지 못함 - 이 도시는 건너뜀 (실패 보고)")
            report[city] = {"error": "pool_fetch_incomplete"}
            continue

        catalog_raw = load_city_catalog_raw(city)
        existing_ids = {a["id"] for a in catalog_raw["accommodations"]}
        existing_content_ids = {a["content_id"] for a in catalog_raw["accommodations"] if a.get("content_id")}
        area_centers = compute_area_centers(city)

        to_add, skipped = resolve_additions_for_city(city, pool, existing_ids, existing_content_ids, area_centers)
        named_titles = set(NAMED_HOTEL_TARGET_TITLES_BY_CITY.get(city, []))
        for record, area_label in to_add:
            if str(record.get("title", "")) in named_titles:
                print(f"  대표 호텔 해석: {record['title']} -> content_id={record['contentid']}, area={area_label}")

        # --- fetch details and build AccommodationData for each ---
        added_accommodations = []
        for record, area_label in to_add:
            content_id = str(record["contentid"])
            detail = client.fetch_lodging_details(content_id)
            time.sleep(REQUEST_INTERVAL_SECONDS)
            item = build_item_for_pool_record(record, area_label)
            accommodation = build_accommodation(city, item, detail)
            added_accommodations.append(accommodation)

        print(f"  추가: {len(added_accommodations)}건, 건너뜀: {len(skipped)}건")
        for s in skipped:
            print(f"    skip: {s}")

        if added_accommodations:
            catalog_raw["accommodations"].extend(a.model_dump() for a in added_accommodations)
            save_city_catalog_raw(city, catalog_raw)

        report[city] = {
            "added": len(added_accommodations),
            "skipped": skipped,
            "final_count": len(catalog_raw["accommodations"]),
        }

    out_dir = PROJECT_ROOT / "local_only" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "add_tour_api_lodging_run_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n완료. local_only/reports/add_tour_api_lodging_run_report.json 에 저장")


if __name__ == "__main__":
    main()
