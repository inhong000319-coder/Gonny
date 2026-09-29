from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService


def _place(
    place_id: str,
    *,
    priority: int,
    activity_type: list[str],
    latitude: float | None = None,
    longitude: float | None = None,
    full_day_recommended: bool = False,
    duration_hours: int = 1,
    closed_days: str | None = None,
) -> PlaceData:
    return PlaceData(
        id=place_id,
        name=place_id,
        activity_type=activity_type,
        budget_level=["low", "medium", "high"],
        suitable_for=["solo", "couple", "friend", "family"],
        time_fit=["morning", "afternoon", "evening"],
        area="test-area",
        duration_hours=duration_hours,
        priority=priority,
        pace=["easy", "tight"],
        mobility=["walkable"],
        summary=f"{place_id} summary",
        latitude=latitude,
        longitude=longitude,
        full_day_recommended=full_day_recommended,
        closed_days=closed_days,
    )


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog - same pattern used throughout this
    test suite (see test_rule_itinerary_closed_days.py), so meal
    recommendation is testable without depending on the real (much larger,
    trained-model-scored) Seoul catalog."""

    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(
            continent="asia",
            country="korea",
            city="testcity",
            default_days=3,
            places=places,
        )

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="testcity", aliases=[])]


def _generate(places: list[PlaceData], *, days: int = 3, concepts: list[str] | None = None, start_date=None):
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))
    request = RuleItineraryRequest(
        continent="asia",
        country="korea",
        city="testcity",
        nights=max(days - 1, 1),
        days=days,
        budget_band="medium",
        concepts=concepts or ["culture"],
        style="easy",
        companion_type="friend",
        start_date=start_date,
    )
    return service.generate(request)


def test_every_non_full_day_gets_lunch_and_dinner_when_the_city_has_enough_food():
    # 20 high-priority non-food fillers dominate the 3 activity slots
    # entirely (food is no longer part of SLOT_CATEGORY_PREFERENCE, so
    # these never compete with food places for a slot at all), and 8
    # food places exist for a 3-day trip (2 meals/day x 3 days = 6 needed,
    # 8 available so there's no exhaustion).
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(20)]
    food_places = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(8)]

    response = _generate([*food_places, *fillers], days=3)

    by_day: dict[int, set[str]] = {}
    for meal in response.meal_recommendations:
        by_day.setdefault(meal.day_number, set()).add(meal.meal_type)

    for day_number in range(1, 4):
        assert by_day.get(day_number) == {"lunch", "dinner"}, f"day {day_number}: {by_day.get(day_number)}"

    # No food place leaked into the 3 activity slots themselves - it's a
    # fully independent recommendation now, not a slot competitor.
    for item in response.items:
        assert item.category != "food"


def test_full_day_place_still_gets_lunch_and_dinner():
    # "activity" concept + a full_day_recommended place makes day 2 of a
    # 3-day trip (the "middle" phase) a full-day day - see
    # RuleItineraryService._pick_full_day_place. The traveler still needs
    # to eat that day even though the day's single activity doesn't
    # itself include meals.
    full_day_place = _place(
        "theme-park", priority=10, activity_type=["액티비티"], full_day_recommended=True,
    )
    fillers = [_place(f"culture-{i}", priority=5, activity_type=["문화·역사"]) for i in range(20)]
    food_places = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(8)]

    response = _generate([full_day_place, *food_places, *fillers], days=3, concepts=["activity"])

    full_day_number = next(
        item.day_number for item in response.items if item.place_name == full_day_place.name
    )
    day_meal_types = {
        meal.meal_type for meal in response.meal_recommendations if meal.day_number == full_day_number
    }
    assert day_meal_types == {"lunch", "dinner"}


def test_no_restaurant_repeats_within_the_same_trip():
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(20)]
    # Exactly 6 food places for a 3-day trip needing exactly 6 meals -
    # every single one must get used exactly once for all 6 to be filled,
    # which only works if none of them repeat.
    food_places = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(6)]

    response = _generate([*food_places, *fillers], days=3)

    place_names = [meal.place_name for meal in response.meal_recommendations]
    assert len(place_names) == 6
    assert len(set(place_names)) == 6, f"a restaurant repeated: {place_names}"


def test_meals_run_out_gracefully_when_the_city_has_too_few_food_entities():
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(20)]
    # Only 2 food places for a 3-day trip needing 6 meals - the rest must
    # be gracefully omitted (no exception, no fabricated recommendation).
    food_places = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(2)]

    response = _generate([*food_places, *fillers], days=3)

    assert len(response.meal_recommendations) == 2
    place_names = {meal.place_name for meal in response.meal_recommendations}
    assert place_names == {"food-0", "food-1"}


def test_lunch_prefers_a_food_place_close_to_the_surrounding_activities():
    # morning/afternoon anchor points sit right next to each other.
    # close_food is right there too; far_food is ~40km away (well outside
    # the city). Identical priority/activity_type on both food candidates
    # isolates the choice to coordinate proximity (meal_candidate_score's
    # coordinate bonuses), not base_score or rating.
    morning_place = _place("morning-spot", priority=8, activity_type=["문화·역사"], latitude=37.5665, longitude=126.9780)
    afternoon_place = _place("afternoon-spot", priority=8, activity_type=["문화·역사"], latitude=37.5670, longitude=126.9785)
    close_food = _place("close-food", priority=5, activity_type=["미식"], latitude=37.5667, longitude=126.9782)
    far_food = _place("far-food", priority=5, activity_type=["미식"], latitude=37.9000, longitude=127.3000)
    fillers = [_place(f"culture-{i}", priority=1, activity_type=["문화·역사"]) for i in range(10)]

    response = _generate(
        [morning_place, afternoon_place, close_food, far_food, *fillers], days=1
    )

    lunch = next((meal for meal in response.meal_recommendations if meal.meal_type == "lunch"), None)
    assert lunch is not None
    assert lunch.place_name == "close-food"


def test_day_duration_warning_accounts_for_meal_time():
    # 3 activity slots at 3h each = 9h, under the 10h threshold on its
    # own (see DAY_DURATION_WARNING_THRESHOLD_HOURS) - only once lunch
    # and dinner (1h each, the default) are added does the day cross it.
    activity_places = [
        _place(f"activity-{i}", priority=9, activity_type=["문화·역사"], duration_hours=3) for i in range(3)
    ]
    food_places = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(4)]

    response = _generate([*activity_places, *food_places], days=1)

    assert any(meal.day_number == 1 for meal in response.meal_recommendations)
    assert any(warning.day_number == 1 for warning in response.day_duration_warnings)


def test_meal_place_names_never_overlap_with_activity_item_place_names():
    # A stronger cross-check of used_ids sharing between activity slots and
    # meals: the exact same restaurant must never show up both as one of
    # the 3 activity items *and* as a meal recommendation.
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(20)]
    food_places = [_place(f"food-{i}", priority=5, activity_type=["미식"]) for i in range(8)]

    response = _generate([*food_places, *fillers], days=3)

    item_place_names = {item.place_name for item in response.items}
    meal_place_names = {meal.place_name for meal in response.meal_recommendations}
    assert item_place_names.isdisjoint(meal_place_names)
