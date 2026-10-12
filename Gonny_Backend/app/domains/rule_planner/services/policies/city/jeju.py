from __future__ import annotations

from collections import defaultdict

from app.domains.rule_planner.schemas import NormalizedRuleRequest

from ...constants import JEJU_AREA_NEIGHBORS, JEJU_AREA_ROUTE_ORDER


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    concept_weights: dict[str, int] = defaultdict(int)
    if "activity" in request.concepts:
        concept_weights["seongsan"] += 24
        concept_weights["east-jeju"] += 14
    if "nature" in request.concepts:
        for area in ("east-jeju", "seogwipo-west", "west-jeju", "seongsan"):
            concept_weights[area] += 14
    if "relax" in request.concepts:
        for area in ("west-jeju", "east-jeju", "seogwipo-west"):
            concept_weights[area] += 12
    if "food" in request.concepts:
        for area in ("east-jeju", "west-jeju"):
            concept_weights[area] += 10
    if "culture" in request.concepts:
        for area in ("east-jeju", "seogwipo-west"):
            concept_weights[area] += 9
    if request.companion_type == "friend":
        for area in ("east-jeju", "west-jeju", "seogwipo-west"):
            concept_weights[area] += 6
    if request.companion_type == "family":
        for area in ("seongsan", "west-jeju", "east-jeju"):
            concept_weights[area] += 8

    return sorted(
        area_scores.keys(),
        key=lambda area: (
            area_scores[area] + concept_weights[area] + (6 if area in JEJU_AREA_ROUTE_ORDER else 0),
            -JEJU_AREA_ROUTE_ORDER.index(area) if area in JEJU_AREA_ROUTE_ORDER else 0,
        ),
        reverse=True,
    )


def preferred_area_match_bonus() -> int:
    return 10


def same_area_continuity_bonus() -> int:
    return 12


def neighbor_area_bonus(previous_area: str | None, place_area: str) -> int:
    if not previous_area:
        return 0
    if place_area in JEJU_AREA_NEIGHBORS.get(previous_area, set()):
        return 5
    return 0


def evening_food_bonus(time_slot: str, categories: set[str]) -> int:
    if time_slot == "evening" and "food" in categories:
        return 3
    return 0


# 가정값: 실측 이동시간이 아니라, 제주 요청 96건 진단(2026-10 PR 설명 참고)에서
# 관찰된 구간 거리 분포로 정했다 - place->meal/meal->place 구간의 p95가
# 49~65km로 나왔고, 기존 coordinate_area_transition_bonus의 FAR 페널티(-6,
# travel_estimate.py)는 40~60km대 구간도 10km대 구간과 똑같이 -6만 줘서
# 억제력이 부족했다. 그 페널티를 대체하지 않고(모드·속도 가정값은 그대로
# 둔다), 제주에서만 더해지는 별도 페널티로 추가한다.
#
# 임계값을 살짝 넘는 구간(31~35km)과 섬을 가로지르는 구간(60km대)을 똑같이
# 취급하면 후자를 충분히 억제하지 못해(진단 중 발견한 실사례: 동쪽 활동 바로
# 다음 슬롯에 서쪽 해수욕장이 고정 페널티로도 안 밀려난 경우), 넘는 만큼
# 더 깎는 선형 가산을 둔다.
EXTREME_DISTANCE_KM_THRESHOLD = 30.0
EXTREME_DISTANCE_BASE_PENALTY = -30
EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM = -2


def extreme_distance_penalty(distance_km: float) -> int:
    if distance_km <= EXTREME_DISTANCE_KM_THRESHOLD:
        return 0
    overage_km = distance_km - EXTREME_DISTANCE_KM_THRESHOLD
    return EXTREME_DISTANCE_BASE_PENALTY + round(overage_km * EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM)
