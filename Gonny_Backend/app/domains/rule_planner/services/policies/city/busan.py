from __future__ import annotations

from collections import defaultdict

from app.domains.rule_planner.schemas import NormalizedRuleRequest

from ...constants import BUSAN_AREA_NEIGHBORS, BUSAN_AREA_ROUTE_ORDER

# Deliberately does NOT define price_exact_match_bonus() - busan keeps the
# shared default (10, policies/city/__init__.py.price_exact_match_bonus's
# fallback). Measured (local_only/reports/accommodation_price_bonus_
# sensitivity.md): busan's dominant pick (라발스호텔) wins on the distance
# term, not price data, so lowering this bonus only removed OTHER
# candidates' one competitive edge and made the existing concentration
# worse (top1 share 49.0%->69.8%, Grid2) - the opposite of seoul/jeju.


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    concept_weights: dict[str, int] = defaultdict(int)
    if "food" in request.concepts:
        for area in ("nampo", "gwangalli", "songdo"):
            concept_weights[area] += 16
    if "shopping" in request.concepts:
        for area in ("nampo", "haeundae"):
            concept_weights[area] += 12
    if "culture" in request.concepts:
        for area in ("nampo", "songdo"):
            concept_weights[area] += 14
    if "relax" in request.concepts:
        for area in ("haeundae", "gwangalli", "songdo"):
            concept_weights[area] += 12
    if "activity" in request.concepts:
        for area in ("haeundae", "songdo"):
            concept_weights[area] += 18
    if request.companion_type == "friend":
        for area in ("gwangalli", "nampo", "haeundae"):
            concept_weights[area] += 8
    if request.companion_type == "family":
        for area in ("haeundae", "songdo"):
            concept_weights[area] += 8

    return sorted(
        area_scores.keys(),
        key=lambda area: (
            area_scores[area] + concept_weights[area] + (6 if area in BUSAN_AREA_ROUTE_ORDER else 0),
            -BUSAN_AREA_ROUTE_ORDER.index(area) if area in BUSAN_AREA_ROUTE_ORDER else 0,
        ),
        reverse=True,
    )


def preferred_area_match_bonus() -> int:
    return 11


def same_area_continuity_bonus() -> int:
    return 12


def neighbor_area_bonus(previous_area: str | None, place_area: str) -> int:
    if not previous_area:
        return 0
    if place_area in BUSAN_AREA_NEIGHBORS.get(previous_area, set()):
        return 6
    return 0


def evening_food_bonus(time_slot: str, categories: set[str]) -> int:
    if time_slot == "evening" and {"food", "nightlife"} & categories:
        return 5
    return 0


# 2단계 장소(기장·강서·가덕도 등, 전부 is_active=false라 아직 라이브에는
# 영향 없음)가 활성화되면, 기존 coordinate_area_transition_bonus의 FAR
# 페널티(-6 고정, travel_estimate.py)만으로는 같은 날 일정에서 먼 구역으로
# 건너뛰는 이동을 억제하지 못한다 - 같은 메커니즘을 이미 쓰는 jeju.py 참고.
#
# 측정(임시 카탈로그에 2단계 131곳을 활성화해 84개 시나리오로 재측정,
# local_only 보고서 - this PR는 실제 활성화를 하지 않는다): 감점 없이는
# 자동차 90분 초과 구간 30건(최대 137분). 임계 12km/기본 -30/km당 -2를
# 적용하면 60분 초과 0건(최대 59분)으로 줄고, 서로 다른 장소 수·상위
# 장소 점유율(3.8%)은 그대로였다. 임계 15km는 110분짜리 구간이 1건
# 남아서, 20km는 90분 이하이지만 60분 초과가 68건 남아서 채택하지
# 않았다. 같은 값을 현재 라이브(2단계 비활성, 363곳)에 적용해도 60분
# 초과가 38->0건으로 줄고 고유 장소 수(111)는 바뀌지 않았다.
#
# jeju.py와 값이 같은 건 우연이 아니라 측정으로 각자 찾은 결과지만,
# accommodation_distance_score와 같은 이유(순환 임포트: jeju.py를
# import하면 policies.city -> jeju -> policies.city 순환이 생긴다)로
# 상수를 재사용하지 않고 독립적으로 둔다.
EXTREME_DISTANCE_KM_THRESHOLD = 12.0
EXTREME_DISTANCE_BASE_PENALTY = -30
EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM = -2


def extreme_distance_penalty(distance_km: float) -> int:
    if distance_km <= EXTREME_DISTANCE_KM_THRESHOLD:
        return 0
    overage_km = distance_km - EXTREME_DISTANCE_KM_THRESHOLD
    return EXTREME_DISTANCE_BASE_PENALTY + round(overage_km * EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM)


# Measured (local_only/reports/headroom_and_variants_analysis.md): busan's
# candidates already had a large reference_point score gap (median 8.0), so
# an additive distance term at -0.6~-2.0/km never changed a single pick in
# the 96-request sweep. Only the replacing form moves anything, and -4.0 was
# the coefficient where average distance (5.42km -> 5.44km) stayed
# essentially flat while budget fit improved (66.7% -> 83.3%). Left
# unrounded for the same reason as seoul (round() caused tie collapse there;
# busan had 0% ties either way, but there's no reason to round one city and
# not the other for the same hook).
ACCOMMODATION_DISTANCE_PENALTY_PER_KM = -4.0


def accommodation_distance_score(distances_km: list[float]) -> float:
    if not distances_km:
        return 0.0
    average_km = sum(distances_km) / len(distances_km)
    return average_km * ACCOMMODATION_DISTANCE_PENALTY_PER_KM
