from __future__ import annotations

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.services.policies.city import jeju_zones


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["sightseeing"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "east-jeju",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample summary",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def test_nearest_zone_picks_the_closest_center() -> None:
    jeju_city_lat, jeju_city_lng = jeju_zones.ZONE_CENTERS["jeju-city"]
    assert jeju_zones.nearest_zone(jeju_city_lat, jeju_city_lng) == "jeju-city"

    seongsan_lat, seongsan_lng = jeju_zones.ZONE_CENTERS["seongsan"]
    assert jeju_zones.nearest_zone(seongsan_lat, seongsan_lng) == "seongsan"


def test_nearest_zone_boundary_point_goes_to_the_actually_closer_center() -> None:
    # Roughly midway between jeju-city and dongbu, but nudged a hair west -
    # the real east-jeju bimodal split this module exists for (see its
    # module docstring) - should resolve to jeju-city, not dongbu.
    jeju_city_lat, jeju_city_lng = jeju_zones.ZONE_CENTERS["jeju-city"]
    dongbu_lat, dongbu_lng = jeju_zones.ZONE_CENTERS["dongbu"]
    midpoint_lat = (jeju_city_lat + dongbu_lat) / 2
    midpoint_lng = (jeju_city_lng + dongbu_lng) / 2 - 0.01

    assert jeju_zones.nearest_zone(midpoint_lat, midpoint_lng) == "jeju-city"


def test_resolve_zone_uses_coordinates_when_available() -> None:
    seongsan_lat, seongsan_lng = jeju_zones.ZONE_CENTERS["seongsan"]
    place = build_place(area="seongsan", latitude=seongsan_lat, longitude=seongsan_lng)

    assert jeju_zones.resolve_zone(place) == "seongsan"


def test_resolve_zone_falls_back_to_area_when_coordinates_are_missing() -> None:
    place_without_coordinates = build_place(area="west-jeju", latitude=None, longitude=None)

    assert jeju_zones.resolve_zone(place_without_coordinates) == jeju_zones.FALLBACK_ZONE_BY_AREA["west-jeju"]


def test_resolve_zone_is_none_for_a_coordinate_less_place_in_an_unmapped_area() -> None:
    place = build_place(area="unmapped-area", latitude=None, longitude=None)

    assert jeju_zones.resolve_zone(place) is None


def test_zone_adjacency_is_symmetric_and_ring_shaped() -> None:
    for zone, neighbors in jeju_zones.ZONE_ADJACENCY.items():
        assert len(neighbors) == 2
        for neighbor in neighbors:
            assert zone in jeju_zones.ZONE_ADJACENCY[neighbor]


def test_are_adjacent_zones_matches_the_ring_order() -> None:
    assert jeju_zones.are_adjacent_zones("jeju-city", "dongbu") is True
    assert jeju_zones.are_adjacent_zones("dongbu", "jeju-city") is True
    assert jeju_zones.are_adjacent_zones("jeju-city", "seongsan") is False


def test_zone_distance_km_is_symmetric_and_positive_for_distinct_zones() -> None:
    distance_a_to_b = jeju_zones.zone_distance_km("jeju-city", "seongsan")
    distance_b_to_a = jeju_zones.zone_distance_km("seongsan", "jeju-city")

    assert distance_a_to_b == distance_b_to_a
    assert distance_a_to_b > 0


def test_zone_distance_km_returns_none_for_an_unknown_zone() -> None:
    assert jeju_zones.zone_distance_km("jeju-city", "not-a-zone") is None
