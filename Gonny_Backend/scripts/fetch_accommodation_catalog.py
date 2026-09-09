from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

# On Windows, stdout defaults to the console codepage (cp949) rather than
# UTF-8 when redirected to a file, corrupting Korean output.
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings
from app.domains.accommodation_catalog.schemas import AccommodationData, CityAccommodationCatalog
from app.services.external_clients import (
    ACCOMMODATION_TYPE_LABELS_BY_LCLS2,
    TOUR_API_AREA_CODE_BY_CITY,
    TourApiClient,
    extract_lodging_amenities,
)

ACCOMMODATIONS_DIR = PROJECT_ROOT / "app" / "data" / "accommodations"
ENV_FILE = REPO_ROOT / ".env"
REQUEST_INTERVAL_SECONDS = 0.2
MAX_RETRIES_ON_API_ERROR = 5
RETRY_BACKOFF_SECONDS = 2.0
CANDIDATES_PER_CITY = 50
MIN_SELECTED_PER_CITY = 10
MAX_SELECTED_PER_CITY = 15

# Keyword match against addr1, in priority order (first match wins) per
# city. Built from the same area vocabulary/labels already used in
# app/data/destinations/*.json and rule_planner's AREA_LABEL_KO, plus a
# few well-known neighborhood/dong names for each area not otherwise
# distinguishable from addr1 alone. Deliberately conservative: no generic
# "구"-level fallback (e.g. bare "중구" would ambiguously match both
# myeongdong and euljiro in Seoul), so some real candidates in these
# cities won't match any area and are excluded rather than guessed at.
AREA_MATCH_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "seoul": {
        "jongno": ["종로"],
        "euljiro": ["을지로"],
        "myeongdong": ["명동"],
        "dongdaemun": ["동대문"],
        "seongsu": ["성수"],
        "hongdae": ["홍대", "서교동", "합정"],
        "yeouido": ["여의도"],
        "gangnam": ["강남", "역삼", "테헤란로"],
        "jamsil": ["잠실"],
        "itaewon": ["이태원"],
        "namsan": ["남산"],
        "gwangjin": ["광진", "건대"],
        "gwanak": ["관악", "신림"],
    },
    "busan": {
        "nampo": ["남포"],
        "songdo": ["송도"],
        "gwangalli": ["광안리", "광안"],
        "haeundae": ["해운대"],
        "dongnae": ["동래"],
        "centum": ["센텀"],
    },
    "jeju": {
        "east-jeju": ["구좌", "조천", "함덕", "김녕"],
        "west-jeju": ["한림", "애월", "한경", "협재"],
        "seongsan": ["성산"],
        "seogwipo-west": ["안덕", "대정", "중문"],
    },
}


def load_tour_api_key_from_env_file() -> str | None:
    if not ENV_FILE.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def match_area(city: str, addr1: str) -> str | None:
    for area, keywords in AREA_MATCH_KEYWORDS.get(city, {}).items():
        if any(keyword in addr1 for keyword in keywords):
            return area
    return None


def parse_room_count(roomcount_text: str) -> int | None:
    match = re.search(r"\d+", roomcount_text or "")
    return int(match.group()) if match else None


def estimate_budget_level(accommodation_type: str, roomcount_text: str) -> list[str]:
    """Best-effort tier from accommodation_type + scale (roomcount is a
    real TourAPI field used as a proxy - larger scale tends to track with
    mid/upper pricing in practice). TourAPI rarely exposes actual price,
    so this is always an estimate - see AccommodationData.budget_level_estimated."""
    if accommodation_type in {"캠핑", "모텔"}:
        return ["low"]
    if accommodation_type == "호스텔":
        return ["low", "medium"]
    if accommodation_type == "펜션·민박":
        return ["medium"]
    if accommodation_type == "콘도미니엄":
        return ["medium", "high"]
    if accommodation_type == "호텔":
        room_count = parse_room_count(roomcount_text)
        if room_count is not None and room_count >= 200:
            return ["medium", "high"]
        return ["medium"]
    return ["medium"]


def estimate_suitable_for(accommodation_type: str) -> list[str]:
    if accommodation_type == "호스텔":
        return ["solo", "friend"]
    if accommodation_type == "캠핑":
        return ["friend", "family"]
    if accommodation_type in {"펜션·민박", "콘도미니엄"}:
        return ["couple", "family", "friend"]
    if accommodation_type == "모텔":
        return ["solo", "couple"]
    return ["solo", "couple", "friend", "family"]


def fetch_candidates_with_retry(client: TourApiClient, city: str) -> list[dict] | None:
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        items = client.fetch_lodging_candidates(city, num_rows=CANDIDATES_PER_CITY)
        if items is not None:
            return items
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return None


def fetch_details_with_retry(client: TourApiClient, content_id: str) -> dict | None:
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        detail = client.fetch_lodging_details(content_id)
        if detail is not None:
            return detail
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return None


def select_diverse_candidates(candidates: list[dict]) -> list[dict]:
    """Round-robins across accommodation_type groups (stable title order
    within each group) so one type (typically 호텔, since it's the most
    common registered category) doesn't dominate the selection. Stops at
    MAX_SELECTED_PER_CITY; never pads with off-criteria candidates to
    reach MIN_SELECTED_PER_CITY - a short list is reported as-is."""
    groups: dict[str, list[dict]] = {}
    for item in candidates:
        groups.setdefault(item["_accommodation_type"], []).append(item)
    for group in groups.values():
        group.sort(key=lambda item: item.get("title", ""))

    selected: list[dict] = []
    type_order = sorted(groups.keys())
    index = 0
    while len(selected) < MAX_SELECTED_PER_CITY and any(groups.values()):
        type_key = type_order[index % len(type_order)]
        if groups[type_key]:
            selected.append(groups[type_key].pop(0))
        index += 1
        if index > 10_000:  # safety valve, should never trigger
            break
    return selected


def build_accommodation(city: str, item: dict, detail: dict | None) -> AccommodationData:
    accommodation_type = item["_accommodation_type"]
    roomcount_text = str((detail or {}).get("roomcount", ""))
    amenities = extract_lodging_amenities(detail) if detail else []
    return AccommodationData(
        id=str(item["contentid"]),
        name=str(item.get("title", "")).strip(),
        city=city,
        area=item["_area"],
        latitude=float(item["mapy"]) if item.get("mapy") else None,
        longitude=float(item["mapx"]) if item.get("mapx") else None,
        content_id=str(item["contentid"]),
        accommodation_type=accommodation_type,
        amenities=amenities,
        budget_level=estimate_budget_level(accommodation_type, roomcount_text),
        budget_level_estimated=True,
        suitable_for=estimate_suitable_for(accommodation_type),
        checkin_time=(str((detail or {}).get("checkintime", "")).strip() or None),
        checkout_time=(str((detail or {}).get("checkouttime", "")).strip() or None),
    )


def process_city(client: TourApiClient, city: str) -> tuple[CityAccommodationCatalog, dict]:
    raw_candidates = fetch_candidates_with_retry(client, city)
    if raw_candidates is None:
        return CityAccommodationCatalog(city=city, accommodations=[]), {
            "fetched": 0,
            "area_matched": 0,
            "type_classified": 0,
            "selected": 0,
        }

    area_matched: list[dict] = []
    for item in raw_candidates:
        area = match_area(city, str(item.get("addr1", "")))
        accommodation_type = ACCOMMODATION_TYPE_LABELS_BY_LCLS2.get(str(item.get("lclsSystm2", "")))
        if area is None or accommodation_type is None or not item.get("mapx") or not item.get("mapy"):
            continue
        item["_area"] = area
        item["_accommodation_type"] = accommodation_type
        area_matched.append(item)

    selected = select_diverse_candidates(area_matched)

    accommodations: list[AccommodationData] = []
    for item in selected:
        detail = fetch_details_with_retry(client, str(item["contentid"]))
        time.sleep(REQUEST_INTERVAL_SECONDS)
        accommodations.append(build_accommodation(city, item, detail))

    stats = {
        "fetched": len(raw_candidates),
        "area_matched": len(area_matched),
        "type_classified": len(area_matched),  # area_matched already requires a known type
        "selected": len(accommodations),
    }
    return CityAccommodationCatalog(city=city, accommodations=accommodations), stats


def save_city_catalog(city: str, catalog: CityAccommodationCatalog) -> None:
    ACCOMMODATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = ACCOMMODATIONS_DIR / f"{city}.json"
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(catalog.model_dump(), file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> None:
    api_key = load_tour_api_key_from_env_file()
    if not api_key:
        print("TOUR_API_KEY not found in .env - aborting without touching any files.")
        return

    settings = Settings(tour_api_key=api_key)
    client = TourApiClient(settings)

    for city in TOUR_API_AREA_CODE_BY_CITY:
        catalog, stats = process_city(client, city)
        save_city_catalog(city, catalog)

        print(f"=== {city} ===")
        print(f"  fetched (areaBasedList2, contentTypeId=32): {stats['fetched']}")
        print(f"  area+type matched (our area vocabulary): {stats['area_matched']}")
        print(f"  selected: {stats['selected']}")
        if stats["selected"] < MIN_SELECTED_PER_CITY:
            print(f"  NOTE: below the {MIN_SELECTED_PER_CITY} target - reported as-is, not padded.")

        type_counts: dict[str, int] = {}
        for accommodation in catalog.accommodations:
            type_counts[accommodation.accommodation_type] = type_counts.get(accommodation.accommodation_type, 0) + 1
        print(f"  accommodation_type distribution: {type_counts}")

        area_counts: dict[str, int] = {}
        for accommodation in catalog.accommodations:
            area_counts[accommodation.area] = area_counts.get(accommodation.area, 0) + 1
        print(f"  area distribution: {area_counts}")
        print()


if __name__ == "__main__":
    main()
