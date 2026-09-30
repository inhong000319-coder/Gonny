"""One-off, fully-hardcoded fill of AccommodationData.view for the 16
accommodations (out of 45 total across seoul/busan/jeju) whose view was
individually confirmed via official/OTA descriptions.

This is NOT a bulk/inferred pass - every id below was researched one at a
time. The other 29 accommodations are deliberately left at view=None
("researched but no evidence found" - not "confirmed no view"), matching
this project's "no unsupported inference" principle. Re-running this
script is idempotent (it just re-sets the same 16 values).

Usage: python scripts/fill_accommodation_view.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACCOMMODATIONS_DIR = PROJECT_ROOT / "app" / "data" / "accommodations"

# city -> {id: view}
VIEW_UPDATES: dict[str, dict[str, str]] = {
    "seoul": {
        "2570164": "city",  # 지유
        "142769": "city",  # 그랜드 인터컨티넨탈 서울 파르나스
        "984650": "river",  # 더리버사이드 호텔
        "142771": "city",  # 임피리얼 팰리스 부티크 호텔
    },
    "busan": {
        "2925797": "ocean",  # 엘시티 레지던스
        "2818890": "ocean",  # 그랜드 조선 부산
        "2731553": "ocean",  # 펠릭스바이STX
        "3532572": "ocean",  # 송정담다펜션
        "2816102": "ocean",  # 그레이193호텔
        "2708705": "ocean",  # 라비드아틀란호텔2
        "2811461": "ocean",  # 베이몬드호텔
    },
    "jeju": {
        "735314": "ocean",  # 까델아스
        "2699343": "ocean",  # 솔트
        "3084957": "ocean",  # 리치호텔
        "1897905": "ocean",  # 노을담은뜨락
        "2757210": "mountain",  # 플레이스 캠프 제주
    },
}

VALID_VIEWS = {"ocean", "city", "river", "mountain"}


def apply_city(city: str, updates: dict[str, str]) -> int:
    assert all(view in VALID_VIEWS for view in updates.values())

    json_path = ACCOMMODATIONS_DIR / f"{city}.json"
    with json_path.open(encoding="utf-8") as f:
        catalog = json.load(f)

    seen_ids: set[str] = set()
    updated_count = 0
    for accommodation in catalog["accommodations"]:
        if accommodation["id"] not in updates:
            continue
        seen_ids.add(accommodation["id"])
        accommodation["view"] = updates[accommodation["id"]]
        updated_count += 1

    missing = set(updates) - seen_ids
    if missing:
        raise ValueError(f"ids not found in {json_path}: {sorted(missing)}")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return updated_count


def main() -> None:
    total_updated = 0
    for city, updates in VIEW_UPDATES.items():
        updated_count = apply_city(city, updates)
        total_updated += updated_count
        print(f"{city}: updated {updated_count} accommodations")
    print(f"\ntotal accommodations updated: {total_updated}")


if __name__ == "__main__":
    main()
