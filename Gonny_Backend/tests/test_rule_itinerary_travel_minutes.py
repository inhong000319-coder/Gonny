from datetime import date

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.travel_estimate import estimate_travel_minutes_between

A_WEDNESDAY = date(2026, 9, 16)


def _place(
    place_id: str,
    *,
    priority: int,
    latitude: float | None = None,
    longitude: float | None = None,
    full_day_recommended: bool = False,
    activity_type: list[str] | None = None,
) -> PlaceData:
    return PlaceData(
        id=place_id,
        name=place_id,
        activity_type=activity_type or ["문화·역사"],
        budget_level=["low", "medium", "high"],
        suitable_for=["solo", "couple", "friend", "family"],
        time_fit=["morning", "afternoon", "evening"],
        area="test-area",
        duration_hours=2,
        priority=priority,
        pace=["easy", "tight"],
        mobility=["walkable"],
        summary=f"{place_id} summary",
        latitude=latitude,
        longitude=longitude,
        full_day_recommended=full_day_recommended,
    )


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog - same pattern as
    test_rule_itinerary_closed_days.py's _FakeCatalogProvider, reused here
    so travel-minutes placement is testable without depending on the real
    (and much larger) Seoul catalog's trained-model scoring."""

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


def _generate(places: list[PlaceData], *, days: int = 1):
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
        start_date=A_WEDNESDAY,
    )
    return service.generate(request)


def test_first_slot_of_the_day_has_no_previous_travel_time():
    places = [
        _place("morning-spot", priority=10, latitude=37.5, longitude=127.0),
        _place("afternoon-spot", priority=9, latitude=37.51, longitude=127.01),
        _place("evening-spot", priority=8, latitude=37.52, longitude=127.02),
    ]

    response = _generate(places)

    first_item = next(item for item in response.items if item.time_slot == "morning")
    assert first_item.travel_minutes_from_previous is None


def test_later_slots_match_estimate_travel_minutes_between():
    morning = _place("morning-spot", priority=10, latitude=37.5, longitude=127.0)
    afternoon = _place("afternoon-spot", priority=9, latitude=37.51, longitude=127.01)
    evening = _place("evening-spot", priority=8, latitude=37.52, longitude=127.02)

    response = _generate([morning, afternoon, evening])

    items_by_slot = {item.time_slot: item for item in response.items}
    expected_afternoon_minutes = estimate_travel_minutes_between(morning, afternoon)
    expected_evening_minutes = estimate_travel_minutes_between(afternoon, evening)

    assert expected_afternoon_minutes is not None
    assert expected_evening_minutes is not None
    assert items_by_slot["afternoon"].travel_minutes_from_previous == expected_afternoon_minutes
    assert items_by_slot["evening"].travel_minutes_from_previous == expected_evening_minutes


def test_missing_coordinates_on_either_place_yields_none():
    morning = _place("morning-spot", priority=10, latitude=37.5, longitude=127.0)
    # No coordinates at all - estimate_travel_minutes_between's None-on-
    # missing-data contract must propagate through untouched.
    afternoon = _place("afternoon-spot", priority=9, latitude=None, longitude=None)
    evening = _place("evening-spot", priority=8, latitude=37.52, longitude=127.02)

    response = _generate([morning, afternoon, evening])

    items_by_slot = {item.time_slot: item for item in response.items}
    assert items_by_slot["afternoon"].travel_minutes_from_previous is None
    # evening's previous place (afternoon) also lacks coordinates, so this
    # leg is unresolvable too, even though evening itself has coordinates.
    assert items_by_slot["evening"].travel_minutes_from_previous is None


def test_full_day_place_always_has_none_travel_minutes():
    full_day_place = _place(
        "full-day-museum",
        priority=10,
        latitude=37.5,
        longitude=127.0,
        full_day_recommended=True,
        activity_type=["액티비티"],
    )
    # Day 1 (arrival) and day 3 (departure) each need 3 non-activity
    # fillers of their own - arrival/departure phases prefer non-activity
    # places, but fall back to whatever's left once fillers run out, which
    # would otherwise "steal" the museum before day 2's full-day pick runs.
    # Plenty of low-priority fillers keeps the museum untouched until then.
    fillers = [
        _place(f"filler-{index}", priority=1, latitude=37.6 + index * 0.01, longitude=127.1 + index * 0.01)
        for index in range(8)
    ]

    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider([full_day_place, *fillers]))
    request = RuleItineraryRequest(
        continent="asia",
        country="korea",
        city="testcity",
        nights=2,
        days=3,
        budget_band="medium",
        concepts=["activity"],
        style="easy",
        companion_type="friend",
        start_date=A_WEDNESDAY,
    )
    response = service.generate(request)

    full_day_items = [item for item in response.items if item.place_name == "full-day-museum"]
    assert len(full_day_items) == 3
    assert all(item.travel_minutes_from_previous is None for item in full_day_items)
