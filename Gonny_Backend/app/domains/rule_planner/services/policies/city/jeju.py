from __future__ import annotations

from collections import defaultdict

from app.domains.destination_catalog.schemas import PlaceData
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


# 시연 피드백: 날마다 "아직 안 쓴 권역"을 고르는 기존 RuleItineraryService.
# _pick_day_area 규칙이 매일 섬을 가로지르게 해서, 숙소 하나에서 매일 다른
# 권역의 장소까지 거리가 멀어졌다(진단 결과 숙소 선택 자체는 거의 최선이었다
# - 원인은 일정 구성). 전날 권역이 있으면 "전날 권역 또는 인접 권역
# (JEJU_AREA_NEIGHBORS) 중 선호 순서가 가장 앞이고 장소가 남은 곳"을
# 기존의 "아직 안 쓴 권역 우선"보다 먼저 시도한다 - 해당하는 권역이 없으면
# None을 돌려줘 기존 로직(RuleItineraryService._pick_day_area)으로
# 폴백한다. 첫날(previous_day_area가 None)은 폴백을 그대로 타므로 여기서
# 따로 처리하지 않는다.
#
# 사전 측정(임시 복사본, 제주 요청 90건): 숙소→장소 거리 중앙값 23.3->17.9km,
# 숙소 구간 중 자동차 40분 초과 65%->60%, 서로 다른 장소 수 44->45, 상위
# 5개 장소 점유율 29.5%->23.6%(오히려 분산됨). #129로 줄인 숙소 제외 이동
# (40분/60분 초과 6%/0%)은 그대로였다 - 자세한 수치는
# local_only/reports/jeju_day_area_continuity.md 참고.
def pick_day_area(
    preferred_areas: list[str],
    places: list[PlaceData],
    used_ids: set[str],
    used_day_areas: set[str],
    previous_day_area: str | None,
) -> str | None:
    if not previous_day_area:
        return None

    candidate_areas = {previous_day_area} | JEJU_AREA_NEIGHBORS.get(previous_day_area, set())
    ordered_candidates = [area for area in preferred_areas if area in candidate_areas]
    for candidate_area in ordered_candidates:
        if any(place.area == candidate_area and place.id not in used_ids for place in places):
            return candidate_area
    return None


# Same measured rationale as seoul.py's price_exact_match_bonus() - see
# that module's comment and local_only/reports/
# accommodation_price_bonus_sensitivity.md. Jeju's priced-accommodation
# selection ratio moved from 92.7%->38.5% (Grid2, vs a 20.0% priced
# catalog share) and ever-selected went 8->12 of 50.
def price_exact_match_bonus() -> int:
    return 6


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
#
# 2026-11 시연 피드백으로 30.0 -> 15.0으로 낮췄다. 30km는 진단 당시 p95
# (49~65km) 바로 밑을 억제하도록 잡은 값이라, 그보다 짧은 15~30km대 구간은
# 감점 없이 그대로 선택되고 있었다 - 이동이 "너무 멀다"는 시연 피드백이
# 가리킨 건 이 구간이었다. 임시 복사본에서 제주 요청 90건으로 재측정한
# 결과(local_only/reports/jeju_extreme_distance_threshold.md), 30->15km로
# 낮추면 숙소 제외 이동 중 자동차 40분 초과 비율이 20%->6%, 60분 초과가
# 7%->0%로 줄었고, 서로 다른 장소 수(45->44)와 상위 5개 장소 점유율
# (28.9%->29.5%)은 거의 그대로였다. 20km(13%/1%)·10km(7%/1%)도 같이
# 재봤는데 15km가 "40분 초과를 크게 줄이면서 다양성은 거의 안 건드리는"
# 균형이 가장 좋았다. 기본 감점(-30)과 km당 감점(-2)은 그대로 둔다.
EXTREME_DISTANCE_KM_THRESHOLD = 15.0
EXTREME_DISTANCE_BASE_PENALTY = -30
EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM = -2


def extreme_distance_penalty(distance_km: float) -> int:
    if distance_km <= EXTREME_DISTANCE_KM_THRESHOLD:
        return 0
    overage_km = distance_km - EXTREME_DISTANCE_KM_THRESHOLD
    return EXTREME_DISTANCE_BASE_PENALTY + round(overage_km * EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM)


# 가정값: accommodation_scoring.py의 기존 reference_point 거리 등급(1/3/7km
# 임계값, CLOSE/NEARBY/FAR 보너스)은 "숙소가 하나의 구역 안에 있는가"를
# 묻는 질문에 맞춰진 값이라, 제주 실측(PR #86 진단 - 숙소->첫 장소 평균
# 35.5km)처럼 거리 자체가 10~40km대인 경우에 적용하면 거의 모든 후보가
# "FAR"(-6) 한 구간에 몰려 버려 후보 간 차별이 되지 않는다. 그래서 이산
# 등급을 재사용하지 않고, 날짜별 첫/마지막 장소까지 거리의 평균에 선형
# 페널티를 매겨 "거리 합이 작을수록 항상 더 유리하다"는 차별력을 유지한다.
# accommodation_scoring.py를 import하면 순환 임포트(accommodation_scoring
# -> policies.city -> jeju)가 생기므로 상수를 독립적으로 둔다.
#
# 계수(-0.6/km)는 기존 예산 적합도(최대 ±10)/동행 적합도(±5)/주차(최대 6)
# 보너스 폭과 비교해, 거리 차가 몇 km 수준이면 기존 보너스가 여전히
# 결정적이되 거리 차가 수십 km로 벌어지면 거리가 우선하도록 잡은 값이다 -
# 진단 결과로 조정 가능한 가정값.
#
# unrounded 유지 - seoul.py/busan.py와 같은 이유(round()는 서로 다른 거리를
# 같은 정수 점수로 몰아 동점을 늘린다). 측정 결과(local_only/reports/
# accommodation_concentration_causes.md) 제주 요청의 22.9~30%가 정확한
# 동점이었고 그 경우 항상 카탈로그 파일 순서가 승자를 결정했다.
ACCOMMODATION_DISTANCE_PENALTY_PER_KM = -0.6


def accommodation_distance_score(distances_km: list[float]) -> float:
    if not distances_km:
        return 0.0
    average_km = sum(distances_km) / len(distances_km)
    return average_km * ACCOMMODATION_DISTANCE_PENALTY_PER_KM
