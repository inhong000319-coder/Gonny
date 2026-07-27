from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
THEME_LABELING_DIR = PROJECT_ROOT / "local_only" / "data" / "theme_labeling"
TARGET_CITIES = ("seoul", "busan", "jeju")

INITIAL_LABEL_FILES = [
    THEME_LABELING_DIR / "pilot_seoul_8곳.csv",
    THEME_LABELING_DIR / "batch1_seoul_busan_jeju_40곳.csv",
]
BATCH2_LABEL_FILE = THEME_LABELING_DIR / "theme_labeling_batch2_신규56곳.csv"

EXPECTED_INITIAL_LABEL_COUNTS = {"seoul": 21, "busan": 13, "jeju": 14}
EXPECTED_BATCH2_LABEL_COUNTS = {"seoul": 30, "busan": 14, "jeju": 12}

REMOVE_FROM_ACTIVITY_TYPE = {"photo", "family"}
ALLOWED_KOREAN_ACTIVITY_TYPES = {
    "자연·트레킹",
    "액티비티",
    "문화·역사",
    "쇼핑",
    "미식",
    "휴양·힐링",
    "온천",
    "나이트라이프",
}
ENGLISH_TO_KOREAN_ACTIVITY_TYPE_MAP = {
    "sightseeing": "문화·역사",
    "culture": "문화·역사",
    "food": "미식",
    "shopping": "쇼핑",
    "relax": "휴양·힐링",
    "nature": "자연·트레킹",
    "activity": "액티비티",
    "nightlife": "나이트라이프",
    "local_experience": "문화·역사",
}

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


def order_place_fields(place: dict) -> dict:
    ordered: dict = {}
    for key in PLACE_FIELD_ORDER:
        if key in place:
            ordered[key] = place[key]
    for key, value in place.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def load_initial_labels() -> dict[tuple[str, str], dict[str, list[str]]]:
    labels: dict[tuple[str, str], dict[str, list[str]]] = {}
    counts: Counter[str] = Counter()

    for path in INITIAL_LABEL_FILES:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                city = row["city"].strip().lower()
                place_id = row["place_id"].strip()
                key = (city, place_id)
                if key in labels:
                    raise ValueError(f"Duplicate initial label row detected for {city}:{place_id}")
                labels[key] = {
                    "activity_type": split_csv_values(row["activity_type"]),
                    "mood": split_csv_values(row["mood"]),
                    "mood_evening_override": split_csv_values(row["mood_evening_override"]),
                    "visual_feature": split_csv_values(row["visual_feature"]),
                }
                counts[city] += 1

    if dict(counts) != EXPECTED_INITIAL_LABEL_COUNTS:
        raise ValueError(f"Unexpected initial labeled place counts: {dict(counts)}")

    return labels


def load_batch2_labels() -> dict[tuple[str, str], dict[str, list[str]]]:
    labels: dict[tuple[str, str], dict[str, list[str]]] = {}
    counts: Counter[str] = Counter()

    with BATCH2_LABEL_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            city = row["city"].strip().lower()
            place_id = row["place_id"].strip()
            key = (city, place_id)
            if key in labels:
                raise ValueError(f"Duplicate batch2 label row detected for {city}:{place_id}")
            labels[key] = {
                "mood": split_csv_values(row["mood"]),
                "mood_evening_override": split_csv_values(row["mood_evening_override"]),
                "visual_feature": split_csv_values(row["visual_feature"]),
            }
            counts[city] += 1

    if dict(counts) != EXPECTED_BATCH2_LABEL_COUNTS:
        raise ValueError(f"Unexpected batch2 labeled place counts: {dict(counts)}")

    return labels


def transform_place_for_initial_migration(
    city: str,
    place: dict,
    labels: dict[tuple[str, str], dict[str, list[str]]],
) -> tuple[dict, bool]:
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
        mood = list(place.get("mood", [])) if "category" not in place else []
        mood_evening_override = list(place.get("mood_evening_override", [])) if "category" not in place else []
        visual_feature = list(place.get("visual_feature", [])) if "category" not in place else []
        used_label = False

    transformed = dict(place)
    transformed.pop("category", None)
    transformed["activity_type"] = activity_type
    transformed["mood"] = mood
    transformed["mood_evening_override"] = mood_evening_override
    transformed["visual_feature"] = visual_feature
    return order_place_fields(transformed), used_label


def all_korean_activity_types(values: list[str]) -> bool:
    return all(value in ALLOWED_KOREAN_ACTIVITY_TYPES for value in values)


def convert_activity_types_to_korean(values: list[str]) -> tuple[list[str], bool]:
    converted: list[str] = []
    for value in values:
        if value in ALLOWED_KOREAN_ACTIVITY_TYPES:
            mapped = value
        else:
            mapped = ENGLISH_TO_KOREAN_ACTIVITY_TYPE_MAP.get(value)
            if mapped is None:
                raise ValueError(f"Unexpected activity_type value for batch2 conversion: {value}")
        if mapped not in converted:
            converted.append(mapped)
    return converted, len(converted) != len(values)


def load_head_catalog_payloads() -> dict[Path, dict]:
    payloads: dict[Path, dict] = {}
    for city in TARGET_CITIES:
        path = DESTINATIONS_DIR / f"{city}.json"
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = subprocess.check_output(
                ["git", "show", f"HEAD:{relative_path}"],
                text=True,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError:
            continue
        payloads[path] = json.loads(text)
    return payloads


def apply_batch2_updates(
    city: str,
    place: dict,
    labels: dict[tuple[str, str], dict[str, list[str]]],
    head_place: dict | None,
) -> tuple[dict, bool, dict | None]:
    label = labels.get((city, str(place.get("id", "")).strip()))
    if label is None:
        return place, False, None

    transformed = dict(place)
    original_activity_type = list(transformed.get("activity_type", []))
    converted_activity_type, had_dedup_loss = convert_activity_types_to_korean(original_activity_type)
    evidence_source = original_activity_type

    if (
        not had_dedup_loss
        and all_korean_activity_types(original_activity_type)
        and head_place is not None
        and head_place.get("activity_type") != original_activity_type
    ):
        head_activity_type = list(head_place.get("activity_type", []))
        _, had_dedup_loss = convert_activity_types_to_korean(head_activity_type)
        if had_dedup_loss:
            evidence_source = head_activity_type

    transformed["activity_type"] = converted_activity_type
    transformed["mood"] = list(label["mood"])
    transformed["mood_evening_override"] = list(label["mood_evening_override"])
    transformed["visual_feature"] = list(label["visual_feature"])

    evidence = None
    if had_dedup_loss:
        evidence = {
            "city": city,
            "place_id": transformed["id"],
            "before": evidence_source,
            "after": converted_activity_type,
        }

    return order_place_fields(transformed), True, evidence


def load_catalog_payloads() -> dict[Path, dict]:
    payloads: dict[Path, dict] = {}
    for city in TARGET_CITIES:
        path = DESTINATIONS_DIR / f"{city}.json"
        with path.open("r", encoding="utf-8") as file:
            payloads[path] = json.load(file)
    return payloads


def verify_batch2_results(
    payloads: dict[Path, dict],
    batch2_labels: dict[tuple[str, str], dict[str, list[str]]],
    matched_batch2_keys: set[tuple[str, str]],
) -> None:
    if matched_batch2_keys != set(batch2_labels):
        missing_keys = sorted(set(batch2_labels) - matched_batch2_keys)
        raise ValueError(f"Batch2 place_id not found in JSON catalogs: {missing_keys}")

    for path, payload in payloads.items():
        city = str(payload.get("city", path.stem)).strip().lower()
        for place in payload.get("places", []):
            key = (city, place["id"])
            if key not in batch2_labels:
                continue

            expected = batch2_labels[key]
            actual = {
                "mood": place.get("mood", []),
                "mood_evening_override": place.get("mood_evening_override", []),
                "visual_feature": place.get("visual_feature", []),
            }
            if actual != expected:
                raise ValueError(f"Batch2 label mismatch for {city}:{place['id']} => {actual} != {expected}")

            english_residue = [
                value for value in place.get("activity_type", []) if value not in ALLOWED_KOREAN_ACTIVITY_TYPES
            ]
            if english_residue:
                raise ValueError(
                    f"English activity_type residue found for {city}:{place['id']} => {english_residue}"
                )


def write_payloads(payloads: dict[Path, dict]) -> None:
    for path, payload in payloads.items():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate() -> None:
    initial_labels = load_initial_labels()
    batch2_labels = load_batch2_labels()
    payloads = load_catalog_payloads()
    head_payloads = load_head_catalog_payloads()

    initial_label_counts: Counter[str] = Counter()
    batch2_label_counts: Counter[str] = Counter()
    matched_batch2_keys: set[tuple[str, str]] = set()
    dedup_evidence: list[dict] = []

    for path, payload in payloads.items():
        city = str(payload.get("city", path.stem)).strip().lower()
        head_places = {
            place["id"]: place for place in head_payloads.get(path, {}).get("places", [])
        }
        transformed_places: list[dict] = []

        for place in payload.get("places", []):
            transformed_place, used_initial_label = transform_place_for_initial_migration(
                city=city,
                place=place,
                labels=initial_labels,
            )
            if used_initial_label:
                initial_label_counts[city] += 1

            transformed_place, used_batch2_label, evidence = apply_batch2_updates(
                city=city,
                place=transformed_place,
                labels=batch2_labels,
                head_place=head_places.get(transformed_place["id"]),
            )
            if used_batch2_label:
                batch2_label_counts[city] += 1
                matched_batch2_keys.add((city, transformed_place["id"]))
            if evidence is not None:
                dedup_evidence.append(evidence)

            transformed_places.append(transformed_place)

        payload["places"] = transformed_places

    if dict(initial_label_counts) != EXPECTED_INITIAL_LABEL_COUNTS:
        raise ValueError(f"Unexpected applied initial label counts: {dict(initial_label_counts)}")
    if dict(batch2_label_counts) != EXPECTED_BATCH2_LABEL_COUNTS:
        raise ValueError(f"Unexpected applied batch2 label counts: {dict(batch2_label_counts)}")

    verify_batch2_results(payloads, batch2_labels, matched_batch2_keys)
    write_payloads(payloads)

    print(f"Initial theme labels applied for {sum(initial_label_counts.values())} places.")
    print(f"Batch2 labels applied for {sum(batch2_label_counts.values())} places.")
    print(f"Initial counts by city: {dict(initial_label_counts)}")
    print(f"Batch2 counts by city: {dict(batch2_label_counts)}")
    print(f"Batch2 dedup evidence count: {len(dedup_evidence)}")
    for evidence in dedup_evidence:
        print("BATCH2_DEDUP", json.dumps(evidence, ensure_ascii=True))


if __name__ == "__main__":
    migrate()
