"""검토가 끝난 부산 확장 장소(기본 입력 scripts/data/busan_expansion_places.json -
--input으로 다른 배치 파일을 줄 수 있다. 1단계 283곳으로 처음 만들어졌고,
2단계 131곳(#158) 등 이후 배치에도 그대로 재사용한다)를
app/data/destinations/busan.json에 반영한다(PR-C).

두 가지 모드:
  (기본) 추가 모드 - 입력 파일의 장소를 is_active=false 그대로 busan.json
    places 배열 뒤에 추가한다. 기존 80곳은 바이트 단위로 손대지 않는다
    (json.load+dump 왕복 대신, 원본 텍스트에서 "places" 배열의 정확한
    닫는 괄호 위치를 찾아 그 앞에 새 항목만 끼워 넣는다 - see
    _splice_new_places_into_text).
  --activate {main,all} - busan.json에 이미 들어 있는(=입력 파일에 있는)
    장소 중 main(alternate 제외)/all(전부)의 is_active를 true로 바꾼다.
    입력 파일에 없는 기존 장소는 절대 건드리지 않는다. 이번 PR에서는
    실행하지 않는다(코드·테스트만 - 전후 비교는 별도 작업).

둘 다 기본은 --dry-run(파일에 쓰지 않고 결과만 출력)이고, --apply를 줘야
실제로 쓴다. 검증 실패·사전 검사 위반은 전부-아니면-전무: 하나라도 걸리면
아무것도 쓰지 않고 종료한다. 외부 API·키·DB 접속이 필요 없다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.stdout.reconfigure(encoding="utf-8")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError  # noqa: E402

from app.domains.destination_catalog.schemas import ALTERNATE_TIER, PlaceData  # noqa: E402
from app.domains.destination_catalog.services.repository import compute_recommended_max_days  # noqa: E402
from app.domains.rule_planner.services.constants import BUSAN_AREA_ROUTE_ORDER  # noqa: E402

CITY = "busan"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "scripts" / "data" / "busan_expansion_places.json"
DEFAULT_CATALOG_PATH = PROJECT_ROOT / "app" / "data" / "destinations" / f"{CITY}.json"

VALID_MVP_TIERS = {"standard", ALTERNATE_TIER}
VALID_BOOKING_VALUES = {None, "required", "recommended"}
# 위/경도 범위 - 부산 행정구역을 넉넉히 덮는 사각형(요구사항 1에 명시된 값).
BUSAN_LAT_RANGE = (34.9, 35.45)
BUSAN_LNG_RANGE = (128.7, 129.35)


class PreflightError(Exception):
    """하나라도 걸리면 아무것도 쓰지 않고 종료해야 하는 사전 검사 실패."""


def load_json_dict(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_input_places(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = load_json_dict(path)
    places = data.get("places")
    if not isinstance(places, list):
        raise PreflightError(f"입력 파일에 places 배열이 없습니다: {path}")
    return data, places


def validate_schema(places: list[dict[str, Any]]) -> list[str]:
    """PlaceData.model_validate로 각 장소를 검증한다. 실패한 장소가 하나라도
    있으면 전부 보고하고(부분 반영 없음), 빈 리스트면 전부 통과."""
    errors: list[str] = []
    for index, raw_place in enumerate(places):
        place_id = raw_place.get("id", f"(id 없음, index={index})")
        try:
            PlaceData.model_validate(raw_place)
        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(str(part) for part in error["loc"])
                errors.append(f"[{index}] id={place_id!r} field={field}: {error['msg']}")
    return errors


def normalize_name_for_dup_check(name: str) -> str:
    """공백·괄호를 지운 뒤 비교 - 완전히 같으면 같은 장소로 본다."""
    return re.sub(r"[\s()（）]", "", name)


def run_preflight_checks(
    input_places: list[dict[str, Any]],
    existing_places: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(to_add, already_applied)를 반환한다. 통과 못 하면 PreflightError를
    던진다(아무것도 쓰지 않고 종료) - 멱등 스킵(이미 반영됨)은 에러가
    아니다."""
    # --- 입력 파일 자체의 불변식 (기존 카탈로그와 무관) ---------------------
    input_ids = [place["id"] for place in input_places]
    duplicate_input_ids = {pid for pid in input_ids if input_ids.count(pid) > 1}
    if duplicate_input_ids:
        raise PreflightError(f"입력 파일 안에 id가 중복됩니다: {sorted(duplicate_input_ids)}")

    not_inactive = [place["id"] for place in input_places if place.get("is_active") is not False]
    if not_inactive:
        raise PreflightError(f"모든 장소는 is_active=false여야 합니다. 위반: {not_inactive}")

    bad_tier = [
        (place["id"], place.get("mvp_tier")) for place in input_places if place.get("mvp_tier") not in VALID_MVP_TIERS
    ]
    if bad_tier:
        raise PreflightError(f"mvp_tier는 {sorted(VALID_MVP_TIERS)} 중 하나여야 합니다. 위반: {bad_tier}")

    bad_area = [(place["id"], place.get("area")) for place in input_places if place.get("area") not in BUSAN_AREA_ROUTE_ORDER]
    if bad_area:
        raise PreflightError(f"area는 부산의 등록된 구역({BUSAN_AREA_ROUTE_ORDER}) 중 하나여야 합니다. 위반: {bad_area}")

    bad_coords = []
    for place in input_places:
        lat, lng = place.get("latitude"), place.get("longitude")
        if lat is None or lng is None:
            bad_coords.append((place["id"], lat, lng))
            continue
        if not (BUSAN_LAT_RANGE[0] <= lat <= BUSAN_LAT_RANGE[1] and BUSAN_LNG_RANGE[0] <= lng <= BUSAN_LNG_RANGE[1]):
            bad_coords.append((place["id"], lat, lng))
    if bad_coords:
        raise PreflightError(f"좌표가 없거나 부산 범위(위도 {BUSAN_LAT_RANGE}, 경도 {BUSAN_LNG_RANGE}) 밖입니다: {bad_coords}")

    bad_url = [
        (place["id"], place.get("official_url"))
        for place in input_places
        if place.get("official_url") and not str(place["official_url"]).startswith(("http://", "https://"))
    ]
    if bad_url:
        raise PreflightError(f"official_url은 없거나 http(s)로 시작해야 합니다. 위반: {bad_url}")

    bad_season = [
        (place["id"], place.get("season_months"))
        for place in input_places
        if any(not isinstance(month, int) or not 1 <= month <= 12 for month in (place.get("season_months") or []))
    ]
    if bad_season:
        raise PreflightError(f"season_months는 1~12만 허용합니다. 위반: {bad_season}")

    bad_booking = [
        (place["id"], place.get("booking")) for place in input_places if place.get("booking") not in VALID_BOOKING_VALUES
    ]
    if bad_booking:
        raise PreflightError(f"booking은 {sorted(v for v in VALID_BOOKING_VALUES if v)} 또는 없음이어야 합니다. 위반: {bad_booking}")

    # --- 기존 카탈로그와의 관계 (충돌/중복/멱등) -----------------------------
    existing_by_id = {place["id"]: place for place in existing_places}
    existing_content_ids = {place["content_id"] for place in existing_places if place.get("content_id")}
    existing_names_normalized = {normalize_name_for_dup_check(place["name"]) for place in existing_places}

    to_add: list[dict[str, Any]] = []
    already_applied: list[dict[str, Any]] = []

    for place in input_places:
        existing_match = existing_by_id.get(place["id"])
        if existing_match is not None:
            if existing_match.get("content_id") == place.get("content_id"):
                already_applied.append(place)
                continue
            raise PreflightError(
                f"기존 카탈로그와 id가 충돌합니다(content_id는 다름 - 같은 장소가 아닐 수 있음): "
                f"id={place['id']!r}, 입력 content_id={place.get('content_id')!r}, "
                f"기존 content_id={existing_match.get('content_id')!r}"
            )

        if place.get("content_id") and place["content_id"] in existing_content_ids:
            raise PreflightError(
                f"기존 카탈로그와 content_id가 충돌합니다(id는 다름): "
                f"id={place['id']!r}, content_id={place['content_id']!r}"
            )

        normalized_name = normalize_name_for_dup_check(place["name"])
        if normalized_name in existing_names_normalized:
            raise PreflightError(
                f"이름이 기존 카탈로그와 정규화 후 완전히 같습니다(중단): "
                f"id={place['id']!r}, name={place['name']!r}"
            )

        to_add.append(place)

    return to_add, already_applied


def count_activity_candidates(places: list[dict[str, Any]]) -> int:
    count = 0
    for raw_place in places:
        place = PlaceData.model_validate(raw_place)
        if place.is_active and place.is_activity_candidate and place.mvp_tier != ALTERNATE_TIER:
            count += 1
    return count


def summarize_by(places: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for place in places:
        value = place.get(key)
        counts[value] = counts.get(value, 0) + 1
    return counts


# --- 기존 바이트를 건드리지 않는 텍스트 삽입 ------------------------------


def _find_matching_bracket(text: str, open_index: int) -> int:
    """open_index에 있는 '[' 또는 '{'의 짝이 되는 닫는 괄호의 인덱스."""
    depth = 0
    index = open_index
    in_string = False
    escape = False
    while index < len(text):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
                if depth == 0:
                    return index
        index += 1
    raise ValueError("짝이 되는 닫는 괄호를 찾지 못했습니다.")


def locate_places_array(text: str) -> tuple[int, int]:
    """최상위 "places" 키의 값인 배열의 (여는 '[' 인덱스, 닫는 ']' 인덱스)."""
    key_index = text.index('"places"')
    colon_index = text.index(":", key_index)
    index = colon_index + 1
    while text[index] in " \t\r\n":
        index += 1
    if text[index] != "[":
        raise ValueError('"places"의 값이 배열이 아닙니다.')
    open_index = index
    close_index = _find_matching_bracket(text, open_index)
    return open_index, close_index


def _detect_item_style(text: str, open_index: int, close_index: int) -> tuple[str, str]:
    """기존 배열 항목의 (줄바꿈 문자, 항목 들여쓰기)를 실제 파일 내용에서
    읽어낸다 - 하드코딩하지 않아 이 함수가 어떤 들여쓰기/줄바꿈 스타일의
    카탈로그에도(테스트용 가짜 카탈로그 포함) 맞춰 동작한다."""
    inside = text[open_index + 1 : close_index]
    if not inside.strip():
        # 빈 배열 - 닫는 괄호 쪽 들여쓰기에서 추정한다.
        before_close = text[:close_index]
        j = len(before_close)
        while j > 0 and before_close[j - 1] in " \t\r\n":
            j -= 1
        close_ws = before_close[j:]
        newline_style = "\r\n" if "\r\n" in close_ws else "\n"
        close_indent = close_ws.split(newline_style)[-1] if newline_style in close_ws else ""
        return newline_style, close_indent + "  "

    stripped = inside.lstrip(" \t\r\n")
    leading_ws = inside[: len(inside) - len(stripped)]
    newline_style = "\r\n" if "\r\n" in leading_ws else "\n"
    item_indent = leading_ws.split(newline_style)[-1]
    return newline_style, item_indent


def _format_place_block(place: dict[str, Any], item_indent: str, newline_style: str) -> str:
    dumped = json.dumps(place, ensure_ascii=False, indent=2)
    lines = dumped.split("\n")
    return newline_style.join(item_indent + line for line in lines)


def splice_new_places_into_text(text: str, new_places: list[dict[str, Any]]) -> str:
    """기존 바이트를 전혀 재직렬화하지 않고, "places" 배열의 마지막 항목
    뒤(닫는 ']' 바로 앞)에 new_places만 문자열로 끼워 넣는다."""
    if not new_places:
        return text

    open_index, close_index = locate_places_array(text)
    newline_style, item_indent = _detect_item_style(text, open_index, close_index)
    inside = text[open_index + 1 : close_index]

    blocks = [_format_place_block(place, item_indent, newline_style) for place in new_places]
    insertion = ("," + newline_style).join(blocks)

    if not inside.strip():
        # 빈 배열이었던 경우 - 선행 쉼표 없이, 여는 괄호 바로 뒤에 넣는다.
        new_inside = newline_style + insertion + newline_style + item_indent[:-2]
        return text[: open_index + 1] + new_inside + text[close_index:]

    # 마지막 기존 항목의 닫는 '}' 바로 뒤(그 뒤의 공백 전)를 찾는다.
    j = close_index
    while j > 0 and text[j - 1] in " \t\r\n":
        j -= 1
    return text[:j] + "," + newline_style + insertion + text[j:]


# --- 추가 모드 --------------------------------------------------------------


def run_add(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    catalog_path = Path(args.catalog) if getattr(args, "catalog", None) else DEFAULT_CATALOG_PATH

    input_data, input_places = load_input_places(input_path)
    schema_errors = validate_schema(input_places)
    if schema_errors:
        print(f"=== 스키마 검증 실패: {len(schema_errors)}건 - 아무것도 쓰지 않습니다 ===")
        for error in schema_errors:
            print(f"  {error}")
        return 1

    with catalog_path.open("r", encoding="utf-8", newline="") as f:
        catalog_text = f.read()
    catalog = json.loads(catalog_text)
    existing_places = catalog.get("places", [])

    try:
        to_add, already_applied = run_preflight_checks(input_places, existing_places)
    except PreflightError as error:
        print(f"=== 사전 검사 실패 - 아무것도 쓰지 않습니다 ===\n{error}")
        return 1

    before_count = count_activity_candidates(existing_places)
    before_recommended_days = compute_recommended_max_days(before_count)
    after_count = count_activity_candidates(existing_places + to_add)
    after_recommended_days = compute_recommended_max_days(after_count)

    print(f"=== {CITY} 확장 장소 반영 ({'apply' if args.apply else 'dry-run'}) ===")
    print(f"입력: {len(input_places)}곳")
    print(f"이미 반영됨(건너뜀): {len(already_applied)}곳")
    print(f"추가: {len(to_add)}곳")
    print(f"tier별: {summarize_by(to_add, 'mvp_tier')}")
    print(f"area별: {summarize_by(to_add, 'area')}")
    print(f"활동 후보 수: {before_count} -> {after_count}")
    print(f"recommended_max_days: {before_recommended_days} -> {after_recommended_days}")

    if not args.apply:
        print("\n(dry-run) 실제로 쓰려면 --apply를 추가하세요.")
        return 0

    if to_add:
        new_text = splice_new_places_into_text(catalog_text, to_add)
        with catalog_path.open("w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        print(f"\n{catalog_path}에 {len(to_add)}곳을 추가했습니다.")
    else:
        print("\n추가할 장소가 없어 파일을 쓰지 않았습니다.")
    return 0


# --- 활성화 모드 (이번 PR에서는 실행하지 않음 - 코드·테스트만) ---------------


def resolve_activation_targets(
    input_places: list[dict[str, Any]],
    mode: str,
) -> set[str]:
    """activate 대상 id 집합 - main은 alternate 제외, all은 전부."""
    if mode == "all":
        return {place["id"] for place in input_places}
    if mode == "main":
        return {place["id"] for place in input_places if place.get("mvp_tier") != ALTERNATE_TIER}
    raise ValueError(f"알 수 없는 activate 모드: {mode}")


def run_activate(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    catalog_path = Path(args.catalog) if getattr(args, "catalog", None) else DEFAULT_CATALOG_PATH

    _input_data, input_places = load_input_places(input_path)
    target_ids = resolve_activation_targets(input_places, args.activate)

    catalog = load_json_dict(catalog_path)
    places = catalog.get("places", [])

    to_activate = [place for place in places if place["id"] in target_ids and not place.get("is_active", True)]
    already_active = [place for place in places if place["id"] in target_ids and place.get("is_active", True)]
    not_found = sorted(target_ids - {place["id"] for place in places})

    print(f"=== {CITY} 확장 장소 활성화 ({args.activate}, {'apply' if args.apply else 'dry-run'}) ===")
    print(f"대상(입력 파일 기준): {len(target_ids)}곳")
    print(f"이미 활성 상태: {len(already_active)}곳")
    print(f"새로 활성화할 장소: {len(to_activate)}곳")
    if not_found:
        print(f"카탈로그에 아직 없는 대상(먼저 추가 모드로 반영 필요): {len(not_found)}곳 - {not_found[:10]}")

    if not args.apply:
        print("\n(dry-run) 실제로 쓰려면 --apply를 추가하세요.")
        return 0

    if not to_activate:
        print("\n활성화할 장소가 없어 파일을 쓰지 않았습니다.")
        return 0

    for place in to_activate:
        place["is_active"] = True

    with catalog_path.open("r", encoding="utf-8", newline="") as f:
        text = f.read()
    newline_style = "\r\n" if "\r\n" in text else "\n"
    with catalog_path.open("w", encoding="utf-8", newline="") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write(newline_style)
    print(f"\n{catalog_path}에서 {len(to_activate)}곳을 활성화했습니다.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"반영할 장소 입력 JSON 경로 (기본: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 destinations/busan.json에 쓴다. 기본은 dry-run(결과만 출력, 파일을 쓰지 않음).",
    )
    parser.add_argument(
        "--activate",
        choices=["main", "all"],
        default=None,
        help="추가 모드 대신 활성화 모드로 실행한다: main(alternate 제외) 또는 all(전부).",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="테스트용 - busan.json 대신 쓸 카탈로그 경로 (기본: app/data/destinations/busan.json)",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    if args.activate:
        return run_activate(args)
    return run_add(args)


if __name__ == "__main__":
    raise SystemExit(main())
