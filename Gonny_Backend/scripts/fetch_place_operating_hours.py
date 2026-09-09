from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

# On Windows, stdout defaults to the console codepage (cp949) rather than
# UTF-8 when redirected to a file, corrupting Korean output. Force UTF-8
# explicitly so `python fetch_place_operating_hours.py > log.txt` is readable.
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings
from app.domains.rule_planner.services.constants import PLACE_NAME_KO
from app.services.external_clients import (
    DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE,
    TOUR_API_ADDRESS_PREFIX_BY_CITY,
    TourApiClient,
)

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
ENV_FILE = REPO_ROOT / ".env"
REQUEST_INTERVAL_SECONDS = 0.2  # be polite to the public API rate limit
MAX_RETRIES_ON_API_ERROR = 5
RETRY_BACKOFF_SECONDS = 2.0


def load_tour_api_key_from_env_file() -> str | None:
    """Scripts don't run through docker-compose's env_file loading, so read
    TOUR_API_KEY out of the repo-root .env directly. This is a one-off
    bootstrap for this script only - not a general dotenv loader."""
    if not ENV_FILE.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def find_coordinates_with_retry(client: TourApiClient, search_name: str, city: str, activity_types: list[str]):
    """Retries only on "api_error" (network/HTTP/parse failure) - a
    genuine "not_found"/"ambiguous" result is never retried since retrying
    won't change a real naming conflict."""
    status = "api_error"
    latitude = longitude = content_id = content_type_id = None
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        latitude, longitude, content_id, content_type_id, status = client.find_place_coordinates(
            search_name, city, activity_types
        )
        if status != "api_error":
            return latitude, longitude, content_id, content_type_id, status
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return latitude, longitude, content_id, content_type_id, status


def fetch_hours_with_retry(client: TourApiClient, content_id: str, content_type_id: str):
    status = "api_error"
    open_hours = closed_days = None
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        open_hours, closed_days, status = client.fetch_place_operating_hours(content_id, content_type_id)
        if status != "api_error":
            return open_hours, closed_days, status
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return open_hours, closed_days, status


def process_city(client: TourApiClient, city: str) -> tuple[dict, list[dict], Counter]:
    path = DESTINATIONS_DIR / f"{city}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    unresolved: list[dict] = []
    content_type_counts: Counter = Counter()

    for place in payload["places"]:
        # place["name"] is sometimes an English/romanized identifier
        # (e.g. "Gyeongbokgung Palace"); PLACE_NAME_KO holds the Korean
        # display name TourAPI's titles are actually written in.
        search_name = PLACE_NAME_KO.get(place["id"], place["name"])
        activity_types = place.get("activity_type", [])
        latitude, longitude, content_id, content_type_id, status = find_coordinates_with_retry(
            client, search_name, city, activity_types
        )
        time.sleep(REQUEST_INTERVAL_SECONDS)

        if status != "ok" or not content_id:
            unresolved.append({"city": city, "id": place["id"], "name": place["name"], "reason": status})
            continue

        # Coordinates were already saved in a previous round for most
        # places; re-derive them here too so this script is self-contained
        # and this re-search naturally also backfills content_id for them.
        place["latitude"] = latitude
        place["longitude"] = longitude
        place["content_id"] = content_id
        content_type_counts[content_type_id or "unknown"] += 1

        open_hours, closed_days, hours_status = fetch_hours_with_retry(client, content_id, content_type_id or "")
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if hours_status == "ok":
            place["open_hours"] = open_hours
            place["closed_days"] = closed_days
        else:
            unresolved.append(
                {"city": city, "id": place["id"], "name": place["name"], "reason": f"hours_{hours_status}"}
            )

    return payload, unresolved, content_type_counts


def save_city_catalog(city: str, payload: dict) -> None:
    path = DESTINATIONS_DIR / f"{city}.json"
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> None:
    api_key = load_tour_api_key_from_env_file()
    if not api_key:
        print("TOUR_API_KEY not found in .env - aborting without touching any files.")
        return

    settings = Settings(tour_api_key=api_key)
    client = TourApiClient(settings)

    all_unresolved: list[dict] = []
    total_content_type_counts: Counter = Counter()
    content_id_count = 0
    hours_count = 0
    total_count = 0

    for city in TOUR_API_ADDRESS_PREFIX_BY_CITY:
        payload, unresolved, content_type_counts = process_city(client, city)
        places = payload["places"]
        total_count += len(places)
        content_id_count += sum(1 for place in places if place.get("content_id"))
        hours_count += sum(1 for place in places if place.get("open_hours") or place.get("closed_days"))
        total_content_type_counts.update(content_type_counts)
        all_unresolved.extend(unresolved)
        save_city_catalog(city, payload)
        city_content_ids = sum(1 for place in places if place.get("content_id"))
        print(f"{city}: content_id {city_content_ids}/{len(places)}")

    print(f"\nTotal content_id resolved: {content_id_count}/{total_count}")
    print(f"Total with open_hours or closed_days populated: {hours_count}/{total_count}")

    print("\ncontentTypeId distribution among resolved places:")
    for content_type_id, count in sorted(total_content_type_counts.items(), key=lambda item: -item[1]):
        mapped = "mapped" if content_type_id in DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE else "NOT mapped"
        print(f"  {content_type_id}: {count} ({mapped})")

    if all_unresolved:
        print(f"\n{len(all_unresolved)} unresolved place(s):")
        for item in all_unresolved:
            print(f"  - [{item['city']}] {item['id']} ({item['name']}) - {item['reason']}")


if __name__ == "__main__":
    main()
