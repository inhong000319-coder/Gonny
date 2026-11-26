"""#139 - GET /rule-itinerary/options의 recommended_max_days.

compute_recommended_max_days(순수 함수)의 슬롯 수 민감도와,
RuleItineraryService.list_catalog_options()가 실제 도시 데이터로 그
함수를 올바르게 호출하는지를 나눠서 확인한다.
"""
from __future__ import annotations

from app.domains.destination_catalog.schemas import ALTERNATE_TIER
from app.domains.destination_catalog.services.provider import LocalJsonPlaceCatalogProvider
from app.domains.destination_catalog.services.repository import compute_recommended_max_days
from app.domains.rule_planner.services.service import RuleItineraryService

# 현재 카탈로그 데이터 기준(2026-11-26, 부산 확장 장소 283곳 활성화 후 확인) -
# 데이터가 바뀌면 이 숫자도 바뀔 수 있으므로, 아래 테스트는 이 값에
# 의존하지 않고 카탈로그에서 직접 센 값과 비교한다. 여기 적어 두는 건
# 보고서와 같은 숫자인지 눈으로도 바로 확인할 수 있게 하기 위함이다.
EXPECTED_RECOMMENDED_MAX_DAYS = {"seoul": 14, "busan": 43, "jeju": 16}


def _activity_candidate_count(city: str) -> int:
    catalog = LocalJsonPlaceCatalogProvider().get_city_catalog(
        continent=None, country=None, city=city, visible_only=True
    )
    # mvp_tier != ALTERNATE_TIER가 빠져 있었다 - PR-A(#152)가
    # repository.list_city_options의 실제 계산에 이 조건을 추가했지만,
    # 그때는 어떤 실제 카탈로그에도 alternate 장소가 없어 이 헬퍼와의
    # 차이가 드러나지 않았다. 부산 확장 장소(alternate 178곳 포함)를
    # 활성화하면서 처음 드러난 테스트 쪽 버그 - 프로덕션 코드(repository.py)는
    # 원래부터 문제없다.
    return sum(
        1
        for place in catalog.places
        if place.is_active and place.is_activity_candidate and place.mvp_tier != ALTERNATE_TIER
    )


def test_compute_recommended_max_days_is_floor_division_by_slot_count() -> None:
    assert compute_recommended_max_days(25, slot_count=3) == 8  # 25 // 3, 나머지 1곳은 안 셈
    assert compute_recommended_max_days(24, slot_count=3) == 8
    assert compute_recommended_max_days(0, slot_count=3) == 0


def test_compute_recommended_max_days_changes_with_slot_count() -> None:
    # 슬롯 수가 바뀌면(성향별 슬롯 수 변경 등 미래 시나리오) 결과도 바뀐다.
    assert compute_recommended_max_days(48, slot_count=3) == 16
    assert compute_recommended_max_days(48, slot_count=4) == 12
    assert compute_recommended_max_days(48, slot_count=2) == 24
    assert compute_recommended_max_days(48, slot_count=48) == 1
    assert compute_recommended_max_days(48, slot_count=49) == 0


def test_compute_recommended_max_days_default_slot_count_is_three() -> None:
    assert compute_recommended_max_days(9) == compute_recommended_max_days(9, slot_count=3) == 3


def test_compute_recommended_max_days_non_positive_slot_count_returns_zero() -> None:
    assert compute_recommended_max_days(48, slot_count=0) == 0
    assert compute_recommended_max_days(48, slot_count=-1) == 0


def test_catalog_options_recommended_max_days_matches_activity_candidate_floor_division() -> None:
    options = RuleItineraryService().list_catalog_options()
    by_city = {option.city: option for option in options}

    for city in ["seoul", "busan", "jeju"]:
        candidate_count = _activity_candidate_count(city)
        assert by_city[city].recommended_max_days == candidate_count // 3, city


def test_catalog_options_recommended_max_days_current_values() -> None:
    # 현재 데이터 기준 실제 값 - 보고서에도 같은 숫자를 적는다.
    options = RuleItineraryService().list_catalog_options()
    by_city = {option.city: option for option in options}

    for city, expected in EXPECTED_RECOMMENDED_MAX_DAYS.items():
        assert by_city[city].recommended_max_days == expected, city


def test_catalog_options_existing_fields_unchanged() -> None:
    # 기존 필드(accommodation_type_counts 등)는 그대로 응답에 남아 있다 -
    # 하위 호환(#139 constraint).
    options = RuleItineraryService().list_catalog_options()
    seoul = next(option for option in options if option.city == "seoul")
    assert seoul.accommodation_type_counts
    assert seoul.aliases is not None
