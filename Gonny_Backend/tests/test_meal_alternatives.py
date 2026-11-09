from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService

# 2026-09-15 is a Tuesday (weekday() == 1) - same fixture date test_slot_alternatives.py uses.
A_TUESDAY = date(2026, 9, 15)

MAX_MEAL_ALTERNATIVES = 3


def _place(
    place_id: str,
    *,
    priority: int = 5,
    activity_type: list[str] | None = None,
    area: str = "test-area",
    name: str | None = None,
    meal_eligible: bool = True,
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
        closed_days=closed_days,
    )


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog - same pattern used throughout this
    test suite (see test_rule_itinerary_meal_recommendation.py)."""

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


def _generate(
    places: list[PlaceData],
    *,
    days: int = 1,
    concepts: list[str] | None = None,
    start_date: date | None = None,
    include_breakfast: bool = False,
    include_alternatives: bool = True,
):
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
        include_breakfast=include_breakfast,
    )
    return service.generate(request, include_weather=False, include_alternatives=include_alternatives)


def _fillers(count: int = 10, *, area: str = "test-area") -> list[PlaceData]:
    return [_place(f"culture-{i}", activity_type=["문화·역사"], priority=9, area=area) for i in range(count)]


# --- place_id is always populated -------------------------------------------


def test_every_meal_has_place_id():
    food_places = [_place(f"food-{i}", priority=10 - i) for i in range(8)]
    response = _generate([*food_places, *_fillers()], days=3)

    assert response.meal_recommendations
    food_ids = {p.id for p in food_places}
    assert all(meal.place_id in food_ids for meal in response.meal_recommendations)


# --- basic alternative shape: bounded, excludes the selected restaurant ----


def test_meal_alternatives_present_bounded_and_exclude_selected():
    food_places = [_place(f"food-{i}", priority=10 - i) for i in range(6)]
    response = _generate([*food_places, *_fillers()], days=1)

    lunch = next(meal for meal in response.meal_recommendations if meal.meal_type == "lunch")
    assert 1 <= len(lunch.alternatives) <= MAX_MEAL_ALTERNATIVES
    assert lunch.place_id not in {alt.place_id for alt in lunch.alternatives}
    assert all(alt.category == "food" for alt in lunch.alternatives)
    # No duplicate candidate inside the alternatives list itself.
    alt_ids = [alt.place_id for alt in lunch.alternatives]
    assert len(alt_ids) == len(set(alt_ids))


# --- candidate rule: unused, meal_eligible, not confirmed closed -----------


def test_meal_alternatives_exclude_ineligible_closed_and_already_used():
    breakfast_pick = _place("morning-cafe", priority=10, name="morning-cafe 카페")
    ineligible = _place("ineligible-food", priority=9, meal_eligible=False)
    closed = _place("closed-food", priority=9, closed_days="매주 화요일 휴무")
    lunch_pick = _place("lunch-pick", priority=8)
    valid_alt = _place("valid-alt-food", priority=7)

    places = [breakfast_pick, ineligible, closed, lunch_pick, valid_alt, *_fillers()]
    response = _generate(places, days=1, start_date=A_TUESDAY, include_breakfast=True)

    breakfast = next(meal for meal in response.meal_recommendations if meal.meal_type == "breakfast")
    assert breakfast.place_id == "morning-cafe"

    lunch = next(meal for meal in response.meal_recommendations if meal.meal_type == "lunch")
    assert lunch.place_id == "lunch-pick"
    alt_ids = {alt.place_id for alt in lunch.alternatives}
    assert "morning-cafe" not in alt_ids, "already used by breakfast - must not reappear as a lunch alternative"
    assert "ineligible-food" not in alt_ids, "meal_eligible=False must never be an alternative"
    assert "closed-food" not in alt_ids, "confirmed closed on the trip's weekday must never be an alternative"
    assert "valid-alt-food" in alt_ids


# --- candidate rule: breakfast extra_filter applies to alternatives too ----


def test_breakfast_alternatives_only_include_breakfast_classified_places():
    cafe_a = _place("cafe-a", priority=10, name="cafe-a 카페")
    cafe_b = _place("cafe-b", priority=9, name="cafe-b 브런치")
    # Highest priority, but no breakfast keyword anywhere - must never be
    # picked nor offered as a breakfast alternative.
    non_breakfast_strong = _place("fancy-dinner-spot", priority=10)

    places = [cafe_a, cafe_b, non_breakfast_strong, *_fillers()]
    response = _generate(places, days=1, include_breakfast=True)

    breakfast = next(meal for meal in response.meal_recommendations if meal.meal_type == "breakfast")
    assert breakfast.place_id == "cafe-a"
    alt_ids = {alt.place_id for alt in breakfast.alternatives}
    assert alt_ids == {"cafe-b"}


# --- candidate rule: same _meal_candidate_pool (never padded wider) --------


def test_meal_alternatives_pool_never_forced_wider_than_same_area():
    selected = _place("same-area-pick", priority=10, area="home-area")
    same_area_other = _place("same-area-other", priority=9, area="home-area")
    # Higher priority, but a different (non-neighboring) area - must never
    # be pulled in while the same-area pool is already non-empty.
    far_area_places = [_place(f"far-{i}", priority=10, area="far-away-area") for i in range(5)]

    places = [selected, same_area_other, *far_area_places, *_fillers(area="home-area")]
    response = _generate(places, days=1)

    lunch = next(meal for meal in response.meal_recommendations if meal.meal_type == "lunch")
    assert lunch.place_id == "same-area-pick"
    alt_ids = {alt.place_id for alt in lunch.alternatives}
    assert alt_ids == {"same-area-other"}


# --- include_alternatives=False gate ----------------------------------------


def test_meal_alternatives_empty_when_include_alternatives_false():
    food_places = [_place(f"food-{i}", priority=10 - i) for i in range(6)]
    response = _generate([*food_places, *_fillers()], days=1, include_alternatives=False)

    assert response.meal_recommendations
    for meal in response.meal_recommendations:
        assert meal.alternatives == []
        assert meal.place_id
