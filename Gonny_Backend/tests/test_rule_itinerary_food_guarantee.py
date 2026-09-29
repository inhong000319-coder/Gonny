from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.request_normalizer import normalize_rule_request
from app.domains.rule_planner.services.service import RuleItineraryService


def _place(place_id: str, *, priority: int, activity_type: list[str]) -> PlaceData:
    return PlaceData(
        id=place_id,
        name=place_id,
        activity_type=activity_type,
        budget_level=["low", "medium", "high"],
        suitable_for=["solo", "couple", "friend", "family"],
        time_fit=["morning", "afternoon", "evening"],
        area="test-area",
        duration_hours=2,
        priority=priority,
        pace=["easy", "tight"],
        mobility=["walkable"],
        summary=f"{place_id} summary",
    )


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog - same pattern as
    test_rule_itinerary_closed_days.py's _FakeCatalogProvider, reused here
    so the food-slot guarantee is testable without depending on the real
    (and much larger, higher-priority-dominated) Seoul catalog."""

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


def _build_items(places: list[PlaceData], *, days: int = 3):
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))
    request = RuleItineraryRequest(
        continent="asia",
        country="korea",
        city="testcity",
        nights=max(days - 1, 1),
        days=days,
        budget_band="medium",
        concepts=["culture"],
        style="easy",
        companion_type="friend",
    )
    normalized = normalize_rule_request(request)
    city_catalog = service.catalog_provider.get_city_catalog(continent="asia", country="korea", city="testcity")
    return service._build_items(normalized, city_catalog)


def test_every_non_full_day_gets_a_food_place_when_the_city_has_enough() -> None:
    # 20 high-priority non-food fillers dominate the naive greedy picks
    # (slot_score favors higher priority), and 5 low-priority food places
    # exist for a 3-day trip - enough that a fresh, unused food candidate
    # is always available for each day (each real place can only be used
    # once across the whole itinerary - see used_ids - so "1 food place
    # total" could never satisfy 3 separate days regardless of the
    # guarantee; that's not this test's scenario, see the "not enough
    # food entities" test below for that case). Without the guarantee,
    # these food places would very likely never get picked at all, since
    # they're outranked by every filler on priority alone.
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(20)]
    food_places = [_place(f"food-place-{i}", priority=1, activity_type=["미식"]) for i in range(5)]

    _, day_place_map, _ = _build_items([*food_places, *fillers], days=3)

    assert day_place_map, "expected at least one day to have places placed"
    for day_number, places in day_place_map.items():
        concept_tags = {tag for place in places for tag in place.concept_tags}
        assert "food" in concept_tags, f"day {day_number} has no food place: {[p.id for p in places]}"


def test_food_guarantee_leaves_a_day_without_food_when_the_only_food_place_was_already_used_that_trip() -> None:
    # Exactly one food place exists for a 3-day trip - once it's used on
    # whichever day places it (via the guarantee or naturally), no food
    # candidate remains for the other days. This is the "후보가 전혀 없으면
    # ... 교체하지 않고 넘어간다" case from this feature's spec: a real data
    # gap for this fake catalog, not a bug - each place can only appear
    # once across the whole itinerary (see used_ids), so 1 food place can
    # never cover every day of a multi-day trip.
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(20)]
    lone_food_place = _place("only-food-place", priority=1, activity_type=["미식"])

    _, day_place_map, _ = _build_items([lone_food_place, *fillers], days=3)

    assert day_place_map
    days_with_food = [
        day_number
        for day_number, places in day_place_map.items()
        if any("food" in place.concept_tags for place in places)
    ]
    # The single food place gets used exactly once, on exactly one day.
    assert days_with_food == [1]


def test_food_guarantee_is_a_noop_when_the_city_has_no_food_entity() -> None:
    # No food-tagged place exists anywhere in this catalog - the guarantee
    # must not fabricate one, raise, or drop a slot; it should just leave
    # every day as the greedy/refinement passes produced it (a data gap,
    # not a bug - see _ensure_food_slot's docstring).
    fillers = [_place(f"culture-{i}", priority=9, activity_type=["문화·역사"]) for i in range(6)]

    _, day_place_map, _ = _build_items(fillers, days=2)

    assert day_place_map
    for places in day_place_map.values():
        assert len(places) == 3  # still a full day of slots, nothing dropped
        concept_tags = {tag for place in places for tag in place.concept_tags}
        assert "food" not in concept_tags


def test_food_guarantee_does_not_disturb_a_day_that_already_has_food() -> None:
    # A high-priority food place naturally wins a slot on its own merit -
    # the guarantee's early-return (see _ensure_food_slot) should leave the
    # day exactly as the greedy/refinement passes produced it.
    food_place = _place("popular-restaurant", priority=10, activity_type=["미식"])
    fillers = [_place(f"culture-{i}", priority=5, activity_type=["문화·역사"]) for i in range(6)]

    items, day_place_map, _ = _build_items([food_place, *fillers], days=1)

    day1_places = day_place_map[1]
    assert any(place.id == "popular-restaurant" for place in day1_places)
    assert any("food" in place.concept_tags for place in day1_places)
