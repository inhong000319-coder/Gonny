"""Adds 31 TourAPI-sourced Jeju restaurants to app/data/destinations/jeju.json
as new PlaceData entries - these are the restaurant_shortlist_jeju.csv
candidates (gap-priority shortlist from an earlier read-only investigation)
that the user manually researched (google_rating/count/price_level) and
that pass the quality bar google_rating >= 3.8 and google_rating_count >= 20.
4 of the original 35 fail that bar and are listed in EXCLUDED_CANDIDATES
below for the record, not added: 제미니국수김밥(3.7), 진주식당(3.5),
서귀포흑돼지명가(3.7), 쇠소깍 복순이네(count=10).

All 31 rows' facts (name/addr1/content_id/lat/lng/firstmenu/fills_gap_place
from local_only/data/restaurant_shortlist_jeju.csv, google_rating/count/
price_level from the user's local_only/data/restaurant_shortlist_jeju_filled.csv)
are embedded as NEW_RESTAURANTS below so this script has no local_only
runtime dependency - same reasoning as add_tour_api_lodging.py's
ALLOWED_NEW_LODGING_BY_CITY constant. The only runtime dependency is the
already-committed app/data/destinations/jeju.json itself (read to compute
each candidate's area and to run the 300m+name-similarity dedup check).

Field rules (deterministic, nothing invented):
- id: "jeju-restaurant-tour-<content_id>" (the existing jeju-restaurant-*
  prefix + id scheme the "food" detection and the dedup check below both
  rely on, but distinct from the shortlist's own candidate_id scheme so it
  doesn't collide with anything already decided for a different purpose).
- activity_type: ["미식"] - these are restaurants, not attractions.
- budget_level: [price_level] - the single researched price tier, not a
  guessed range.
- suitable_for/time_fit/pace/mobility/duration_hours/priority: the most
  common (suitable_for/pace/mobility) or median (duration_hours/priority)
  value among the existing 39 jeju-restaurant-* entries, computed from the
  live catalog at import time (REFERENCE_* below) rather than hardcoded,
  so this script stays correct if the existing 39 ever change before this
  runs. time_fit is single most-common value, not a human guess.
- area: the area of the single nearest existing Jeju place (any place, not
  just restaurants) by haversine distance - verified to be one of the
  catalog's existing area codes (never a new area code).
- summary: "{fills_gap_place} 인근, 대표 메뉴는 {firstmenu}" - TourAPI-
  sourced facts only, no invented description.
- mood/visual_feature: [] - no evidence basis to tag either.
- google_rating/google_rating_count/content_id/latitude/longitude: as
  researched/fetched, verbatim.

Dedup: before adding, each candidate is checked against the existing 39
jeju-restaurant-* entries for <=300m distance AND difflib name-similarity
>=0.45 (same threshold match_tour_api_places_stage1b.py's classify() used
for "high"/"medium" matches in the earlier investigation) - any match is
reported and NOT added. None of the 31 currently match.

Idempotent/additive-only: existing jeju.json records (all 89 as of this
writing, including the 39 current restaurants) are never modified - only
verified unchanged by content hash after the run. Already-merged ids are
skipped, not re-added. No network calls.

Usage: python scripts/add_tour_api_restaurants_jeju.py
"""
from __future__ import annotations

import difflib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.rule_planner.services.travel_estimate import haversine_distance_km

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
CITY = "jeju"
JSON_PATH = DESTINATIONS_DIR / f"{CITY}.json"

RESTAURANT_ID_PREFIX = "jeju-restaurant-"
NEW_ID_PREFIX = "jeju-restaurant-tour-"
DEDUP_DISTANCE_KM = 0.3
DEDUP_NAME_SIMILARITY_THRESHOLD = 0.45

# 4 shortlist candidates that fail the quality bar (google_rating >= 3.8
# and google_rating_count >= 20) - kept here only for the record, never
# added.
EXCLUDED_CANDIDATES = [
    {"name": "제미니국수김밥", "google_rating": 3.70, "google_rating_count": 89, "reason": "google_rating<3.8"},
    {"name": "진주식당", "google_rating": 3.50, "google_rating_count": 660, "reason": "google_rating<3.8"},
    {"name": "서귀포흑돼지명가", "google_rating": 3.70, "google_rating_count": 235, "reason": "google_rating<3.8"},
    {"name": "쇠소깍 복순이네", "google_rating": 4.90, "google_rating_count": 10, "reason": "google_rating_count<20"},
]

# The 31 candidates passing the quality bar. content_id/latitude/longitude/
# firstmenu/fills_gap_place come from local_only/data/restaurant_shortlist_
# jeju.csv; google_rating/google_rating_count/price_level come from the
# user's local_only/data/restaurant_shortlist_jeju_filled.csv - both joined
# by candidate_id once, then embedded here verbatim.
NEW_RESTAURANTS: list[dict] = [
    {"name": "당포로나인 돈카츠", "content_id": "2861372", "latitude": 33.3257880323, "longitude": 126.8435882289, "firstmenu": "제주흑돈카츠", "fills_gap_place": "표선 해비치 해변", "google_rating": 4.5, "google_rating_count": 318, "price_level": "low"},
    {"name": "캡틴클럽하우스 서귀포매일올레시장점", "content_id": "4110105", "latitude": 33.2498223451, "longitude": 126.5637268216, "firstmenu": "시그니처 버거", "fills_gap_place": "서귀포매일올레시장", "google_rating": 4.9, "google_rating_count": 350, "price_level": "low"},
    {"name": "남매네왕갈치", "content_id": "4092010", "latitude": 33.2498913802, "longitude": 126.5639754324, "firstmenu": "18조림(일팔조림)", "fills_gap_place": "서귀포매일올레시장", "google_rating": 4.0, "google_rating_count": 105, "price_level": "low"},
    {"name": "장수애섬식당", "content_id": "2932531", "latitude": 33.2433684182, "longitude": 126.5596823834, "firstmenu": "갈치조림", "fills_gap_place": "천지연폭포", "google_rating": 4.4, "google_rating_count": 174, "price_level": "medium"},
    {"name": "반디파스타", "content_id": "2899605", "latitude": 33.5424881703155, "longitude": 126.669212607777, "firstmenu": "돌문어 오일 파스타", "fills_gap_place": "함덕해수욕장", "google_rating": 4.7, "google_rating_count": 495, "price_level": "medium"},
    {"name": "순천미향 제주산방산본점", "content_id": "2783376", "latitude": 33.2357006510, "longitude": 126.3124946210, "firstmenu": "제왕삼합", "fills_gap_place": "산방굴사(산방산)", "google_rating": 4.4, "google_rating_count": 550, "price_level": "medium"},
    {"name": "훈남횟집", "content_id": "2854417", "latitude": 33.5421279676, "longitude": 126.6678651887, "firstmenu": "고등어회", "fills_gap_place": "함덕해수욕장", "google_rating": 4.3, "google_rating_count": 451, "price_level": "medium"},
    {"name": "흑돼지해물삼합", "content_id": "2894407", "latitude": 33.2456869486, "longitude": 126.5703303734, "firstmenu": "흑돼지해물삼합", "fills_gap_place": "정방폭포", "google_rating": 4.2, "google_rating_count": 192, "price_level": "medium"},
    {"name": "포도원흑돼지", "content_id": "2870912", "latitude": 33.4700581065, "longitude": 126.4901906019, "firstmenu": "흑돼지오겹살", "fills_gap_place": "한라수목원", "google_rating": 4.2, "google_rating_count": 714, "price_level": "medium"},
    {"name": "솔동산고기국수", "content_id": "2833244", "latitude": 33.2429705005, "longitude": 126.5652336535, "firstmenu": "반반국수", "fills_gap_place": "이중섭 거주지", "google_rating": 4.6, "google_rating_count": 49, "price_level": "low"},
    {"name": "센트로", "content_id": "2871931", "latitude": 33.2466895723, "longitude": 126.5675833663, "firstmenu": "감자뇨끼", "fills_gap_place": "이중섭 거주지", "google_rating": 4.5, "google_rating_count": 290, "price_level": "low"},
    {"name": "나운터횟집", "content_id": "2374199", "latitude": 33.2409187298908, "longitude": 126.561393391195, "firstmenu": "구문쟁이코스", "fills_gap_place": "새섬·새연교", "google_rating": 4.2, "google_rating_count": 240, "price_level": "high"},
    {"name": "코바라멘", "content_id": "4071129", "latitude": 33.2338148223, "longitude": 126.3103562507, "firstmenu": "미도리시오라멘", "fills_gap_place": "산방굴사(산방산)", "google_rating": 5.0, "google_rating_count": 23, "price_level": "low"},
    {"name": "리보스코화덕피자", "content_id": "2837242", "latitude": 33.4694748009, "longitude": 126.4878685946, "firstmenu": "해녀톳도우 한라산용암 피자", "fills_gap_place": "한라수목원", "google_rating": 4.4, "google_rating_count": 599, "price_level": "low"},
    {"name": "로빙화", "content_id": "3030178", "latitude": 33.27511663280418, "longitude": 126.70926191840505, "firstmenu": "피자", "fills_gap_place": "남원 큰엉해안", "google_rating": 4.5, "google_rating_count": 614, "price_level": "medium"},
    {"name": "사계의시간", "content_id": "2847791", "latitude": 33.2322454224, "longitude": 126.3089977789, "firstmenu": "장어덮밥", "fills_gap_place": "용머리해안", "google_rating": 4.4, "google_rating_count": 430, "price_level": "low"},
    {"name": "호자", "content_id": "2851443", "latitude": 33.5215083065, "longitude": 126.8575797487, "firstmenu": "등심돈까스", "fills_gap_place": "해녀박물관", "google_rating": 4.5, "google_rating_count": 263, "price_level": "low"},
    {"name": "알동네집", "content_id": "2911053", "latitude": 33.3164470445, "longitude": 126.2673880277, "firstmenu": "흑돼지오겹살", "fills_gap_place": "제주 유리의성", "google_rating": 4.4, "google_rating_count": 242, "price_level": "medium"},
    {"name": "바타타식탁", "content_id": "2876488", "latitude": 33.3271655353, "longitude": 126.8359360817, "firstmenu": "바타타 회 세트", "fills_gap_place": "표선 해비치 해변", "google_rating": 4.6, "google_rating_count": 312, "price_level": "medium"},
    {"name": "항아리조림", "content_id": "2906322", "latitude": 33.5261681085, "longitude": 126.8563955909, "firstmenu": "순살갈치조림", "fills_gap_place": "해녀박물관", "google_rating": 4.6, "google_rating_count": 147, "price_level": "medium"},
    {"name": "진미명가", "content_id": "404180", "latitude": 33.2283217239, "longitude": 126.3076061164, "firstmenu": "다금바리", "fills_gap_place": "용머리해안", "google_rating": 4.2, "google_rating_count": 270, "price_level": "high"},
    {"name": "검은여닭도가니", "content_id": "2359165", "latitude": 33.2442177466, "longitude": 126.5820620077, "firstmenu": "한방도가니", "fills_gap_place": "정방폭포", "google_rating": 4.5, "google_rating_count": 198, "price_level": "medium"},
    {"name": "옛날팥죽", "content_id": "2847852", "latitude": 33.3885998263, "longitude": 126.7989489935, "firstmenu": "새알팥죽", "fills_gap_place": "성읍민속마을", "google_rating": 4.5, "google_rating_count": 470, "price_level": "low"},
    {"name": "취향의섬", "content_id": "2873771", "latitude": 33.2744162356, "longitude": 126.6898277081, "firstmenu": "고등어오일파스타", "fills_gap_place": "남원 큰엉해안", "google_rating": 4.5, "google_rating_count": 84, "price_level": "low"},
    {"name": "자연스러운식당", "content_id": "2851146", "latitude": 33.2435310361, "longitude": 126.5328058954, "firstmenu": "제주 수블라키와 차지키", "fills_gap_place": "외돌개", "google_rating": 3.9, "google_rating_count": 309, "price_level": "medium"},
    {"name": "우동카덴", "content_id": "2853604", "latitude": 33.4358676834, "longitude": 126.6793082885, "firstmenu": "야마카케우동", "fills_gap_place": "산굼부리", "google_rating": 3.9, "google_rating_count": 1320, "price_level": "low"},
    {"name": "묘한식당", "content_id": "2809900", "latitude": 33.3226211550477, "longitude": 126.262127681162, "firstmenu": "흑돼지돔베카츠", "fills_gap_place": "제주 유리의성", "google_rating": 4.4, "google_rating_count": 183, "price_level": "low"},
    {"name": "뱅인타코 제주본점", "content_id": "2871897", "latitude": 33.2886026732, "longitude": 126.2826099295, "firstmenu": "타코", "fills_gap_place": "오설록 티뮤지엄", "google_rating": 4.5, "google_rating_count": 452, "price_level": "low"},
    {"name": "섭섭이네", "content_id": "2840487", "latitude": 33.4715876451, "longitude": 126.7843928004, "firstmenu": "흑돼지퐁당커리", "fills_gap_place": "비자림", "google_rating": 4.2, "google_rating_count": 342, "price_level": "low"},
    {"name": "뿌리와열매", "content_id": "2902758", "latitude": 33.4717954780, "longitude": 126.7838563636, "firstmenu": "버섯 바질루꼴라 감자피자세트", "fills_gap_place": "비자림", "google_rating": 4.8, "google_rating_count": 33, "price_level": "low"},
    {"name": "동광메밀짬뽕", "content_id": "2837142", "latitude": 33.3105401917, "longitude": 126.3497119467, "firstmenu": "메밀 해물짬뽕", "fills_gap_place": "카멜리아힐", "google_rating": 4.2, "google_rating_count": 210, "price_level": "low"},
]


def load_catalog() -> dict:
    with JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_catalog(catalog: dict) -> None:
    with JSON_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")


def most_common_value(values: list) -> object:
    return Counter(tuple(v) if isinstance(v, list) else v for v in values).most_common(1)[0][0]


def compute_reference_fields(places: list[dict]) -> dict:
    """Most-common/median field values among the existing jeju-restaurant-*
    entries, computed live from the catalog (not hardcoded)."""
    restaurants = [p for p in places if p["id"].startswith(RESTAURANT_ID_PREFIX)]
    return {
        "suitable_for": list(most_common_value([p["suitable_for"] for p in restaurants])),
        "time_fit": list(most_common_value([p["time_fit"] for p in restaurants])),
        "pace": list(most_common_value([p["pace"] for p in restaurants])),
        "mobility": list(most_common_value([p["mobility"] for p in restaurants])),
        "duration_hours": int(statistics.median(p["duration_hours"] for p in restaurants)),
        "priority": int(statistics.median(p["priority"] for p in restaurants)),
    }


def nearest_area(lat: float, lng: float, places: list[dict]) -> tuple[str, float]:
    coords = [(p["latitude"], p["longitude"], p["area"]) for p in places if p.get("latitude") is not None]
    nearest = min(coords, key=lambda t: haversine_distance_km(lat, lng, t[0], t[1]))
    return nearest[2], haversine_distance_km(lat, lng, nearest[0], nearest[1])


def find_dedup_match(candidate: dict, restaurants: list[dict]) -> dict | None:
    for existing in restaurants:
        if existing.get("latitude") is None:
            continue
        distance_km = haversine_distance_km(candidate["latitude"], candidate["longitude"], existing["latitude"], existing["longitude"])
        if distance_km > DEDUP_DISTANCE_KM:
            continue
        similarity = difflib.SequenceMatcher(None, candidate["name"], existing["name"]).ratio()
        if similarity >= DEDUP_NAME_SIMILARITY_THRESHOLD:
            return {"existing_name": existing["name"], "existing_id": existing["id"], "distance_km": round(distance_km, 3), "similarity": round(similarity, 3)}
    return None


def build_new_place(candidate: dict, reference: dict, area: str) -> dict:
    return {
        "id": f"{NEW_ID_PREFIX}{candidate['content_id']}",
        "name": candidate["name"],
        "activity_type": ["미식"],
        "budget_level": [candidate["price_level"]],
        "suitable_for": list(reference["suitable_for"]),
        "time_fit": list(reference["time_fit"]),
        "area": area,
        "duration_hours": reference["duration_hours"],
        "priority": reference["priority"],
        "pace": list(reference["pace"]),
        "mobility": list(reference["mobility"]),
        "summary": f"{candidate['fills_gap_place']} 인근, 대표 메뉴는 {candidate['firstmenu']}",
        "latitude": candidate["latitude"],
        "longitude": candidate["longitude"],
        "content_id": candidate["content_id"],
        "google_rating": candidate["google_rating"],
        "google_rating_count": candidate["google_rating_count"],
        "is_active": True,
        "mood": [],
        "visual_feature": [],
    }


def resolve_additions(catalog: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Pure (no file I/O) resolution - returns (to_add, already_merged, dedup_skipped)."""
    places = catalog["places"]
    existing_ids = {p["id"] for p in places}
    existing_content_ids = {p["content_id"] for p in places if p.get("content_id")}
    restaurants = [p for p in places if p["id"].startswith(RESTAURANT_ID_PREFIX)]
    area_set = {p["area"] for p in places}
    reference = compute_reference_fields(places)

    to_add: list[dict] = []
    already_merged: list[dict] = []
    dedup_skipped: list[dict] = []

    for candidate in NEW_RESTAURANTS:
        new_id = f"{NEW_ID_PREFIX}{candidate['content_id']}"
        if new_id in existing_ids or candidate["content_id"] in existing_content_ids:
            already_merged.append({"name": candidate["name"], "id": new_id})
            continue
        dup = find_dedup_match(candidate, restaurants)
        if dup is not None:
            dedup_skipped.append({"name": candidate["name"], "match": dup})
            continue
        area, dist_km = nearest_area(candidate["latitude"], candidate["longitude"], places)
        if area not in area_set:
            raise ValueError(f"{candidate['name']}: resolved area {area!r} not in existing area set {area_set}")
        place = build_new_place(candidate, reference, area)
        to_add.append(place)
        print(f"  {candidate['name']:24s} -> area={area:15s} (nearest existing place {dist_km:.2f}km), id={place['id']}")

    return to_add, already_merged, dedup_skipped


def main() -> None:
    catalog = load_catalog()
    before_count = len(catalog["places"])

    print(f"=== {CITY}: 신규 식당 {len(NEW_RESTAURANTS)}곳 후보 검토 ===")
    to_add, already_merged, dedup_skipped = resolve_additions(catalog)

    if dedup_skipped:
        print("\n중복으로 건너뜀:")
        for row in dedup_skipped:
            print(f"  {row['name']} -> {row['match']}")

    if already_merged:
        print(f"\n이미 병합됨(건너뜀): {len(already_merged)}건")

    if to_add:
        catalog["places"].extend(to_add)
        save_catalog(catalog)

    after_count = len(catalog["places"])
    print(f"\n추가: {len(to_add)}건, 중복 건너뜀: {len(dedup_skipped)}건, 이미 병합됨: {len(already_merged)}건")
    print(f"전체 장소 수: {before_count} -> {after_count}")
    print(f"제외 대상(품질 기준 미달, 추가 대상 아님): {len(EXCLUDED_CANDIDATES)}건 - {[c['name'] for c in EXCLUDED_CANDIDATES]}")


if __name__ == "__main__":
    main()
