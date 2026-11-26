"""#139 - 활동 장소가 바닥난(place_count=0) 날에도 day_travel에 이동
시간이 남는 현상의 원인 확인.

RuleDaySummary.place_count는 활동 장소만 센다(day_place_map 기준 -
_build_day_summaries). 반면 _recommend_meals는 "활동 슬롯 루프가 아무것도
못 채운 날도 식사는 독립적으로 추천한다"는 기존 동작(서비스 docstring
참고)이라, 활동이 0곳인 날도 조식/중식/석식이 그대로 추천될 수 있고
day_travel은 그 식사 구간까지 포함해 계산한다. 즉 이 "0곳인데 이동
시간이 있다"는 현상은 버그(호텔→호텔처럼 실제가 아닌 구간)가 아니라
실제로 방문하는 식당까지의 정상적인 이동 시간이다 - 그래서 이번 작업은
이 동작을 고치지 않았고(안전하게 "작게" 고칠 버그가 없었다), 이 테스트는
그 결론을 실제 데이터로 재확인해 둔다(회귀 문서화).

부산 전용 사례(test_busan_day10_of_30_nights_has_zero_activities_but_
real_meal_travel)는 scripts/add_busan_expansion_places.py --activate all
로 부산 활동 후보가 25->130(alternate 제외)으로 늘면서 삭제했다 -
recommended_max_days가 8->43이 돼, RuleItineraryRequest.nights의 최대
허용값(30, 즉 최대 31일 일정) 안에서는 더는 활동 후보 풀이 바닥나지
않는다(31일 일정으로 돌려도 place_count=0인 날이 전혀 없음을 확인).
이 "풀 고갈 + 정상적인 식사 이동시간"이라는 검증 대상 자체는
_recommend_meals/_build_day_travel의 도시 무관 로직이라(날짜 범위를
city_catalog 유무와 무관하게 순회하고, city는 estimate_transport_options
호출에만 쓰임 - 둘 다 분기 없음), 제주 테스트 하나로 충분히 커버된다 -
_recommend_meals의 day_places 빈 날 스킵 로직을 일부러 깨뜨려
제주 테스트가 실패하는 것으로 직접 확인했다(검증 후 원복, 커밋에
포함되지 않음).
"""
from __future__ import annotations

from app.domains.rule_planner.schemas import RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService


def _generate_long_trip(city: str, nights: int):
    service = RuleItineraryService()
    request = RuleItineraryRequest.model_validate(
        {
            "city": city,
            "nights": nights,
            "days": nights + 1,
            "travelers": 2,
            "companion_type": "couple",
            "budget_band": "medium",
            "concepts": ["sightseeing", "food"],
            "style": "easy",
        }
    )
    return service.generate(request, include_weather=False)


def test_jeju_day17_of_30_nights_has_zero_activities_but_real_meal_travel() -> None:
    response = _generate_long_trip("jeju", 30)
    day_number = 17

    day_summary = next(s for s in response.day_summaries if s.day_number == day_number)
    assert day_summary.place_count == 0, "활동 장소 풀이 16일치(48곳)에 바닥나는 사례 - 48곳/3슬롯=16일"

    day_items = [item for item in response.items if item.day_number == day_number]
    assert day_items == []

    day_meals = [meal for meal in response.meal_recommendations if meal.day_number == day_number]
    assert len(day_meals) >= 1, "식사는 활동 풀 고갈과 무관하게 독립적으로 추천된다"

    day_travel = next(d for d in response.day_travel if d.day_number == day_number)
    assert day_travel.legs, "식사가 있으니 실제 구간이 있어야 한다"
    for leg in day_travel.legs:
        # 숙소->숙소로 끝나는(같은 지점을 오가는) 가짜 구간이 아니라, 전부
        # 실제 식당을 오가는 구간이어야 한다.
        assert not (leg.from_kind == "accommodation" and leg.to_kind == "accommodation"), leg
        assert leg.distance_km >= 0

    assert day_summary.travel_minutes is not None and day_summary.travel_minutes > 0
