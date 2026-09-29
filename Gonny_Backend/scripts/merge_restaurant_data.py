"""Merges the researched-restaurant CSVs (local_only/data/*_restaurants_geocoded.csv)
into app/data/destinations/{city}.json as new PlaceData entries.

Reproducible, deterministic mapping - re-run any time the CSVs change
(e.g. once the 25 currently-ungeocoded rows get coordinates). Rows without
both latitude and longitude are skipped (see SKIPPED_UNGEOCODED_LOG below
for what got skipped on the run that produced the committed JSON).

Usage: python scripts/merge_restaurant_data.py
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

CITIES = ["seoul", "busan", "jeju"]

PRIORITY_BY_CONFIDENCE = {"high": 8, "medium": 6, "low": 4}
MVP_TIER_BY_CONFIDENCE = {"high": "core"}  # medium/low keep the schema default ("standard")

# Substring markers checked across cuisine + rating_summary + evidence_note
# (combined, since a "무한리필"/"오마카세" cue can show up in any of the
# three columns depending on how the row was written up).
CHEAP_MARKERS = ["노포", "무한리필", "가성비"]
EXPENSIVE_MARKERS = ["미쉐린", "오마카세"]

# Cuisine-only substring markers for a lunch-leaning time_fit - noodle/
# brunch/kimbap-style dishes people commonly eat at lunch, not just dinner.
LUNCH_LEANING_CUISINE_MARKERS = ["냉면", "국수", "분식", "브런치"]


def _budget_level(search_text: str) -> list[str]:
    if any(marker in search_text for marker in EXPENSIVE_MARKERS):
        return ["medium", "high"]
    if any(marker in search_text for marker in CHEAP_MARKERS):
        return ["low", "medium"]
    return ["medium"]


def _time_fit(cuisine: str) -> list[str]:
    if any(marker in cuisine for marker in LUNCH_LEANING_CUISINE_MARKERS):
        return ["afternoon", "evening"]
    return ["evening"]


def _parse_optional_float(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    return int(float(value)) if value else None


def row_to_place_data(row: dict[str, str]) -> dict:
    combined_text = f"{row['cuisine']} {row['rating_summary']} {row['evidence_note']}"
    confidence = row["confidence"].strip().lower()
    priority = PRIORITY_BY_CONFIDENCE[confidence]

    place: dict = {
        "id": row["id"].strip(),
        "name": row["name"].strip(),
        "activity_type": ["미식"],
        "budget_level": _budget_level(combined_text),
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": _time_fit(row["cuisine"]),
        "area": row["area"].strip(),
        "duration_hours": 1,
        "priority": priority,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": row["evidence_note"].strip(),
        "latitude": _parse_optional_float(row["latitude"]),
        "longitude": _parse_optional_float(row["longitude"]),
        "google_rating": _parse_optional_float(row["google_rating"]),
        "google_rating_count": _parse_optional_int(row["google_rating_count"]),
        "is_active": True,
    }
    if confidence in MVP_TIER_BY_CONFIDENCE:
        place["mvp_tier"] = MVP_TIER_BY_CONFIDENCE[confidence]
    return place


def load_geocoded_rows(city: str) -> tuple[list[dict], list[dict]]:
    """Returns (geocoded_rows, skipped_rows) for one city's CSV."""
    csv_path = LOCAL_DATA_DIR / f"{city}_restaurants_geocoded.csv"
    with csv_path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    geocoded = [row for row in rows if row["latitude"].strip() and row["longitude"].strip()]
    skipped = [row for row in rows if not (row["latitude"].strip() and row["longitude"].strip())]
    return geocoded, skipped


def merge_city(city: str) -> tuple[int, list[str]]:
    json_path = DESTINATIONS_DIR / f"{city}.json"
    with json_path.open(encoding="utf-8") as f:
        catalog = json.load(f)

    existing_ids = {place["id"] for place in catalog["places"]}
    geocoded_rows, skipped_rows = load_geocoded_rows(city)

    new_places = []
    for row in geocoded_rows:
        place = row_to_place_data(row)
        if place["id"] in existing_ids:
            raise ValueError(f"id collision in {city}: {place['id']!r} already exists in {json_path}")
        new_places.append(place)
        existing_ids.add(place["id"])

    catalog["places"].extend(new_places)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    skipped_names = [row["name"] for row in skipped_rows]
    return len(new_places), skipped_names


def main() -> None:
    total_added = 0
    for city in CITIES:
        added_count, skipped_names = merge_city(city)
        total_added += added_count
        print(f"{city}: added {added_count} restaurants, skipped {len(skipped_names)} (no coordinates)")
        for name in skipped_names:
            print(f"  - skipped (ungeocoded): {name}")

    print(f"\ntotal restaurants merged: {total_added}")


if __name__ == "__main__":
    main()
