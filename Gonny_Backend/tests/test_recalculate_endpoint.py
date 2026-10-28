from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.rule_planner.schemas import (
    NormalizedRuleRequest,
    RuleFixedSlotAssignment,
    RuleItineraryRecalculateRequest,
    RuleItineraryRequest,
)
from app.domains.rule_planner.services.recalculate import build_fixed_slots_lookup
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.travel_estimate import estimate_travel_minutes_between
from app.main import app

CITIES = ["seoul", "busan", "jeju"]

# One unambiguous-weekly-closure, non-food, active real place per city (see
# closed_days.py's module docstring - most closed_days text is too
# ambiguous/complex to match, these are hand-picked known-simple ones).
CLOSED_MONDAY_PLACE = {"seoul": "war-memorial-korea", "jeju": "jeju-national-museum"}
CLOSED_SUNDAY_PLACE = {"busan": "gukje-market"}


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


def build_recalc_request(city: str, fixed_slots: list[dict], accommodation_id: str | None, **overrides) -> RuleItineraryRecalculateRequest:
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
        "accommodation_id": accommodation_id,
    }
    data.update(overrides)
    return RuleItineraryRecalculateRequest.model_validate(data)


def strip_volatile(dump: dict) -> dict:
    dump.pop("weather_alerts", None)
    dump.pop("weather_status", None)
    return dump


def strip_place_id(dump: dict) -> dict:
    for item in dump["items"]:
        item.pop("place_id", None)
    return dump


# --- schema: place_id is additive and populated everywhere -----------------


def test_place_id_populated_on_every_item_for_each_city():
    service = RuleItineraryService()
    for city in CITIES:
        response = service.generate(build_real_request(city), include_weather=False)
        assert all(item.place_id for item in response.items), city


def test_place_id_populated_on_full_day_items():
    service = RuleItineraryService()
    request = build_real_request("seoul", concepts=["activity"], companion_type="family")
    response = service.generate(request, include_weather=False)
    full_day_days = [
        day for day in {i.day_number for i in response.items}
        if len({i.place_id for i in response.items if i.day_number == day}) == 1
    ]
    assert full_day_days, "expected at least one full-day itinerary day in this fixture"


# --- no-change recalculate reproduces generate() exactly, including place_id


@pytest.mark.parametrize("city", CITIES)
def test_no_change_recalculate_matches_generate(city):
    service = RuleItineraryService()
    request = build_real_request(city)
    gen = service.generate(request, include_weather=False)

    recalc_request = build_recalc_request(
        city, fixed_slots_from_items(gen.items), gen.accommodation_recommendation.id if gen.accommodation_recommendation else None
    )
    recalc = service.recalculate(recalc_request)

    gen_dump = strip_volatile(gen.model_dump(mode="json"))
    recalc_dump = strip_volatile(recalc.model_dump(mode="json"))
    assert gen_dump == recalc_dump, city


def test_no_change_recalculate_matches_generate_for_full_day_seoul():
    service = RuleItineraryService()
    request = build_real_request("seoul", concepts=["activity"], companion_type="family")
    gen = service.generate(request, include_weather=False)
    full_day_day_numbers = {
        day for day in {i.day_number for i in gen.items}
        if len({i.place_id for i in gen.items if i.day_number == day}) == 1
    }
    assert full_day_day_numbers

    recalc_request = build_recalc_request(
        "seoul",
        fixed_slots_from_items(gen.items),
        gen.accommodation_recommendation.id if gen.accommodation_recommendation else None,
        concepts=["activity"],
        companion_type="family",
    )
    recalc = service.recalculate(recalc_request)

    gen_dump = strip_volatile(gen.model_dump(mode="json"))
    recalc_dump = strip_volatile(recalc.model_dump(mode="json"))
    assert gen_dump == recalc_dump

    for day in full_day_day_numbers:
        day_items = [i for i in recalc.items if i.day_number == day]
        assert len(day_items) == 3
        assert len({i.place_id for i in day_items}) == 1
        assert all(i.alternatives == [] for i in day_items)


# --- swap scenarios: a) single activity slot, b) multiple activity slots,
# c) accommodation, d) activity + accommodation together ---------------


@pytest.mark.parametrize("city", CITIES)
def test_swap_single_activity_slot(city):
    service = RuleItineraryService()
    request = build_real_request(city)
    gen = service.generate(request, include_weather=False)

    swappable = next(i for i in gen.items if i.alternatives)
    alt = swappable.alternatives[0]
    fixed_slots = fixed_slots_from_items(gen.items)
    for entry in fixed_slots:
        if entry["day_number"] == swappable.day_number and entry["time_slot"] == swappable.time_slot:
            entry["place_id"] = alt.place_id

    recalc_request = build_recalc_request(city, fixed_slots, gen.accommodation_recommendation.id)
    recalc = service.recalculate(recalc_request)

    swapped_item = next(
        i for i in recalc.items if i.day_number == swappable.day_number and i.time_slot == swappable.time_slot
    )
    assert swapped_item.place_id == alt.place_id

    for item in recalc.items:
        if item.day_number == swappable.day_number and item.time_slot == swappable.time_slot:
            continue
        original = next(i for i in gen.items if i.day_number == item.day_number and i.time_slot == item.time_slot)
        assert item.place_id == original.place_id, (city, item.day_number, item.time_slot)

    place_ids = [i.place_id for i in recalc.items]
    assert len(place_ids) == len(set(place_ids)), city

    recalc_again = service.recalculate(recalc_request)
    assert strip_volatile(recalc.model_dump(mode="json")) == strip_volatile(recalc_again.model_dump(mode="json")), city


@pytest.mark.parametrize("city", CITIES)
def test_swap_multiple_activity_slots(city):
    service = RuleItineraryService()
    request = build_real_request(city)
    gen = service.generate(request, include_weather=False)

    swappable_items = []
    seen_days = set()
    for item in gen.items:
        if item.alternatives and item.day_number not in seen_days:
            swappable_items.append(item)
            seen_days.add(item.day_number)
        if len(swappable_items) == 2:
            break
    assert len(swappable_items) >= 2, city

    fixed_slots = fixed_slots_from_items(gen.items)
    other_place_ids = {i.place_id for i in gen.items}
    swap_map = {}
    for swappable in swappable_items:
        other_place_ids.discard(swappable.place_id)
        alt = next((a for a in swappable.alternatives if a.place_id not in other_place_ids), None)
        assert alt is not None, city
        swap_map[(swappable.day_number, swappable.time_slot)] = alt.place_id
        other_place_ids.add(alt.place_id)
        for entry in fixed_slots:
            if entry["day_number"] == swappable.day_number and entry["time_slot"] == swappable.time_slot:
                entry["place_id"] = alt.place_id

    recalc_request = build_recalc_request(city, fixed_slots, gen.accommodation_recommendation.id)
    recalc = service.recalculate(recalc_request)

    for (day_number, time_slot), expected_place_id in swap_map.items():
        swapped_item = next(i for i in recalc.items if i.day_number == day_number and i.time_slot == time_slot)
        assert swapped_item.place_id == expected_place_id, city

    place_ids = [i.place_id for i in recalc.items]
    assert len(place_ids) == len(set(place_ids)), city


@pytest.mark.parametrize("city", CITIES)
def test_swap_accommodation(city):
    service = RuleItineraryService()
    request = build_real_request(city)
    gen = service.generate(request, include_weather=False)
    assert gen.accommodation_alternatives, city
    new_acc = gen.accommodation_alternatives[0]

    recalc_request = build_recalc_request(city, fixed_slots_from_items(gen.items), new_acc.id)
    recalc = service.recalculate(recalc_request)

    assert recalc.accommodation_recommendation.id == new_acc.id, city
    assert new_acc.id not in {a.id for a in recalc.accommodation_alternatives}, city
    assert recalc.estimated_cost.accommodation_included == (new_acc.average_price_krw is not None), city

    day1_travel = next(dt for dt in recalc.day_travel if dt.day_number == 1)
    leg_names = [name for leg in day1_travel.legs for name in (leg.from_name, leg.to_name)]
    assert new_acc.name in leg_names, city

    activity_names = {i.place_name for i in recalc.items}
    meal_names = {m.place_name for m in recalc.meal_recommendations}
    assert not (activity_names & meal_names), city


@pytest.mark.parametrize("city", CITIES)
def test_swap_activity_and_accommodation_together(city):
    service = RuleItineraryService()
    request = build_real_request(city)
    gen = service.generate(request, include_weather=False)
    assert gen.accommodation_alternatives, city
    new_acc = gen.accommodation_alternatives[0]

    swappable = next(i for i in gen.items if i.alternatives)
    alt = swappable.alternatives[0]
    fixed_slots = fixed_slots_from_items(gen.items)
    for entry in fixed_slots:
        if entry["day_number"] == swappable.day_number and entry["time_slot"] == swappable.time_slot:
            entry["place_id"] = alt.place_id

    recalc_request = build_recalc_request(city, fixed_slots, new_acc.id)
    recalc = service.recalculate(recalc_request)

    swapped_item = next(
        i for i in recalc.items if i.day_number == swappable.day_number and i.time_slot == swappable.time_slot
    )
    assert swapped_item.place_id == alt.place_id, city
    assert recalc.accommodation_recommendation.id == new_acc.id, city

    place_ids = [i.place_id for i in recalc.items]
    assert len(place_ids) == len(set(place_ids)), city


def test_swap_recomputes_travel_minutes_from_previous():
    service = RuleItineraryService()
    provider = service.catalog_provider
    request = build_real_request("seoul")
    gen = service.generate(request, include_weather=False)

    day1_morning = next(i for i in gen.items if i.day_number == 1 and i.time_slot == "morning")
    assert day1_morning.alternatives
    alt = day1_morning.alternatives[0]

    fixed_slots = fixed_slots_from_items(gen.items)
    for entry in fixed_slots:
        if entry["day_number"] == 1 and entry["time_slot"] == "morning":
            entry["place_id"] = alt.place_id

    recalc_request = build_recalc_request("seoul", fixed_slots, gen.accommodation_recommendation.id)
    recalc = service.recalculate(recalc_request)

    catalog = provider.get_city_catalog(continent="asia", country="korea", city="seoul", visible_only=True)
    places_by_id = {p.id: p for p in catalog.places}
    day1_afternoon_after = next(i for i in recalc.items if i.day_number == 1 and i.time_slot == "afternoon")
    expected = estimate_travel_minutes_between(places_by_id[alt.place_id], places_by_id[day1_afternoon_after.place_id])
    assert day1_afternoon_after.travel_minutes_from_previous == expected


# --- 422 validation errors: 9 cases, >=1 per city --------------------------


def _generate_and_pin(service, city, **overrides):
    request = build_real_request(city, **overrides)
    gen = service.generate(request, include_weather=False)
    fixed_slots = fixed_slots_from_items(gen.items)
    accommodation_id = gen.accommodation_recommendation.id if gen.accommodation_recommendation else None
    return gen, fixed_slots, accommodation_id


def test_unknown_place_id_seoul():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "seoul")
    fixed_slots[0]["place_id"] = "does-not-exist-xyz"
    recalc_request = build_recalc_request("seoul", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_food_place_id_seoul():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "seoul")
    catalog = service.catalog_provider.get_city_catalog(continent="asia", country="korea", city="seoul", visible_only=True)
    food_place = next(p for p in catalog.places if "food" in p.concept_tags)
    fixed_slots[0]["place_id"] = food_place.id
    recalc_request = build_recalc_request("seoul", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_disallowed_slot_seoul():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "seoul")
    fixed_slots[0]["day_number"] = 99
    recalc_request = build_recalc_request("seoul", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_missing_slot_busan():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "busan")
    fixed_slots.pop()
    recalc_request = build_recalc_request("busan", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_duplicate_slot_busan():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "busan")
    fixed_slots.append(dict(fixed_slots[0]))
    recalc_request = build_recalc_request("busan", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_cross_day_duplicate_place_busan():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "busan")
    day1_morning_id = next(e["place_id"] for e in fixed_slots if e["day_number"] == 1 and e["time_slot"] == "morning")
    for entry in fixed_slots:
        if entry["day_number"] == 2 and entry["time_slot"] == "morning":
            entry["place_id"] = day1_morning_id
    recalc_request = build_recalc_request("busan", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_partial_same_place_within_a_day_jeju():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "jeju")
    day1_entries = [e for e in fixed_slots if e["day_number"] == 1]
    assert len(day1_entries) >= 2
    day1_entries[1]["place_id"] = day1_entries[0]["place_id"]
    recalc_request = build_recalc_request("jeju", fixed_slots, accommodation_id)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_unknown_accommodation_id_jeju():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "jeju")
    recalc_request = build_recalc_request("jeju", fixed_slots, "does-not-exist-hotel")
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


@pytest.mark.parametrize(
    "city,place_id,weekday",
    [
        ("seoul", CLOSED_MONDAY_PLACE["seoul"], 0),
        ("busan", CLOSED_SUNDAY_PLACE["busan"], 6),
        ("jeju", CLOSED_MONDAY_PLACE["jeju"], 0),
    ],
)
def test_closed_day_place(city, place_id, weekday):
    service = RuleItineraryService()
    start_date = date(2026, 11, 1)
    while start_date.weekday() != weekday:
        start_date += timedelta(days=1)

    gen, fixed_slots, accommodation_id = _generate_and_pin(service, city, start_date=start_date)

    existing_slot = next((e for e in fixed_slots if e["place_id"] == place_id), None)
    day1_morning_entry = next(e for e in fixed_slots if e["day_number"] == 1 and e["time_slot"] == "morning")
    if existing_slot is not None and existing_slot is not day1_morning_entry:
        existing_slot["place_id"], day1_morning_entry["place_id"] = day1_morning_entry["place_id"], existing_slot["place_id"]
    else:
        day1_morning_entry["place_id"] = place_id

    recalc_request = build_recalc_request(city, fixed_slots, accommodation_id, start_date=start_date)
    with pytest.raises(HTTPException) as exc_info:
        service.recalculate(recalc_request)
    assert exc_info.value.status_code == 422


def test_inactive_place_id_rejected_by_build_fixed_slots_lookup():
    # No inactive places exist in any real catalog today, so this rule is
    # exercised directly against build_fixed_slots_lookup with a synthetic
    # catalog (same pattern test_accommodation_alternatives.py uses for
    # edge cases the real catalogs don't happen to contain).
    place = PlaceData(
        id="inactive-place",
        name="Inactive Place",
        activity_type=["문화·역사"],
        budget_level=["medium"],
        suitable_for=["couple"],
        time_fit=["morning"],
        area="gangnam",
        duration_hours=2,
        priority=5,
        pace=["easy"],
        mobility=["walk"],
        summary="test",
        is_active=False,
    )
    catalog = CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=[place])
    normalized = NormalizedRuleRequest.model_validate(
        {
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
    )
    with pytest.raises(HTTPException) as exc_info:
        build_fixed_slots_lookup(
            fixed_slots=[RuleFixedSlotAssignment(day_number=1, time_slot="morning", place_id="inactive-place")],
            request=normalized,
            city_catalog=catalog,
        )
    assert exc_info.value.status_code == 422


# --- response contract -------------------------------------------------


def test_recalculate_endpoint_response_has_place_id_field():
    service = RuleItineraryService()
    gen, fixed_slots, accommodation_id = _generate_and_pin(service, "seoul")

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
            "fixed_slots": fixed_slots,
            "accommodation_id": accommodation_id,
        }
        response = client.post("/rule-itinerary/recalculate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert all("place_id" in item and item["place_id"] for item in body["items"])


def test_generate_endpoint_response_has_place_id_field_and_is_otherwise_unchanged():
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
    assert all("place_id" in item and item["place_id"] for item in body["items"])
    assert "accommodation_recommendation" in body
    assert "accommodation_alternatives" in body
    assert all("alternatives" in item for item in body["items"])


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


def test_recalculate_invalid_payload_returns_422_via_endpoint():
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
            "fixed_slots": [{"day_number": 1, "time_slot": "morning", "place_id": "does-not-exist-xyz"}],
            "accommodation_id": None,
        }
        response = client.post("/rule-itinerary/recalculate", json=payload)

    assert response.status_code == 422
