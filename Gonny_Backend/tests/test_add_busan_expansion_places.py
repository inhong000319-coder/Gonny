from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from add_busan_expansion_places import (  # noqa: E402
    locate_places_array,
    main,
    resolve_activation_targets,
    run_activate,
    run_add,
)

from app.domains.destination_catalog.schemas import ALTERNATE_TIER  # noqa: E402


def build_place(**overrides) -> dict:
    # name은 id에서 파생시켜 기본값을 써도 서로 다른 장소가 이름-정규화
    # 중복 검사에 우연히 걸리지 않게 한다 - 그 검사 자체를 테스트하는
    # 곳에서는 name을 명시적으로 겹치게 넘긴다.
    place = {
        "id": "busan-sample",
        "name": f"{overrides.get('id', 'busan-sample')} 이름",
        "activity_type": ["문화·역사"],
        "budget_level": ["medium"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["afternoon"],
        "area": "nampo",
        "duration_hours": 2,
        "priority": 6,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": "샘플 요약",
        "latitude": 35.0,
        "longitude": 129.0,
        "content_id": "1000001",
        "official_url": None,
        "is_active": False,
        "mvp_tier": "standard",
        "season_months": [],
        "booking": None,
        "theme_tags": [],
    }
    place.update(overrides)
    return place


def write_catalog(path: Path, places: list[dict]) -> None:
    """실제 busan.json과 같은 스타일(2-space indent, CRLF, ensure_ascii=False,
    끝 줄바꿈)로 가짜 카탈로그를 만든다."""
    catalog = {
        "continent": "asia",
        "country": "korea",
        "city": "busan",
        "aliases": ["busan"],
        "default_days": 3,
        "places": places,
    }
    text = json.dumps(catalog, ensure_ascii=False, indent=2)
    text = text.replace("\n", "\r\n") + "\r\n"
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_input(path: Path, places: list[dict]) -> None:
    payload = {"city": "busan", "generated": "2026-11-25", "source": "test", "places": places}
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)


def read_catalog(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_args(
    *,
    input_path: Path,
    catalog_path: Path,
    apply: bool = False,
    activate: str | None = None,
    exclude_areas: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        input=input_path, apply=apply, activate=activate, catalog=catalog_path, exclude_areas=exclude_areas
    )


# --- 추가 모드: dry-run은 쓰지 않는다 ---------------------------------------


def test_dry_run_does_not_write_file(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2")])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=False))

    assert exit_code == 0
    assert catalog_path.read_bytes() == before


# --- apply 후 개수·tier 보존 -------------------------------------------------


def test_apply_adds_places_and_preserves_count_and_tier(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    new_places = [
        build_place(id="new-standard", content_id="2", mvp_tier="standard"),
        build_place(id="new-alternate", content_id="3", mvp_tier=ALTERNATE_TIER, theme_tags=["walk"]),
    ]
    write_input(input_path, new_places)

    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))
    assert exit_code == 0

    catalog = read_catalog(catalog_path)
    assert len(catalog["places"]) == 3
    by_id = {p["id"]: p for p in catalog["places"]}
    assert by_id["new-standard"]["mvp_tier"] == "standard"
    assert by_id["new-alternate"]["mvp_tier"] == ALTERNATE_TIER
    assert by_id["new-alternate"]["theme_tags"] == ["walk"]
    # 모두 is_active=false 그대로
    assert all(p["is_active"] is False for p in [by_id["new-standard"], by_id["new-alternate"]])


# --- 기존 장소 바이트 보존 ---------------------------------------------------


def test_apply_preserves_existing_bytes_before_and_after_insertion(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(
        catalog_path,
        [build_place(id="existing-a", content_id="1"), build_place(id="existing-b", content_id="2", area="haeundae")],
    )
    original_text = catalog_path.read_text(encoding="utf-8")
    open_idx, close_idx = locate_places_array(original_text)
    j = close_idx
    while j > 0 and original_text[j - 1] in " \t\r\n":
        j -= 1
    prefix = original_text[:j]
    tail = original_text[j:]

    write_input(input_path, [build_place(id="new-a", content_id="3")])
    run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    new_text = catalog_path.read_text(encoding="utf-8")
    assert new_text.startswith(prefix)
    assert new_text.endswith(tail)


# --- 두 번째 apply는 변화 0(멱등) --------------------------------------------


def test_second_apply_is_idempotent(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2")])

    run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))
    after_first = catalog_path.read_bytes()

    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))
    after_second = catalog_path.read_bytes()

    assert exit_code == 0
    assert after_first == after_second
    assert len(read_catalog(catalog_path)["places"]) == 2


# --- 전무 종료: id 충돌 ------------------------------------------------------


def test_id_collision_with_different_content_id_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="dup-id", content_id="existing-content")])
    write_input(input_path, [build_place(id="dup-id", content_id="different-content")])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 전무 종료: content_id 충돌 ----------------------------------------------


def test_content_id_collision_with_different_id_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="shared-content")])
    write_input(input_path, [build_place(id="new-b", content_id="shared-content")])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 전무 종료: area 불일치 --------------------------------------------------


def test_area_not_in_busan_areas_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2", area="seoul-gangnam")])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 부산 확장 2단계(#158)가 추가한 새 구역도 area 검증을 통과한다 ----------


def test_phase2_new_areas_pass_area_validation(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(
        input_path,
        [
            build_place(id="new-seomyeon", content_id="2", area="seomyeon"),
            build_place(id="new-gijang", content_id="3", area="gijang"),
            build_place(id="new-gupo", content_id="4", area="gupo"),
            build_place(id="new-gangseo", content_id="5", area="gangseo"),
            build_place(id="new-gadeok", content_id="6", area="gadeok"),
        ],
    )

    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 0
    assert len(read_catalog(catalog_path)["places"]) == 6


def test_area_still_rejects_values_outside_all_eleven_busan_areas(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2", area="jeju-city")])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 전무 종료: 좌표 범위 밖 --------------------------------------------------


def test_coordinates_out_of_busan_range_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2", latitude=37.5, longitude=127.0)])  # 서울 좌표

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 전무 종료: PlaceData 검증 실패 ------------------------------------------


def test_schema_validation_failure_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    bad_place = build_place(id="new-a", content_id="2")
    del bad_place["name"]  # 필수 필드 누락
    write_input(input_path, [bad_place])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 전무 종료: is_active=true 섞임 -------------------------------------------


def test_any_active_place_in_input_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2", is_active=True)])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 전무 종료: 이름 정규화 중복 ----------------------------------------------


def test_normalized_name_duplicate_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1", name="감천 문화마을")])
    write_input(input_path, [build_place(id="new-a", content_id="2", name="감천문화마을")])

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 입력 안 id 중복도 전무 종료 ---------------------------------------------


def test_duplicate_ids_within_input_aborts_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(
        input_path,
        [build_place(id="new-a", content_id="2"), build_place(id="new-a", content_id="3")],
    )

    before = catalog_path.read_bytes()
    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 1
    assert catalog_path.read_bytes() == before


# --- 멱등 스킵: 같은 id·같은 content_id면 에러가 아니라 건너뜀만 -------------


def test_same_id_and_content_id_is_skipped_not_an_error(tmp_path, capsys):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="shared", content_id="99")])
    write_input(input_path, [build_place(id="shared", content_id="99"), build_place(id="new-a", content_id="2")])

    exit_code = run_add(make_args(input_path=input_path, catalog_path=catalog_path, apply=True))

    assert exit_code == 0
    catalog = read_catalog(catalog_path)
    assert len(catalog["places"]) == 2  # 기존 1 + 신규 1 (shared는 건너뜀)
    output = capsys.readouterr().out
    assert "이미 반영됨(건너뜀): 1곳" in output


# --- 활성화 모드: 대상 범위 ---------------------------------------------------


def test_activate_main_skips_alternate_and_leaves_outside_places_untouched(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(
        catalog_path,
        [
            build_place(id="in-input-standard", content_id="1", mvp_tier="standard", is_active=False),
            build_place(id="in-input-alternate", content_id="2", mvp_tier=ALTERNATE_TIER, is_active=False),
            build_place(id="outside-input", content_id="3", mvp_tier="standard", is_active=False),
        ],
    )
    write_input(
        input_path,
        [
            build_place(id="in-input-standard", content_id="1", mvp_tier="standard"),
            build_place(id="in-input-alternate", content_id="2", mvp_tier=ALTERNATE_TIER),
        ],
    )

    exit_code = run_activate(make_args(input_path=input_path, catalog_path=catalog_path, apply=True, activate="main"))
    assert exit_code == 0

    catalog = read_catalog(catalog_path)
    by_id = {p["id"]: p for p in catalog["places"]}
    assert by_id["in-input-standard"]["is_active"] is True
    assert by_id["in-input-alternate"]["is_active"] is False  # alternate는 main에서 제외
    assert by_id["outside-input"]["is_active"] is False  # 입력 밖은 절대 건드리지 않음


def test_activate_all_activates_every_input_place_regardless_of_tier(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(
        catalog_path,
        [
            build_place(id="in-input-standard", content_id="1", mvp_tier="standard", is_active=False),
            build_place(id="in-input-alternate", content_id="2", mvp_tier=ALTERNATE_TIER, is_active=False),
            build_place(id="outside-input", content_id="3", mvp_tier="standard", is_active=False),
        ],
    )
    write_input(
        input_path,
        [
            build_place(id="in-input-standard", content_id="1", mvp_tier="standard"),
            build_place(id="in-input-alternate", content_id="2", mvp_tier=ALTERNATE_TIER),
        ],
    )

    exit_code = run_activate(make_args(input_path=input_path, catalog_path=catalog_path, apply=True, activate="all"))
    assert exit_code == 0

    catalog = read_catalog(catalog_path)
    by_id = {p["id"]: p for p in catalog["places"]}
    assert by_id["in-input-standard"]["is_active"] is True
    assert by_id["in-input-alternate"]["is_active"] is True
    assert by_id["outside-input"]["is_active"] is False


def test_activate_dry_run_does_not_write(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="in-input", content_id="1", mvp_tier="standard", is_active=False)])
    write_input(input_path, [build_place(id="in-input", content_id="1", mvp_tier="standard")])

    before = catalog_path.read_bytes()
    exit_code = run_activate(make_args(input_path=input_path, catalog_path=catalog_path, apply=False, activate="main"))

    assert exit_code == 0
    assert catalog_path.read_bytes() == before


def test_resolve_activation_targets_main_excludes_alternate():
    places = [
        build_place(id="a", mvp_tier="standard"),
        build_place(id="b", mvp_tier=ALTERNATE_TIER),
    ]
    assert resolve_activation_targets(places, "main") == {"a"}
    assert resolve_activation_targets(places, "all") == {"a", "b"}


# --- --exclude-areas (활성화 모드 전용) --------------------------------------


def test_resolve_activation_targets_exclude_areas_narrows_the_set():
    places = [
        build_place(id="a", mvp_tier="standard", area="gijang"),
        build_place(id="b", mvp_tier=ALTERNATE_TIER, area="gijang"),
        build_place(id="c", mvp_tier="standard", area="seomyeon"),
    ]
    assert resolve_activation_targets(places, "all", exclude_areas={"gijang"}) == {"c"}
    assert resolve_activation_targets(places, "all") == {"a", "b", "c"}  # 기본값(None)은 기존 동작과 동일


def test_activate_with_exclude_areas_has_correct_counts_and_report(tmp_path, capsys):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    phase2_places = [
        build_place(id="gijang-a", content_id="2", area="gijang", mvp_tier="standard"),
        build_place(id="gijang-b", content_id="3", area="gijang", mvp_tier=ALTERNATE_TIER),
        build_place(id="seomyeon-a", content_id="4", area="seomyeon", mvp_tier="standard"),
    ]
    # 실제 흐름처럼 활성화 전에 이미 카탈로그에 비활성으로 들어있는 상태.
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1"), *phase2_places])
    write_input(input_path, phase2_places)

    exit_code = run_activate(
        make_args(input_path=input_path, catalog_path=catalog_path, apply=True, activate="all", exclude_areas="gijang")
    )

    assert exit_code == 0
    catalog = read_catalog(catalog_path)
    by_id = {p["id"]: p for p in catalog["places"]}
    assert by_id["gijang-a"]["is_active"] is False
    assert by_id["gijang-b"]["is_active"] is False
    assert by_id["seomyeon-a"]["is_active"] is True
    assert by_id["existing-a"]["is_active"] is False  # 입력 파일 밖은 절대 안 건드림

    output = capsys.readouterr().out
    assert "대상(입력 파일 기준): 1곳" in output
    assert "제외된 장소: 2곳" in output
    assert "'gijang': 2" in output


def test_activate_without_exclude_areas_is_unaffected(tmp_path):
    # exclude_areas를 안 주면(기존 호출부처럼) 기존 동작과 완전히 같다.
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    phase2_places = [
        build_place(id="gijang-a", content_id="2", area="gijang", mvp_tier="standard"),
        build_place(id="seomyeon-a", content_id="3", area="seomyeon", mvp_tier="standard"),
    ]
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1"), *phase2_places])
    write_input(input_path, phase2_places)

    exit_code = run_activate(make_args(input_path=input_path, catalog_path=catalog_path, apply=True, activate="all"))

    assert exit_code == 0
    catalog = read_catalog(catalog_path)
    by_id = {p["id"]: p for p in catalog["places"]}
    assert by_id["gijang-a"]["is_active"] is True
    assert by_id["seomyeon-a"]["is_active"] is True


def test_exclude_areas_rejected_in_add_mode(tmp_path, monkeypatch, capsys):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1")])
    write_input(input_path, [build_place(id="new-a", content_id="2")])

    before = catalog_path.read_bytes()
    monkeypatch.setattr(
        sys, "argv", ["add_busan_expansion_places.py", "--input", str(input_path), "--catalog", str(catalog_path), "--exclude-areas", "gijang"]
    )
    exit_code = main()

    assert exit_code == 1
    assert catalog_path.read_bytes() == before
    assert "--activate 모드에서만" in capsys.readouterr().out


def test_exclude_areas_rejects_unknown_area_without_writing(tmp_path):
    catalog_path = tmp_path / "busan.json"
    input_path = tmp_path / "input.json"
    write_catalog(catalog_path, [build_place(id="existing-a", content_id="1", mvp_tier="standard", is_active=False)])
    write_input(input_path, [build_place(id="existing-a", content_id="1", mvp_tier="standard")])

    before = catalog_path.read_bytes()
    exit_code = run_activate(
        make_args(
            input_path=input_path,
            catalog_path=catalog_path,
            apply=True,
            activate="all",
            exclude_areas="not-a-real-area",
        )
    )

    assert exit_code == 1
    assert catalog_path.read_bytes() == before
