from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.travel_estimate import (
    WALK_OPTION_MAX_MINUTES,
    estimate_mode_minutes,
    estimate_transport_options,
    estimate_walk_option_minutes,
)


def build_place(place_id: str, latitude: float | None, longitude: float | None, **overrides) -> PlaceData:
    data = {
        "id": place_id,
        "name": place_id,
        "activity_type": ["sightseeing"],
        "budget_level": ["medium"],
        "suitable_for": ["couple"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "gangnam",
        "duration_hours": 1,
        "priority": 7,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": "sample",
        "latitude": latitude,
        "longitude": longitude,
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def build_accommodation(latitude: float | None, longitude: float | None, **overrides) -> AccommodationData:
    data = {
        "id": "stay",
        "name": "Stay",
        "city": "seoul",
        "area": "gangnam",
        "accommodation_type": "호텔",
        "budget_level": ["medium"],
        "suitable_for": ["couple"],
        "latitude": latitude,
        "longitude": longitude,
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)


# --- Mode-aware minute calculations (travel_estimate.py) ------------------


def test_mode_minutes_increase_with_distance_for_transit_and_car() -> None:
    distances = [0.5, 1.0, 2.0, 5.0, 10.0]
    for mode in ["transit", "car"]:
        minutes = [estimate_mode_minutes(mode, d, "seoul") for d in distances]
        assert minutes == sorted(minutes), (mode, minutes)
        assert len(set(minutes)) > 1


def test_near_zero_distance_still_returns_at_least_the_fixed_time() -> None:
    assert estimate_mode_minutes("transit", 0.0, "seoul") == 10
    assert estimate_mode_minutes("car", 0.0, "seoul") == 8
    assert estimate_walk_option_minutes(0.0) == 1


def test_same_distance_jeju_car_faster_than_seoul_car() -> None:
    assert estimate_mode_minutes("car", 5.0, "jeju") < estimate_mode_minutes("car", 5.0, "seoul")


def test_same_distance_jeju_transit_slower_than_seoul_transit() -> None:
    assert estimate_mode_minutes("transit", 5.0, "jeju") > estimate_mode_minutes("transit", 5.0, "seoul")


def test_unknown_city_falls_back_to_seoul_profile() -> None:
    assert estimate_mode_minutes("transit", 5.0, "unknown-city") == estimate_mode_minutes("transit", 5.0, "seoul")
    assert estimate_mode_minutes("car", 5.0, "unknown-city") == estimate_mode_minutes("car", 5.0, "seoul")


def test_walk_option_included_only_at_or_under_threshold() -> None:
    # 1.0km rounds to exactly WALK_OPTION_MAX_MINUTES (20); 1.1km rounds to 21.
    included_distance = 1.0
    excluded_distance = 1.1
    assert estimate_walk_option_minutes(included_distance) == WALK_OPTION_MAX_MINUTES
    assert estimate_walk_option_minutes(excluded_distance) == WALK_OPTION_MAX_MINUTES + 1

    included_options = estimate_transport_options(included_distance, "seoul")
    excluded_options = estimate_transport_options(excluded_distance, "seoul")
    assert "walk" in [option.mode for option in included_options]
    assert "walk" not in [option.mode for option in excluded_options]
    assert {"transit", "car"} <= {option.mode for option in included_options}
    assert {"transit", "car"} <= {option.mode for option in excluded_options}


def test_mode_minutes_do_not_invert_across_the_old_1_2_1_3km_boundary() -> None:
    # estimate_straight_line_travel_minutes (the old, untouched function)
    # inverts right at this boundary because it switches speed tiers with
    # no fixed cost. The new per-mode functions use one continuous formula
    # with a fixed cost, so they must not invert here.
    for mode in ["transit", "car"]:
        for city in ["seoul", "busan", "jeju"]:
            below = estimate_mode_minutes(mode, 1.2, city)
            above = estimate_mode_minutes(mode, 1.3, city)
            assert above >= below, (mode, city, below, above)


# --- Day-travel assembly (service.py, white-box on the new helpers) -------


def test_leg_count_matches_sequence_length_plus_accommodation_legs() -> None:
    service = RuleItineraryService()
    morning = build_place("morning", 37.50, 127.00)
    lunch = build_place("lunch", 37.501, 127.001)
    afternoon = build_place("afternoon", 37.502, 127.002)
    dinner = build_place("dinner", 37.503, 127.003)
    evening = build_place("evening", 37.504, 127.004)
    accommodation = build_accommodation(37.49, 126.99)

    sequence = service._sequence_day_places_with_kind([morning, afternoon, evening], lunch_place=lunch, dinner_place=dinner)
    assert len(sequence) == 5

    day_travel = service._build_day_travel({1: sequence}, accommodation, city="seoul")

    assert len(day_travel) == 1
    legs = day_travel[0].legs
    # 5 sequence entries -> 4 internal legs, plus 2 accommodation legs (start and end).
    assert len(legs) == (len(sequence) - 1) + 2
    assert legs[0].from_kind == "accommodation" and legs[0].to_kind == "place"
    assert legs[-1].to_kind == "accommodation"
    assert [leg.to_kind for leg in legs[:-1]] == ["place", "meal", "place", "meal", "place"]


def test_missing_coordinates_drop_only_the_adjacent_legs() -> None:
    service = RuleItineraryService()
    morning = build_place("morning", 37.50, 127.00)
    lunch = build_place("lunch", 37.501, 127.001)
    afternoon = build_place("afternoon", None, None)  # no coordinates
    dinner = build_place("dinner", 37.503, 127.003)
    evening = build_place("evening", 37.504, 127.004)
    accommodation = build_accommodation(37.49, 126.99)

    sequence = service._sequence_day_places_with_kind([morning, afternoon, evening], lunch_place=lunch, dinner_place=dinner)
    day_travel = service._build_day_travel({1: sequence}, accommodation, city="seoul")

    assert len(day_travel) == 1
    legs = day_travel[0].legs
    # acc->morning and morning->lunch survive; lunch->afternoon and
    # afternoon->dinner are dropped (afternoon has no coordinates);
    # dinner->evening and evening->acc survive. No exception anywhere.
    pairs = [(leg.from_name, leg.to_name) for leg in legs]
    assert ("lunch", "afternoon") not in pairs
    assert ("afternoon", "dinner") not in pairs
    assert len(legs) == 4


def test_day_with_zero_legs_is_excluded_from_day_travel() -> None:
    service = RuleItineraryService()
    lone_place = build_place("lone", 37.50, 127.00)
    sequence = service._sequence_day_places_with_kind([lone_place], lunch_place=None, dinner_place=None)

    day_travel = service._build_day_travel({1: sequence}, None, city="seoul")

    assert day_travel == []


def test_totals_use_the_smaller_of_mode_minutes_and_walk_minutes_per_leg() -> None:
    service = RuleItineraryService()
    near = build_place("near", 37.5000, 127.0000)
    far = build_place("far", 37.5700, 127.0800)  # a few km away, no walk option
    sequence = service._sequence_day_places_with_kind([near, far], lunch_place=None, dinner_place=None)

    day_travel = service._build_day_travel({1: sequence}, None, city="seoul")

    leg = day_travel[0].legs[0]
    walk_option = next((o for o in leg.options if o.mode == "walk"), None)
    transit_option = next(o for o in leg.options if o.mode == "transit")
    car_option = next(o for o in leg.options if o.mode == "car")
    expected_transit_total = min(transit_option.minutes, walk_option.minutes) if walk_option else transit_option.minutes
    expected_car_total = min(car_option.minutes, walk_option.minutes) if walk_option else car_option.minutes

    assert day_travel[0].transit_total_minutes == expected_transit_total
    assert day_travel[0].car_total_minutes == expected_car_total


def test_sequence_with_kind_matches_meal_splice_order_and_kind_tags() -> None:
    service = RuleItineraryService()
    morning = build_place("morning", 37.50, 127.00)
    afternoon = build_place("afternoon", 37.51, 127.01)
    evening = build_place("evening", 37.52, 127.02)
    lunch = build_place("lunch", 37.505, 127.005)
    dinner = build_place("dinner", 37.515, 127.015)

    spliced = service._splice_meals_into_day_places([morning, afternoon, evening], lunch_place=lunch, dinner_place=dinner)
    sequence = service._sequence_day_places_with_kind([morning, afternoon, evening], lunch_place=lunch, dinner_place=dinner)

    assert [place for place, _kind in sequence] == spliced
    assert [kind for _place, kind in sequence] == ["place", "meal", "place", "meal", "place"]


# --- Integration: real catalogs for each city ------------------------------


def _build_request(city: str) -> RuleItineraryRequest:
    return RuleItineraryRequest(
        city=city,
        nights=2,
        days=3,
        travelers=2,
        companion_type="couple",
        budget_band="medium",
        concepts=["sightseeing", "culture"],
        style="easy",
    )


def test_generate_fills_day_travel_with_internally_consistent_totals_for_each_city() -> None:
    service = RuleItineraryService()
    for city in ["seoul", "busan", "jeju"]:
        response = service.generate(_build_request(city))

        assert response.day_travel, city
        for day_travel in response.day_travel:
            assert 1 <= day_travel.day_number <= response.days
            assert day_travel.legs
            for leg in day_travel.legs:
                modes = {option.mode for option in leg.options}
                assert {"transit", "car"} <= modes
                assert leg.source == "estimate"
                assert leg.distance_km >= 0

            def leg_contribution(leg, mode):
                mode_minutes = next(o.minutes for o in leg.options if o.mode == mode)
                walk_option = next((o for o in leg.options if o.mode == "walk"), None)
                return min(mode_minutes, walk_option.minutes) if walk_option else mode_minutes

            assert day_travel.transit_total_minutes == sum(leg_contribution(leg, "transit") for leg in day_travel.legs)
            assert day_travel.car_total_minutes == sum(leg_contribution(leg, "car") for leg in day_travel.legs)


def test_day_travel_leg_order_matches_the_point_in_day_sequence_for_each_city() -> None:
    service = RuleItineraryService()
    for city in ["seoul", "busan", "jeju"]:
        request = _build_request(city)
        normalized = service._normalize_request(request)
        city_catalog = service.catalog_provider.get_city_catalog(
            continent=normalized.continent, country=normalized.country, city=normalized.city, visible_only=True
        )
        items, day_place_map, _closed = service._build_items(normalized, city_catalog)
        accommodation = service._recommend_accommodation(normalized, city_catalog, day_place_map)
        _meals, _augmented, day_sequence_with_kind = service._recommend_meals(normalized, city_catalog, day_place_map)

        response = service.generate(request)

        for day_travel in response.day_travel:
            sequence = day_sequence_with_kind[day_travel.day_number]
            expected_names = [service._localize_place_name(place) for place, _kind in sequence]
            if accommodation is not None and accommodation.latitude is not None and accommodation.longitude is not None:
                expected_names = [accommodation.name, *expected_names, accommodation.name]

            leg_names = [day_travel.legs[0].from_name, *[leg.to_name for leg in day_travel.legs]]
            cursor = 0
            for name in leg_names:
                while cursor < len(expected_names) and expected_names[cursor] != name:
                    cursor += 1
                assert cursor < len(expected_names), (city, day_travel.day_number, name, expected_names)
                cursor += 1


# --- Regression: unrelated response fields must not move -------------------


def test_travel_minutes_from_previous_unchanged_for_a_fixed_request() -> None:
    service = RuleItineraryService()
    response = service.generate(_build_request("seoul"))

    item_minutes = [(item.day_number, item.time_slot, item.travel_minutes_from_previous) for item in response.items]
    meal_minutes = [
        (meal.day_number, meal.meal_type, meal.travel_minutes_from_previous) for meal in response.meal_recommendations
    ]

    assert item_minutes == [
        (1, "morning", None),
        (1, "afternoon", None),
        (1, "evening", None),
        (2, "morning", None),
        (2, "afternoon", None),
        (2, "evening", None),
        (3, "morning", None),
        (3, "afternoon", 5),
        (3, "evening", None),
    ]
    assert meal_minutes == [
        (1, "lunch", None),
        (1, "dinner", 6),
        (2, "lunch", 8),
        (2, "dinner", None),
        (3, "lunch", 2),
        (3, "dinner", 18),
    ]
