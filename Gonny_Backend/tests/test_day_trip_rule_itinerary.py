"""#140 - 당일치기(0박 1일) 일정 생성/재계산.

숙소 관련 응답 필드가 전부 비어 있는지, days/nights 조합 검증이 맞는지,
도착·출발·이동수단 조합 72가지가 전부 올바른 상태(200 또는 422)를
내는지, 재계산에서 숙소 관련 필드를 보내면 422가 나는지를 확인한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.rule_planner.schemas import RuleItineraryRecalculateRequest, RuleItineraryRequest
from app.domains.rule_planner.services.arrival_departure import has_any_usable_slot
from app.domains.rule_planner.services.request_normalizer import normalize_duration
from app.domains.rule_planner.services.service import RuleItineraryService

CITIES = ["seoul", "busan", "jeju"]


def build_day_trip_request(city: str, **overrides) -> RuleItineraryRequest:
    data = {
        "city": city,
        "nights": 0,
        "travelers": 2,
        "companion_type": "couple",
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
    }
    data.update(overrides)
    return RuleItineraryRequest.model_validate(data)


# --- (1) nights=0 생성: 숙소 필드가 전부 비어 있음 ---------------------------


@pytest.mark.parametrize("city", CITIES)
def test_day_trip_generate_has_empty_accommodation_fields(city: str) -> None:
    service = RuleItineraryService()
    response = service.generate(build_day_trip_request(city), include_weather=False)

    assert response.nights == 0
    assert response.days == 1
    assert len(response.items) > 0, city

    assert response.accommodation_recommendation is None
    assert response.accommodation_alternatives == []
    assert response.accommodation_stays == []
    assert response.accommodation_split_note == "당일치기 일정이라 숙소를 추천하지 않아요."

    assert len(response.day_travel) == 1
    for leg in response.day_travel[0].legs:
        assert leg.from_kind != "accommodation", city
        assert leg.to_kind != "accommodation", city

    assert response.estimated_cost is not None
    assert response.estimated_cost.nights == 0
    assert response.estimated_cost.accommodation_included is False


@pytest.mark.parametrize("split_mode", ["single", "two", "auto"])
def test_day_trip_generate_ignores_accommodation_split_mode(split_mode: str) -> None:
    # 0박이면 분할 모드와 무관하게 항상 숙소가 없다 - 오류도 아니다.
    service = RuleItineraryService()
    response = service.generate(
        build_day_trip_request("jeju", accommodation_split=split_mode), include_weather=False
    )
    assert response.accommodation_stays == []
    assert response.accommodation_split_note == "당일치기 일정이라 숙소를 추천하지 않아요."


# --- (2) days/nights 조합 검증 -----------------------------------------------


def test_nights_zero_and_days_one_normalizes_cleanly() -> None:
    assert normalize_duration(nights=0, days=1, duration_label=None) == (0, 1)


def test_nights_zero_and_days_none_normalizes_to_one_day() -> None:
    assert normalize_duration(nights=0, days=None, duration_label=None) == (0, 1)


@pytest.mark.parametrize("days", [2, 3, 7])
def test_nights_zero_with_days_two_or_more_is_rejected(days: int) -> None:
    with pytest.raises(HTTPException) as exc_info:
        normalize_duration(nights=0, days=days, duration_label=None)
    assert exc_info.value.status_code == 422
    assert "nights" in exc_info.value.detail


def test_days_one_without_nights_normalizes_to_day_trip() -> None:
    # #140 전에는 (1, 1)이었다 - days만 1로 오면 이제 당일치기(0박)가
    # 된다는 의도된 동작 변경(보고서 참고).
    assert normalize_duration(nights=None, days=1, duration_label=None) == (0, 1)


def test_existing_nights_and_days_combinations_unchanged() -> None:
    # nights>=1 요청은 전부 변경 전과 완전히 같아야 한다(가장 중요한 제약).
    assert normalize_duration(nights=3, days=4, duration_label=None) == (3, 4)
    assert normalize_duration(nights=3, days=None, duration_label=None) == (3, 4)
    assert normalize_duration(nights=None, days=4, duration_label=None) == (3, 4)
    assert normalize_duration(nights=None, days=None, duration_label=None) == (2, 3)
    assert normalize_duration(nights=None, days=None, duration_label="3박 4일") == (3, 4)


def test_generate_endpoint_rejects_nights_zero_with_days_two() -> None:
    service = RuleItineraryService()
    with pytest.raises(HTTPException) as exc_info:
        service.generate(build_day_trip_request("seoul", days=2), include_weather=False)
    assert exc_info.value.status_code == 422


# --- (3) 도착×출발×이동수단 72가지 조합 -------------------------------------

ARRIVAL_PERIODS = ["morning", "afternoon", "evening", "night"]
DEPARTURE_PERIODS = ["before_lunch", "afternoon", "evening_or_later"]
TRANSPORT_MODES = ["transit", "car"]


@pytest.mark.parametrize("mode", TRANSPORT_MODES)
@pytest.mark.parametrize("departure_period", DEPARTURE_PERIODS)
@pytest.mark.parametrize("arrival_period", ARRIVAL_PERIODS)
@pytest.mark.parametrize("city", CITIES)
def test_day_trip_72_arrival_departure_transport_combinations(
    city: str, arrival_period: str, departure_period: str, mode: str
) -> None:
    service = RuleItineraryService()
    request = build_day_trip_request(
        city,
        arrival_period=arrival_period,
        departure_period=departure_period,
        transport_by_day=[mode],
    )
    is_feasible = has_any_usable_slot(arrival_period=arrival_period, departure_period=departure_period, days=1)

    if is_feasible:
        response = service.generate(request, include_weather=False)
        assert response.nights == 0
        assert response.days == 1
        assert response.accommodation_stays == []
    else:
        with pytest.raises(HTTPException) as exc_info:
            service.generate(request, include_weather=False)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail  # 한국어 메시지가 비어있지 않음


# --- (4) 재계산: nights=0 성공, 숙소 관련 필드는 422 ------------------------


def test_recalculate_day_trip_succeeds_and_reproduces_generate() -> None:
    service = RuleItineraryService()
    generated = service.generate(build_day_trip_request("seoul"), include_weather=False)

    fixed_slots = [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in generated.items]
    recalc_request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul",
            "nights": 0,
            "travelers": 2,
            "companion_type": "couple",
            "budget_band": "medium",
            "concepts": ["sightseeing", "food"],
            "style": "easy",
            "fixed_slots": fixed_slots,
        }
    )
    recalculated = service.recalculate(recalc_request)

    gen_dump = generated.model_dump(mode="json")
    recalc_dump = recalculated.model_dump(mode="json")
    gen_dump.pop("weather_alerts", None); gen_dump.pop("weather_status", None)
    recalc_dump.pop("weather_alerts", None); recalc_dump.pop("weather_status", None)
    assert gen_dump == recalc_dump
    assert recalculated.accommodation_stays == []


@pytest.mark.parametrize(
    "extra_field",
    ["accommodation_id", "stay_nights", "stay_accommodation_ids"],
)
def test_recalculate_day_trip_rejects_accommodation_fields(extra_field: str) -> None:
    service = RuleItineraryService()
    generated = service.generate(build_day_trip_request("seoul"), include_weather=False)
    fixed_slots = [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in generated.items]

    base = {
        "city": "seoul",
        "nights": 0,
        "travelers": 2,
        "companion_type": "couple",
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
        "fixed_slots": fixed_slots,
    }
    extra_values = {
        "accommodation_id": "any-id",
        "stay_nights": [0],
        "stay_accommodation_ids": ["any-id"],
    }
    base[extra_field] = extra_values[extra_field]
    recalc_request = RuleItineraryRecalculateRequest.model_validate(base)

    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422
    assert "당일치기" in exc_info.value.detail
