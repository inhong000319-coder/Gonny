from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService
from app.main import app

# 2026-09-15 is a Tuesday (weekday() == 1).
A_TUESDAY = date(2026, 9, 15)

MAX_ALTERNATIVES = 3


def _place(place_id: str, *, priority: int, **overrides) -> PlaceData:
    data = {
        "id": place_id,
        "name": place_id,
        "activity_type": ["문화·역사"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "test-area",
        "duration_hours": 2,
        "priority": priority,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": f"{place_id} summary",
        "average_cost_krw": 1000 * priority,
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog - same pattern as
    test_rule_itinerary_closed_days.py's fake provider."""

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


def _filler_places(count: int = 10) -> list[PlaceData]:
    names = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
    return [_place(name, priority=min(10, 10 - index)) for index, name in enumerate(names[:count])]


def _rule_set_catalog() -> list[PlaceData]:
    places = _filler_places(10)
    places.append(_place("restaurant-x", priority=10, activity_type=["미식"]))
    places.append(_place("inactive-y", priority=10, is_active=False))
    places.append(_place("morning-only-z", priority=10, time_fit=["morning"]))
    places.append(_place("closed-tuesday", priority=7, closed_days="매주 화요일 휴무"))
    return places


def _build_request(*, start_date: date | None, days: int = 1, nights: int = 1, concepts=None) -> RuleItineraryRequest:
    return RuleItineraryRequest(
        continent="asia",
        country="korea",
        city="testcity",
        nights=nights,
        days=days,
        budget_band="medium",
        concepts=concepts or ["culture"],
        style="easy",
        companion_type="friend",
        start_date=start_date,
    )


def _generate(places: list[PlaceData], request: RuleItineraryRequest, **kwargs):
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))
    return service.generate(request, **kwargs)


# --- core alternative-rule invariants ---------------------------------------


def test_alternatives_respect_all_rules_at_once():
    places = _rule_set_catalog()
    places_by_id = {place.id: place for place in places}
    request = _build_request(start_date=A_TUESDAY)

    response = _generate(places, request)

    assert response.items, "fixture should produce at least one item"
    used_place_names = {item.place_name for item in response.items}

    for item in response.items:
        # 최대 3곳
        assert len(item.alternatives) <= MAX_ALTERNATIVES

        chosen_place_id = item.place_name  # fake places use id == name
        for alt in item.alternatives:
            place = places_by_id[alt.place_id]

            # 현재 선택과 같은 장소 없음
            assert alt.place_id != chosen_place_id

            # 같은 일정 다른 슬롯 장소 없음 (전 일차 포함)
            assert place.name not in used_place_names

            # 식당 없음
            assert "food" not in place.concept_tags
            assert alt.place_id != "restaurant-x"

            # 비활성 없음
            assert place.is_active
            assert alt.place_id != "inactive-y"

            # 슬롯 time_fit 위반 없음
            assert item.time_slot in place.time_fit

            # 휴무일 제외 (start_date=A_TUESDAY, day 1 == Tuesday)
            assert alt.place_id != "closed-tuesday"


def test_morning_only_candidate_never_appears_as_afternoon_or_evening_alternative():
    places = _rule_set_catalog()
    request = _build_request(start_date=None)

    response = _generate(places, request)

    for item in response.items:
        if item.time_slot != "morning":
            assert all(alt.place_id != "morning-only-z" for alt in item.alternatives)


def test_closed_day_candidate_is_excluded_only_when_start_date_makes_it_closed():
    places = _rule_set_catalog()

    closed_response = _generate(places, _build_request(start_date=A_TUESDAY))
    for item in closed_response.items:
        assert all(alt.place_id != "closed-tuesday" for alt in item.alternatives)

    # No start_date -> closed-day exclusion never triggers (same rule as the
    # real selection logic's _is_open_on_day / _day_weekday).
    open_response = _generate(places, _build_request(start_date=None))
    appeared = any(
        alt.place_id == "closed-tuesday" for item in open_response.items for alt in item.alternatives
    )
    assert appeared


def test_alternatives_are_deterministic_across_repeated_calls():
    places = _rule_set_catalog()
    request = _build_request(start_date=A_TUESDAY)

    first = _generate(places, request)
    second = _generate(places, request)

    first_ids = [[alt.place_id for alt in item.alternatives] for item in first.items]
    second_ids = [[alt.place_id for alt in item.alternatives] for item in second.items]
    assert first_ids == second_ids


def test_include_alternatives_false_yields_empty_lists():
    places = _rule_set_catalog()
    request = _build_request(start_date=A_TUESDAY)

    response = _generate(places, request, include_alternatives=False)

    assert response.items
    assert all(item.alternatives == [] for item in response.items)


def test_full_day_item_has_empty_alternatives():
    places = _filler_places(10)
    places.append(
        _place(
            # Lowest priority so it can never win a normal (non-full-day)
            # slot on day 1/3 - _pick_full_day_place ranks it independently
            # (base_score + 20) and it's the only full_day_recommended
            # candidate, so it still wins day 2's full-day slot regardless.
            "funday-place",
            priority=1,
            activity_type=["액티비티"],
            full_day_recommended=True,
        )
    )
    request = _build_request(start_date=None, days=3, nights=2, concepts=["activity"])

    response = _generate(places, request)

    full_day_items = [item for item in response.items if item.place_name == "funday-place"]
    assert len(full_day_items) == 3, "fixture should make day 2 a full-day item"
    for item in full_day_items:
        assert item.day_number == 2
        assert item.alternatives == []


# --- real-city coverage (Seoul / Busan / Jeju) ------------------------------


def test_each_real_city_has_at_least_one_slot_with_an_alternative():
    service = RuleItineraryService()
    for city in ["seoul", "busan", "jeju"]:
        request = RuleItineraryRequest(
            city=city,
            nights=2,
            days=3,
            travelers=2,
            companion_type="couple",
            budget_band="medium",
            concepts=["sightseeing", "food"],
            style="easy",
        )
        response = service.generate(request)
        assert response.items, city
        total_alternatives = sum(len(item.alternatives) for item in response.items)
        assert total_alternatives >= 1, city


# --- response-contract: /rule-itinerary/generate ----------------------------


def test_generate_endpoint_response_has_existing_fields_plus_alternatives():
    with TestClient(app) as client:
        payload = {
            "city": "seoul",
            "nights": 2,
            "days": 3,
            "travelers": 2,
            "companion_type": "couple",
            "budget_band": "medium",
            "concepts": ["sightseeing", "food"],
            "style": "easy",
        }
        response = client.post("/rule-itinerary/generate", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert "items" in body and body["items"]
    assert "meal_recommendations" in body
    assert "accommodation_recommendation" in body
    assert "day_travel" in body
    assert "day_summaries" in body
    assert "estimated_cost" in body
    assert "day_duration_warnings" in body
    assert "closed_day_exclusions" in body

    for item in body["items"]:
        assert "alternatives" in item
        for alt in item["alternatives"]:
            assert set(alt.keys()) >= {"place_id", "place_name", "category", "area", "notes", "average_cost_krw"}


# --- compare-transport is unaffected ----------------------------------------


def test_compare_transport_never_computes_alternatives(monkeypatch):
    import app.domains.rule_planner.services.service as service_module

    call_count = {"generate": 0, "compare": 0}
    real_compute = service_module.compute_item_alternatives

    def counting_compute(**kwargs):
        call_count["generate"] += 1
        return real_compute(**kwargs)

    monkeypatch.setattr(service_module, "compute_item_alternatives", counting_compute)

    service = RuleItineraryService()
    request = RuleItineraryRequest(
        city="seoul",
        nights=2,
        days=3,
        travelers=2,
        companion_type="couple",
        budget_band="medium",
        concepts=["sightseeing", "food"],
        style="easy",
    )

    comparison = service.compare_transport(request)
    assert call_count["generate"] == 0, "compare_transport must never trigger alternatives computation"
    assert comparison.base is not None

    service.generate(request)
    assert call_count["generate"] == 1, "a direct generate() call must still compute alternatives"


def test_compare_transport_endpoint_response_shape_is_unchanged():
    with TestClient(app) as client:
        payload = {
            "city": "seoul",
            "nights": 2,
            "days": 3,
            "travelers": 2,
            "companion_type": "couple",
            "budget_band": "medium",
            "concepts": ["sightseeing", "food"],
            "style": "easy",
        }
        response = client.post("/rule-itinerary/compare-transport", json=payload)

    assert response.status_code == 200
    body = response.json()
    # RuleTransportComparisonResponse carries only travel-minute totals
    # (base/comparisons) - no RuleItineraryItem/alternatives ever appears on
    # this path, unchanged by this feature.
    assert set(body.keys()) == {"base", "comparisons"}
    assert "total_travel_minutes" in body["base"]
    for comparison in body["comparisons"]:
        assert "scenario" in comparison and "days" in comparison
