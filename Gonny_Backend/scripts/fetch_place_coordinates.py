from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

# On Windows, stdout defaults to the console codepage (cp949) rather than
# UTF-8 when redirected to a file, corrupting Korean output. Force UTF-8
# explicitly so `python fetch_place_coordinates.py > log.txt` is readable.
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings
from app.domains.rule_planner.services.constants import PLACE_NAME_KO
from app.services.external_clients import TOUR_API_ADDRESS_PREFIX_BY_CITY, TourApiClient

DESTINATIONS_DIR = PROJECT_ROOT / "app" / "data" / "destinations"
ENV_FILE = REPO_ROOT / ".env"
REQUEST_INTERVAL_SECONDS = 0.2  # be polite to the public API rate limit
MAX_RETRIES_ON_API_ERROR = 3
RETRY_BACKOFF_SECONDS = 2.0


def load_tour_api_key_from_env_file() -> str | None:
    """Scripts don't run through docker-compose's env_file loading, so read
    TOUR_API_KEY out of the repo-root .env directly. This is a one-off
    bootstrap for this script only - not a general dotenv loader."""
    if not ENV_FILE.exists():
        return None
    match = re.search(r"^TOUR_API_KEY=(.*)$", ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() or None if match else None


def find_coordinates_with_retry(
    client: TourApiClient, search_name: str, city: str, activity_types: list[str]
) -> tuple[float | None, float | None, str]:
    """Retries only on "api_error" (network/HTTP/parse failure) - a
    genuine "not_found"/"ambiguous" result is never retried since retrying
    won't change a real naming conflict.

    This script only needs coordinates - content_id/content_type_id
    (also returned by find_place_coordinates now) are discarded here; see
    scripts/fetch_place_operating_hours.py, which uses them to fetch
    open_hours/closed_days in the same pass.
    """
    status = "api_error"
    latitude = longitude = None
    for attempt in range(MAX_RETRIES_ON_API_ERROR):
        latitude, longitude, _content_id, _content_type_id, status = client.find_place_coordinates(
            search_name, city, activity_types
        )
        if status != "api_error":
            return latitude, longitude, status
        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return latitude, longitude, status


def fetch_coordinates_for_city(client: TourApiClient, city: str) -> tuple[dict, list[dict]]:
    path = DESTINATIONS_DIR / f"{city}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    unresolved: list[dict] = []
    for place in payload["places"]:
        # place["name"] is sometimes an English/romanized identifier
        # (e.g. "Gyeongbokgung Palace"); PLACE_NAME_KO holds the Korean
        # display name TourAPI's titles are actually written in.
        search_name = PLACE_NAME_KO.get(place["id"], place["name"])
        latitude, longitude, status = find_coordinates_with_retry(
            client, search_name, city, place.get("activity_type", [])
        )
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if status == "ok":
            place["latitude"] = latitude
            place["longitude"] = longitude
        else:
            unresolved.append({"city": city, "id": place["id"], "name": place["name"], "reason": status})

    return payload, unresolved


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
    resolved_count = 0
    total_count = 0

    for city in TOUR_API_ADDRESS_PREFIX_BY_CITY:
        payload, unresolved = fetch_coordinates_for_city(client, city)
        total_count += len(payload["places"])
        resolved_count += len(payload["places"]) - len(unresolved)
        all_unresolved.extend(unresolved)
        save_city_catalog(city, payload)
        print(f"{city}: {len(payload['places']) - len(unresolved)}/{len(payload['places'])} resolved")

    print(f"\nTotal: {resolved_count}/{total_count} places resolved")
    if all_unresolved:
        print(f"\n{len(all_unresolved)} unresolved place(s):")
        for item in all_unresolved:
            print(f"  - [{item['city']}] {item['id']} ({item['name']}) - {item['reason']}")


if __name__ == "__main__":
    main()
