from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from add_tour_api_lodging import (  # noqa: E402
    ALLOWED_NEW_LODGING_BY_CITY,
    NAMED_HOTEL_TARGET_TITLES_BY_CITY,
    resolve_additions_for_city,
)

from app.domains.rule_planner.services.policies.city.jeju_zones import ZONE_CENTERS  # noqa: E402

ACCOMMODATIONS_DIR = PROJECT_ROOT / "app" / "data" / "accommodations"


def build_pool_record(**overrides) -> dict:
    record = {
        "contentid": "9000001",
        "title": "샘플 호텔",
        "addr1": "서울특별시 강남구 테헤란로 1",
        "mapx": "127.0300000",
        "mapy": "37.5000000",
        "lclsSystm2": "AC01",
    }
    record.update(overrides)
    return record


AREA_CENTERS = {"gangnam": (37.4979, 127.0276)}


def _patch_allowlists(seoul_allowed=None, seoul_named=None):
    original_allowed = {city: dict(entries) for city, entries in ALLOWED_NEW_LODGING_BY_CITY.items()}
    original_named = {city: list(titles) for city, titles in NAMED_HOTEL_TARGET_TITLES_BY_CITY.items()}
    ALLOWED_NEW_LODGING_BY_CITY["seoul"] = seoul_allowed or {}
    NAMED_HOTEL_TARGET_TITLES_BY_CITY["seoul"] = seoul_named or []
    return original_allowed, original_named


def _restore_allowlists(original_allowed, original_named):
    ALLOWED_NEW_LODGING_BY_CITY.clear()
    ALLOWED_NEW_LODGING_BY_CITY.update(original_allowed)
    NAMED_HOTEL_TARGET_TITLES_BY_CITY.clear()
    NAMED_HOTEL_TARGET_TITLES_BY_CITY.update(original_named)


# --- resolve_additions_for_city(): allow-listed content_ids -----------------


def test_resolve_additions_adds_an_allowlisted_record_with_its_hardcoded_area() -> None:
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"})
    try:
        pool = [build_pool_record(contentid="9000001")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert len(to_add) == 1
        record, area_label = to_add[0]
        assert record["contentid"] == "9000001"
        assert area_label == "gangnam"
        assert skipped == []
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_when_content_id_already_in_catalog() -> None:
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"})
    try:
        pool = [build_pool_record(contentid="9000001")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), {"9000001"}, AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
        assert "이미 카탈로그에 존재" in skipped[0]["reason"]
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_when_content_id_already_used_as_an_id() -> None:
    # Existing records have id == content_id, but the check is defensive
    # against either matching.
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"})
    try:
        pool = [build_pool_record(contentid="9000001")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, {"9000001"}, set(), AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_an_allowlisted_id_missing_from_the_pool() -> None:
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"})
    try:
        to_add, skipped = resolve_additions_for_city("seoul", [], set(), set(), AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
        assert "조회 실패" in skipped[0]["reason"]
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_an_unclassified_type() -> None:
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"})
    try:
        pool = [build_pool_record(contentid="9000001", lclsSystm2="AC99")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
        assert skipped[0]["reason"] == "유형 미분류"
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_a_record_with_no_coordinates() -> None:
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"})
    try:
        pool = [build_pool_record(contentid="9000001", mapx="", mapy="")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
        assert skipped[0]["reason"] == "좌표 없음"
    finally:
        _restore_allowlists(*original)


# --- resolve_additions_for_city(): named-hotel exact-title resolution -------


def test_resolve_additions_resolves_a_named_hotel_by_exact_title_match() -> None:
    original = _patch_allowlists(seoul_named=["타겟 호텔"])
    try:
        pool = [build_pool_record(contentid="9000002", title="타겟 호텔")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert len(to_add) == 1
        record, area_label = to_add[0]
        assert record["contentid"] == "9000002"
        assert area_label == "gangnam"  # keyword match on addr1 "강남구"
        assert skipped == []
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_a_named_hotel_with_no_exact_match() -> None:
    original = _patch_allowlists(seoul_named=["타겟 호텔"])
    try:
        pool = [build_pool_record(contentid="9000002", title="타겟 호텔 별관")]  # not an exact match
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
        assert "정확히 하나로 확인 안됨" in skipped[0]["reason"]
        assert "매칭 0건" in skipped[0]["reason"]
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_skips_a_named_hotel_with_an_ambiguous_match() -> None:
    original = _patch_allowlists(seoul_named=["타겟 호텔"])
    try:
        pool = [
            build_pool_record(contentid="9000002", title="타겟 호텔"),
            build_pool_record(contentid="9000003", title="타겟 호텔"),
        ]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert to_add == []
        assert len(skipped) == 1
        assert "매칭 2건" in skipped[0]["reason"]
    finally:
        _restore_allowlists(*original)


def test_resolve_additions_does_not_double_add_a_named_hotel_already_in_the_allowlist() -> None:
    original = _patch_allowlists(seoul_allowed={"9000002": "gangnam"}, seoul_named=["타겟 호텔"])
    try:
        pool = [build_pool_record(contentid="9000002", title="타겟 호텔")]
        to_add, skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)

        assert len(to_add) == 1  # added once, via the allowlist entry
        assert len(skipped) == 1
        assert "허용 목록과 중복" in skipped[0]["reason"]
    finally:
        _restore_allowlists(*original)


# --- idempotency -------------------------------------------------------------


def test_resolve_additions_is_idempotent_once_ids_are_recorded_as_existing() -> None:
    original = _patch_allowlists(seoul_allowed={"9000001": "gangnam"}, seoul_named=["타겟 호텔"])
    try:
        pool = [
            build_pool_record(contentid="9000001"),
            build_pool_record(contentid="9000002", title="타겟 호텔"),
        ]
        first_to_add, first_skipped = resolve_additions_for_city("seoul", pool, set(), set(), AREA_CENTERS)
        assert len(first_to_add) == 2
        assert first_skipped == []

        added_content_ids = {record["contentid"] for record, _ in first_to_add}
        second_to_add, second_skipped = resolve_additions_for_city("seoul", pool, set(), added_content_ids, AREA_CENTERS)

        assert second_to_add == []
        assert len(second_skipped) == 2
        assert all("이미 카탈로그에 존재" in s["reason"] for s in second_skipped)
    finally:
        _restore_allowlists(*original)


# --- real-catalog checks (script already applied) ---------------------------


def _load_real_catalog(city: str) -> list[dict]:
    return json.loads((ACCOMMODATIONS_DIR / f"{city}.json").read_text(encoding="utf-8"))["accommodations"]


def test_real_catalogs_have_no_duplicate_ids_or_content_ids() -> None:
    for city in ("seoul", "busan", "jeju"):
        accommodations = _load_real_catalog(city)
        ids = [a["id"] for a in accommodations]
        content_ids = [a["content_id"] for a in accommodations if a.get("content_id")]
        assert len(ids) == len(set(ids)), city
        assert len(content_ids) == len(set(content_ids)), city


def test_real_catalogs_new_accommodations_have_coordinates_type_and_area() -> None:
    for city in ("seoul", "busan", "jeju"):
        accommodations = {a["id"]: a for a in _load_real_catalog(city)}
        for content_id in ALLOWED_NEW_LODGING_BY_CITY[city]:
            accommodation = accommodations.get(content_id)
            if accommodation is None:
                continue  # legitimately skipped (e.g. not in the pool at run time) - covered by the run report
            assert accommodation["latitude"] is not None, (city, content_id)
            assert accommodation["longitude"] is not None, (city, content_id)
            assert accommodation["accommodation_type"], (city, content_id)
            assert accommodation["area"], (city, content_id)
            assert accommodation["content_id"] == content_id


def test_real_catalogs_jeju_zone_codes_are_a_subset_of_known_zone_centers() -> None:
    jeju_accommodations = _load_real_catalog("jeju")
    added_ids = set(ALLOWED_NEW_LODGING_BY_CITY["jeju"])
    for accommodation in jeju_accommodations:
        if accommodation["id"] in added_ids:
            assert accommodation["area"] in ZONE_CENTERS, accommodation["id"]


# Hardcoded snapshot of the original 45 (id -> key fields), taken before
# scripts/add_tour_api_lodging.py ran, so a future accidental edit to the
# existing catalog entries is caught even though they aren't the subject
# of this script.
ORIGINAL_45_SNAPSHOT: dict[str, dict[str, object]] = {
    "seoul": {
        "3084991": {"content_id": "3084991", "accommodation_type": "호텔", "area": "euljiro", "latitude": 37.566501918, "longitude": 127.0033298707},
        "2592489": {"content_id": "2592489", "accommodation_type": "펜션·민박", "area": "jongno", "latitude": 37.5797528699, "longitude": 126.9873670606},
        "2570164": {"content_id": "2570164", "accommodation_type": "호스텔", "area": "jongno", "latitude": 37.5737346471, "longitude": 127.0164673572},
        "142769": {"content_id": "142769", "accommodation_type": "호텔", "area": "gangnam", "latitude": 37.5095984514, "longitude": 127.0608845757},
        "2541308": {"content_id": "2541308", "accommodation_type": "호텔", "area": "jamsil", "latitude": 37.510126522, "longitude": 127.0805716573},
        "2572829": {"content_id": "2572829", "accommodation_type": "호스텔", "area": "itaewon", "latitude": 37.5357636211, "longitude": 126.9920595457},
        "142721": {"content_id": "142721", "accommodation_type": "호텔", "area": "gangnam", "latitude": 37.5053372605, "longitude": 127.0289098282},
        "3080814": {"content_id": "3080814", "accommodation_type": "호텔", "area": "gangnam", "latitude": 37.5024544344, "longitude": 127.038497926},
        "2571971": {"content_id": "2571971", "accommodation_type": "호스텔", "area": "jongno", "latitude": 37.5774778296, "longitude": 126.9704270026},
        "984650": {"content_id": "984650", "accommodation_type": "호텔", "area": "gangnam", "latitude": 37.5187882827, "longitude": 127.0180965434},
        "142766": {"content_id": "142766", "accommodation_type": "호텔", "area": "jamsil", "latitude": 37.5123821225, "longitude": 127.0976311526},
        "1327006": {"content_id": "1327006", "accommodation_type": "호텔", "area": "yeouido", "latitude": 37.5212667678, "longitude": 126.9186194232},
        "3080826": {"content_id": "3080826", "accommodation_type": "호텔", "area": "gangnam", "latitude": 37.5006324696, "longitude": 127.0410782986},
        "2008490": {"content_id": "2008490", "accommodation_type": "호텔", "area": "gangnam", "latitude": 37.511034348, "longitude": 127.0582208886},
        "142771": {"content_id": "142771", "accommodation_type": "호텔", "area": "itaewon", "latitude": 37.5354165502, "longitude": 126.998245103},
    },
    "busan": {
        "2754601": {"content_id": "2754601", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1592408683, "longitude": 129.1531418525},
        "2925797": {"content_id": "2925797", "accommodation_type": "콘도미니엄", "area": "haeundae", "latitude": 35.1619491796, "longitude": 129.1683126815},
        "3532715": {"content_id": "3532715", "accommodation_type": "펜션·민박", "area": "gwangalli", "latitude": 35.168222552, "longitude": 129.1183890728},
        "3533138": {"content_id": "3533138", "accommodation_type": "펜션·민박", "area": "gwangalli", "latitude": 35.1569128366, "longitude": 129.1253526663},
        "2818890": {"content_id": "2818890", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1601048456, "longitude": 129.1631548469},
        "3083428": {"content_id": "3083428", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1617295697, "longitude": 129.1580746892},
        "2731553": {"content_id": "2731553", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.163001657, "longitude": 129.1584801742},
        "3532572": {"content_id": "3532572", "accommodation_type": "펜션·민박", "area": "haeundae", "latitude": 35.178772849, "longitude": 129.1981457361},
        "2574073": {"content_id": "2574073", "accommodation_type": "펜션·민박", "area": "haeundae", "latitude": 35.1822391732, "longitude": 129.200550987},
        "2816102": {"content_id": "2816102", "accommodation_type": "호텔", "area": "gwangalli", "latitude": 35.1540103687, "longitude": 129.1245417048},
        "2705418": {"content_id": "2705418", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1609381479, "longitude": 129.1665100882},
        "3533169": {"content_id": "3533169", "accommodation_type": "펜션·민박", "area": "haeundae", "latitude": 35.1622938525, "longitude": 129.1827197529},
        "2708705": {"content_id": "2708705", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1611685856, "longitude": 129.1615188489},
        "142978": {"content_id": "142978", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1624489933, "longitude": 129.161266058},
        "2811461": {"content_id": "2811461", "accommodation_type": "호텔", "area": "haeundae", "latitude": 35.1595992286, "longitude": 129.1567804158},
    },
    "jeju": {
        "1894943": {"content_id": "1894943", "accommodation_type": "호텔", "area": "seogwipo-west", "latitude": 33.3178733106, "longitude": 126.3875196113},
        "3084988": {"content_id": "3084988", "accommodation_type": "콘도미니엄", "area": "west-jeju", "latitude": 33.348127981, "longitude": 126.3672651377},
        "735314": {"content_id": "735314", "accommodation_type": "펜션·민박", "area": "west-jeju", "latitude": 33.4753472289, "longitude": 126.3666540021},
        "2699343": {"content_id": "2699343", "accommodation_type": "호스텔", "area": "west-jeju", "latitude": 33.4670365589, "longitude": 126.3363346046},
        "3084957": {"content_id": "3084957", "accommodation_type": "호텔", "area": "west-jeju", "latitude": 33.472097309, "longitude": 126.3489500598},
        "984562": {"content_id": "984562", "accommodation_type": "콘도미니엄", "area": "west-jeju", "latitude": 33.3469894223, "longitude": 126.3802668112},
        "1897905": {"content_id": "1897905", "accommodation_type": "펜션·민박", "area": "seogwipo-west", "latitude": 33.2562936895, "longitude": 126.1903769911},
        "2626800": {"content_id": "2626800", "accommodation_type": "펜션·민박", "area": "seogwipo-west", "latitude": 33.2368032498, "longitude": 126.3088143604},
        "139008": {"content_id": "139008", "accommodation_type": "호텔", "area": "east-jeju", "latitude": 33.5421529255, "longitude": 126.6654098459},
        "137476": {"content_id": "137476", "accommodation_type": "콘도미니엄", "area": "west-jeju", "latitude": 33.4631615996, "longitude": 126.3117312768},
        "2991120": {"content_id": "2991120", "accommodation_type": "펜션·민박", "area": "east-jeju", "latitude": 33.5444525773, "longitude": 126.6595658566},
        "2624249": {"content_id": "2624249", "accommodation_type": "호텔", "area": "seongsan", "latitude": 33.4718785742, "longitude": 126.9127177787},
        "984523": {"content_id": "984523", "accommodation_type": "호텔", "area": "west-jeju", "latitude": 33.3377949264, "longitude": 126.3124118005},
        "2757210": {"content_id": "2757210", "accommodation_type": "콘도미니엄", "area": "seongsan", "latitude": 33.4498866488, "longitude": 126.9182122544},
        "1853848": {"content_id": "1853848", "accommodation_type": "펜션·민박", "area": "west-jeju", "latitude": 33.4665921534, "longitude": 126.3356596732},
    },
}


def test_original_45_accommodations_are_unchanged() -> None:
    for city, expected_by_id in ORIGINAL_45_SNAPSHOT.items():
        accommodations = {a["id"]: a for a in _load_real_catalog(city)}
        assert len(expected_by_id) == 15, city
        for accommodation_id, expected in expected_by_id.items():
            actual = accommodations.get(accommodation_id)
            assert actual is not None, (city, accommodation_id, "원래 있던 숙소가 사라짐")
            for field, expected_value in expected.items():
                assert actual[field] == expected_value, (city, accommodation_id, field)
