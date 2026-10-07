# 좌표는 조사로 확인한 값이다 (지도 서비스/공식 페이지 대조). 이동시간 추정에 쓸
# 정밀도이며 지도 표시용 정밀도는 아니다. 지역 단위 장소(예: 인사동, 홍대, 강남)는
# 대표 한 점만 찍었다. 신뢰도가 낮은 항목(아래 LOW_CONFIDENCE_IDS)은 지도에 쓰기
# 전에 재확인할 것. 근거를 찾지 못한 4곳(e-land-hangang-cruise, s-factory,
# daelim-sangga, delmoondo-gimnyeong)은 이번에 채우지 않는다.
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "destinations"

LOW_CONFIDENCE_IDS = {"itaewon", "apgujeong-rodeo", "kbs-hall", "sema-bunker", "dongbaek-island"}

# (city, id, latitude, longitude)
COORDINATES: list[tuple[str, str, float, float]] = [
    # Seoul (22)
    ("seoul", "insadong", 37.57374, 126.98530),
    ("seoul", "namsan-tower", 37.551216, 126.988276),
    ("seoul", "hongdae", 37.5552233, 126.9235335),
    ("seoul", "gangnam", 37.497823, 127.027746),
    ("seoul", "yeonnam-forest", 37.5585635, 126.9255684),
    ("seoul", "itaewon", 37.539967, 126.992012),
    ("seoul", "apgujeong-rodeo", 37.52763, 127.04063),
    ("seoul", "seokchon-lake", 37.5113096, 127.1051525),
    ("seoul", "euljiro", 37.567195, 126.991791),
    ("seoul", "dongdaemun-shopping-town", 37.5665256, 127.0092236),
    ("seoul", "itaewon-antique-furniture-street", 37.533527, 126.994384),
    ("seoul", "namsan-park-trail", 37.554911, 126.986684),
    ("seoul", "seoul-sky", 37.512530, 127.102305),
    ("seoul", "lotte-world-mall", 37.514165, 127.104075),
    ("seoul", "63-square", 37.519867, 126.940329),
    ("seoul", "trick-eye-museum-seoul", 37.553525, 126.921704),
    ("seoul", "seonjeongneung", 37.508890, 127.049170),
    ("seoul", "ak-plaza-hongdae", 37.557746, 126.926498),
    ("seoul", "hyundai-motorstudio-seoul", 37.521290, 127.034314),
    ("seoul", "kbs-hall", 37.524758, 126.916868),
    ("seoul", "sema-bunker", 37.525405, 126.924208),
    ("seoul", "bongil-spa-land", 37.485870, 126.938447),
    # Busan (7)
    ("busan", "dongbaek-island", 35.15366, 129.15232),
    ("busan", "millac-the-market", 35.15422, 129.12704),
    ("busan", "sea-life-busan-aquarium", 35.15920, 129.16103),
    ("busan", "busan-x-the-sky", 35.159848, 129.169791),
    ("busan", "busan-modern-history-museum", 35.10272, 129.03216),
    ("busan", "shinsegae-spaland", 35.168817, 129.129524),
    ("busan", "club-d-oasis", 35.160042, 129.168483),
    # Jeju (6)
    ("jeju", "aewol-cafe", 33.45920, 126.31060),
    ("jeju", "jungmun-saekdal", 33.24543, 126.41121),
    ("jeju", "dongmun-market", 33.51153, 126.52605),
    ("jeju", "arte-museum-jeju", 33.39669, 126.34498),
    ("jeju", "jeju-glass-castle", 33.31458, 126.27366),
    ("jeju", "jeju-teddy-bear-museum", 33.25002, 126.41215),
]


def apply_coordinates(
    payloads: dict[str, dict], coordinates: list[tuple[str, str, float, float]]
) -> tuple[int, int, dict[str, int], dict[str, int]]:
    """Mutates each city payload's places in place. Pure (no file I/O) so
    it's unit-testable without touching the real catalog files.

    Raises if a (city, id) pair isn't found exactly once, or if the place
    already has *different* coordinates (refuses to guess which is right).
    Already-matching coordinates are counted as skipped, not an error -
    this is what makes a re-run idempotent.
    """
    filled = 0
    skipped = 0
    per_city_filled: dict[str, int] = {}
    per_city_skipped: dict[str, int] = {}
    for city, place_id, latitude, longitude in coordinates:
        payload = payloads[city]
        matches = [place for place in payload["places"] if place["id"] == place_id]
        if len(matches) != 1:
            raise RuntimeError(f"{city}: place id {place_id} not found exactly once")
        place = matches[0]

        existing_lat, existing_lng = place.get("latitude"), place.get("longitude")
        if existing_lat is not None or existing_lng is not None:
            if existing_lat == latitude and existing_lng == longitude:
                skipped += 1
                per_city_skipped[city] = per_city_skipped.get(city, 0) + 1
                continue
            raise RuntimeError(
                f"{city}/{place_id} ({place['name']}): already has coordinates "
                f"({existing_lat}, {existing_lng}) that differ from ({latitude}, {longitude}) - "
                "refusing to guess which one is right"
            )

        place["latitude"] = latitude
        place["longitude"] = longitude
        filled += 1
        per_city_filled[city] = per_city_filled.get(city, 0) + 1

    return filled, skipped, per_city_filled, per_city_skipped


def main() -> None:
    paths = {city: DATA_DIR / f"{city}.json" for city in sorted({entry[0] for entry in COORDINATES})}
    payloads = {city: json.loads(path.read_text(encoding="utf-8")) for city, path in paths.items()}

    filled, skipped, per_city_filled, per_city_skipped = apply_coordinates(payloads, COORDINATES)

    for city, path in paths.items():
        text = json.dumps(payloads[city], indent=2, ensure_ascii=False).replace("\n", "\r\n") + "\r\n"
        path.write_text(text, encoding="utf-8", newline="")

    print(f"filled {filled}, skipped (already set) {skipped}")
    for city in sorted(paths):
        print(f"  {city}: filled {per_city_filled.get(city, 0)}, skipped {per_city_skipped.get(city, 0)}")


if __name__ == "__main__":
    main()
