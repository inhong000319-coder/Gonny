from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
LABEL_FILES = [
    PROJECT_ROOT / "local_only" / "data" / "theme_labeling" / "pilot_seoul_8곳.csv",
    PROJECT_ROOT / "local_only" / "data" / "theme_labeling" / "batch1_seoul_busan_jeju_40곳.csv",
]
EXPECTED_LABEL_COUNTS = {"seoul": 21, "busan": 13, "jeju": 14}
REMOVE_FROM_ACTIVITY_TYPE = {"photo", "family"}
PLACE_FIELD_ORDER = [
    "id",
    "name",
    "activity_type",
    "mood",
    "mood_evening_override",
    "visual_feature",
    "budget_level",
    "suitable_for",
    "time_fit",
    "area",
    "duration_hours",
    "priority",
    "pace",
    "mobility",
    "summary",
    "official_url",
    "booking_hint",
    "is_active",
    "mvp_tier",
    "full_day_recommended",
    "full_day_notes",
    "slot_bias",
    "mood_keywords",
    "highlight_tags",
    "note_templates",
]


def split_csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_labels() -> dict[tuple[str, str], dict[str, list[str] | str]]:
    labels: dict[tuple[str, str], dict[str, list[str] | str]] = {}
    counts: Counter[str] = Counter()

    for path in LABEL_FILES:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                city = row["city"].strip().lower()
                place_id = row["place_id"].strip()
                key = (city, place_id)
                if key in labels:
                    raise ValueError(f"Duplicate label row detected for {city}:{place_id}")
                labels[key] = {
                    "activity_type": split_csv_values(row["activity_type"]),
                    "mood": split_csv_values(row["mood"]),
                    "mood_evening_override": split_csv_values(row["mood_evening_override"]),
                    "visual_feature": split_csv_values(row["visual_feature"]),
                }
                counts[city] += 1

    if dict(counts) != EXPECTED_LABEL_COUNTS:
        raise ValueError(f"Unexpected labeled place counts: {dict(counts)}")

    return labels


def transform_place(city: str, place: dict, labels: dict[tuple[str, str], dict[str, list[str] | str]]) -> tuple[dict, bool]:
    label = labels.get((city, str(place.get("id", "")).strip()))
    if label is not None:
        activity_type = list(label["activity_type"])
        mood = list(label["mood"])
        mood_evening_override = list(label["mood_evening_override"])
        visual_feature = list(label["visual_feature"])
        used_label = True
    else:
        source_activity_type = place.get("category", place.get("activity_type", []))
        activity_type = [value for value in source_activity_type if value not in REMOVE_FROM_ACTIVITY_TYPE]
        mood = []
        mood_evening_override = []
        visual_feature = []
        used_label = False

    transformed = dict(place)
    transformed.pop("category", None)
    transformed["activity_type"] = activity_type
    transformed["mood"] = mood
    transformed["mood_evening_override"] = mood_evening_override
    transformed["visual_feature"] = visual_feature

    ordered: dict = {}
    for key in PLACE_FIELD_ORDER:
        if key in transformed:
            ordered[key] = transformed[key]
    for key, value in transformed.items():
        if key not in ordered:
            ordered[key] = value

    return ordered, used_label


def migrate() -> None:
    labels = load_labels()
    labeled_counts: Counter[str] = Counter()

    for path in sorted(DESTINATIONS_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        city = str(payload.get("city", path.stem)).strip().lower()
        places = payload.get("places", [])
        transformed_places: list[dict] = []

        for place in places:
            transformed_place, used_label = transform_place(city, place, labels)
            transformed_places.append(transformed_place)
            if used_label:
                labeled_counts[city] += 1

        payload["places"] = transformed_places

        with path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")

    if dict(labeled_counts) != EXPECTED_LABEL_COUNTS:
        raise ValueError(f"Unexpected applied label counts: {dict(labeled_counts)}")

    print(f"Migrated theme axes for {sum(labeled_counts.values())} labeled places.")
    print(f"Applied counts by city: {dict(labeled_counts)}")


if __name__ == "__main__":
    migrate()
