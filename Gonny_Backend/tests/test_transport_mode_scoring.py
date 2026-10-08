from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleItineraryRequest
from app.domains.rule_planner.services import travel_estimate as travel_estimate_module
from app.domains.rule_planner.services.accommodation_scoring import (
    PARKING_BONUS_ALL_CAR,
    PARKING_BONUS_SOME_CAR,
    accommodation_score,
    select_accommodation_recommendation,
)
from app.domains.rule_planner.services.request_normalizer import normalize_rule_request
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.slot_scoring import (
    TRANSIT_SUBWAY_FRIENDLY_BONUS,
    TRANSIT_TAXI_NEEDED_PENALTY,
    slot_score,
)
from app.domains.rule_planner.services.travel_estimate import (
    CLOSE_TRANSITION_BONUS,
    FAR_TRANSITION_PENALTY,
    NEARBY_TRANSITION_BONUS,
    coordinate_area_transition_bonus,
    estimate_day_total_minutes,
)


def build_place(place_id: str, **overrides) -> PlaceData:
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
        "latitude": 37.50,
        "longitude": 127.00,
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "stay",
        "name": "Stay",
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


def patched_distance(monkeypatch, distance_km: float) -> None:
    monkeypatch.setattr(travel_estimate_module, "haversine_distance_km", lambda *args, **kwargs: distance_km)


# --- (a) request/normalization validation -----------------------------------


def test_transport_by_day_length_mismatch_is_rejected_with_expected_length_in_message() -> None:
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, transport_by_day=["transit", "car"])

    with pytest.raises(HTTPException) as excinfo:
        normalize_rule_request(request)

    assert excinfo.value.status_code == 422
    assert "3" in excinfo.value.detail


def test_unknown_transport_mode_value_is_rejected_by_pydantic() -> None:
    with pytest.raises(ValidationError):
        RuleItineraryRequest(city="seoul", transport_by_day=["bike"])


def test_transport_by_day_none_is_accepted_and_stays_none() -> None:
    normalized = normalize_rule_request(RuleItineraryRequest(city="seoul", nights=2, days=3))

    assert normalized.transport_by_day is None


def test_transport_by_day_is_reflected_in_normalized_request_and_response() -> None:
    modes = ["transit", "car", "transit"]
    request = RuleItineraryRequest(city="seoul", nights=2, days=3, transport_by_day=modes)

    normalized = normalize_rule_request(request)
    assert normalized.transport_by_day == modes

    response = RuleItineraryService().generate(request)
    assert response.transport_by_day == modes


# --- (b) mode-aware coordinate transition bonus ------------------------------


def test_mode_none_reproduces_the_pre_existing_bonus() -> None:
    previous = build_place("prev")
    place = build_place("place")

    assert coordinate_area_transition_bonus(previous, place, mode=None) == coordinate_area_transition_bonus(
        previous, place
    )


def test_jeju_transit_penalizes_a_distant_pair_that_car_still_rewards(monkeypatch) -> None:
    # Same 8km pair, same city (jeju): car's fixed cost (8min) + its faster
    # cruising speed keeps the pair inside the "nearby" tier, but transit's
    # fixed cost (10min) plus jeju's slow transit speed (15km/h) pushes it
    # past the "far" tier into the penalty.
    patched_distance(monkeypatch, 8.0)
    previous = build_place("prev")
    place = build_place("place")

    car_bonus = coordinate_area_transition_bonus(previous, place, mode="car", city="jeju")
    transit_bonus = coordinate_area_transition_bonus(previous, place, mode="transit", city="jeju")

    assert car_bonus == NEARBY_TRANSITION_BONUS
    assert transit_bonus == FAR_TRANSITION_PENALTY
    assert transit_bonus < car_bonus


@pytest.mark.parametrize("mode", ["transit", "car"])
@pytest.mark.parametrize("city", ["seoul", "busan", "jeju"])
def test_bonus_tier_boundary_shifts_by_the_mode_fixed_time(monkeypatch, mode: str, city: str) -> None:
    fixed_minutes = travel_estimate_module.TRANSPORT_PROFILES[mode]["fixed_minutes"]
    close_threshold = travel_estimate_module.CLOSE_TRAVEL_MINUTES_THRESHOLD + fixed_minutes

    # Binary-search (in distance) for exactly the close-tier boundary and one
    # minute past it, using the production scoring_minutes() function itself
    # so this test tracks the real formula rather than hand-derived numbers.
    def minutes_at(distance_km: float) -> int:
        return travel_estimate_module.scoring_minutes(mode, distance_km, city)

    distance_at_boundary = None
    distance_past_boundary = None
    distance_km = 0.01
    while distance_km <= 50.0:
        minutes = minutes_at(distance_km)
        if minutes == close_threshold and distance_at_boundary is None:
            distance_at_boundary = distance_km
        if minutes == close_threshold + 1 and distance_past_boundary is None:
            distance_past_boundary = distance_km
            break
        distance_km += 0.001
    assert distance_at_boundary is not None
    assert distance_past_boundary is not None

    previous = build_place("prev")
    place = build_place("place")

    patched_distance(monkeypatch, distance_at_boundary)
    assert coordinate_area_transition_bonus(previous, place, mode=mode, city=city) == CLOSE_TRANSITION_BONUS

    patched_distance(monkeypatch, distance_past_boundary)
    assert coordinate_area_transition_bonus(previous, place, mode=mode, city=city) == NEARBY_TRANSITION_BONUS


# --- (c) mobility tag handling in slot_score() -------------------------------


def _score_for_mode(mobility: list[str], *, transport_by_day: list[str] | None) -> int:
    # Same place/mobility every call - only transport_by_day changes - so any
    # score difference is purely from the mode-aware scoring under test, not
    # from base_score()'s ML prediction (which reads mobility as a feature
    # and would otherwise confound a cross-mobility comparison).
    place = build_place("p", mobility=mobility, latitude=None, longitude=None)
    request = build_request(transport_by_day=transport_by_day)
    return slot_score(place=place, request=request, time_slot="morning", day_number=1, preferred_area=None)


def test_transit_day_adds_the_new_taxi_needed_penalty_on_top_of_the_legacy_one() -> None:
    # Day 1 is "arrival" phase, where the legacy taxi-needed/train-friendly
    # penalty (-4, see phase_score) applies regardless of mode (only a car
    # day skips it) - so going from no mode to a transit day adds just the
    # new -8 on top, nothing else changes for this place.
    none_score = _score_for_mode(["taxi-needed"], transport_by_day=None)
    transit_score = _score_for_mode(["taxi-needed"], transport_by_day=["transit", "transit", "transit"])

    assert transit_score == none_score + TRANSIT_TAXI_NEEDED_PENALTY


def test_transit_day_adds_the_new_subway_friendly_bonus() -> None:
    none_score = _score_for_mode(["subway-friendly"], transport_by_day=None)
    transit_score = _score_for_mode(["subway-friendly"], transport_by_day=["transit", "transit", "transit"])

    assert transit_score == none_score + TRANSIT_SUBWAY_FRIENDLY_BONUS


def test_car_day_removes_the_legacy_taxi_needed_penalty_with_no_replacement() -> None:
    none_score = _score_for_mode(["taxi-needed"], transport_by_day=None)
    car_score = _score_for_mode(["taxi-needed"], transport_by_day=["car", "car", "car"])

    # The legacy arrival-phase penalty (-4) is gone on a car day, and no new
    # car-specific bonus/penalty is added in its place (per spec).
    assert car_score == none_score + 4


def test_mode_none_keeps_the_legacy_taxi_needed_penalty_unchanged() -> None:
    no_mode_taxi_needed = _score_for_mode(["taxi-needed"], transport_by_day=None)
    no_mode_walkable = _score_for_mode(["walkable"], transport_by_day=None)

    # Legacy arrival-phase penalty (-4) still applies with no mode set -
    # same comparison as before this feature existed.
    assert no_mode_taxi_needed == no_mode_walkable - 4


# --- (d) accommodation parking bonus -----------------------------------------


def test_all_car_days_give_the_full_parking_bonus_to_a_parking_stay() -> None:
    request = build_request(transport_by_day=["car", "car", "car"])
    with_parking = build_accommodation(amenities=["주차가능"])
    without_parking = build_accommodation(id="no-parking", amenities=[])

    assert accommodation_score(with_parking, request, None) == accommodation_score(
        without_parking, request, None
    ) + PARKING_BONUS_ALL_CAR


def test_some_car_days_give_the_partial_parking_bonus() -> None:
    request = build_request(transport_by_day=["car", "transit", "transit"])
    with_parking = build_accommodation(amenities=["주차가능"])
    without_parking = build_accommodation(id="no-parking", amenities=[])

    assert accommodation_score(with_parking, request, None) == accommodation_score(
        without_parking, request, None
    ) + PARKING_BONUS_SOME_CAR


def test_no_car_days_or_unset_give_no_parking_bonus_and_no_penalty_for_lacking_it() -> None:
    no_car_request = build_request(transport_by_day=["transit", "transit", "transit"])
    unset_request = build_request(transport_by_day=None)
    with_parking = build_accommodation(amenities=["주차가능"])
    without_parking = build_accommodation(id="no-parking", amenities=[])

    for request in [no_car_request, unset_request]:
        assert accommodation_score(with_parking, request, None) == accommodation_score(without_parking, request, None)


def test_parking_bonus_is_not_a_hard_filter() -> None:
    # A non-parking stay that otherwise fits much better must still be able
    # to win - the parking bonus only nudges the ranking.
    request = build_request(transport_by_day=["car", "car", "car"], companion_type="family")
    better_fit_no_parking = build_accommodation(
        id="better", suitable_for=["family"], amenities=[], latitude=37.50, longitude=127.00
    )
    worse_fit_with_parking = build_accommodation(
        id="worse", suitable_for=["solo"], amenities=["주차가능"], latitude=30.0, longitude=120.0
    )

    selected = select_accommodation_recommendation(
        [better_fit_no_parking, worse_fit_with_parking], request, (37.50, 127.00)
    )

    assert selected.id == "better"


# --- (e) day duration warnings (mode-aware totals) ---------------------------


def test_day_total_minutes_uses_mode_aware_estimate_when_mode_given(monkeypatch) -> None:
    patched_distance(monkeypatch, 8.0)
    places = [build_place("a", duration_hours=1), build_place("b", duration_hours=1)]

    car_total = estimate_day_total_minutes(places, None, mode="car", city="jeju")
    transit_total = estimate_day_total_minutes(places, None, mode="transit", city="jeju")
    default_total = estimate_day_total_minutes(places, None)

    assert car_total == 1 * 60 + 1 * 60 + travel_estimate_module.scoring_minutes("car", 8.0, "jeju")
    assert transit_total == 1 * 60 + 1 * 60 + travel_estimate_module.scoring_minutes("transit", 8.0, "jeju")
    assert car_total != transit_total
    assert default_total == 1 * 60 + 1 * 60 + travel_estimate_module.estimate_straight_line_travel_minutes(8.0)


def test_day_total_minutes_mode_none_is_unchanged() -> None:
    places = [build_place("a", duration_hours=2), build_place("b", duration_hours=1)]

    assert estimate_day_total_minutes(places, None, mode=None, city="seoul") == estimate_day_total_minutes(
        places, None
    )


# --- (f) integration: generate() with transport_by_day set ------------------


@pytest.mark.parametrize("mode", ["transit", "car"])
def test_generate_accepts_uniform_transport_by_day_and_echoes_it_back(mode: str) -> None:
    service = RuleItineraryService()
    request = RuleItineraryRequest(
        city="seoul",
        nights=2,
        days=3,
        travelers=2,
        companion_type="couple",
        budget_band="medium",
        concepts=["sightseeing", "culture"],
        style="easy",
        transport_by_day=[mode, mode, mode],
    )

    response = service.generate(request)

    assert response.transport_by_day == [mode, mode, mode]
    assert len(response.items) > 0
