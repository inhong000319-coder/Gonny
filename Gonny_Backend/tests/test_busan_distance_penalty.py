from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.policies.city import extreme_distance_penalty
from app.domains.rule_planner.services.policies.city.busan import (
    EXTREME_DISTANCE_BASE_PENALTY,
    EXTREME_DISTANCE_KM_THRESHOLD,
    EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM,
)
from app.domains.rule_planner.services.policies.city.busan import extreme_distance_penalty as busan_penalty
from app.domains.rule_planner.services.slot_scoring import slot_score
from app.domains.rule_planner.services.travel_estimate import haversine_distance_km


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["문화·역사"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "nampo",
        "duration_hours": 1,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample",
        "latitude": 35.0966,
        "longitude": 129.0306,
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def build_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "busan",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


# --- 상수 경계값 ---------------------------------------------------------------


def test_extreme_distance_penalty_is_zero_at_exact_threshold() -> None:
    assert busan_penalty(EXTREME_DISTANCE_KM_THRESHOLD) == 0


def test_extreme_distance_penalty_is_zero_just_under_threshold() -> None:
    assert busan_penalty(EXTREME_DISTANCE_KM_THRESHOLD - 0.01) == 0


def test_extreme_distance_penalty_applies_base_penalty_just_over_threshold() -> None:
    # 임계를 살짝 넘으면: overage가 0km로 반올림돼 기본 감점만 적용된다.
    assert busan_penalty(EXTREME_DISTANCE_KM_THRESHOLD + 0.01) == EXTREME_DISTANCE_BASE_PENALTY


def test_extreme_distance_penalty_scales_linearly_with_overage() -> None:
    distance = EXTREME_DISTANCE_KM_THRESHOLD + 10
    expected = EXTREME_DISTANCE_BASE_PENALTY + round(10 * EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM)
    assert busan_penalty(distance) == expected


def test_extreme_distance_penalty_never_positive() -> None:
    for distance in [0, 5, 11.9, 12, 12.1, 50, 100, 500]:
        assert busan_penalty(distance) <= 0


def test_extreme_distance_penalty_at_the_measured_12km_threshold() -> None:
    # 고정된 실제 km 값으로 못박아 둔다(상수를 다시 바꿔도 이 테스트가
    # 조용히 따라가지 않고 깨지도록) - 측정값(이 파일 상단 busan.py의
    # 주석 참고): 임계 12km, 15km/20km는 채택하지 않았다.
    assert busan_penalty(12) == 0
    assert busan_penalty(13) < 0


# --- 디스패처(policies/city/__init__.py) ------------------------------------


def test_dispatcher_returns_zero_when_other_place_is_none() -> None:
    request = build_request(city="busan")
    place = build_place()
    assert extreme_distance_penalty(request, None, place) == 0


def test_dispatcher_returns_zero_when_coordinates_missing() -> None:
    request = build_request(city="busan")
    far_other = build_place(id="far", latitude=None, longitude=None)
    place = build_place()
    assert extreme_distance_penalty(request, far_other, place) == 0


def test_dispatcher_applies_busan_penalty_for_a_real_extreme_distance() -> None:
    request = build_request(city="busan")
    # nampo 인근 vs 가덕도 인근 - 임계(12km)를 훌쩍 넘는 실제 거리.
    nampo = build_place(id="nampo-ish", latitude=35.0966, longitude=129.0306)
    gadeok = build_place(id="gadeok-ish", latitude=35.024, longitude=128.809)
    distance = haversine_distance_km(35.0966, 129.0306, 35.024, 128.809)
    assert distance > EXTREME_DISTANCE_KM_THRESHOLD

    penalty = extreme_distance_penalty(request, nampo, gadeok)
    assert penalty == busan_penalty(distance)
    assert penalty < 0


# --- 서울·제주는 영향받지 않는다 ---------------------------------------------


def test_dispatcher_is_zero_for_seoul_regardless_of_distance() -> None:
    far_other = build_place(id="far", latitude=35.0966, longitude=129.0306)
    place = build_place(id="near", latitude=35.024, longitude=128.809)
    request = build_request(city="seoul")
    assert extreme_distance_penalty(request, far_other, place) == 0


def test_dispatcher_is_zero_for_a_city_with_no_policy_module_at_all() -> None:
    far_other = build_place(id="far", latitude=35.0966, longitude=129.0306)
    place = build_place(id="near", latitude=35.024, longitude=128.809)
    request = build_request(city="tokyo")
    assert extreme_distance_penalty(request, far_other, place) == 0


def test_jeju_penalty_values_unchanged_by_this_busan_addition() -> None:
    # busan.py가 독립적인 상수를 둔 것이 실제로 jeju의 값에 영향이 없는지 -
    # jeju.py 쪽 상수를 직접 다시 확인한다(순환 임포트 회피가 의도대로
    # 작동하는지의 증거).
    from app.domains.rule_planner.services.policies.city.jeju import (
        EXTREME_DISTANCE_BASE_PENALTY as JEJU_BASE,
    )
    from app.domains.rule_planner.services.policies.city.jeju import (
        EXTREME_DISTANCE_KM_THRESHOLD as JEJU_THRESHOLD,
    )
    from app.domains.rule_planner.services.policies.city.jeju import (
        EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM as JEJU_PER_KM,
    )
    from app.domains.rule_planner.services.policies.city.jeju import extreme_distance_penalty as jeju_penalty

    assert JEJU_THRESHOLD == 15.0
    assert JEJU_BASE == -30
    assert JEJU_PER_KM == -2
    assert jeju_penalty(16) == -32  # 변경 전부터 성립했던 값(임계 15 + 1km 초과), 그대로 유지


# --- 슬롯 점수: 먼 후보가 가까운 후보보다 낮게 나온다 ------------------------


def test_busan_slot_score_prefers_nearby_candidate_over_far_one() -> None:
    request = build_request(city="busan")
    previous_place = build_place(id="prev", area="nampo", latitude=35.0966, longitude=129.0306)

    nearby = build_place(id="nearby", area="nampo", latitude=35.0986, longitude=129.0327)  # ~0.3km
    far = build_place(id="far", area="gangseo", latitude=35.024, longitude=128.809)  # ~22km

    nearby_score = slot_score(
        place=nearby, request=request, time_slot="afternoon", day_number=2, preferred_area="nampo",
        previous_place=previous_place, next_place=None,
    )
    far_score = slot_score(
        place=far, request=request, time_slot="afternoon", day_number=2, preferred_area="nampo",
        previous_place=previous_place, next_place=None,
    )

    assert nearby_score > far_score


def test_seoul_slot_score_gap_unaffected_by_the_same_huge_distance() -> None:
    # 같은 지리적 구성을 서울로 재사용 - busan 전용 감점이 발동하면 안 되므로,
    # 기존 coordinate_area_transition_bonus(상한 있음, 거리에 비례하지 않음)
    # 차이만큼만 벌어져야 한다.
    from app.domains.rule_planner.services.travel_estimate import coordinate_area_transition_bonus

    request = build_request(city="seoul")
    previous_place = build_place(id="prev", area="gangnam", latitude=35.0966, longitude=129.0306)
    nearby = build_place(id="nearby", area="gangnam", latitude=35.0986, longitude=129.0327)
    far = build_place(id="far", area="gangnam", latitude=35.024, longitude=128.809)

    nearby_score = slot_score(
        place=nearby, request=request, time_slot="afternoon", day_number=2, preferred_area="gangnam",
        previous_place=previous_place, next_place=None,
    )
    far_score = slot_score(
        place=far, request=request, time_slot="afternoon", day_number=2, preferred_area="gangnam",
        previous_place=previous_place, next_place=None,
    )

    expected_nearby_bonus = coordinate_area_transition_bonus(previous_place, nearby)
    expected_far_bonus = coordinate_area_transition_bonus(previous_place, far)
    assert nearby_score - far_score == expected_nearby_bonus - expected_far_bonus
    assert nearby_score - far_score <= 20  # CLOSE(14) - FAR(-6): 한 등급 안에서 가능한 최대 차
