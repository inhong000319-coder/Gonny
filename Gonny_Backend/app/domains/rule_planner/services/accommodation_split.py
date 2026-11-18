from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest

from .accommodation_scoring import compute_day_endpoints, compute_reference_point, rank_accommodations
from .travel_estimate import estimate_straight_line_travel_minutes, haversine_distance_km, scoring_minutes

AccommodationSplitMode = Literal["single", "two", "auto"]

# "알아서"(auto)는 분할이 한 곳보다 이동시간 합계를 10% 이상 줄여줄 때만 분할한다.
# 10%는 사용자가 확정한 임계값으로, 근소한 차이로 숙소를 옮기는 번거로움이 이동시간
# 절감보다 크다고 보는 기준이다 - 작은 개선(예: 2~3%)에도 매번 분할을 권하면
# 체크아웃/체크인을 늘리는 비용에 비해 체감 이득이 적다.
AUTO_SPLIT_MIN_GAIN_RATIO = 0.10

# 5박 이상에서도 숙소 수는 3곳을 넘기지 않는다(사용자 확정 상한).
MAX_STAYS_CAP = 3


def _max_stays_for_nights(nights: int) -> int:
    if nights <= 2:
        return 1
    if nights <= 4:
        return 2
    return MAX_STAYS_CAP


def _partitions_with_k_parts(nights: int, k: int) -> list[tuple[int, ...]]:
    """All k-tuples summing to `nights` where every part is >=1, and every
    part that is neither first nor last (a "middle" stay) is >=2 - the
    user-confirmed rule that a stay sandwiched between two others must be
    at least 2 nights, while the two end stays may be a single night."""

    def helper(remaining: int, parts_left: int, position: int) -> list[list[int]]:
        if parts_left == 1:
            return [[remaining]] if remaining >= 1 else []
        min_this = 1 if position == 0 else 2
        results: list[list[int]] = []
        for this_part in range(min_this, remaining + 1):
            left = remaining - this_part
            remaining_parts_after = parts_left - 1
            # Of the parts still to place, the last one (global position k-1)
            # only needs >=1; the rest are middle stays needing >=2 each.
            min_needed_rest = 1 + 2 * (remaining_parts_after - 1)
            if left < min_needed_rest:
                continue
            for rest in helper(left, parts_left - 1, position + 1):
                results.append([this_part] + rest)
        return results

    return [tuple(parts) for parts in helper(nights, k, 0)]


def allowed_partitions(nights: int) -> list[tuple[int, ...]]:
    """Every allowed way to split `nights` nights across 1..max_stays
    accommodations, per the user-confirmed rule: middle stays need >=2
    nights, end stays allow 1, and the max stay count is 1 for 1-2 nights,
    2 for 3-4 nights, 3 for 5+ nights (capped at MAX_STAYS_CAP). Ordered by
    stay count ascending, then by first-part size descending within a
    count (both ties the selection logic in this module relies on)."""
    if nights < 1:
        raise ValueError(f"nights must be >= 1, got {nights}")
    max_stays = _max_stays_for_nights(nights)
    partitions: list[tuple[int, ...]] = []
    for k in range(1, max_stays + 1):
        partitions.extend(_partitions_with_k_parts(nights, k))
    return partitions


@dataclass(frozen=True)
class StayWindow:
    stay_index: int
    start_night: int
    nights: int
    day_numbers: list[int]


def build_stay_windows(partition: tuple[int, ...], days: int) -> list[StayWindow]:
    """Maps a partition of nights onto the trip's days. Night n belongs to
    whichever stay its running total falls into; day d's first leg uses
    night max(d-1, 1)'s stay and its last leg uses night min(d, nights)'s
    stay (day 1 and the final day both collapse to a single night, so no
    special-casing is needed) - see the module docstring's day/night
    mapping. A day shared by two stays (a checkout day) appears in both
    stays' day_numbers."""
    nights = sum(partition)
    night_to_stay: dict[int, int] = {}
    night_cursor = 1
    for stay_index, stay_nights in enumerate(partition):
        for _ in range(stay_nights):
            night_to_stay[night_cursor] = stay_index
            night_cursor += 1

    day_numbers_by_stay: dict[int, list[int]] = {i: [] for i in range(len(partition))}
    for day_number in range(1, days + 1):
        start_night = max(day_number - 1, 1)
        end_night = min(day_number, nights)
        for stay_index in (night_to_stay[start_night], night_to_stay[end_night]):
            if day_number not in day_numbers_by_stay[stay_index]:
                day_numbers_by_stay[stay_index].append(day_number)

    windows: list[StayWindow] = []
    night_cursor = 1
    for stay_index, stay_nights in enumerate(partition):
        windows.append(
            StayWindow(
                stay_index=stay_index,
                start_night=night_cursor,
                nights=stay_nights,
                day_numbers=sorted(day_numbers_by_stay[stay_index]),
            )
        )
        night_cursor += stay_nights
    return windows


@dataclass(frozen=True)
class StayAccommodationPlan:
    stay_index: int
    start_night: int
    nights: int
    day_numbers: list[int]
    accommodation: AccommodationData | None
    alternatives: list[AccommodationData]


def resolve_stay_accommodations(
    stay_windows: list[StayWindow],
    *,
    accommodations: list[AccommodationData],
    request: NormalizedRuleRequest,
    city_catalog: CityPlaceCatalog,
    day_place_map: dict[int, list[PlaceData]],
    forced_ids: list[str | None] | None = None,
    require_distinct: bool = False,
) -> list[StayAccommodationPlan] | None:
    """Resolves one accommodation (plus its alternatives) per stay window,
    reusing compute_reference_point/compute_day_endpoints/rank_accommodations
    unchanged - each is restricted to only that stay's own day_numbers, so
    the scoring itself (budget/companion/parking/distance tiers) is
    identical to the single-accommodation path, just over a narrower
    day_place_map. Returns None when require_distinct is True and some
    stay (with no forced id) can't find an accommodation not already
    claimed by an earlier stay - the caller treats that partition as
    infeasible."""
    claimed_ids: set[str] = set()
    forced = forced_ids if forced_ids is not None else [None] * len(stay_windows)
    plans: list[StayAccommodationPlan] = []
    for window, forced_id in zip(stay_windows, forced):
        restricted_map = {day: day_place_map[day] for day in window.day_numbers if day in day_place_map}
        reference_point = compute_reference_point(restricted_map, city_catalog)
        day_endpoints = compute_day_endpoints(restricted_map)
        ranked = rank_accommodations(accommodations, request, reference_point, day_endpoints)

        if forced_id is not None:
            pick = next((a for a in accommodations if a.id == forced_id), None)
            # Excludes claimed_ids (earlier stays' picks) before slicing to
            # 3, not just the final all-picked-ids pass below - otherwise a
            # forced stay could show fewer than 3 alternatives (one sliced
            # away, then stripped by the final pass) where the auto-select
            # branch below would have backfilled a 3rd. For a single stay
            # (no earlier stays), claimed_ids is always empty here, so this
            # reproduces the pre-split fixed-accommodation_id alternatives
            # exactly ([a for a in ranked if a.id != exclude_id][:3]).
            alternatives = [a for a in ranked if a.id != forced_id and a.id not in claimed_ids][:3]
        else:
            pick = next((a for a in ranked if a.id not in claimed_ids), None)
            if pick is None:
                if require_distinct:
                    return None
                alternatives = []
            else:
                alternatives = [a for a in ranked if a.id != pick.id and a.id not in claimed_ids][:3]

        if pick is not None:
            claimed_ids.add(pick.id)
        plans.append(
            StayAccommodationPlan(
                stay_index=window.stay_index,
                start_night=window.start_night,
                nights=window.nights,
                day_numbers=window.day_numbers,
                accommodation=pick,
                alternatives=alternatives,
            )
        )

    # A stay's alternatives are computed before later stays are resolved,
    # so they can still contain an accommodation a *later* stay ends up
    # picking. Final pass: no stay's alternatives ever list an
    # accommodation any stay actually selected (single-stay plans are
    # unaffected - their own pick was already excluded above).
    all_picked_ids = {plan.accommodation.id for plan in plans if plan.accommodation is not None}
    return [
        plan
        if not any(a.id in all_picked_ids for a in plan.alternatives)
        else StayAccommodationPlan(
            stay_index=plan.stay_index,
            start_night=plan.start_night,
            nights=plan.nights,
            day_numbers=plan.day_numbers,
            accommodation=plan.accommodation,
            alternatives=[a for a in plan.alternatives if a.id not in all_picked_ids],
        )
        for plan in plans
    ]


def accommodation_leg_minutes(
    accommodation: AccommodationData | None,
    place: PlaceData,
    *,
    mode: str | None,
    city: str,
) -> int:
    """Minutes for one accommodation<->place leg, mirroring
    estimate_day_total_minutes's existing mode=None-vs-mode-given branching
    (see travel_estimate.estimate_accommodation_transition_minutes /
    _scoring_accommodation_transition_minutes) so the split comparison
    metric and day-duration warnings use "the existing default" exactly as
    specified when a day has no transport_by_day entry."""
    if accommodation is None or accommodation.latitude is None or accommodation.longitude is None:
        return 0
    if place.latitude is None or place.longitude is None:
        return 0
    distance_km = haversine_distance_km(
        accommodation.latitude, accommodation.longitude, place.latitude, place.longitude
    )
    if mode is None:
        return estimate_straight_line_travel_minutes(distance_km)
    return scoring_minutes(mode, distance_km, city)


def day_start_end_accommodations(
    stay_plans: list[StayAccommodationPlan], days: int
) -> dict[int, tuple[AccommodationData | None, AccommodationData | None]]:
    """For each day, which stay's accommodation the day starts from and
    which it ends at - see build_stay_windows for the night/day mapping
    this mirrors. With a single stay, both sides are always that one
    stay's accommodation, reproducing the pre-split single-accommodation
    behavior exactly."""
    nights = sum(plan.nights for plan in stay_plans)
    night_to_stay: dict[int, int] = {}
    night_cursor = 1
    for plan in stay_plans:
        for _ in range(plan.nights):
            night_to_stay[night_cursor] = plan.stay_index
            night_cursor += 1
    accommodation_by_stay = {plan.stay_index: plan.accommodation for plan in stay_plans}

    result: dict[int, tuple[AccommodationData | None, AccommodationData | None]] = {}
    for day_number in range(1, days + 1):
        start_night = max(day_number - 1, 1)
        end_night = min(day_number, nights)
        start_acc = accommodation_by_stay.get(night_to_stay.get(start_night))
        end_acc = accommodation_by_stay.get(night_to_stay.get(end_night))
        result[day_number] = (start_acc, end_acc)
    return result


def _accommodation_adjacent_minutes_total(
    stay_plans: list[StayAccommodationPlan],
    day_place_map: dict[int, list[PlaceData]],
    *,
    transport_by_day: list[str] | None,
    city: str,
    days: int,
) -> int:
    day_accs = day_start_end_accommodations(stay_plans, days)
    total = 0
    for day_number in range(1, days + 1):
        places = day_place_map.get(day_number) or []
        if not places:
            continue
        mode = transport_by_day[day_number - 1] if transport_by_day and day_number - 1 < len(transport_by_day) else None
        start_acc, end_acc = day_accs.get(day_number, (None, None))
        total += accommodation_leg_minutes(start_acc, places[0], mode=mode, city=city)
        total += accommodation_leg_minutes(end_acc, places[-1], mode=mode, city=city)
    return total


def select_stay_plan(
    *,
    split_mode: AccommodationSplitMode,
    nights: int,
    days: int,
    accommodations: list[AccommodationData],
    request: NormalizedRuleRequest,
    city_catalog: CityPlaceCatalog,
    day_place_map: dict[int, list[PlaceData]],
    transport_by_day: list[str] | None,
    city: str,
    forced_first_id: str | None = None,
) -> tuple[list[StayAccommodationPlan], str | None]:
    """Chooses the stay plan for `split_mode`, always falling back to a
    single stay (never an error) when a split isn't possible or isn't
    worth it, per the user-confirmed rules:
    - "single": always one stay.
    - "two": the best (shortest accommodation<->place time) among the
      allowed exactly-2-stay partitions, taking it even if the gain is
      small; falls back to one stay (with a note) when nights<=2 or no
      2-stay partition can get distinct accommodations.
    - "auto": compares one stay against the best of every allowed
      multi-stay partition, splitting only when that candidate's gain over
      one stay is >= AUTO_SPLIT_MIN_GAIN_RATIO.
    `forced_first_id` reproduces the legacy recalculate() accommodation_id
    behavior (always the first stay, in every candidate) alongside the
    split search.
    """
    single_windows = build_stay_windows((nights,), days)
    single_forced = [forced_first_id]
    single_plan = resolve_stay_accommodations(
        single_windows,
        accommodations=accommodations,
        request=request,
        city_catalog=city_catalog,
        day_place_map=day_place_map,
        forced_ids=single_forced,
        require_distinct=False,
    )
    assert single_plan is not None  # a single stay never fails (require_distinct=False)

    if split_mode == "single":
        return single_plan, None

    candidate_partitions = [p for p in allowed_partitions(nights) if len(p) >= 2]
    if split_mode == "two":
        candidate_partitions = [p for p in candidate_partitions if len(p) == 2]

    feasible: list[tuple[tuple[int, ...], list[StayAccommodationPlan], int]] = []
    for partition in candidate_partitions:
        windows = build_stay_windows(partition, days)
        forced_ids = [forced_first_id] + [None] * (len(partition) - 1)
        plan = resolve_stay_accommodations(
            windows,
            accommodations=accommodations,
            request=request,
            city_catalog=city_catalog,
            day_place_map=day_place_map,
            forced_ids=forced_ids,
            require_distinct=True,
        )
        if plan is None:
            continue
        minutes = _accommodation_adjacent_minutes_total(
            plan, day_place_map, transport_by_day=transport_by_day, city=city, days=days
        )
        feasible.append((partition, plan, minutes))

    if not feasible:
        if nights <= 2:
            note = "숙박일수가 2박 이하라 숙소를 한 곳으로 유지합니다."
        else:
            note = "서로 다른 숙소를 찾지 못해 분할 없이 한 곳으로 유지합니다."
        return single_plan, note

    # Deterministic tie-break: shortest total time, then fewer stays, then
    # the candidate whose first stay is the longest, then the partition
    # itself (fully deterministic even if every other key ties).
    feasible.sort(key=lambda c: (c[2], len(c[0]), -c[0][0], c[0]))
    best_partition, best_plan, best_minutes = feasible[0]

    if split_mode == "two":
        return best_plan, None

    single_minutes = _accommodation_adjacent_minutes_total(
        single_plan, day_place_map, transport_by_day=transport_by_day, city=city, days=days
    )
    gain_ratio = (single_minutes - best_minutes) / single_minutes if single_minutes > 0 else 0.0
    if gain_ratio >= AUTO_SPLIT_MIN_GAIN_RATIO:
        return best_plan, None
    note = (
        f"분할 시 이동시간 절감이 {gain_ratio:.0%}로 기준({AUTO_SPLIT_MIN_GAIN_RATIO:.0%}) 미달이라 "
        "숙소를 한 곳으로 유지합니다."
    )
    return single_plan, note
