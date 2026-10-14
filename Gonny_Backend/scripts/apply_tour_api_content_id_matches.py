"""Applies TourAPI content_id to 23 Seoul/Busan/Jeju destinations/*.json
places that passed review:

- 18 "high" matches (normalized title exact match + distance <=300m,
  re-verified with locationBasedList2) - see local_only/reports/
  tour_api_place_matching_stage1b_high_full.json.
- 5 medium/ambiguous candidates a human explicitly approved after
  reviewing local_only/reports/tour_api_place_matching_stage1b_
  medium_full.json and ..._low_ambiguous_full.json's ambiguous
  candidates (2026-10-14) - see TARGET_CANDIDATE_TITLE_BY_PLACE_ID below
  for exactly which candidate title was approved for each.

For every target place, the approved candidate title is looked up
against the actual report JSON (not just trusted from this script's own
table) - if the title doesn't appear there (typo, stale report, etc.),
or appears for more than one distinct content_id, or doesn't appear at
all, that place is skipped and reported rather than guessed at.

Idempotent and conservative, same pattern as scripts/apply_jeju_place_text.py/
scripts/apply_jeju_mood_visual.py: a place that already has a non-empty
content_id is never overwritten (even if the stored value happens to
differ from what we'd apply) - it's skipped and reported. Re-running
with the same reports is always a no-op once applied.

For every place that DOES get a new content_id this run, its
detailCommon2 overview is fetched once and cached to
local_only/tour_api_overview_cache/overview_cache.json (never a
committed path). detailCommon2 only accepts serviceKey/MobileOS/
MobileApp/_type/contentId - see local_only/reports/
tour_api_coverage_investigation.md for why (defaultYN/overviewYN/
contentTypeId all raise INVALID_REQUEST_PARAMETER_ERROR there, unlike
detailIntro2).

Jeju 섭지코지(content_id=127813)'s existing content_id/coordinates are
untouched - it already has a content_id, so the "don't overwrite"
rule already protects it; it is not in TARGET_CANDIDATE_TITLE_BY_PLACE_ID
either way.

Usage: python scripts/apply_tour_api_content_id_matches.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
REPORTS_DIR = PROJECT_ROOT / "local_only" / "reports"
OVERVIEW_CACHE_DIR = PROJECT_ROOT / "local_only" / "tour_api_overview_cache"
OVERVIEW_CACHE_PATH = OVERVIEW_CACHE_DIR / "overview_cache.json"

CITIES = ["seoul", "busan", "jeju"]

REQUEST_INTERVAL_SECONDS = 0.25
MAX_RETRIES_ON_API_ERROR = 5
RETRY_BACKOFF_SECONDS = 2.0

# place_id -> the exact TourAPI candidate title that was approved for it.
# The first 18 are stage 1b's "high" matches (title+distance re-verified
# via locationBasedList2 - see tour_api_place_matching_stage1b_high_full.json).
# The last 5 are medium/ambiguous candidates a human reviewed and approved
# from the one-line listing produced for review (2026-10-14).
TARGET_CANDIDATE_TITLE_BY_PLACE_ID: dict[str, str] = {
    # --- 18 high (stage 1b) ---
    "seoul-restaurant-euljiro-mugyodong-bugeoguk": "무교동 북어국집",
    "seoul-restaurant-dongdaemun-jinokhwa": "진옥화할매원조닭한마리",
    "seoul-restaurant-seongsu-seongsudarak": "성수다락",
    "seoul-restaurant-seongsu-onryang": "온량",
    "seoul-restaurant-gangnam-gangnam-jinhaejang": "강남진해장",
    "seoul-restaurant-jamsil-vikings-wharf": "바이킹스워프 롯데월드몰점",
    "seoul-restaurant-itaewon-yujin-makguksu": "유진막국수",
    "busan-restaurant-nampo-18beon-wandangjip": "18번완당집",
    "busan-restaurant-haeundae-obanjang": "오반장",
    "busan-restaurant-haeundae-ilpum-hanwoo": "일품한우",
    "busan-restaurant-haeundae-halmaejib": "할매집",
    "jeju-restaurant-eastjeju-sarang-bunsik": "사랑분식",
    "jeju-restaurant-seongsan-geuriunbada": "그리운바다성산포",
    "jeju-restaurant-seongsan-bokjassi-yeontan": "복자씨연탄구이",
    "jeju-restaurant-seogwipowest-gozipdolwuruk": "고집돌우럭 중문점",
    "jeju-restaurant-seogwipowest-jungmun-doldam-heukdwaeji": "중문 돌담흑돼지",
    "jeju-restaurant-seogwipowest-jungmun-sudu-ribomal": "중문수두리보말칼국수",
    "jeju-restaurant-westjeju-hyeopjae-suudong": "협재 수우동",
    # --- 5 medium/ambiguous approved by human review (2026-10-14) ---
    "seoul-restaurant-jongno-xiaobao": "샤오바오우육면 종로본점",
    "busan-restaurant-gwangalli-yoikuma": "요이쿠마 본점",
    "jungmun-saekdal": "중문색달해수욕장",
    "sea-life-busan-aquarium": "씨라이프부산아쿠아리움",
    "seoul-restaurant-gangnam-apgujeong-gadam": "가담",
}


def load_api_key() -> str | None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", env_path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def load_tour_api_base_url() -> str:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        match = re.search(r"^TOUR_API_BASE_URL=(.*)$", env_path.read_text(encoding="utf-8"), re.MULTILINE)
        if match and match.group(1).strip():
            return match.group(1).strip().rstrip("/")
    return "https://apis.data.go.kr/B551011/KorService2"


def load_catalogs() -> dict[str, dict]:
    return {city: json.loads((DESTINATIONS_DIR / f"{city}.json").read_text(encoding="utf-8")) for city in CITIES}


def find_place(catalogs: dict[str, dict], place_id: str) -> tuple[str, dict] | tuple[None, None]:
    for city, catalog in catalogs.items():
        for place in catalog["places"]:
            if place["id"] == place_id:
                return city, place
    return None, None


def load_report_candidates() -> dict[str, list[dict]]:
    """Returns place_name -> list of {"title", "content_id"} candidate
    records collected from every stage 1/1b report that carries one -
    the high/medium full dumps (one candidate per place) and the
    ambiguous list (several candidates per place)."""
    candidates_by_place_name: dict[str, list[dict]] = {}

    def add(place_name: str, title: str, content_id: str) -> None:
        candidates_by_place_name.setdefault(place_name, []).append({"title": title, "content_id": str(content_id)})

    high_path = REPORTS_DIR / "tour_api_place_matching_stage1b_high_full.json"
    if high_path.exists():
        high = json.loads(high_path.read_text(encoding="utf-8"))
        for entries in high.values():
            for e in entries:
                add(e["place"], e["title"], e["content_id"])

    medium_path = REPORTS_DIR / "tour_api_place_matching_stage1b_medium_full.json"
    if medium_path.exists():
        medium = json.loads(medium_path.read_text(encoding="utf-8"))
        for entries in medium.values():
            for e in entries:
                add(e["place"], e["title"], e["content_id"])

    low_ambiguous_path = REPORTS_DIR / "tour_api_place_matching_stage1b_low_ambiguous_full.json"
    if low_ambiguous_path.exists():
        low_ambiguous = json.loads(low_ambiguous_path.read_text(encoding="utf-8"))
        for entries in low_ambiguous.get("ambiguous", {}).values():
            for e in entries:
                for c in e.get("candidates", []):
                    add(e["place"], c["title"], c["contentid"])

    return candidates_by_place_name


def resolve_content_id(place_name: str, expected_title: str, report_candidates: dict[str, list[dict]]) -> tuple[str | None, str]:
    """Returns (content_id_or_None, reason). reason is only meaningful
    when content_id is None."""
    candidates = report_candidates.get(place_name)
    if not candidates:
        return None, "장소를 어떤 보고서에서도 찾지 못함"

    matches = [c for c in candidates if c["title"] == expected_title]
    if not matches:
        return None, f"보고서에 제목 {expected_title!r}과 정확히 일치하는 후보가 없음"

    distinct_ids = {m["content_id"] for m in matches}
    if len(distinct_ids) > 1:
        return None, f"제목은 일치하지만 보고서에 서로 다른 content_id가 여러 개 있음: {sorted(distinct_ids)}"

    return matches[0]["content_id"], ""


def fetch_detail_common(base_url: str, api_key: str, content_id: str) -> dict | None:
    import httpx

    url = f"{base_url}/detailCommon2"
    params = {
        "serviceKey": api_key,
        "MobileOS": "ETC",
        "MobileApp": "Gonny",
        "_type": "json",
        "contentId": content_id,
    }
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            payload = resp.json()["response"]
            if payload["header"]["resultCode"] != "0000":
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            body = payload["body"]["items"]
            items = body["item"] if body else []
            if not isinstance(items, list):
                items = [items]
            return items[0] if items else None
        except Exception:
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return None


def load_overview_cache() -> dict[str, dict]:
    if OVERVIEW_CACHE_PATH.exists():
        return json.loads(OVERVIEW_CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_overview_cache(cache: dict[str, dict]) -> None:
    OVERVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OVERVIEW_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_content_ids(catalogs: dict[str, dict], report_candidates: dict[str, list[dict]]) -> dict:
    """Pure core (no file I/O) - mutates catalogs[...]["places"] in
    place. Returns a result dict with per-place outcomes; callers decide
    what to do with it (write files, fetch overviews, print)."""
    applied: list[dict] = []
    skipped: list[dict] = []

    for place_id, expected_title in TARGET_CANDIDATE_TITLE_BY_PLACE_ID.items():
        city, place = find_place(catalogs, place_id)
        if place is None:
            skipped.append({"place_id": place_id, "city": None, "reason": "카탈로그에서 id를 찾지 못함"})
            continue

        existing_content_id = place.get("content_id")
        if existing_content_id:
            skipped.append(
                {"place_id": place_id, "city": city, "place_name": place["name"], "reason": f"이미 content_id={existing_content_id} 보유 - 덮어쓰지 않음"}
            )
            continue

        content_id, reason = resolve_content_id(place["name"], expected_title, report_candidates)
        if content_id is None:
            skipped.append({"place_id": place_id, "city": city, "place_name": place["name"], "reason": reason})
            continue

        place["content_id"] = content_id
        applied.append({"place_id": place_id, "city": city, "place_name": place["name"], "content_id": content_id, "title": expected_title})

    return {"applied": applied, "skipped": skipped}


def save_catalogs(catalogs: dict[str, dict]) -> None:
    for city, catalog in catalogs.items():
        path = DESTINATIONS_DIR / f"{city}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
            f.write("\n")


def main() -> None:
    catalogs = load_catalogs()
    report_candidates = load_report_candidates()

    result = apply_content_ids(catalogs, report_candidates)
    save_catalogs(catalogs)

    print(f"적용됨: {len(result['applied'])} / {len(TARGET_CANDIDATE_TITLE_BY_PLACE_ID)}")
    by_city_applied: dict[str, int] = {}
    for a in result["applied"]:
        by_city_applied[a["city"]] = by_city_applied.get(a["city"], 0) + 1
        print(f"  + {a['city']} / {a['place_id']} / {a['place_name']} -> content_id={a['content_id']}")
    print(f"도시별 적용 건수: {by_city_applied}")

    print(f"\n건너뜀: {len(result['skipped'])}")
    for s in result["skipped"]:
        print(f"  - {s['place_id']} ({s.get('place_name', '?')}): {s['reason']}")

    api_key = load_api_key()
    if not api_key:
        print("\nTOUR_API_KEY not found in .env - overview 캐싱을 건너뜁니다.")
        return

    base_url = load_tour_api_base_url()
    overview_cache = load_overview_cache()
    newly_cached = 0
    overview_lengths: list[int] = []

    for a in result["applied"]:
        if a["place_id"] in overview_cache:
            continue  # idempotent - don't re-fetch what's already cached
        detail = fetch_detail_common(base_url, api_key, a["content_id"])
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if detail is None:
            overview_cache[a["place_id"]] = {"content_id": a["content_id"], "title": a["title"], "overview": None, "fetch_failed": True}
            continue
        overview = str(detail.get("overview", "") or "")
        overview_cache[a["place_id"]] = {
            "content_id": a["content_id"],
            "title": detail.get("title", a["title"]),
            "overview": overview,
            "fetch_failed": False,
        }
        newly_cached += 1
        overview_lengths.append(len(overview))

    save_overview_cache(overview_cache)

    print(f"\noverview 신규 캐싱: {newly_cached}")
    if overview_lengths:
        print(f"  길이: min={min(overview_lengths)} max={max(overview_lengths)} mean={sum(overview_lengths) / len(overview_lengths):.1f}")
    failed = [pid for pid, v in overview_cache.items() if v.get("fetch_failed")]
    if failed:
        print(f"  조회 실패: {failed}")


if __name__ == "__main__":
    main()
