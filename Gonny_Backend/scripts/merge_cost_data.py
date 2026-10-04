"""Adds average_cost_krw (tourist attractions) and average_price_krw
(accommodations) from individually-researched figures.

Value semantics (deliberately preserved - do not mix 0 and null):
  0    -> confirmed free
  N>0  -> confirmed representative adult admission (attractions) or
          standard single-room nightly rate in KRW (accommodations)
  absent / null -> researched, but no reliable figure found

Only the ids listed below are touched. Food (미식) entities are never
given a cost - their menu-price spread makes this field meaningless
for them. Re-running is idempotent (same values re-set).

Usage: python scripts/merge_cost_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
ACCOMMODATIONS_DIR = PROJECT_ROOT / "app" / "data" / "accommodations"

DESTINATION_COSTS: dict[str, dict[str, int]] = {
    "seoul": {
        "gyeongbokgung": 3000,
        "bukchon": 0,
        "namsan-tower": 29000,
        "yeouido-hangang": 0,
        "coex": 0,
        "changdeokgung": 8000,
        "yeonnam-forest": 0,
        "seokchon-lake": 0,
        "ddp": 0,
        "lotte-world-adventure": 67000,
        "e-land-hangang-cruise": 18000,
        "sewoon-plaza": 0,
        "cheonggyecheon-museum": 0,
        "seoul-forest": 0,
        "myeongdong-cathedral": 0,
        "bank-of-korea-money-museum": 0,
        "heunginjimun-gate": 0,
        "war-memorial-korea": 0,
        "itaewon-antique-furniture-street": 0,
        "namsan-cable-car": 15000,
        "namsan-park-trail": 0,
        "seoul-sky": 29000,
        "63-square": 15000,
        "ktng-sangsangmadang-hongdae": 0,
        "trick-eye-museum-seoul": 15000,
        "bongeunsa-temple": 0,
        "seonjeongneung": 1000,
        "daelim-sangga": 0,
        "lotte-world-aquarium": 35000,
        "seoul-baekje-museum": 0,
        "ak-plaza-hongdae": 0,
        "sema-bunker": 0,
    },
    "busan": {
        "blue-line-park": 10000,
        "gamcheon-culture-village": 0,
        "songdo-cable-car": 17000,
        "taejongdae": 0,
        "haeundae-beach": 0,
        "dongbaek-island": 0,
        "songdo-beach": 0,
        "amnam-park": 0,
        "f1963": 0,
        "busan-x-the-sky": 27000,
        "yongdusan-park": 0,
        "bosu-book-street": 0,
        "songdo-yonggung-suspension-bridge": 1000,
        "busan-tower": 12000,
        "busan-modern-history-museum": 0,
        "busan-moca": 0,
        "huinnyeoul-culture-village": 0,
        "heosimchung": 15000,
        "shinsegae-spaland": 25000,
        "club-d-oasis": 30000,
    },
    "jeju": {
        "hamdeok-beach": 0,
        "seongsan-ilchulbong": 5000,
        "seopjikoji": 0,
        "bijarim": 3000,
        "hallim-park": 15000,
        "hyeopjae-beach": 0,
        "camellia-hill": 10000,
        "jungmun-saekdal": 0,
        "jeju-rail-bike": 30000,
        "arte-museum-jeju": 18000,
        "jeju-glass-castle": 9000,
        "yeomiji-botanical-garden": 10000,
        "jeju-teddy-bear-museum": 12000,
        "gwangchigi-beach": 0,
        "seongeup-folk-village": 0,
        "jeju-stone-park": 5000,
        "haenyeo-museum": 1100,
        "snoopy-garden-jeju": 19000,
        "9-81-park-jeju": 29500,
        "saebyeol-oreum": 0,
    },
}

ACCOMMODATION_PRICES: dict[str, dict[str, int]] = {
    "seoul": {
        "2592489": 143391,
        "2572829": 49886,
        "142721": 323400,
        "984650": 69111,
        "142766": 762300,
        "2008490": 182664,
        "142771": 197123,
    },
    "busan": {
        "2754601": 109000,
        "2925797": 250401,
        "2818890": 550000,
        "3083428": 58206,
        "2731553": 352000,
        "2816102": 65000,
        "2705418": 42862,
        "2708705": 280000,
        "142978": 70000,
        "2811461": 85195,
    },
    "jeju": {
        "1894943": 880000,
        "735314": 80000,
        "2699343": 90000,
        "3084957": 54835,
        "1897905": 69000,
        "139008": 60000,
        "137476": 110000,
        "2991120": 500000,
        "2624249": 142269,
        "2757210": 64900,
    },
}

FOOD_TAG = "미식"


def _apply(
    json_path: Path,
    list_key: str,
    updates: dict[str, int],
    field: str,
    *,
    reject_food: bool,
) -> int:
    with json_path.open(encoding="utf-8") as f:
        catalog = json.load(f)

    by_id = {item["id"]: item for item in catalog[list_key]}
    missing = [item_id for item_id in updates if item_id not in by_id]
    if missing:
        raise ValueError(f"ids not found in {json_path.name}: {missing}")

    if reject_food:
        food_ids = [
            item_id for item_id in updates if FOOD_TAG in by_id[item_id].get("activity_type", [])
        ]
        if food_ids:
            raise ValueError(f"food entities must not get {field}: {food_ids}")

    for item_id, value in updates.items():
        by_id[item_id][field] = value

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return len(updates)


def main() -> None:
    for city, updates in DESTINATION_COSTS.items():
        count = _apply(
            DESTINATIONS_DIR / f"{city}.json",
            "places",
            updates,
            "average_cost_krw",
            reject_food=True,
        )
        print(f"destinations/{city}: set average_cost_krw on {count} places")

    for city, updates in ACCOMMODATION_PRICES.items():
        count = _apply(
            ACCOMMODATIONS_DIR / f"{city}.json",
            "accommodations",
            updates,
            "average_price_krw",
            reject_food=False,
        )
        print(f"accommodations/{city}: set average_price_krw on {count} accommodations")


if __name__ == "__main__":
    main()
