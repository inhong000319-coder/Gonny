"""Fill slot_bias for zero-bias, non-restaurant, active places using the
S4-real rule (see local_only/reports/slot_bias_s4_real.md,
slot_bias_zero_bias_places.md).

Rule: for each city/slot, split existing places with a nonzero slot_bias
for that slot into two groups by whether that slot is in their time_fit
("has") or not ("not_has"). The fill value for a target place's slot is
the rounded mean of whichever group its time_fit puts it in. A group with
zero samples is skipped (no fill). One additional exception, requested
explicitly for this apply: busan's afternoon "not_has" group (n=1) is
also skipped, even though it has one sample - its single data point was
judged too thin to apply (see report for the measured justification: it
never changed any selection outcome across any simulated request set).

This script never overwrites an existing nonzero slot_bias value, and
never touches restaurants (places where "food" is in concept_tags, i.e.
raw activity_type contains "미식") or inactive places. Idempotent: running
twice produces zero changes the second time, because target places are
selected by "slot_bias is empty", which becomes false after the first
run.

Usage:
    python scripts/apply_slot_bias_s4_real.py --dry-run
    python scripts/apply_slot_bias_s4_real.py --apply
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "app" / "data" / "destinations"
CITIES = ("seoul", "busan", "jeju")
TIME_SLOTS = ("morning", "afternoon", "evening")

# The 52 target place ids, frozen at the time this script was written
# (verified dry-run: seoul 12 / busan 9 / jeju 31). compute_group_stats()
# always excludes these from the "existing nonzero slot_bias" reference
# population, even after they are filled - otherwise a second run would
# feed this script's own synthetic fills back into the group means it
# verifies against, which would silently change what "correct" means on
# every re-run instead of keeping a fixed reference. This is what makes
# the idempotency check (run twice, second run changes nothing) actually
# mean something.
FROZEN_TARGET_IDS = {
    "seoul": {"gyeongbokgung", "bukchon", "namsan-tower", "yeouido-hangang", "coex", "changdeokgung",
              "yeonnam-forest", "seokchon-lake", "ddp", "lotte-world-adventure", "woori-sulfur-spa", "bongil-spa-land"},
    "busan": {"haeundae-beach", "dongbaek-island", "blue-line-park", "gamcheon-culture-village",
              "songdo-cable-car", "taejongdae", "heosimchung", "shinsegae-spaland", "club-d-oasis"},
    "jeju": {"hamdeok-beach", "seongsan-ilchulbong", "seopjikoji", "bijarim", "hallim-park", "hyeopjae-beach",
             "camellia-hill", "jungmun-saekdal", "soesokkak", "sanbanggulsa", "yongmeori-coast", "cheonjiyeon-falls",
             "jeongbang-falls", "oedolgae", "songaksan", "manjanggul", "yongduam", "jeju-folk-village",
             "lee-jungseob-residence", "saeyeongyo-saeseom", "jeju-national-museum", "jeju-mokgwana",
             "pyoseon-haevichi-beach", "halla-arboretum", "samseonghyeol", "jeju-43-peace-park", "sangumburi",
             "namwon-keuneong", "hueree-park", "bonte-museum", "alddreu-airfield"},
}

# Hardcoded fill table (S4-real), with its basis documented. Verified
# against a fresh computation from the current data before anything is
# applied; the script aborts if they disagree (data has moved since this
# table was derived, re-run the investigation instead of trusting this
# table blindly).
#
#   city     slot       has_fill (n)   not_has_fill (n)
#   seoul    morning    +5 (n=14)      -4 (n=12)
#   seoul    afternoon  +5 (n=27)      n=0, no fill
#   seoul    evening    +5 (n=13)      -4 (n=14)
#   busan    morning    +5 (n=8)       -3 (n=6)
#   busan    afternoon  +6 (n=13)      n=1, SKIPPED BY REQUEST (see module docstring)
#   busan    evening    +7 (n=7)       -3 (n=7)
#   jeju     morning    +5 (n=11)      -4 (n=2)  <- n=2, provisional, see report
#   jeju     afternoon  +6 (n=13)      n=0, no fill
#   jeju     evening    +6 (n=2)       -5 (n=11) <- has_fill n=2, provisional, see report
# NOTE: these are the raw S4-real computed values (what verify_table()
# checks against a fresh recomputation) - busan afternoon not_has is +2
# here because that IS what the data computes to (n=1). The decision to
# not apply it lives separately in MANUAL_SKIP_CELLS/fill_value_for(), so
# that verification always checks "did the data change", never "did we
# remember to skip it".
EXPECTED_TABLE = {
    "seoul": {"morning": {"has": 5, "not_has": -4}, "afternoon": {"has": 5, "not_has": None}, "evening": {"has": 5, "not_has": -4}},
    "busan": {"morning": {"has": 5, "not_has": -3}, "afternoon": {"has": 6, "not_has": 2}, "evening": {"has": 7, "not_has": -3}},
    "jeju": {"morning": {"has": 5, "not_has": -4}, "afternoon": {"has": 6, "not_has": None}, "evening": {"has": 6, "not_has": -5}},
}
# Cells that are skipped even though a computed value exists (by explicit
# request, not because the sample is empty).
MANUAL_SKIP_CELLS = {("busan", "afternoon", "not_has")}
# Cells whose basis is n<3 and is flagged as a provisional judgment, not
# a statistically settled rule - carried through to the report verbatim.
PROVISIONAL_CELLS = {("jeju", "morning", "not_has"), ("jeju", "evening", "has")}


def load_city(city: str) -> tuple[dict, list[dict]]:
    path = DATA_DIR / f"{city}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data, data["places"]


def is_non_restaurant_active(place: dict) -> bool:
    return bool(place.get("is_active", True)) and "미식" not in place.get("activity_type", [])


def is_slot_bias_empty(place: dict) -> bool:
    return not place.get("slot_bias")


def compute_group_stats(places: list[dict], exclude_ids: set[str]) -> dict:
    table = {}
    for slot in TIME_SLOTS:
        has_vals, not_has_vals = [], []
        for p in places:
            if not is_non_restaurant_active(p) or p["id"] in exclude_ids:
                continue
            bias = p.get("slot_bias") or {}
            if slot not in bias:
                continue
            v = bias[slot]
            (has_vals if slot in (p.get("time_fit") or []) else not_has_vals).append(v)
        table[slot] = {
            "has_n": len(has_vals), "has_fill": round(statistics.mean(has_vals)) if has_vals else None,
            "not_has_n": len(not_has_vals), "not_has_fill": round(statistics.mean(not_has_vals)) if not_has_vals else None,
        }
    return table


def verify_table(computed: dict) -> list[str]:
    """Returns a list of mismatch descriptions; empty means verified OK."""
    mismatches = []
    for city in CITIES:
        for slot in TIME_SLOTS:
            for group in ("has", "not_has"):
                expected = EXPECTED_TABLE[city][slot][group]
                actual = computed[city][slot][f"{group}_fill"]
                if expected != actual:
                    mismatches.append(f"{city} {slot} {group}: 하드코딩={expected} 재계산={actual}")
    return mismatches


def target_places(places: list[dict]) -> list[dict]:
    return [p for p in places if is_non_restaurant_active(p) and is_slot_bias_empty(p)]


def fill_value_for(city: str, slot: str, time_fit: list[str]) -> tuple[int | None, str]:
    """Returns (value, reason). reason is 'has'/'not_has'/'skip_manual'/'skip_no_sample'/'skip_no_time_fit'."""
    if not time_fit:
        return None, "skip_no_time_fit"
    group = "has" if slot in time_fit else "not_has"
    if (city, slot, group) in MANUAL_SKIP_CELLS:
        return None, "skip_manual"
    value = EXPECTED_TABLE[city][slot][group]
    if value is None:
        return None, "skip_no_sample"
    return value, group


def build_plan(city: str, places: list[dict]) -> list[dict]:
    plan = []
    for p in target_places(places):
        new_bias = {}
        detail = {}
        for slot in TIME_SLOTS:
            value, reason = fill_value_for(city, slot, p.get("time_fit") or [])
            detail[slot] = (value, reason)
            if value is not None:
                new_bias[slot] = value
        plan.append({"id": p["id"], "name": p.get("name"), "time_fit": p.get("time_fit"), "new_slot_bias": new_bias, "detail": detail})
    return plan


def dump_city(data: dict, path: Path) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    computed = {}
    all_places = {}
    for city in CITIES:
        data, places = load_city(city)
        all_places[city] = (data, places)
        computed[city] = compute_group_stats(places, FROZEN_TARGET_IDS[city])

    mismatches = verify_table(computed)
    if mismatches:
        print("[중단] 하드코딩된 채움표가 현재 데이터에서 재계산한 값과 다릅니다:")
        for m in mismatches:
            print(f"  - {m}")
        return 1
    print("[확인] 채움표가 현재 데이터와 일치함 (재계산 검증 통과, 대상 52곳은 기준 집단에서 제외하고 계산)")

    total_plan = {}
    for city in CITIES:
        _, places = all_places[city]
        plan = build_plan(city, places)
        total_plan[city] = plan

    print("\n=== 대상(아직 비어 있는) 장소 수 ===")
    expected_counts = {"seoul": 12, "busan": 9, "jeju": 31}
    total_remaining = sum(len(total_plan[c]) for c in CITIES)
    total_expected = sum(expected_counts.values())
    for city in CITIES:
        n = len(total_plan[city])
        print(f"  {city}: {n}곳 (최초 기준 {expected_counts[city]})")
    if total_remaining == total_expected:
        print(f"[확인] 최초 적용 전 상태: 52곳 전부 비어 있음")
    elif total_remaining == 0:
        print(f"[확인] 이미 전부 채워져 있음 - 적용 대상 0곳(idempotent 상태)")
    else:
        print(f"[중단] 대상 장소 수가 '최초 상태(52곳 전부 미보유)'도 '적용 후 상태(0곳)'도 아닙니다"
              f"(현재 {total_remaining}곳) - 부분 적용 또는 외부 변경 가능성, 확인 필요.")
        return 1

    print("\n=== 장소·슬롯별 채움값 (dry-run) ===")
    for city in CITIES:
        print(f"\n-- {city} --")
        for item in total_plan[city]:
            cells = []
            for slot in TIME_SLOTS:
                value, reason = item["detail"][slot]
                cells.append(f"{slot}={value if value is not None else reason}")
            print(f"  {item['id']} ({item['name']}) time_fit={item['time_fit']}: {', '.join(cells)}")

    print("\n=== 건너뛴 칸 (의도적 제외) ===")
    for city in CITIES:
        for item in total_plan[city]:
            for slot in TIME_SLOTS:
                value, reason = item["detail"][slot]
                if reason == "skip_manual":
                    print(f"  {city} {item['id']} {slot}: 수동 제외(부산 afternoon 미포함, n=1)")

    if args.dry_run:
        print("\n[dry-run] 실제 파일은 수정하지 않았습니다.")
        return 0

    # --apply
    changed_files = []
    for city in CITIES:
        data, places = all_places[city]
        by_id = {p["id"]: p for p in places}
        before_snapshot = {p["id"]: dict(p.get("slot_bias") or {}) for p in places}
        n_changed = 0
        for item in total_plan[city]:
            place = by_id[item["id"]]
            if place.get("slot_bias"):
                # safety: never overwrite an existing nonzero value
                raise RuntimeError(f"{city}/{item['id']}: slot_bias가 이미 있음 - 중단")
            if not item["new_slot_bias"]:
                continue
            place["slot_bias"] = item["new_slot_bias"]
            n_changed += 1
        # verify no other place's pre-existing nonzero slot_bias changed
        for p in places:
            before = before_snapshot[p["id"]]
            after = p.get("slot_bias") or {}
            if before and before != after:
                raise RuntimeError(f"{city}/{p['id']}: 기존 slot_bias 값이 변경됨 - 중단")
        path = DATA_DIR / f"{city}.json"
        dump_city(data, path)
        changed_files.append((city, n_changed))
        print(f"[적용] {city}.json: {n_changed}곳에 slot_bias 채움")

    print("\n[완료] 적용됨:", changed_files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
