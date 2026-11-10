from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService

CITIES = ["seoul", "busan", "jeju"]


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
    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(continent="asia", country="korea", city="testcity", default_days=3, places=places)

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="testcity", aliases=[])]


def _abundant_catalog() -> list[PlaceData]:
    fillers = [_place(f"culture-{i}", activity_type=["문화·역사"], priority=10 - (i % 10)) for i in range(20)]
    food_places = [_place(f"food-{i}", priority=10 - (i % 10)) for i in range(20)]
    return [*fillers, *food_places]


def _build_request(
    *,
    city: str = "testcity",
    continent: str = "asia",
    country: str = "korea",
    days: int = 3,
    concepts: list[str] | None = None,
    companion_type: str = "friend",
    style: str = "easy",
    include_breakfast: bool = True,
    arrival_period: str | None = None,
    departure_period: str | None = None,
) -> RuleItineraryRequest:
    return RuleItineraryRequest(
        continent=continent,
        country=country,
        city=city,
        nights=max(days - 1, 1),
        days=days,
        budget_band="medium",
        concepts=concepts or ["sightseeing", "food"],
        style=style,
        companion_type=companion_type,
        include_breakfast=include_breakfast,
        arrival_period=arrival_period,
        departure_period=departure_period,
    )


def _assert_no_overlap(response) -> None:
    """A meal's alternatives must never include a restaurant that's already
    the final pick of *any* meal or activity item in this trip (itself
    included, though that half is covered separately by
    test_meal_alternatives.py's "excludes selected" check)."""
    all_used_ids = {item.place_id for item in response.items if item.place_id} | {
        meal.place_id for meal in response.meal_recommendations if meal.place_id
    }
    for meal in response.meal_recommendations:
        alt_ids = {alt.place_id for alt in meal.alternatives}
        overlap = alt_ids & all_used_ids
        assert not overlap, (
            f"day {meal.day_number} {meal.meal_type} ({meal.place_id}) alternatives overlap "
            f"with already-used places: {overlap}"
        )


# --- (a) no overlap with other meals/activities, across conditions ---------


def test_no_meal_alternative_overlaps_with_other_meals_or_activities_fake_catalog():
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(_abundant_catalog()))
    combos = [
        {"days": 1, "include_breakfast": False},
        {"days": 1, "include_breakfast": True},
        {"days": 3, "include_breakfast": True},
        {"days": 3, "include_breakfast": False, "concepts": ["sightseeing", "food", "activity"]},
        {"days": 3, "include_breakfast": True, "arrival_period": "afternoon"},
        {"days": 3, "include_breakfast": True, "departure_period": "afternoon"},
    ]
    for combo in combos:
        request = _build_request(**combo)
        response = service.generate(request, include_weather=False)
        assert response.meal_recommendations, combo
        _assert_no_overlap(response)


@pytest.mark.parametrize("city", CITIES)
@pytest.mark.parametrize("include_breakfast", [False, True])
def test_no_meal_alternative_overlaps_real_catalog(city, include_breakfast):
    service = RuleItineraryService()
    request = _build_request(
        city=city,
        continent=None,
        country=None,
        days=3,
        companion_type="couple",
        include_breakfast=include_breakfast,
    )
    response = service.generate(request, include_weather=False)
    assert response.meal_recommendations
    _assert_no_overlap(response)


# --- (b) selection (place_id) is unaffected by computing alternatives ------


def test_selected_meal_place_ids_unaffected_by_alternatives_computation():
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(_abundant_catalog()))
    request = _build_request(days=3, include_breakfast=True)

    with_alternatives = service.generate(request, include_weather=False, include_alternatives=True)
    without_alternatives = service.generate(request, include_weather=False, include_alternatives=False)

    def meal_key(meal):
        return (meal.day_number, meal.meal_type, meal.place_id)

    with_keys = sorted(meal_key(m) for m in with_alternatives.meal_recommendations)
    without_keys = sorted(meal_key(m) for m in without_alternatives.meal_recommendations)
    assert with_keys == without_keys

    # Activity picks must also be identical - the alternatives pass only
    # ever reads used_ids, never mutates selection.
    with_items = sorted((i.day_number, i.time_slot, i.place_id) for i in with_alternatives.items)
    without_items = sorted((i.day_number, i.time_slot, i.place_id) for i in without_alternatives.items)
    assert with_items == without_items

    # And alternatives must actually be empty on the False side.
    assert all(meal.alternatives == [] for meal in without_alternatives.meal_recommendations)


@pytest.mark.parametrize("city", CITIES)
def test_selected_meal_place_ids_unaffected_by_alternatives_computation_real_catalog(city):
    service = RuleItineraryService()
    request = _build_request(city=city, continent=None, country=None, days=3, include_breakfast=True)

    with_alternatives = service.generate(request, include_weather=False, include_alternatives=True)
    without_alternatives = service.generate(request, include_weather=False, include_alternatives=False)

    def meal_key(meal):
        return (meal.day_number, meal.meal_type, meal.place_id)

    assert sorted(meal_key(m) for m in with_alternatives.meal_recommendations) == sorted(
        meal_key(m) for m in without_alternatives.meal_recommendations
    )


# --- (c) include_alternatives=False -> empty (already covered in
# test_meal_alternatives.py; re-asserted above as part of (b)) -------------


# --- (d) fixed_meals + (a) ---------------------------------------------


def test_no_overlap_holds_with_fixed_meals():
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(_abundant_catalog()))
    request = _build_request(days=3, include_breakfast=True)
    gen = service.generate(request, include_weather=False)

    # Pin day 1's lunch to one of its own alternatives (a restaurant that
    # would NOT have been picked for lunch on its own), to actually
    # exercise the fixed_meals path rather than reproducing generate()'s
    # own pick.
    day1_lunch = next(m for m in gen.meal_recommendations if m.day_number == 1 and m.meal_type == "lunch")
    assert day1_lunch.alternatives, "fixture must give day 1 lunch at least one alternative"
    pinned_alt = day1_lunch.alternatives[0]

    from app.domains.rule_planner.schemas import RuleItineraryRecalculateRequest

    fixed_slots = [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in gen.items]
    recalc_payload = {
        **request.model_dump(),
        "fixed_slots": fixed_slots,
        "accommodation_id": None,
        "fixed_meals": [{"day_number": 1, "meal_type": "lunch", "place_id": pinned_alt.place_id}],
    }
    recalc_request = RuleItineraryRecalculateRequest.model_validate(recalc_payload)
    recalc = service.recalculate(recalc_request)

    fixed_meal_after = next(m for m in recalc.meal_recommendations if m.day_number == 1 and m.meal_type == "lunch")
    assert fixed_meal_after.place_id == pinned_alt.place_id
    _assert_no_overlap(recalc)
