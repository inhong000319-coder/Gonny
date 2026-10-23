"""Fill latitude/longitude for 3 seoul non-restaurant places that had
none: daelim-sangga, s-factory, e-land-hangang-cruise.

Source: Google Maps place page Plus Codes (!20s... parameter), decoded by
the user (cell size ~3m). See local_only/reports/
seoul_missing_coordinates_apply.md for the validation this was checked
against (same-area centroid distance, daelim-sangga vs sewoon-plaza).

  - daelim-sangga ("대림상가", 서울 중구 산림동 207-2 일대):
    Google Maps place "대림상가", plus code 8Q98HX9W+253
    -> (37.567512, 126.995422)
  - s-factory ("S-Factory", 성동구 성수동):
    Google Maps place "S-Factory", plus code 8Q99G3R5+WP9
    -> (37.542287, 127.059359)
  - e-land-hangang-cruise ("여의도 이랜드크루즈(한강유람선)", 영등포구 여의도동):
    Google Maps place "여의도 이랜드크루즈(한강유람선)", plus code 8Q98GWGQ+78Q
    -> (37.525712, 126.938359)
    CAVEAT: Google Maps classifies this place as "cruise_agency" - this
    may be the ticket office/company address rather than the actual
    boarding pier. Not resolved here; flagged as a limitation in the
    report, not corrected by this script.

content_id is untouched (confirmed unused in the live generate() request
path - see missing_coordinates_impact.md item 1) - only latitude/
longitude are filled.

Usage:
    python scripts/apply_seoul_missing_coordinates.py --dry-run
    python scripts/apply_seoul_missing_coordinates.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.domains.rule_planner.services.travel_estimate import haversine_distance_km  # noqa: E402

DATA_DIR = REPO_ROOT / "app" / "data" / "destinations"
SEOUL_PATH = DATA_DIR / "seoul.json"

# (id, latitude, longitude) - see module docstring for source per place.
NEW_COORDINATES: list[tuple[str, float, float]] = [
    ("daelim-sangga", 37.567512, 126.995422),
    ("s-factory", 37.542287, 127.059359),
    ("e-land-hangang-cruise", 37.525712, 126.938359),
]

# Abort the whole run if a new coordinate lands this far or farther from
# the centroid of other same-area places that already have coordinates -
# a sign the coordinate or the area tag may not actually match.
MAX_CENTROID_DISTANCE_KM = 3.0


def load_seoul() -> tuple[dict, list[dict]]:
    data = json.loads(SEOUL_PATH.read_text(encoding="utf-8"))
    return data, data["places"]


def validate(places: list[dict]) -> list[str]:
    """Returns a list of problems; empty means validation passed."""
    problems = []
    by_id = {p["id"]: p for p in places}
    for place_id, lat, lon in NEW_COORDINATES:
        if place_id not in by_id:
            problems.append(f"{place_id}: 카탈로그에 없음")
            continue
        place = by_id[place_id]
        existing_lat, existing_lon = place.get("latitude"), place.get("longitude")
        if existing_lat is not None or existing_lon is not None:
            if existing_lat == lat and existing_lon == lon:
                continue  # already applied, idempotent no-op later
            problems.append(f"{place_id}: 이미 좌표가 있음({existing_lat},{existing_lon}) - 덮어쓰지 않음, 수동 확인 필요")
            continue

        area = place.get("area")
        same_area = [p for p in places if p.get("area") == area and p["id"] != place_id
                     and p.get("latitude") is not None and p.get("longitude") is not None]
        if not same_area:
            problems.append(f"{place_id}: area={area}에 좌표 있는 다른 장소가 없어 검증 불가")
            continue
        centroid_lat = sum(p["latitude"] for p in same_area) / len(same_area)
        centroid_lon = sum(p["longitude"] for p in same_area) / len(same_area)
        dist_km = haversine_distance_km(lat, lon, centroid_lat, centroid_lon)
        print(f"[검증] {place_id}: area={area} 기준 같은-area 장소 {len(same_area)}곳 중심에서 {dist_km*1000:.1f}m")
        if dist_km >= MAX_CENTROID_DISTANCE_KM:
            problems.append(f"{place_id}: 같은 area 중심에서 {dist_km:.2f}km 떨어짐 ({MAX_CENTROID_DISTANCE_KM}km 기준 초과)")
    return problems


def dump_seoul(data: dict) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    with SEOUL_PATH.open("w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data, places = load_seoul()

    problems = validate(places)
    if problems:
        print("[중단] 검증 실패:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("[확인] 검증 통과(3km 미만, 이미 있는 값과 충돌 없음)")

    by_id = {p["id"]: p for p in places}
    plan = []
    for place_id, lat, lon in NEW_COORDINATES:
        place = by_id[place_id]
        if place.get("latitude") == lat and place.get("longitude") == lon:
            plan.append((place_id, "skip_already_applied", place.get("latitude"), place.get("longitude"), lat, lon))
        else:
            plan.append((place_id, "fill", place.get("latitude"), place.get("longitude"), lat, lon))

    print("\n=== 적용 계획 ===")
    for place_id, action, old_lat, old_lon, new_lat, new_lon in plan:
        print(f"  {place_id}: ({old_lat}, {old_lon}) -> ({new_lat}, {new_lon}) [{action}]")

    if args.dry_run:
        print("\n[dry-run] 실제 파일은 수정하지 않았습니다.")
        return 0

    n_filled = 0
    for place_id, action, _, _, new_lat, new_lon in plan:
        if action == "skip_already_applied":
            continue
        place = by_id[place_id]
        if place.get("latitude") is not None or place.get("longitude") is not None:
            raise RuntimeError(f"{place_id}: 적용 직전 재확인에서 이미 좌표가 있음 - 중단")
        place["latitude"] = new_lat
        place["longitude"] = new_lon
        n_filled += 1

    dump_seoul(data)
    print(f"\n[적용] seoul.json: {n_filled}곳에 좌표 채움")
    return 0


if __name__ == "__main__":
    sys.exit(main())
