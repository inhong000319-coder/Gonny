from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import (
    CatalogCityOption,
    RuleItineraryRecalculateRequest,
    RuleItineraryRequest,
)
from app.domains.rule_planner.services.service import RuleItineraryService

CITIES = ["seoul", "busan", "jeju"]

# 9곳 - PR #97/non_restaurant_meal_investigation.md가 meal_eligible=False로
# 확정한 비식당 "food" 태그 장소. 이번 작업 전까지는 식사에도 활동에도
# 뽑히지 않아 일정에 아예 안 나왔다.
NON_RESTAURANT_FOOD_PLACE_IDS = {
    "seoul": {"insadong", "seongsu", "apgujeong-rodeo"},
    "busan": {"millak-waterfront", "onjeoncheon-cafe"},
    "jeju": {"woljeongri", "aewol-cafe", "osulloc", "delmoondo-gimnyeong"},
}


def _place(place_id: str, *, priority: int = 5, activity_type: list[str] | None = None, **overrides) -> PlaceData:
    data = {
        "id": place_id,
        "name": place_id,
        "activity_type": activity_type or ["미식"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "test-area",
        "duration_hours": 1,
        "priority": priority,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": f"{place_id} summary",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


class _FakeCatalogProvider(PlaceCatalogProvider):
    def __init__(self, places: list[PlaceData], *, city: str = "testcity"):
        self._city = city
        self._catalog = CityPlaceCatalog(continent="asia", country="korea", city=city, default_days=3, places=places)

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city=self._city, aliases=[])]


def _load_real_places(city: str) -> list[PlaceData]:
    payload = json.loads((PROJECT_ROOT / "app" / "data" / "destinations" / f"{city}.json").read_text(encoding="utf-8"))
    return [PlaceData.model_validate(p) for p in payload["places"]]


def _build_request(*, city: str = "testcity", days: int = 1, concepts: list[str] | None = None, **overrides) -> RuleItineraryRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": city,
        "nights": max(days - 1, 1),
        "days": days,
        "budget_band": "medium",
        "concepts": concepts or ["culture"],
        "style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return RuleItineraryRequest.model_validate(data)


def _build_real_request(city: str, **overrides) -> RuleItineraryRequest:
    data = {
        "city": city,
        "nights": 2,
        "days": 3,
        "travelers": 2,
        "companion_type": "couple",
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
    }
    data.update(overrides)
    return RuleItineraryRequest.model_validate(data)


# --- (1) non-meal-eligible "food" places can win an activity slot ----------


def test_non_meal_eligible_food_place_can_win_an_activity_slot():
    fillers = [_place(f"culture-{i}", priority=1, activity_type=["문화·역사"]) for i in range(10)]
    cafe = _place("scenic-cafe", priority=10, activity_type=["미식"], meal_eligible=False)
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider([cafe, *fillers]))
    # concepts=["food"]로 맞춰야 base_score의 컨셉 일치 보너스가 cafe
    # 쪽으로 붙는다 - 안 그러면 fillers의 "문화·역사" 컨셉 일치가 priority
    # 차이를 압도해버려 cafe가 못 이긴다(base_score는 scikit-learn 적합도
    # 모델 예측값이라 priority 하나만으로 결과를 보장 못 함 - 다른
    # 테스트에서도 확인된 사실).
    response = service.generate(_build_request(days=1, concepts=["food"]), include_weather=False)

    assert any(item.place_name == "scenic-cafe" for item in response.items)


# --- (2) a real (meal_eligible=True) restaurant is still excluded ----------


def test_meal_eligible_restaurant_still_excluded_from_activities():
    fillers = [_place(f"culture-{i}", priority=1, activity_type=["문화·역사"]) for i in range(10)]
    restaurant = _place("real-restaurant", priority=10, activity_type=["미식"], meal_eligible=True)
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider([restaurant, *fillers]))
    response = service.generate(_build_request(days=1), include_weather=False)

    assert all(item.place_name != "real-restaurant" for item in response.items)


# --- (3) still excluded from meal picks and meal alternatives --------------


def test_non_meal_eligible_food_place_excluded_from_meal_picks_and_alternatives():
    fillers = [_place(f"culture-{i}", priority=1, activity_type=["문화·역사"]) for i in range(10)]
    cafe = _place("scenic-cafe", priority=10, activity_type=["미식"], meal_eligible=False)
    real_food = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(5)]
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider([cafe, *real_food, *fillers]))
    response = service.generate(_build_request(days=1, include_breakfast=True), include_weather=False)

    assert response.meal_recommendations, "fixture must produce at least one meal to make this check meaningful"
    assert all(meal.place_name != "scenic-cafe" for meal in response.meal_recommendations)
    assert all(
        alt.place_name != "scenic-cafe" for meal in response.meal_recommendations for alt in meal.alternatives
    )


# --- (4) fixed_slots accepts the 9 real places, still rejects a real restaurant


@pytest.mark.parametrize("city", CITIES)
def test_fixed_slots_accepts_each_non_restaurant_food_place(city):
    service = RuleItineraryService()
    request = _build_real_request(city)
    gen = service.generate(request, include_weather=False)
    accommodation_id = gen.accommodation_recommendation.id if gen.accommodation_recommendation else None

    for place_id in NON_RESTAURANT_FOOD_PLACE_IDS[city]:
        fixed_slots = [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in gen.items]
        # 이 fix 덕분에 generate()가 이 장소를 이미 자연히 뽑았을 수 있다
        # (실제로 jeju의 기본 조합에서 osulloc/delmoondo-gimnyeong이 그렇다)
        # - 그러면 손대지 않고 그대로 재계산해도 충분한 검증이고, 억지로
        # 다른 슬롯에 또 지정하면 같은 장소가 두 일차에 걸치는 422가
        # 난다(의도된 별개 규칙). 아직 없을 때만 슬롯 하나를 바꿔 넣는다.
        if not any(slot["place_id"] == place_id for slot in fixed_slots):
            fixed_slots[0]["place_id"] = place_id
        recalc_request = RuleItineraryRecalculateRequest.model_validate(
            {**request.model_dump(), "fixed_slots": fixed_slots, "accommodation_id": accommodation_id}
        )
        recalc = service.recalculate(recalc_request)
        assert any(item.place_id == place_id for item in recalc.items), (city, place_id)


@pytest.mark.parametrize("city", CITIES)
def test_fixed_slots_still_rejects_a_real_restaurant(city):
    service = RuleItineraryService()
    request = _build_real_request(city)
    gen = service.generate(request, include_weather=False)
    accommodation_id = gen.accommodation_recommendation.id if gen.accommodation_recommendation else None
    catalog = service.catalog_provider.get_city_catalog(
        continent=gen.continent, country=gen.country, city=gen.city, visible_only=True
    )
    restaurant = next(p for p in catalog.places if p.is_active and "food" in p.concept_tags and p.meal_eligible)

    fixed_slots = [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in gen.items]
    fixed_slots[0]["place_id"] = restaurant.id
    recalc_request = RuleItineraryRecalculateRequest.model_validate(
        {**request.model_dump(), "fixed_slots": fixed_slots, "accommodation_id": accommodation_id}
    )
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


# --- (5) delmoondo-gimnyeong's item category is never "food" ---------------


def test_delmoondo_gimnyeong_category_is_not_food():
    service = RuleItineraryService()
    request = _build_real_request("jeju")
    gen = service.generate(request, include_weather=False)

    item = next((i for i in gen.items if i.place_id == "delmoondo-gimnyeong"), None)
    if item is None:
        # 이 조합에서 자연히 안 뽑히면 fixed_slots로 강제한다.
        accommodation_id = gen.accommodation_recommendation.id if gen.accommodation_recommendation else None
        fixed_slots = [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in gen.items]
        target = next(s for s in fixed_slots if s["day_number"] == 1 and s["time_slot"] == "afternoon")
        target["place_id"] = "delmoondo-gimnyeong"
        recalc_request = RuleItineraryRecalculateRequest.model_validate(
            {**request.model_dump(), "fixed_slots": fixed_slots, "accommodation_id": accommodation_id}
        )
        recalc = service.recalculate(recalc_request)
        item = next(i for i in recalc.items if i.place_id == "delmoondo-gimnyeong")

    assert item.category != "food"


def test_resolve_item_category_uses_relax_when_food_is_the_only_code():
    cafe = _place("single-tag-cafe", priority=10, activity_type=["미식"], meal_eligible=False)
    fillers = [_place(f"culture-{i}", priority=1, activity_type=["문화·역사"]) for i in range(10)]
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider([cafe, *fillers]))
    # concepts=["food"] - test_non_meal_eligible_food_place_can_win_an_activity_slot
    # 와 같은 이유(컨셉 일치 보너스가 없으면 cafe가 fillers에 못 이긴다).
    response = service.generate(_build_request(days=1, concepts=["food"]), include_weather=False)

    item = next(i for i in response.items if i.place_name == "single-tag-cafe")
    assert item.category == "relax"


def test_other_places_category_is_unaffected():
    # 일반 활동 장소(meal_eligible과 무관)의 category는 그대로여야 한다 -
    # _resolve_item_category의 새 분기는 "food 태그 + meal_eligible=False"
    # 조합에서만 동작해야 한다.
    fillers = [_place(f"culture-{i}", priority=1, activity_type=["문화·역사"]) for i in range(10)]
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(fillers))
    response = service.generate(_build_request(days=1), include_weather=False)

    assert all(item.category == "culture" for item in response.items)


# --- (6) weather indoor swap candidates and slot alternatives apply the same rule


def test_slot_alternatives_can_include_a_non_restaurant_food_place():
    real_places = _load_real_places("jeju")
    cafe = next(p for p in real_places if p.id == "delmoondo-gimnyeong")
    fillers = [p for p in real_places if p.id != "delmoondo-gimnyeong" and "food" not in p.concept_tags][:20]
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider([cafe, *fillers], city="jeju"))
    response = service.generate(_build_request(city="jeju", days=3, concepts=["sightseeing"]), include_weather=False)

    item_ids = {item.place_id for item in response.items}
    alt_ids = {alt.place_id for item in response.items for alt in item.alternatives}
    # 활동 후보 풀에 들어갔다면 실제로 그 슬롯을 이기거나(items), 적어도
    # 다른 추천 후보로는 나와야 한다(alternatives) - 둘 중 하나는 반드시
    # 참이어야 한다(이기면 대안 목록엔 안 나오는 게 정상).
    assert "delmoondo-gimnyeong" in item_ids or "delmoondo-gimnyeong" in alt_ids


class _FakeRainWeatherClient:
    def __init__(self, start_date):
        from datetime import timedelta

        self.start_date = start_date
        self._timedelta = timedelta

    def fetch_5day_forecast(self, destination, *, allow_mock_fallback: bool = True):
        return [
            {
                "forecast_date": self.start_date + self._timedelta(days=i),
                "condition": "rain",
                "min_temp_c": 10.0,
                "max_temp_c": 15.0,
                "precipitation_mm": 12.0,
            }
            for i in range(5)
        ]


def test_weather_swap_candidates_can_include_a_non_restaurant_food_place():
    from datetime import date

    # 2026-09-15 is a Tuesday - matches tests/test_weather_alert_swap.py's own fixture date.
    a_tuesday = date(2026, 9, 15)

    real_places = _load_real_places("jeju")
    cafe = next(p for p in real_places if p.id == "delmoondo-gimnyeong")
    assert cafe.setting == "indoor", "fixture relies on delmoondo-gimnyeong being an indoor swap candidate"
    outdoor_places = [p for p in real_places if p.setting == "outdoor" and p.is_active][:5]
    fillers = [
        p for p in real_places if p.id != "delmoondo-gimnyeong" and "food" not in p.concept_tags
    ][:20]

    service = RuleItineraryService(
        catalog_provider=_FakeCatalogProvider([cafe, *outdoor_places, *fillers], city="jeju"),
        weather_client=_FakeRainWeatherClient(start_date=a_tuesday),
    )
    response = service.generate(
        _build_request(city="jeju", days=3, concepts=["sightseeing"], start_date=a_tuesday)
    )

    item_ids = {item.place_id for item in response.items}
    swap_ids = {
        candidate.place_id
        for alert in response.weather_alerts
        for affected in alert.affected_items
        for candidate in affected.swap_candidates
    }
    assert "delmoondo-gimnyeong" in item_ids or "delmoondo-gimnyeong" in swap_ids
