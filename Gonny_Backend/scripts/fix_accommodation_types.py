from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "accommodations"

HOTEL_SUITABLE_FOR = ["solo", "couple", "friend", "family"]
GUEST_HOUSE_SUITABLE_FOR = ["couple", "family", "friend"]

# (city, id, from_type, to_type, budget_level, suitable_for)
CORRECTIONS: list[tuple[str, str, str, str, list[str], list[str]]] = [
    ("seoul", "3084991", "모텔", "호텔", ["medium", "high"], HOTEL_SUITABLE_FOR),
    ("seoul", "2541308", "모텔", "호텔", ["medium"], HOTEL_SUITABLE_FOR),
    ("seoul", "3080814", "모텔", "호텔", ["medium"], HOTEL_SUITABLE_FOR),
    ("busan", "2754601", "모텔", "호텔", ["medium"], HOTEL_SUITABLE_FOR),
    ("busan", "3083428", "모텔", "호텔", ["medium"], HOTEL_SUITABLE_FOR),
    ("busan", "2705418", "콘도미니엄", "호텔", ["medium", "high"], HOTEL_SUITABLE_FOR),
    ("busan", "2731553", "콘도미니엄", "호텔", ["medium", "high"], HOTEL_SUITABLE_FOR),
    ("busan", "2574073", "호스텔", "펜션·민박", ["medium"], GUEST_HOUSE_SUITABLE_FOR),
    ("busan", "3533138", "호스텔", "펜션·민박", ["medium"], GUEST_HOUSE_SUITABLE_FOR),
    ("jeju", "1894943", "모텔", "호텔", ["high"], HOTEL_SUITABLE_FOR),
    ("jeju", "2626800", "호스텔", "펜션·민박", ["medium"], GUEST_HOUSE_SUITABLE_FOR),
    ("jeju", "2624249", "호스텔", "호텔", ["medium"], HOTEL_SUITABLE_FOR),
]


def main() -> None:
    payloads = {}
    for city in sorted({correction[0] for correction in CORRECTIONS}):
        path = DATA_DIR / f"{city}.json"
        payloads[city] = (path, json.loads(path.read_text(encoding="utf-8")))

    applied = 0
    for city, acc_id, from_type, to_type, budget_level, suitable_for in CORRECTIONS:
        _, payload = payloads[city]
        matches = [item for item in payload["accommodations"] if item["id"] == acc_id]
        if len(matches) != 1:
            raise RuntimeError(f"{city}: accommodation id {acc_id} not found exactly once")
        item = matches[0]
        if item["accommodation_type"] == to_type:
            continue
        if item["accommodation_type"] != from_type:
            raise RuntimeError(
                f"{city}/{acc_id} ({item['name']}): expected type {from_type!r}, "
                f"found {item['accommodation_type']!r}"
            )
        item["accommodation_type"] = to_type
        item["budget_level"] = budget_level
        item["suitable_for"] = suitable_for
        applied += 1

    for path, payload in payloads.values():
        text = json.dumps(payload, indent=2, ensure_ascii=False).replace("\n", "\r\n") + "\r\n"
        path.write_text(text, encoding="utf-8", newline="")

    print(f"applied {applied} corrections ({len(CORRECTIONS) - applied} already applied)")


if __name__ == "__main__":
    main()
