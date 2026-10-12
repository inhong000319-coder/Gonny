from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.policies.city import extreme_distance_penalty
from app.domains.rule_planner.services.policies.city.jeju import (
    EXTREME_DISTANCE_BASE_PENALTY,
    EXTREME_DISTANCE_KM_THRESHOLD,
    EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM,
)
from app.domains.rule_planner.services.policies.city.jeju import extreme_distance_penalty as jeju_penalty
from app.domains.rule_planner.services.slot_scoring import meal_candidate_score
from app.domains.rule_planner.services.travel_estimate import haversine_distance_km


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["미식"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "east-jeju",
        "duration_hours": 1,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample",
        "latitude": 33.45,
        "longitude": 126.66,
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def build_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "jeju",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["sightseeing"],
        "style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


# --- (3) boundary cases for the new constants -------------------------------


def test_extreme_distance_penalty_is_zero_at_exact_threshold() -> None:
    assert jeju_penalty(EXTREME_DISTANCE_KM_THRESHOLD) == 0


def test_extreme_distance_penalty_is_zero_just_under_threshold() -> None:
    assert jeju_penalty(EXTREME_DISTANCE_KM_THRESHOLD - 0.01) == 0


def test_extreme_distance_penalty_applies_base_penalty_just_over_threshold() -> None:
    # Just a hair over the threshold: overage rounds to 0km, so only the
    # base penalty applies.
    assert jeju_penalty(EXTREME_DISTANCE_KM_THRESHOLD + 0.01) == EXTREME_DISTANCE_BASE_PENALTY


def test_extreme_distance_penalty_scales_linearly_with_overage() -> None:
    distance = EXTREME_DISTANCE_KM_THRESHOLD + 10
    expected = EXTREME_DISTANCE_BASE_PENALTY + round(10 * EXTREME_DISTANCE_PENALTY_PER_EXTRA_KM)
    assert jeju_penalty(distance) == expected


def test_extreme_distance_penalty_never_positive() -> None:
    for distance in [0, 10, 29.9, 30, 30.1, 50, 100, 500]:
        assert jeju_penalty(distance) <= 0


# --- dispatcher (policies/city/__init__.py) ---------------------------------


def test_dispatcher_returns_zero_when_other_place_is_none() -> None:
    request = build_request(city="jeju")
    place = build_place()
    assert extreme_distance_penalty(request, None, place) == 0


def test_dispatcher_returns_zero_when_coordinates_missing() -> None:
    request = build_request(city="jeju")
    far_other = build_place(id="far", latitude=None, longitude=None)
    place = build_place()
    assert extreme_distance_penalty(request, far_other, place) == 0


def test_dispatcher_applies_jeju_penalty_for_a_real_extreme_distance() -> None:
    request = build_request(city="jeju")
    # East coast vs west coast of Jeju - well over the 30km threshold.
    east = build_place(id="east", latitude=33.45, longitude=126.90)
    west = build_place(id="west", latitude=33.39, longitude=126.24)
    distance = haversine_distance_km(33.45, 126.90, 33.39, 126.24)
    assert distance > EXTREME_DISTANCE_KM_THRESHOLD

    penalty = extreme_distance_penalty(request, east, west)
    assert penalty == jeju_penalty(distance)
    assert penalty < 0


# --- (2) Seoul/Busan are completely unaffected -------------------------------


def test_dispatcher_is_always_zero_for_seoul_and_busan_regardless_of_distance() -> None:
    # Same huge distance as the Jeju case above, just relabeled to
    # seoul/busan - must stay 0 since neither policy module defines
    # extreme_distance_penalty at all.
    far_other = build_place(id="far", latitude=33.45, longitude=126.90)
    place = build_place(id="near", latitude=33.39, longitude=126.24)

    for city in ("seoul", "busan"):
        request = build_request(city=city)
        assert extreme_distance_penalty(request, far_other, place) == 0


def test_dispatcher_is_zero_for_a_city_with_no_policy_module_at_all() -> None:
    far_other = build_place(id="far", latitude=33.45, longitude=126.90)
    place = build_place(id="near", latitude=33.39, longitude=126.24)
    request = build_request(city="tokyo")
    assert extreme_distance_penalty(request, far_other, place) == 0


# --- (1) meal_candidate_score prefers a nearby candidate over a far one ----


def test_jeju_meal_candidate_score_prefers_nearby_over_far_candidate() -> None:
    request = build_request(city="jeju")
    previous_place = build_place(id="prev", latitude=33.45, longitude=126.90)  # east coast

    nearby_meal = build_place(id="nearby-meal", latitude=33.46, longitude=126.92)  # ~2km away
    far_meal = build_place(id="far-meal", latitude=33.39, longitude=126.24)  # ~65km away

    nearby_score = meal_candidate_score(nearby_meal, request, previous_place=previous_place, next_place=None)
    far_score = meal_candidate_score(far_meal, request, previous_place=previous_place, next_place=None)

    assert nearby_score > far_score


def test_seoul_meal_candidate_score_is_unaffected_by_the_same_huge_distance() -> None:
    # Same geometry (reused as if it were Seoul coordinates) - the Jeju-only
    # penalty must not fire, so only the shared, pre-existing
    # coordinate_area_transition_bonus tiers (capped, not scaling with
    # distance) should separate the two candidates' scores.
    from app.domains.rule_planner.services.travel_estimate import coordinate_area_transition_bonus

    request = build_request(city="seoul")
    previous_place = build_place(id="prev", area="gangnam", latitude=33.45, longitude=126.90)
    nearby_meal = build_place(id="nearby-meal", area="gangnam", latitude=33.46, longitude=126.92)
    far_meal = build_place(id="far-meal", area="gangnam", latitude=33.39, longitude=126.24)

    nearby_score = meal_candidate_score(nearby_meal, request, previous_place=previous_place, next_place=None)
    far_score = meal_candidate_score(far_meal, request, previous_place=previous_place, next_place=None)

    expected_nearby_bonus = coordinate_area_transition_bonus(previous_place, nearby_meal)
    expected_far_bonus = coordinate_area_transition_bonus(previous_place, far_meal)
    # Both candidates are otherwise identical (same base_score inputs), so
    # the gap must be exactly the shared, capped transition-bonus
    # difference, not the Jeju-only (unbounded, distance-scaling) penalty -
    # which would make the gap far larger than any single bonus tier can.
    assert nearby_score - far_score == expected_nearby_bonus - expected_far_bonus
    assert nearby_score - far_score <= 20  # CLOSE(14) - FAR(-6): the widest possible single-tier gap
