from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleItineraryRequest
from app.domains.rule_planner.services.accommodation_scoring import (
    rank_accommodations,
    select_accommodation_recommendation,
)
from app.domains.rule_planner.services.service import RuleItineraryService
from app.main import app


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "sample-hotel",
        "name": "Sample Hotel",
        "city": "seoul",
        "area": "gangnam",
        "accommodation_type": "호텔",
        "budget_level": ["medium"],
        "suitable_for": ["couple"],
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)


def build_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "seoul",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
        "companion_type": "couple",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


def build_real_request(city: str, **overrides) -> RuleItineraryRequest:
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


# --- rank_accommodations: top matches select_accommodation_recommendation --


def test_rank_top_matches_select_for_a_synthetic_tie():
    request = build_request(budget_band="medium", companion_type="couple")
    same_point = (37.5665, 126.9780)
    later_id = build_accommodation(id="zz-later-id", latitude=same_point[0], longitude=same_point[1])
    earlier_id = build_accommodation(id="aa-earlier-id", latitude=same_point[0], longitude=same_point[1])

    ranked = rank_accommodations([later_id, earlier_id], request, same_point)
    selected = select_accommodation_recommendation([later_id, earlier_id], request, same_point)

    assert ranked[0].id == selected.id == "aa-earlier-id"


def test_rank_preserves_distance_then_id_tie_break_order():
    from app.domains.rule_planner.services.travel_estimate import haversine_distance_km

    request = build_request(budget_band="medium", companion_type="couple")
    reference_point = (37.5665, 126.9780)
    nearer_but_later_id = build_accommodation(id="zz-nearer", latitude=37.5790, longitude=126.9780)
    farther_but_earlier_id = build_accommodation(id="aa-farther", latitude=37.5890, longitude=126.9780)

    nearer_km = haversine_distance_km(*reference_point, nearer_but_later_id.latitude, nearer_but_later_id.longitude)
    farther_km = haversine_distance_km(*reference_point, farther_but_earlier_id.latitude, farther_but_earlier_id.longitude)
    assert 1.0 < nearer_km < farther_km <= 3.0  # same NEARBY tier -> genuine score tie

    ranked = rank_accommodations([farther_but_earlier_id, nearer_but_later_id], request, reference_point)
    assert [a.id for a in ranked] == ["zz-nearer", "aa-farther"]


def test_rank_empty_pool_returns_empty_list_and_select_returns_none():
    request = build_request()
    assert rank_accommodations([], request, None) == []
    assert select_accommodation_recommendation([], request, None) is None


def test_rank_top_matches_select_for_each_real_city():
    service = RuleItineraryService()
    for city in ["seoul", "busan", "jeju"]:
        request = build_real_request(city)
        normalized = service._normalize_request(request)
        city_catalog = service.catalog_provider.get_city_catalog(
            continent=normalized.continent, country=normalized.country, city=normalized.city, visible_only=True
        )
        from app.domains.rule_planner.services.accommodation_scoring import (
            compute_day_endpoints,
            compute_reference_point,
            load_city_accommodations,
        )

        _items, day_place_map, _closed, _slots, _feedback, _areas = service._build_items(normalized, city_catalog)
        accommodations = load_city_accommodations(city_catalog.city)
        reference_point = compute_reference_point(day_place_map, city_catalog)
        day_endpoints = compute_day_endpoints(day_place_map)

        ranked = rank_accommodations(accommodations, normalized, reference_point, day_endpoints)
        selected = select_accommodation_recommendation(accommodations, normalized, reference_point, day_endpoints)

        assert ranked, city
        assert ranked[0].id == selected.id, city


# --- accommodation_alternatives rule tests ----------------------------------


def test_alternatives_max_three_and_exclude_the_recommendation():
    request = build_request()
    pool = [build_accommodation(id=f"acc-{i}", latitude=37.56 + i * 0.001, longitude=126.97) for i in range(6)]

    ranked = rank_accommodations(pool, request, (37.5665, 126.9780))
    recommended = ranked[0]
    alternatives = ranked[1:4]

    assert len(alternatives) <= 3
    assert recommended.id not in {a.id for a in alternatives}
    assert len(alternatives) == 3  # 6-candidate pool, plenty for 3


def test_alternatives_drawn_from_the_same_coordinate_preferred_pool_as_selection():
    request = build_request(budget_band="low", companion_type="solo")
    # Scores much better on fit but has no coordinates - must never appear
    # as a recommendation OR an alternative once a coordinate-having
    # candidate exists (see rank_accommodations' coordinate-preference rule).
    no_coords_better_fit = build_accommodation(
        id="no-coords", budget_level=["low"], suitable_for=["solo"], latitude=None, longitude=None,
    )
    with_coords = [
        build_accommodation(id=f"coord-{i}", latitude=37.56 + i * 0.001, longitude=126.97, budget_level=["high"], suitable_for=["family"])
        for i in range(3)
    ]

    ranked = rank_accommodations([no_coords_better_fit, *with_coords], request, (37.5665, 126.9780))

    assert "no-coords" not in {a.id for a in ranked}


def test_alternatives_respect_type_filter_even_when_another_type_scores_higher():
    request = build_request(accommodation_types=["펜션·민박"])
    higher_scoring_hotel = build_accommodation(id="hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"])
    pensions = [
        build_accommodation(id=f"pension-{i}", accommodation_type="펜션·민박", budget_level=["low"], suitable_for=["solo"])
        for i in range(3)
    ]

    ranked = rank_accommodations([higher_scoring_hotel, *pensions], request, None)

    assert ranked[0].id != "hotel"
    assert all(a.accommodation_type == "펜션·민박" for a in ranked[1:4])


def test_alternatives_empty_when_real_seoul_type_pool_has_only_the_recommendation():
    # Real catalog fact (test_accommodation_options.py's catalog-count
    # assertion confirms this): Seoul has exactly 1 콘도미니엄.
    from app.domains.rule_planner.services.accommodation_scoring import load_city_accommodations

    accommodations = load_city_accommodations("seoul")
    request = build_request(city="seoul", accommodation_types=["콘도미니엄"])

    ranked = rank_accommodations(accommodations, request, None)

    assert len(ranked) == 1
    assert ranked[1:4] == []


def test_alternatives_has_exactly_one_when_real_seoul_type_pool_has_two():
    # Real catalog fact: Seoul has exactly 2 모텔.
    from app.domains.rule_planner.services.accommodation_scoring import load_city_accommodations

    accommodations = load_city_accommodations("seoul")
    request = build_request(city="seoul", accommodation_types=["모텔"])

    ranked = rank_accommodations(accommodations, request, None)

    assert len(ranked) == 2
    assert len(ranked[1:4]) == 1


def test_alternatives_empty_when_city_has_no_accommodation_data():
    request = build_request(city="nowhere-city")
    ranked = rank_accommodations([], request, None)
    assert ranked == []
    assert ranked[1:4] == []


def test_alternatives_empty_when_include_alternatives_false():
    service = RuleItineraryService()
    request = build_real_request("seoul")

    response = service.generate(request, include_weather=False, include_alternatives=False)

    assert response.accommodation_recommendation is not None
    assert response.accommodation_alternatives == []


def test_alternatives_deterministic_across_two_identical_calls():
    service = RuleItineraryService()
    request = build_real_request("seoul")

    first = service.generate(request, include_weather=False)
    second = service.generate(request, include_weather=False)

    assert [a.id for a in first.accommodation_alternatives] == [a.id for a in second.accommodation_alternatives]


def test_each_real_city_has_accommodation_alternatives():
    service = RuleItineraryService()
    for city in ["seoul", "busan", "jeju"]:
        request = build_real_request(city)
        response = service.generate(request, include_weather=False)

        assert response.accommodation_recommendation is not None, city
        assert len(response.accommodation_alternatives) >= 1, city
        assert response.accommodation_recommendation.id not in {
            a.id for a in response.accommodation_alternatives
        }, city


# --- response contract --------------------------------------------------


def test_generate_endpoint_response_has_existing_fields_plus_accommodation_alternatives():
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

    assert "accommodation_recommendation" in body
    assert "accommodation_alternatives" in body
    assert isinstance(body["accommodation_alternatives"], list)
    assert 1 <= len(body["accommodation_alternatives"]) <= 3
    for alt in body["accommodation_alternatives"]:
        assert "id" in alt and "name" in alt and "accommodation_type" in alt
    # items[].alternatives (PR #104) unchanged by this feature
    assert all("alternatives" in item for item in body["items"])


def test_compare_transport_never_computes_accommodation_alternatives(monkeypatch):
    import app.domains.rule_planner.services.service as service_module

    call_count = {"alt": 0}
    real_method = service_module.RuleItineraryService._recommend_accommodation_alternatives

    def counting_method(self, *args, **kwargs):
        call_count["alt"] += 1
        return real_method(self, *args, **kwargs)

    monkeypatch.setattr(
        service_module.RuleItineraryService, "_recommend_accommodation_alternatives", counting_method
    )

    service = RuleItineraryService()
    request = build_real_request("seoul")

    comparison = service.compare_transport(request)
    assert call_count["alt"] == 0, "compare_transport must never trigger accommodation alternatives computation"
    assert comparison.base is not None

    service.generate(request, include_weather=False)
    assert call_count["alt"] == 1, "a direct generate() call must still compute accommodation alternatives"


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
    assert set(body.keys()) == {"base", "comparisons"}
