"""Applies local_only/data/jeju_places_text_batch1.csv's hand-written text
(summary/note_template/highlight_tags) onto the 24 Jeju places merged by
scripts/merge_jeju_places.py (PR #88), replacing the placeholder sentences
that script generated ("서귀포 서부에 있는 자연·트레킹 장소다." etc.).

Only summary/note_templates/highlight_tags are touched - every other
field (area, coordinates, cost, hours, ...) and every other place
(the original 65, Seoul, Busan) is left exactly as-is.

All-or-nothing: any validation problem (see validate_rows()) aborts
before writing anything, rather than applying a partial update. Re-running
with the same CSV is a no-op (idempotent) - it just re-sets the same
values.

Usage: python scripts/apply_jeju_place_text.py
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

CSV_PATH = LOCAL_DATA_DIR / "jeju_places_text_batch1.csv"
CITY = "jeju"

REQUIRED_COLUMNS = ("id", "name", "summary", "note_template", "highlight_tags")
PLACEHOLDER_PATTERN = re.compile(r"\{[^}]*\}")
ALLOWED_PLACEHOLDER = "{place_name}"


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate_rows(rows: list[dict[str, str]], existing_ids: set[str]) -> list[str]:
    """Returns a list of error messages - empty means the CSV is safe to
    apply. Never raises on its own; the caller decides what to do with a
    non-empty list (see main())."""
    errors: list[str] = []

    seen_ids: dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):  # header is row 1
        for column in REQUIRED_COLUMNS:
            if not row.get(column, "").strip():
                errors.append(f"row {row_number} ({row.get('id') or '?'}): blank '{column}'")

        row_id = row.get("id", "").strip()
        if row_id:
            if row_id in seen_ids:
                errors.append(f"row {row_number}: duplicate id {row_id!r} (also row {seen_ids[row_id]})")
            else:
                seen_ids[row_id] = row_number

            if row_id not in existing_ids:
                errors.append(f"row {row_number}: id {row_id!r} not found in {CITY}.json")

        note_template = row.get("note_template", "")
        placeholders = set(PLACEHOLDER_PATTERN.findall(note_template))
        disallowed = placeholders - {ALLOWED_PLACEHOLDER}
        if disallowed:
            errors.append(f"row {row_number} ({row_id}): note_template has disallowed placeholder(s) {sorted(disallowed)}")

        summary_placeholders = set(PLACEHOLDER_PATTERN.findall(row.get("summary", "")))
        if summary_placeholders:
            errors.append(f"row {row_number} ({row_id}): summary must not contain placeholders, found {sorted(summary_placeholders)}")

    return errors


def apply_rows(catalog: dict, rows: list[dict[str, str]]) -> int:
    """Pure core (no file I/O) - mutates catalog["places"] in place and
    returns how many places were updated. Callers must validate first;
    this assumes every row's id already exists in catalog."""
    by_id = {place["id"]: place for place in catalog["places"]}
    updated = 0
    for row in rows:
        place = by_id[row["id"].strip()]
        place["summary"] = row["summary"].strip()
        place["note_templates"] = [row["note_template"].strip()]
        place["highlight_tags"] = [tag.strip() for tag in row["highlight_tags"].split("|") if tag.strip()]
        updated += 1
    return updated


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

    updated_count = apply_rows(catalog, rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{CITY}: updated summary/note_templates/highlight_tags on {updated_count} places")


if __name__ == "__main__":
    main()
