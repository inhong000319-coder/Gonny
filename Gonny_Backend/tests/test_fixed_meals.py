from __future__ import annotations

import sys
from datetime import date
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
    NormalizedRuleRequest,
    RuleFixedMealSlot,
    RuleItineraryRecalculateRequest,
    RuleItineraryRequest,
)
from app.domains.rule_planner.services.recalculate import build_fixed_meals_lookup
from app.domains.rule_planner.services.service import RuleItineraryService

# 2026-09-15 is a Tuesday (weekday() == 1) - same fixture date other test
# files in this suite use (see test_slot_alternatives.py).
A_TUESDAY = date(2026, 9, 15)


def _place(
    place_id: str,
    *,
    priority: int = 5,
    activity_type: list[str] | None = None,
    area: str = "test-area",
    name: str | None = None,
    meal_eligible: bool = True,
    is_active: bool = True,
    closed_days: str | None = None,
) -> PlaceData:
    return PlaceData(
        id=place_id,
        name=name or place_id,
        activity_type=activity_type or ["미식"],
        budget_level=["low", "medium", "high"],
        suitable_for=["solo", "couple", "friend", "family"],
        time_fit=["morning", "afternoon", "evening"],
        area=area,
        duration_hours=1,
        priority=priority,
        pace=["easy", "tight"],
        mobility=["walkable"],
        summary=f"{place_id} summary",
        meal_eligible=meal_eligible,
        is_active=is_active,
        closed_days=closed_days,
    )


def _catalog(places: list[PlaceData]) -> CityPlaceCatalog:
    return CityPlaceCatalog(continent="asia", country="korea", city="testcity", default_days=3, places=places)


def _request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "testcity",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
        "companion_type": "friend",
        "include_breakfast": True,
    }
    data.update(overrides)
    return NormalizedRuleRequest(**data)


def _meal(day_number: int, meal_type: str, place_id: str) -> RuleFixedMealSlot:
    return RuleFixedMealSlot(day_number=day_number, meal_type=meal_type, place_id=place_id)


# =============================================================================
# build_fixed_meals_lookup unit tests - one per 422 rule, same style as
# test_recalculate_endpoint.py's build_fixed_slots_lookup coverage.
# =============================================================================


def test_valid_fixed_meals_resolve_without_error():
    lunch_place = _place("good-lunch-food")
    breakfast_place = _place("breakfast-cafe", name="breakfast-cafe 카페")
    catalog = _catalog([lunch_place, breakfast_place])
    resolved = build_fixed_meals_lookup(
        fixed_meals=[_meal(1, "lunch", "good-lunch-food"), _meal(1, "breakfast", "breakfast-cafe")],
        request=_request(),
        city_catalog=catalog,
        fixed_slots_lookup={},
    )
    assert resolved[(1, "lunch")].id == "good-lunch-food"
    assert resolved[(1, "breakfast")].id == "breakfast-cafe"


def test_unknown_place_id():
    catalog = _catalog([_place("good-lunch-food")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "does-not-exist-xyz")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_inactive_place():
    catalog = _catalog([_place("inactive-food", is_active=False)])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "inactive-food")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_not_food_tagged_place():
    catalog = _catalog([_place("not-food-activity", activity_type=["문화·역사"])])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "not-food-activity")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_meal_ineligible_place():
    catalog = _catalog([_place("ineligible-food", meal_eligible=False)])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "ineligible-food")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_breakfast_type_but_not_breakfast_classified():
    # No breakfast keyword anywhere (name/summary/highlight_tags/mood_keywords).
    catalog = _catalog([_place("good-lunch-food")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "breakfast", "good-lunch-food")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_day_number_out_of_range():
    catalog = _catalog([_place("good-lunch-food")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(99, "lunch", "good-lunch-food")],
            request=_request(days=3),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_breakfast_not_allowed_when_include_breakfast_is_false():
    catalog = _catalog([_place("breakfast-cafe", name="breakfast-cafe 카페")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "breakfast", "breakfast-cafe")],
            request=_request(include_breakfast=False),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_meal_not_allowed_due_to_arrival_period():
    # "night" arrival on day 1 of a 1-day trip blocks every slot/meal.
    catalog = _catalog([_place("good-lunch-food")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "good-lunch-food")],
            request=_request(days=1, nights=1, arrival_period="night"),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_duplicate_day_and_meal_type():
    catalog = _catalog([_place("food-a"), _place("food-b")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "food-a"), _meal(1, "lunch", "food-b")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_same_place_used_in_two_fixed_meals():
    catalog = _catalog([_place("food-a")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "food-a"), _meal(2, "dinner", "food-a")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


def test_same_place_used_in_a_fixed_meal_and_an_activity_slot():
    # build_fixed_slots_lookup itself already rejects any food place from
    # fixed_slots (see its own "식당은 활동 슬롯에 지정할 수 없습니다" check),
    # so this collision is structurally unreachable through the full
    # recalculate() pipeline - fixed_slots_lookup is hand-built here purely
    # to exercise build_fixed_meals_lookup's own defensive check in
    # isolation. See local_only/reports/meal_slot_alternatives_backend.md
    # for why this is still worth keeping (future-proofing, not dead code
    # removal).
    place = _place("food-a")
    catalog = _catalog([place])
    fixed_slots_lookup = {(2, "morning"): place}
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "food-a")],
            request=_request(),
            city_catalog=catalog,
            fixed_slots_lookup=fixed_slots_lookup,
        )
    assert exc_info.value.status_code == 422


def test_confirmed_closed_day():
    catalog = _catalog([_place("closed-tue-food", closed_days="매주 화요일 휴무")])
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_meals_lookup(
            fixed_meals=[_meal(1, "lunch", "closed-tue-food")],
            request=_request(start_date=A_TUESDAY),
            city_catalog=catalog,
            fixed_slots_lookup={},
        )
    assert exc_info.value.status_code == 422


# =============================================================================
# End-to-end via RuleItineraryService.recalculate() - pinning actually takes
# effect, auto-picked meals avoid the pinned restaurant, and omitting
# fixed_meals entirely reproduces generate()'s own picks exactly.
# =============================================================================


class _FakeCatalogProvider(PlaceCatalogProvider):
    def __init__(self, places: list[PlaceData]):
        self._catalog = _catalog(places)

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="testcity", aliases=[])]


def _abundant_catalog_provider() -> _FakeCatalogProvider:
    fillers = [_place(f"culture-{i}", activity_type=["문화·역사"], priority=10 - (i % 10)) for i in range(20)]
    food_places = [_place(f"food-{i}", priority=10 - (i % 10)) for i in range(15)]
    return _FakeCatalogProvider([*fillers, *food_places])


def _build_generate_request(**overrides) -> RuleItineraryRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "testcity",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
        "companion_type": "friend",
        "include_breakfast": True,
    }
    data.update(overrides)
    return RuleItineraryRequest.model_validate(data)


def _build_recalc_request(*, fixed_slots, accommodation_id, fixed_meals=None, **overrides):
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "testcity",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
        "companion_type": "friend",
        "include_breakfast": True,
        "fixed_slots": fixed_slots,
        "accommodation_id": accommodation_id,
    }
    if fixed_meals is not None:
        data["fixed_meals"] = fixed_meals
    data.update(overrides)
    return RuleItineraryRecalculateRequest.model_validate(data)


def _fixed_slots_from_items(items) -> list[dict]:
    return [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in items]


def test_fixed_meal_pins_an_alternative_restaurant():
    service = RuleItineraryService(catalog_provider=_abundant_catalog_provider())
    gen = service.generate(_build_generate_request(), include_weather=False)
    meal_with_alt = next(m for m in gen.meal_recommendations if m.alternatives)
    chosen_alt = meal_with_alt.alternatives[0]

    recalc_request = _build_recalc_request(
        fixed_slots=_fixed_slots_from_items(gen.items),
        accommodation_id=gen.accommodation_recommendation.id if gen.accommodation_recommendation else None,
        fixed_meals=[
            {"day_number": meal_with_alt.day_number, "meal_type": meal_with_alt.meal_type, "place_id": chosen_alt.place_id}
        ],
    )
    recalc = service.recalculate(recalc_request)

    fixed = next(
        m for m in recalc.meal_recommendations
        if m.day_number == meal_with_alt.day_number and m.meal_type == meal_with_alt.meal_type
    )
    assert fixed.place_id == chosen_alt.place_id
    assert fixed.place_name == chosen_alt.place_name


def test_auto_picked_meals_never_duplicate_a_fixed_meal_place():
    service = RuleItineraryService(catalog_provider=_abundant_catalog_provider())
    gen = service.generate(_build_generate_request(), include_weather=False)
    meal_with_alt = next(m for m in gen.meal_recommendations if m.alternatives)
    chosen_alt = meal_with_alt.alternatives[0]

    recalc_request = _build_recalc_request(
        fixed_slots=_fixed_slots_from_items(gen.items),
        accommodation_id=gen.accommodation_recommendation.id if gen.accommodation_recommendation else None,
        fixed_meals=[
            {"day_number": meal_with_alt.day_number, "meal_type": meal_with_alt.meal_type, "place_id": chosen_alt.place_id}
        ],
    )
    recalc = service.recalculate(recalc_request)

    place_ids = [m.place_id for m in recalc.meal_recommendations]
    assert len(place_ids) == len(set(place_ids)), f"duplicate restaurant across meals: {place_ids}"


def test_fixed_meals_absent_reproduces_generate_meals_exactly():
    service = RuleItineraryService(catalog_provider=_abundant_catalog_provider())
    gen = service.generate(_build_generate_request(), include_weather=False)

    recalc_request = _build_recalc_request(
        fixed_slots=_fixed_slots_from_items(gen.items),
        accommodation_id=gen.accommodation_recommendation.id if gen.accommodation_recommendation else None,
    )
    recalc = service.recalculate(recalc_request)

    gen_meals = [m.model_dump(mode="json") for m in gen.meal_recommendations]
    recalc_meals = [m.model_dump(mode="json") for m in recalc.meal_recommendations]
    assert gen_meals == recalc_meals
