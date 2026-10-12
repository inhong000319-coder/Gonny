"""Merges local_only/data/jeju_places_batch1.csv (24 Jeju sightseeing/
activity places) into app/data/destinations/jeju.json as new PlaceData
entries - same id-based idempotent pattern as scripts/merge_restaurant_data.py
(already-merged ids are skipped, not re-added or treated as an error) and
scripts/merge_cost_data.py (0 vs null cost semantics).

Every value either comes straight from the CSV or is produced by one of
the deterministic rules below - nothing is invented (no awards/rankings/
reviews). Rules for fields the CSV doesn't carry:

- area: the CSV's area_suggestion column, verbatim - no new area codes.
- activity_type: the CSV's "|"-separated activity_type column, split.
- setting: the CSV's setting column, verbatim (indoor/outdoor/mixed).
- average_cost_krw: the CSV's average_cost_krw if present (int); 0 if
  is_free=="true" (confirmed free, same 0-vs-null convention as
  scripts/merge_cost_data.py); else None (not researched/no reliable
  figure) - average_cost_krw and is_free are never both set in this CSV.
- priority/mvp_tier: reuses merge_restaurant_data.py's confidence mapping
  (PRIORITY_BY_CONFIDENCE, MVP_TIER_BY_CONFIDENCE - "high" confidence only
  gets mvp_tier="core", medium/low keep the schema default "standard").
- duration_hours: 2 for every row. The existing Jeju catalog's 26 non-food
  places (duration_hours 2 or 3) are overwhelmingly 2 (22/26) and none of
  these 24 new museum/market/garden/waterfall/coast/viewpoint-type rows
  have a CSV-sourced duration - this is a 가정값 (assumed value), not
  measured per place.
- time_fit: parsed from open_hours.
    * "상시 개방" anywhere in the string -> always-open ->
      ["morning", "afternoon", "evening"].
    * Else, every "~HH:MM" closing time mentioned (there can be several,
      for seasonal/multi-part hours like "[하절기] ... / [동절기] ...")
      is extracted and the LATEST one is used as "how late this place
      can stay open" (a defensible single number out of a
      multi-schedule string).
        - latest closing <= 18:00 -> ["morning", "afternoon"]
        - latest closing >= 21:00 -> ["morning", "afternoon", "evening"]
        - anything else (the 18:01-20:59 gap, or no "~HH:MM" pattern
          found at all e.g. a bare "09:00" with no range) is treated the
          same as "can't parse" - this is the fallback the task spec
          itself gives for unparseable hours, so the gap is folded into
          it rather than inventing an undocumented third rule:
          ["morning", "afternoon"] (the existing catalog's most common
          time_fit value).
- mobility: ["taxi-needed"] for every row - the existing catalog's most
  common mobility value for non-food places; a 가정값, since the CSV
  carries no mobility signal of its own.
- pace: ["easy"] for every row (no CSV signal; matches the existing
  catalog's near-universal value - 63/65 places).
- budget_level: derived from the row's resolved average_cost_krw (see
  above, not the raw CSV columns) - free or <= 10,000 KRW ->
  ["low", "medium"]; > 10,000 KRW -> ["medium", "high"]; unknown (None)
  -> ["low", "medium", "high"] (no claim either way).
- suitable_for: all 4 companion types - the CSV gives no basis to
  exclude any of them.
- mood / visual_feature / mood_keywords / highlight_tags: left empty
  ([]) - the existing catalog's hand-written values for these fields are
  bespoke editorial color (e.g. "노을이 예쁜"), not something derivable
  from this CSV's facts, and the task says not to invent that kind of
  claim.
- summary / note_templates: a single generic, deterministic sentence
  built only from the CSV's own name/area/activity_type(first value) -
  reuses the existing {place_name} placeholder convention (see
  note_generator.py) rather than any of the catalog's bespoke prose.
  category_label uses only the FIRST activity_type value (a sanbanggulsa-
  style "문화·역사|자연·트레킹" row would otherwise produce an
  unreadably long sentence) - a 가정값 about which of the row's own
  listed categories is "the" category for this one generated sentence.
- rain_sensitive_light: indoor/mixed -> False (always, per spec).
  outdoor -> True only when the CSV's own name contains "해변"/
  "해수욕장" (beach) - reverse-engineered from the existing catalog's
  outdoor rain_sensitive_light=True places, which are exactly the
  beach-named ones (함덕/월정리/협재/중문색달/광치기) plus two ride-based
  활동 entries (jeju-rail-bike, 9.81 파크) that have no equivalent among
  these 24 CSV rows. A 가정값: "ride-based" isn't checked here since no
  new row's activity_type is "액티비티".

Rows without both latitude and longitude, or that otherwise fail to
parse, would be skipped and reported by name (none exist in this CSV as
of this writing - see the PR description for the empty report).

Usage: python scripts/merge_jeju_places.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
LOCAL_DATA_DIR = PROJECT_ROOT / "local_only" / "data"

CSV_PATH = LOCAL_DATA_DIR / "jeju_places_batch1.csv"
CITY = "jeju"

# Reused from merge_restaurant_data.py (same confidence -> priority/
# mvp_tier mapping, so "high"-confidence rows from either source are
# treated identically).
PRIORITY_BY_CONFIDENCE = {"high": 8, "medium": 6, "low": 4}
MVP_TIER_BY_CONFIDENCE = {"high": "core"}

DEFAULT_DURATION_HOURS = 2
DEFAULT_MOBILITY = ["taxi-needed"]
DEFAULT_PACE = ["easy"]
DEFAULT_SUITABLE_FOR = ["solo", "couple", "friend", "family"]
FALLBACK_TIME_FIT = ["morning", "afternoon"]

LOW_COST_MAX_KRW = 10000
BEACH_NAME_MARKERS = ["해변", "해수욕장"]

AREA_LABEL_KO = {
    "east-jeju": "제주 동부",
    "west-jeju": "제주 서부",
    "seogwipo-west": "서귀포 서부",
    "seongsan": "성산",
}


def _parse_optional_float(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def _resolve_average_cost_krw(row: dict[str, str]) -> int | None:
    raw_cost = row["average_cost_krw"].strip()
    if raw_cost:
        return int(float(raw_cost))
    if row["is_free"].strip().lower() == "true":
        return 0
    return None


def _budget_level(average_cost_krw: int | None) -> list[str]:
    if average_cost_krw is None:
        return ["low", "medium", "high"]
    if average_cost_krw <= LOW_COST_MAX_KRW:
        return ["low", "medium"]
    return ["medium", "high"]


_CLOSING_TIME_PATTERN = re.compile(r"~(\d{1,2}):(\d{2})")


def _time_fit(open_hours: str) -> list[str]:
    if "상시 개방" in open_hours:
        return ["morning", "afternoon", "evening"]

    matches = _CLOSING_TIME_PATTERN.findall(open_hours)
    if not matches:
        return list(FALLBACK_TIME_FIT)

    latest_closing_hour = max(int(hour) + int(minute) / 60 for hour, minute in matches)
    if latest_closing_hour <= 18:
        return ["morning", "afternoon"]
    if latest_closing_hour >= 21:
        return ["morning", "afternoon", "evening"]
    return list(FALLBACK_TIME_FIT)


def _rain_sensitive_light(setting: str, name: str) -> bool:
    if setting != "outdoor":
        return False
    return any(marker in name for marker in BEACH_NAME_MARKERS)


def _summary_and_note_templates(name: str, area: str, category_label: str) -> tuple[str, list[str]]:
    area_label = AREA_LABEL_KO.get(area, area)
    summary = f"{area_label}에 있는 {category_label} 장소다."
    note_template = f"{{place_name}}은(는) {area_label} 일정에 넣을 수 있는 {category_label} 장소예요."
    return summary, [note_template]


def row_to_place_data(row: dict[str, str]) -> dict:
    activity_type = [value.strip() for value in row["activity_type"].split("|") if value.strip()]
    confidence = row["confidence"].strip().lower()
    priority = PRIORITY_BY_CONFIDENCE[confidence]
    average_cost_krw = _resolve_average_cost_krw(row)
    area = row["area_suggestion"].strip()
    name = row["name"].strip()
    setting = row["setting"].strip()

    place: dict = {
        "id": row["id"].strip(),
        "name": name,
        "activity_type": activity_type,
        "budget_level": _budget_level(average_cost_krw),
        "suitable_for": list(DEFAULT_SUITABLE_FOR),
        "time_fit": _time_fit(row["open_hours"]),
        "area": area,
        "duration_hours": DEFAULT_DURATION_HOURS,
        "priority": priority,
        "pace": list(DEFAULT_PACE),
        "mobility": list(DEFAULT_MOBILITY),
        "latitude": _parse_optional_float(row["latitude"]),
        "longitude": _parse_optional_float(row["longitude"]),
        "average_cost_krw": average_cost_krw,
        "content_id": row["content_id"].strip() or None,
        "open_hours": row["open_hours"].strip() or None,
        "closed_days": row["closed_days"].strip() or None,
        "setting": setting or None,
        "rain_sensitive_light": _rain_sensitive_light(setting, name),
        "is_active": True,
    }
    summary, note_templates = _summary_and_note_templates(name, area, activity_type[0])
    place["summary"] = summary
    place["note_templates"] = note_templates
    if confidence in MVP_TIER_BY_CONFIDENCE:
        place["mvp_tier"] = MVP_TIER_BY_CONFIDENCE[confidence]
    return place


def load_rows() -> tuple[list[dict], list[dict]]:
    """Returns (usable_rows, skipped_rows)."""
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    usable = [row for row in rows if row["latitude"].strip() and row["longitude"].strip()]
    skipped = [row for row in rows if not (row["latitude"].strip() and row["longitude"].strip())]
    return usable, skipped


def merge_rows_into_catalog(catalog: dict, rows: list[dict]) -> tuple[int, int]:
    """Pure core of merge() - mutates catalog["places"] in place and
    returns (added_count, already_merged_count). No file I/O, so this is
    what the idempotency/dedup behavior is unit-tested against."""
    existing_ids = {place["id"] for place in catalog["places"]}

    seen_this_run: set[str] = set()
    new_places = []
    already_merged_count = 0
    for row in rows:
        place = row_to_place_data(row)
        if place["id"] in seen_this_run:
            raise ValueError(f"duplicate id within the CSV itself: {place['id']!r}")
        seen_this_run.add(place["id"])
        if place["id"] in existing_ids:
            already_merged_count += 1
            continue
        new_places.append(place)
        existing_ids.add(place["id"])

    catalog["places"].extend(new_places)
    return len(new_places), already_merged_count


def merge() -> tuple[int, int, list[str]]:
    json_path = DESTINATIONS_DIR / f"{CITY}.json"
    with json_path.open(encoding="utf-8") as f:
        catalog = json.load(f)

    usable_rows, skipped_rows = load_rows()
    added_count, already_merged_count = merge_rows_into_catalog(catalog, usable_rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    skipped_names = [row["name"] for row in skipped_rows]
    return added_count, already_merged_count, skipped_names


def main() -> None:
    added_count, already_merged_count, skipped_names = merge()
    print(
        f"{CITY}: added {added_count} places, "
        f"{already_merged_count} already merged (skipped), "
        f"{len(skipped_names)} skipped (no coordinates)"
    )
    for name in skipped_names:
        print(f"  - skipped (no coordinates): {name}")


if __name__ == "__main__":
    main()
