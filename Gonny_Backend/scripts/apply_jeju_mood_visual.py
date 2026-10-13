"""Applies local_only/data/jeju_mood_visual_batch1.csv's evidence-based
mood/visual_feature values to 3 of the 24 Jeju places merged by
scripts/merge_jeju_places.py. The other 21 have no textual evidence for
either field and are deliberately left as [] - guessing one would violate
this project's "no unsupported inference" principle (same rule
scripts/merge_jeju_places.py's own docstring states for mood/
visual_feature/mood_keywords/highlight_tags).

Same spirit as scripts/tag_restaurant_mood_visual.py (every value is
checked against real evidence text, nothing bulk-inferred, mood/
visual_feature stay within the fixed 활기참/조용함/포토스팟/야경
vocabulary) - this one reads that evidence from a CSV instead of being
hardcoded, since a vocabulary violation needs to be caught
programmatically (see [Constraints]), not just avoided by hand.

mood/visual_feature values and their evidence (verbatim from the CSV,
kept here too so the reasoning survives even if local_only/ changes):

- saeyeongyo-saeseom (새연교·새섬) -> visual_feature: 야경, 포토스팟
  evidence: "이 야경이 아름다운 다리는 '새연교'로 제주 유명 명소 중 한
  곳이다. / 테마 포토존 등 다양한 편의시설이 꾸며졌다. / 화려한 LED
  조명시설까지 갖췄다." (mood 칸은 CSV에 값이 없어 비워 둔다)
  source: https://www.ktriptips.com/kor/tourspot/879234 (confidence: high)

- jeju-mokgwana (제주목관아) -> visual_feature: 야경
  evidence: "[야간 개장] 수요일~일요일 18:00~21:00 / ※ 야간 개장 무료
  입장 (5월~10월)" (mood 칸은 CSV에 값이 없어 비워 둔다)
  source: https://www.ktriptips.com/kor/tourspot/128641 (confidence: medium)

- namwon-keuneong (남원큰엉해안) -> mood: 조용함
  evidence: "갯바위 낚시터로, 조용한 휴식처로, 연인들의 데이트 코스로도
  유명하다." (visual_feature 칸은 CSV에 값이 없어 비워 둔다)
  source: https://www.ktriptips.com/kor/tourspot/128795 (confidence: medium)

Idempotent and all-or-nothing: any vocabulary violation, blank/duplicate
id, or unknown id aborts before writing anything (same pattern as
scripts/apply_jeju_place_text.py). A field (mood or visual_feature) that
already holds a non-empty value is never overwritten - it's skipped and
reported instead, so re-running with the same CSV always ends in the same
state. A blank CSV cell is left untouched, not written as [] - see
apply_rows().

Usage: python scripts/apply_jeju_mood_visual.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
LOCAL_DATA_DIR = PROJECT_ROOT / "local_only" / "data"

CSV_PATH = LOCAL_DATA_DIR / "jeju_mood_visual_batch1.csv"
CITY = "jeju"

ALLOWED_MOOD = {"활기참", "조용함"}
ALLOWED_VISUAL_FEATURE = {"포토스팟", "야경"}
EDITABLE_FIELDS = ("mood", "visual_feature")


def _parse_values(raw: str) -> list[str]:
    return [value.strip() for value in raw.split("|") if value.strip()]


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate_rows(rows: list[dict[str, str]], existing_ids: set[str]) -> list[str]:
    """Returns a list of error messages - empty means safe to apply."""
    errors: list[str] = []
    seen_ids: dict[str, int] = {}

    for row_number, row in enumerate(rows, start=2):  # header is row 1
        row_id = row.get("id", "").strip()
        if not row_id:
            errors.append(f"row {row_number}: blank id")
            continue

        if row_id in seen_ids:
            errors.append(f"row {row_number}: duplicate id {row_id!r} (also row {seen_ids[row_id]})")
        else:
            seen_ids[row_id] = row_number

        if row_id not in existing_ids:
            errors.append(f"row {row_number}: id {row_id!r} not found in {CITY}.json")

        mood_values = _parse_values(row.get("mood", ""))
        visual_values = _parse_values(row.get("visual_feature", ""))
        bad_mood = [value for value in mood_values if value not in ALLOWED_MOOD]
        bad_visual = [value for value in visual_values if value not in ALLOWED_VISUAL_FEATURE]
        if bad_mood:
            errors.append(f"row {row_number} ({row_id}): mood value(s) outside allowed vocabulary: {bad_mood}")
        if bad_visual:
            errors.append(
                f"row {row_number} ({row_id}): visual_feature value(s) outside allowed vocabulary: {bad_visual}"
            )

    return errors


def apply_rows(catalog: dict, rows: list[dict[str, str]]) -> tuple[dict[str, list[str]], list[tuple[str, str, list]]]:
    """Pure core (no file I/O) - mutates catalog["places"] in place.

    Returns (applied, skipped):
      applied: place_id -> list of fields actually written this run.
      skipped: list of (place_id, field, existing_value) for fields left
      untouched because they already held a non-empty value.

    Assumes every row's id already exists in catalog (validate_rows()
    must be called first)."""
    by_id = {place["id"]: place for place in catalog["places"]}
    applied: dict[str, list[str]] = {}
    skipped: list[tuple[str, str, list]] = []

    for row in rows:
        place = by_id[row["id"].strip()]
        for field in EDITABLE_FIELDS:
            csv_values = _parse_values(row.get(field, ""))
            if not csv_values:
                continue  # blank CSV cell - leave this field untouched

            existing_values = place.get(field) or []
            if existing_values:
                skipped.append((place["id"], field, existing_values))
                continue

            place[field] = csv_values
            applied.setdefault(place["id"], []).append(field)

    return applied, skipped


def main() -> None:
    json_path = DESTINATIONS_DIR / f"{CITY}.json"
    with json_path.open(encoding="utf-8") as f:
        catalog = json.load(f)
    existing_ids = {place["id"] for place in catalog["places"]}

    rows = load_rows()
    errors = validate_rows(rows, existing_ids)
    if errors:
        print(f"{len(errors)} error(s) found - no changes applied:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    applied, skipped = apply_rows(catalog, rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{CITY}: applied fields on {len(applied)} place(s)")
    for place_id, fields in applied.items():
        print(f"  - {place_id}: {fields}")
    if skipped:
        print(f"skipped (already had a non-empty value): {len(skipped)}")
        for place_id, field, existing_values in skipped:
            print(f"  - {place_id}.{field} already = {existing_values}")


if __name__ == "__main__":
    main()
