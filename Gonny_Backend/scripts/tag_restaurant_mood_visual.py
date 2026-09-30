"""Adds mood/visual_feature tags to a small, explicitly-verified subset of
the 192 individually-researched restaurants merged by
scripts/merge_restaurant_data.py (see feature/restaurant-recommendations).

This is NOT a bulk/inferred tagging pass - every id below was checked
against its evidence_note/cuisine/rating_summary text in
local_only/data/{city}_restaurants_geocoded.csv one at a time, and only
gets tagged when that text gives a real, specific reason to (see the
comment above each group). Every other researched restaurant (roughly
160+ more) is deliberately left with mood/visual_feature as [] - guessing
a mood/visual_feature for a place with no textual evidence would violate
this project's "no unsupported inference" principle, so this script never
touches an id it doesn't have a hardcoded entry for.

mood/visual_feature are a small controlled vocabulary across the whole
catalog: mood is only ever "활기참"/"조용함", visual_feature is only ever
"포토스팟"/"야경" (see VISUAL_FEATURE_CODE_MAP in
app/domains/destination_catalog/schemas.py). This pass adds "활기참",
"조용함" and "포토스팟" - no restaurant in this dataset had clear textual
evidence for "야경" ("뷰" in the source text was always part of "리뷰"),
so that value is never used here.

Usage: python scripts/tag_restaurant_mood_visual.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"

MOOD_LIVELY = "활기참"
MOOD_QUIET = "조용함"
VISUAL_PHOTO_SPOT = "포토스팟"

# Each entry: place id -> (city json file, mood values to add, visual_feature values to add).
# Grouped and commented with the textual evidence used to decide each one -
# see [Goal]/[Context] of the task this script was written for.

# visual_feature: 포토스팟 - distinctive, camera-worthy interior/plating
# explicitly called out in evidence_note.
PHOTO_SPOT_IDS = {
    "seoul-restaurant-jongno-salon-sulla": "seoul",  # "앤틱 인테리어"
    "seoul-restaurant-jongno-bangida": "seoul",  # "플레이팅이 화려한"
}

# mood: 조용함 - omakase/fine dining, counter-seat or course-based format
# that's inherently quiet dining, not evidence about any specific place's
# noise level per se, but a reliable format-based inference.
QUIET_MOOD_IDS = {
    "seoul-restaurant-gangnam-sushi-sumire": "seoul",  # "하이엔드 오마카세"
    "seoul-restaurant-jamsil-gold-chamchi": "seoul",  # "참치 오마카세"
    "busan-restaurant-nampo-sushibuok": "busan",  # "프라이빗 공간 제공 스시 오마카세"
    "seoul-restaurant-jamsil-bichaena": "seoul",  # "고급 한정식 파인다이닝, 롯데월드타워 81층"
}

# mood: 활기참, grouped by shared evidence:
# (A) Jeju Dongmun Market vicinity - market-specific liveliness.
JEJU_DONGMUN_MARKET_IDS = {
    "jeju-restaurant-eastjeju-ilpalpaljuk": "jeju",
    "jeju-restaurant-eastjeju-sarang-bunsik": "jeju",
    "jeju-restaurant-eastjeju-seoul-bunsik": "jeju",
    "jeju-restaurant-eastjeju-jangchun": "jeju",
    "jeju-restaurant-eastjeju-anseong": "jeju",
    "jeju-restaurant-eastjeju-hanil": "jeju",
    "jeju-restaurant-eastjeju-dongmun-ollejjinbbang": "jeju",
    "jeju-restaurant-eastjeju-nakwon-tteokjip": "jeju",
}

# (B) Seoul Gwangjang Market - same market-liveliness rationale as (A).
SEOUL_GWANGJANG_MARKET_IDS = {
    "seoul-restaurant-jongno-gwangjang-chapssal": "seoul",
}

# (C) 24-hour/always-open operation - always-on casual atmosphere.
ALWAYS_OPEN_IDS = {
    "seoul-restaurant-myeongdong-wontang-gamja-galbitang": "seoul",  # "24시간 영업"
    "seoul-restaurant-yeouido-gimsambo": "seoul",  # "24시간 연중무휴 운영"
    "seoul-restaurant-yeouido-jangdokdae": "seoul",  # "24시간 연중무휴 운영"
    "seoul-restaurant-yeouido-sinuiju-sundae": "seoul",  # "24시간 연중무휴 운영"
    "seoul-restaurant-gangnam-hyundai-sundaeguk": "seoul",  # "24시간 운영"
    "seoul-restaurant-gangnam-yeongdong-seolleongtang": "seoul",  # "24시간 운영"
    "seoul-restaurant-gangnam-gangnam-jinhaejang": "seoul",  # "24시간 운영"
}

# (D) Euljiro tool-alley open-air (야장) row - repeatedly confirmed in
# media as a lively open-air alley; woojiljip is explicitly named its
# flagship, the other 3 sit in the same alley.
EULJIRO_ALLEY_IDS = {
    "seoul-restaurant-euljiro-woojiljip": "seoul",  # "을지로 공구골목 대표 야장 맛집"
    "seoul-restaurant-euljiro-gaetmaeul": "seoul",
    "seoul-restaurant-euljiro-tongiljip": "seoul",
    "seoul-restaurant-euljiro-mapo-jjukkumi": "seoul",
}

# (E) Busan Nampo - popular spot explicitly described as having long waits.
BUSAN_NAMPO_POPULAR_IDS = {
    "busan-restaurant-nampo-18beon-wandangjip": "busan",  # "웨이팅 많은 인기 맛집으로 소개"
}

# (F) Myeongdong flagship landmark eateries - repeatedly confirmed across
# multiple sources as a perpetually-busy Myeongdong landmark.
MYEONGDONG_LANDMARK_IDS = {
    "seoul-restaurant-myeongdong-hadongkwan": "seoul",  # "명동 대표 노포", 다수 매체 반복 확인
    "seoul-restaurant-myeongdong-myeongdong-mandu": "seoul",  # "40년 이상 운영된 명동 대표 노포"
    "seoul-restaurant-myeongdong-hamheung-guksujip": "seoul",
}


def build_updates() -> dict[str, dict[str, list[str]]]:
    """id -> {"mood": [...], "visual_feature": [...]} - each id appears in
    at most one of the mood groups and at most one of the visual_feature
    groups above, so merging is a straightforward dict build."""
    updates: dict[str, dict[str, list[str]]] = {}

    def add(ids: dict[str, str], *, mood: str | None = None, visual_feature: str | None = None) -> None:
        for place_id in ids:
            entry = updates.setdefault(place_id, {"mood": [], "visual_feature": []})
            if mood and mood not in entry["mood"]:
                entry["mood"].append(mood)
            if visual_feature and visual_feature not in entry["visual_feature"]:
                entry["visual_feature"].append(visual_feature)

    add(PHOTO_SPOT_IDS, visual_feature=VISUAL_PHOTO_SPOT)
    add(QUIET_MOOD_IDS, mood=MOOD_QUIET)
    add(JEJU_DONGMUN_MARKET_IDS, mood=MOOD_LIVELY)
    add(SEOUL_GWANGJANG_MARKET_IDS, mood=MOOD_LIVELY)
    add(ALWAYS_OPEN_IDS, mood=MOOD_LIVELY)
    add(EULJIRO_ALLEY_IDS, mood=MOOD_LIVELY)
    add(BUSAN_NAMPO_POPULAR_IDS, mood=MOOD_LIVELY)
    add(MYEONGDONG_LANDMARK_IDS, mood=MOOD_LIVELY)

    return updates


ID_TO_CITY = {
    **PHOTO_SPOT_IDS,
    **QUIET_MOOD_IDS,
    **JEJU_DONGMUN_MARKET_IDS,
    **SEOUL_GWANGJANG_MARKET_IDS,
    **ALWAYS_OPEN_IDS,
    **EULJIRO_ALLEY_IDS,
    **BUSAN_NAMPO_POPULAR_IDS,
    **MYEONGDONG_LANDMARK_IDS,
}


def tag_city(city: str, updates: dict[str, dict[str, list[str]]]) -> int:
    json_path = DESTINATIONS_DIR / f"{city}.json"
    with json_path.open(encoding="utf-8") as f:
        catalog = json.load(f)

    ids_for_this_city = {place_id for place_id, target_city in ID_TO_CITY.items() if target_city == city}
    tagged_count = 0
    seen_ids: set[str] = set()

    for place in catalog["places"]:
        if place["id"] not in ids_for_this_city:
            continue
        seen_ids.add(place["id"])
        place["mood"] = updates[place["id"]]["mood"]
        place["visual_feature"] = updates[place["id"]]["visual_feature"]
        tagged_count += 1

    missing = ids_for_this_city - seen_ids
    if missing:
        raise ValueError(f"ids not found in {json_path}: {sorted(missing)}")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return tagged_count


def main() -> None:
    updates = build_updates()
    total_tagged = 0
    for city in ["seoul", "busan", "jeju"]:
        tagged_count = tag_city(city, updates)
        total_tagged += tagged_count
        print(f"{city}: tagged {tagged_count}")
    print(f"\ntotal restaurants tagged: {total_tagged}")


if __name__ == "__main__":
    main()
