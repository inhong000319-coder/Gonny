from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import (
    NormalizedRuleRequest,
    RuleItineraryRecalculateRequest,
    RuleItineraryRequest,
)
from app.domains.rule_planner.services.accommodation_split import (
    AUTO_SPLIT_MIN_GAIN_RATIO,
    StayAccommodationPlan,
    _accommodation_adjacent_minutes_total,
    allowed_partitions,
    build_stay_windows,
    day_start_end_accommodations,
    resolve_stay_accommodations,
    select_stay_plan,
)
from app.domains.rule_planner.services.recalculate import validate_stay_plan_request
from app.domains.rule_planner.services.service import RuleItineraryService

CITIES = ["seoul", "busan", "jeju"]


# --- shared builders --------------------------------------------------


def build_place(place_id: str, area: str, latitude: float, longitude: float, **overrides) -> PlaceData:
    data = {
        "id": place_id,
        "name": place_id,
        "activity_type": ["sightseeing"],
        "budget_level": ["medium"],
        "suitable_for": ["couple"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": area,
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


def build_accommodation(accommodation_id: str, area: str, latitude: float, longitude: float, **overrides) -> AccommodationData:
    data = {
        "id": accommodation_id,
        "name": accommodation_id,
        "city": "seoul",
        "area": area,
        "accommodation_type": "호텔",
        "budget_level": ["medium"],
        "suitable_for": ["couple"],
        "latitude": latitude,
        "longitude": longitude,
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)


def build_normalized_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "seoul",
        "travelers": 2,
        "nights": 4,
        "days": 5,
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


def fixed_slots_from_items(items) -> list[dict]:
    return [{"day_number": i.day_number, "time_slot": i.time_slot, "place_id": i.place_id} for i in items]


def build_recalc_request(city: str, fixed_slots: list[dict], **overrides) -> RuleItineraryRecalculateRequest:
    data = {
        "city": city,
        "nights": 2,
        "days": 3,
        "travelers": 2,
        "companion_type": "couple",
        "budget_band": "medium",
        "concepts": ["sightseeing", "food"],
        "style": "easy",
        "fixed_slots": fixed_slots,
    }
    data.update(overrides)
    return RuleItineraryRecalculateRequest.model_validate(data)


def strip_volatile(dump: dict) -> dict:
    dump.pop("weather_alerts", None)
    dump.pop("weather_status", None)
    return dump


# A catalog with two well-separated areas ("west"/"east", ~35km apart) so
# compute_reference_point's area-average coordinate cleanly distinguishes
# them, plus a handful of extra catalog places per area (not necessarily
# visited) so the average isn't just the one place actually scheduled.
def two_region_catalog() -> CityPlaceCatalog:
    west_places = [build_place(f"west-extra-{i}", "west", 37.50 + i * 0.001, 126.80 + i * 0.001) for i in range(3)]
    east_places = [build_place(f"east-extra-{i}", "east", 37.50 + i * 0.001, 127.20 + i * 0.001) for i in range(3)]
    return CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=west_places + east_places)


def tiny_gain_catalog() -> CityPlaceCatalog:
    # Same single area/coordinates everywhere - splitting can't meaningfully
    # shorten any accommodation<->place leg.
    places = [build_place(f"mid-extra-{i}", "mid", 37.50, 127.00) for i in range(3)]
    return CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=places)


# --- (1) allowed_partitions -------------------------------------------


def test_allowed_partitions_matches_spec_examples():
    assert allowed_partitions(1) == [(1,)]
    assert allowed_partitions(2) == [(2,)]
    assert set(allowed_partitions(3)) == {(3,), (1, 2), (2, 1)}
    assert set(allowed_partitions(4)) == {(4,), (1, 3), (2, 2), (3, 1)}
    assert set(allowed_partitions(5)) == {
        (5,),
        (1, 4),
        (2, 3),
        (3, 2),
        (4, 1),
        (1, 2, 2),
        (2, 2, 1),
        (1, 3, 1),
    }


def test_allowed_partitions_one_and_two_nights_are_single_stay_only():
    assert allowed_partitions(1) == [(1,)]
    assert allowed_partitions(2) == [(2,)]


def test_allowed_partitions_never_has_a_single_night_middle_stay():
    for nights in range(3, 12):
        for partition in allowed_partitions(nights):
            for middle_stay_nights in partition[1:-1]:
                assert middle_stay_nights >= 2, (nights, partition)


def test_allowed_partitions_stay_count_cap_by_nights():
    for nights in (1, 2):
        assert max(len(p) for p in allowed_partitions(nights)) == 1
    for nights in (3, 4):
        assert max(len(p) for p in allowed_partitions(nights)) == 2
    for nights in range(5, 12):
        assert max(len(p) for p in allowed_partitions(nights)) == 3


def test_allowed_partitions_every_entry_sums_to_nights():
    for nights in range(1, 10):
        for partition in allowed_partitions(nights):
            assert sum(partition) == nights


# --- (2) split selection ------------------------------------------------


def _day_place_map_two_regions(days: int, west_days: set[int]) -> dict[int, list[PlaceData]]:
    return {
        day: [
            build_place(
                f"place-{day}",
                "west" if day in west_days else "east",
                37.50 if day in west_days else 37.50,
                126.80 if day in west_days else 127.20,
            )
        ]
        for day in range(1, days + 1)
    }


def test_single_mode_always_returns_exactly_one_stay():
    request = build_normalized_request(accommodation_split="single")
    catalog = two_region_catalog()
    day_place_map = _day_place_map_two_regions(5, west_days={1, 2, 3})
    accommodations = [
        build_accommodation("west-hotel", "west", 37.50, 126.80),
        build_accommodation("east-hotel", "east", 37.50, 127.20),
    ]
    stay_plan, note = select_stay_plan(
        split_mode="single",
        nights=4,
        days=5,
        accommodations=accommodations,
        request=request,
        city_catalog=catalog,
        day_place_map=day_place_map,
        transport_by_day=None,
        city="seoul",
    )
    assert len(stay_plan) == 1
    assert note is None


def test_two_mode_splits_into_two_distinct_accommodations_even_with_small_gain():
    request = build_normalized_request(accommodation_split="two")
    catalog = two_region_catalog()
    day_place_map = _day_place_map_two_regions(5, west_days={1, 2, 3})
    accommodations = [
        build_accommodation("west-hotel", "west", 37.50, 126.80),
        build_accommodation("east-hotel", "east", 37.50, 127.20),
    ]
    stay_plan, note = select_stay_plan(
        split_mode="two",
        nights=4,
        days=5,
        accommodations=accommodations,
        request=request,
        city_catalog=catalog,
        day_place_map=day_place_map,
        transport_by_day=None,
        city="seoul",
    )
    assert note is None
    assert len(stay_plan) == 2
    ids = [plan.accommodation.id for plan in stay_plan if plan.accommodation is not None]
    assert len(ids) == 2
    assert len(set(ids)) == 2  # distinct

    two_total = _accommodation_adjacent_minutes_total(
        stay_plan, day_place_map, transport_by_day=None, city="seoul", days=5
    )
    single_windows = build_stay_windows((4,), 5)
    single_plan = resolve_stay_accommodations(
        single_windows,
        accommodations=accommodations,
        request=request,
        city_catalog=catalog,
        day_place_map=day_place_map,
    )
    single_total = _accommodation_adjacent_minutes_total(
        single_plan, day_place_map, transport_by_day=None, city="seoul", days=5
    )
    assert two_total < single_total


def test_auto_mode_splits_when_gain_is_large():
    request = build_normalized_request(accommodation_split="auto")
    catalog = two_region_catalog()
    day_place_map = _day_place_map_two_regions(5, west_days={1, 2, 3})
    accommodations = [
        build_accommodation("west-hotel", "west", 37.50, 126.80),
        build_accommodation("east-hotel", "east", 37.50, 127.20),
    ]
    stay_plan, note = select_stay_plan(
        split_mode="auto",
        nights=4,
        days=5,
        accommodations=accommodations,
        request=request,
        city_catalog=catalog,
        day_place_map=day_place_map,
        transport_by_day=None,
        city="seoul",
    )
    assert note is None
    assert len(stay_plan) == 2


def test_auto_mode_falls_back_to_single_below_gain_threshold():
    request = build_normalized_request(accommodation_split="auto")
    catalog = tiny_gain_catalog()
    day_place_map = {
        day: [build_place(f"place-{day}", "mid", 37.50, 127.00)] for day in range(1, 6)
    }
    accommodations = [
        build_accommodation("hotel-a", "mid", 37.50, 127.00),
        build_accommodation("hotel-b", "mid", 37.50, 127.00),
    ]
    stay_plan, note = select_stay_plan(
        split_mode="auto",
        nights=4,
        days=5,
        accommodations=accommodations,
        request=request,
        city_catalog=catalog,
        day_place_map=day_place_map,
        transport_by_day=None,
        city="seoul",
    )
    assert len(stay_plan) == 1
    assert note is not None
    assert f"{AUTO_SPLIT_MIN_GAIN_RATIO:.0%}" in note


def test_nights_two_or_less_falls_back_to_single_for_two_and_auto():
    request = build_normalized_request(nights=2, days=3, accommodation_split="two")
    catalog = two_region_catalog()
    day_place_map = _day_place_map_two_regions(3, west_days={1})
    accommodations = [
        build_accommodation("west-hotel", "west", 37.50, 126.80),
        build_accommodation("east-hotel", "east", 37.50, 127.20),
    ]
    for split_mode in ("two", "auto"):
        stay_plan, note = select_stay_plan(
            split_mode=split_mode,
            nights=2,
            days=3,
            accommodations=accommodations,
            request=request,
            city_catalog=catalog,
            day_place_map=day_place_map,
            transport_by_day=None,
            city="seoul",
        )
        assert len(stay_plan) == 1
        assert note is not None
        assert "2박" in note


def test_two_mode_falls_back_to_single_when_no_distinct_accommodation_available():
    request = build_normalized_request(nights=4, days=5, accommodation_split="two")
    catalog = two_region_catalog()
    day_place_map = _day_place_map_two_regions(5, west_days={1, 2, 3})
    # Only one accommodation exists in the whole pool - no 2-stay partition
    # can ever get 2 distinct accommodations.
    accommodations = [build_accommodation("only-hotel", "west", 37.50, 126.80)]
    stay_plan, note = select_stay_plan(
        split_mode="two",
        nights=4,
        days=5,
        accommodations=accommodations,
        request=request,
        city_catalog=catalog,
        day_place_map=day_place_map,
        transport_by_day=None,
        city="seoul",
    )
    assert len(stay_plan) == 1
    assert note is not None


# --- (3) response structure (real cities, through the full pipeline) ---


@pytest.mark.parametrize("split_mode", ["single", "two", "auto"])
def test_accommodation_stays_matches_compat_fields_and_hides_price(split_mode):
    service = RuleItineraryService()
    request = build_real_request("jeju", nights=4, days=5, accommodation_split=split_mode)
    response = service.generate(request, include_weather=False)

    if not response.accommodation_stays:
        pytest.skip("no accommodation data resolved for this fixture")

    first_stay = response.accommodation_stays[0]
    assert first_stay.accommodation == response.accommodation_recommendation
    assert [a.id for a in first_stay.alternatives] == [a.id for a in response.accommodation_alternatives]

    for stay in response.accommodation_stays:
        if stay.accommodation is not None:
            assert stay.accommodation.average_price_krw is None
        for alt in stay.alternatives:
            assert alt.average_price_krw is None

    picked_ids = [stay.accommodation.id for stay in response.accommodation_stays if stay.accommodation is not None]
    assert len(picked_ids) == len(set(picked_ids))  # distinct across stays

    all_picked = set(picked_ids)
    for stay in response.accommodation_stays:
        for alt in stay.alternatives:
            assert alt.id not in all_picked


def test_single_split_response_unchanged_except_new_fields():
    service = RuleItineraryService()
    for city in CITIES:
        request = build_real_request(city, nights=3, days=4)
        with_default = service.generate(request, include_weather=False)
        explicit_single = service.generate(
            build_real_request(city, nights=3, days=4, accommodation_split="single"), include_weather=False
        )
        default_dump = strip_volatile(with_default.model_dump(mode="json"))
        explicit_dump = strip_volatile(explicit_single.model_dump(mode="json"))
        assert default_dump == explicit_dump, city


# --- (4) day_travel: checkout-day legs / single-stay unchanged ---------


def test_day_start_end_accommodations_checkout_day_uses_old_then_new_stay():
    stay_a = AccommodationData.model_validate(
        {"id": "a", "name": "A", "city": "seoul", "area": "west", "accommodation_type": "호텔",
         "budget_level": ["medium"], "suitable_for": ["couple"], "latitude": 37.5, "longitude": 126.8}
    )
    stay_b = AccommodationData.model_validate(
        {"id": "b", "name": "B", "city": "seoul", "area": "east", "accommodation_type": "호텔",
         "budget_level": ["medium"], "suitable_for": ["couple"], "latitude": 37.5, "longitude": 127.2}
    )
    plans = [
        StayAccommodationPlan(stay_index=0, start_night=1, nights=2, day_numbers=[1, 2, 3], accommodation=stay_a, alternatives=[]),
        StayAccommodationPlan(stay_index=1, start_night=3, nights=2, day_numbers=[3, 4, 5], accommodation=stay_b, alternatives=[]),
    ]
    # nights=4, days=5, partition (2,2): day3 is the checkout day.
    mapping = day_start_end_accommodations(plans, days=5)
    assert mapping[1] == (stay_a, stay_a)
    assert mapping[2] == (stay_a, stay_a)
    assert mapping[3] == (stay_a, stay_b)  # checkout: leaves stay_a, arrives at stay_b
    assert mapping[4] == (stay_b, stay_b)
    assert mapping[5] == (stay_b, stay_b)


def test_day_start_end_accommodations_single_stay_matches_legacy_both_ends():
    stay = AccommodationData.model_validate(
        {"id": "only", "name": "Only", "city": "seoul", "area": "west", "accommodation_type": "호텔",
         "budget_level": ["medium"], "suitable_for": ["couple"], "latitude": 37.5, "longitude": 126.8}
    )
    plans = [StayAccommodationPlan(stay_index=0, start_night=1, nights=3, day_numbers=[1, 2, 3, 4], accommodation=stay, alternatives=[])]
    mapping = day_start_end_accommodations(plans, days=4)
    for day_number in range(1, 5):
        start_acc, end_acc = mapping[day_number]
        assert start_acc is stay
        assert end_acc is stay


def test_build_day_travel_single_stay_matches_legacy_shape():
    service = RuleItineraryService()
    morning = build_place("morning", "west", 37.50, 127.00)
    afternoon = build_place("afternoon", "west", 37.502, 127.002)
    accommodation = build_accommodation("stay", "west", 37.49, 126.99)
    sequence = service._build_day_sequence_with_kind(
        {"morning": morning, "afternoon": afternoon}, breakfast_place=None, lunch_place=None, dinner_place=None
    )
    stay_plan = [
        StayAccommodationPlan(stay_index=0, start_night=1, nights=1, day_numbers=[1], accommodation=accommodation, alternatives=[])
    ]
    day_travel = service._build_day_travel({1: sequence}, stay_plan, city="seoul", days=1)
    assert len(day_travel) == 1
    legs = day_travel[0].legs
    assert legs[0].from_kind == "accommodation" and legs[0].to_kind == "place"
    assert legs[-1].to_kind == "accommodation"
    assert day_travel[0].expected_leg_count == (len(sequence) - 1) + 2


def test_build_day_travel_checkout_day_first_and_last_legs_use_different_stays():
    service = RuleItineraryService()
    morning = build_place("morning", "west", 37.50, 127.00)
    afternoon = build_place("afternoon", "west", 37.502, 127.002)
    stay_a = build_accommodation("stay-a", "west", 37.49, 126.99)
    stay_b = build_accommodation("stay-b", "east", 37.52, 127.30)
    sequence = service._build_day_sequence_with_kind(
        {"morning": morning, "afternoon": afternoon}, breakfast_place=None, lunch_place=None, dinner_place=None
    )
    # day 3 of a (2,2) partition over nights=4/days=5: leaves stay_a, arrives stay_b.
    stay_plan = [
        StayAccommodationPlan(stay_index=0, start_night=1, nights=2, day_numbers=[1, 2, 3], accommodation=stay_a, alternatives=[]),
        StayAccommodationPlan(stay_index=1, start_night=3, nights=2, day_numbers=[3, 4, 5], accommodation=stay_b, alternatives=[]),
    ]
    day_travel = service._build_day_travel({3: sequence}, stay_plan, city="seoul", days=5)
    assert len(day_travel) == 1
    legs = day_travel[0].legs
    assert legs[0].from_name == "stay-a"
    assert legs[-1].to_name == "stay-b"


# --- (5) recalculate: stay_nights / stay_accommodation_ids validation --


def test_validate_stay_plan_request_rejects_mismatched_sum():
    request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul", "nights": 4, "days": 5, "fixed_slots": [],
            "stay_nights": [1, 1],
        }
    )
    normalized = build_normalized_request(nights=4, days=5)
    with pytest.raises(HTTPException) as exc_info:
        validate_stay_plan_request(request=request, normalized=normalized, city_catalog=two_region_catalog())
    assert exc_info.value.status_code == 422


def test_validate_stay_plan_request_rejects_disallowed_partition():
    request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul", "nights": 5, "days": 6, "fixed_slots": [],
            "stay_nights": [2, 1, 2],  # middle stay with 1 night - disallowed
        }
    )
    normalized = build_normalized_request(nights=5, days=6)
    with pytest.raises(HTTPException) as exc_info:
        validate_stay_plan_request(request=request, normalized=normalized, city_catalog=two_region_catalog())
    assert exc_info.value.status_code == 422


def test_validate_stay_plan_request_rejects_stay_accommodation_ids_without_stay_nights():
    request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul", "nights": 4, "days": 5, "fixed_slots": [],
            "stay_accommodation_ids": ["some-id", None],
        }
    )
    normalized = build_normalized_request(nights=4, days=5)
    with pytest.raises(HTTPException):
        validate_stay_plan_request(request=request, normalized=normalized, city_catalog=two_region_catalog())


def test_validate_stay_plan_request_rejects_accommodation_id_with_stay_accommodation_ids():
    request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul", "nights": 4, "days": 5, "fixed_slots": [],
            "accommodation_id": "foo",
            "stay_nights": [2, 2],
            "stay_accommodation_ids": ["west-hotel", "east-hotel"],
        }
    )
    normalized = build_normalized_request(nights=4, days=5)
    with pytest.raises(HTTPException):
        validate_stay_plan_request(request=request, normalized=normalized, city_catalog=two_region_catalog())


def test_validate_stay_plan_request_rejects_unknown_accommodation_id():
    request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul", "nights": 4, "days": 5, "fixed_slots": [],
            "stay_nights": [2, 2],
            "stay_accommodation_ids": ["no-such-hotel", None],
        }
    )
    normalized = build_normalized_request(nights=4, days=5)
    with pytest.raises(HTTPException) as exc_info:
        validate_stay_plan_request(request=request, normalized=normalized, city_catalog=two_region_catalog())
    assert exc_info.value.status_code == 422


def test_validate_stay_plan_request_accepts_valid_split():
    request = RuleItineraryRecalculateRequest.model_validate(
        {
            "city": "seoul", "nights": 4, "days": 5, "fixed_slots": [],
            "stay_nights": [2, 2],
        }
    )
    normalized = build_normalized_request(nights=4, days=5)
    validate_stay_plan_request(request=request, normalized=normalized, city_catalog=two_region_catalog())  # no raise


@pytest.mark.parametrize("city", CITIES)
def test_recalculate_with_explicit_stay_nights_reproduces_a_prior_split_result(city):
    service = RuleItineraryService()
    request = build_real_request(city, nights=4, days=5, accommodation_split="two")
    generated = service.generate(request, include_weather=False)
    if len(generated.accommodation_stays) < 2:
        pytest.skip("this fixture didn't produce a 2-stay split to reproduce")

    stay_nights = [stay.nights for stay in generated.accommodation_stays]
    stay_accommodation_ids = [
        stay.accommodation.id if stay.accommodation is not None else None for stay in generated.accommodation_stays
    ]

    recalc_request = build_recalc_request(
        city,
        fixed_slots_from_items(generated.items),
        nights=4,
        days=5,
        accommodation_split="two",
        stay_nights=stay_nights,
        stay_accommodation_ids=stay_accommodation_ids,
    )
    recalculated = service.recalculate(recalc_request)

    gen_dump = strip_volatile(generated.model_dump(mode="json"))
    recalc_dump = strip_volatile(recalculated.model_dump(mode="json"))
    assert gen_dump == recalc_dump, city


def test_recalculate_legacy_accommodation_id_still_pins_first_stay():
    service = RuleItineraryService()
    request = build_real_request("seoul")
    generated = service.generate(request, include_weather=False)
    assert generated.accommodation_recommendation is not None

    recalc_request = build_recalc_request(
        "seoul",
        fixed_slots_from_items(generated.items),
        accommodation_id=generated.accommodation_recommendation.id,
    )
    recalculated = service.recalculate(recalc_request)
    assert len(recalculated.accommodation_stays) == 1
    assert recalculated.accommodation_stays[0].accommodation.id == generated.accommodation_recommendation.id
