from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.destination_catalog.services.repository import DestinationCatalogRepository
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService


def _place(place_id: str, *, priority: int, average_cost_krw: int | None) -> PlaceData:
    return PlaceData(
        id=place_id,
        name=place_id,
        activity_type=["문화·역사"],
        budget_level=["low", "medium", "high"],
        suitable_for=["solo", "couple", "friend", "family"],
        time_fit=["morning", "afternoon", "evening"],
        area="test-area",
        duration_hours=1,
        priority=priority,
        pace=["easy", "tight"],
        mobility=["walkable"],
        summary=f"{place_id} summary",
        average_cost_krw=average_cost_krw,
    )


class _FakeCatalogProvider(PlaceCatalogProvider):
    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(
            continent="asia", country="korea", city="testcity", default_days=1, places=places
        )

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="testcity", aliases=[])]


def test_zero_cost_is_kept_distinct_from_unknown_cost() -> None:
    free = _place("free-place", priority=5, average_cost_krw=0)
    unknown = _place("unknown-place", priority=5, average_cost_krw=None)

    assert free.model_dump()["average_cost_krw"] == 0
    assert unknown.model_dump()["average_cost_krw"] is None


def test_itinerary_items_copy_the_source_place_cost() -> None:
    places = [
        _place("free-place", priority=9, average_cost_krw=0),
        _place("paid-place", priority=8, average_cost_krw=5000),
        _place("unknown-place", priority=7, average_cost_krw=None),
    ]
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))
    request = RuleItineraryRequest(
        continent="asia",
        country="korea",
        city="testcity",
        nights=1,
        days=1,
        budget_band="medium",
        concepts=["culture"],
        style="easy",
        companion_type="friend",
    )

    response = service.generate(request)

    costs = {item.place_name: item.average_cost_krw for item in response.items}
    assert costs["free-place"] == 0
    assert costs["paid-place"] == 5000
    assert costs["unknown-place"] is None


def test_food_entities_never_carry_a_cost_in_the_real_catalog() -> None:
    repository = DestinationCatalogRepository()
    for catalog in repository.load_catalogs():
        for place in catalog.places:
            if "미식" in place.activity_type:
                assert place.average_cost_krw is None, f"{place.id} is food but has a cost"