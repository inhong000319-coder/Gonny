from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.place_catalog import PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest
from app.services.rule_itinerary_service import RuleItineraryService


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "category": ["sightseeing"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "city-center",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample summary",
        "slot_bias": {},
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


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
        "companion_type": "friend",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


def test_slot_bias_has_stronger_effect_on_matching_time_slot() -> None:
    service = RuleItineraryService()
    request = build_request()
    morning_focused = build_place(slot_bias={"morning": 8})
    neutral = build_place(id="neutral-place")

    focused_score = service._slot_score(
        place=morning_focused,
        request=request,
        time_slot="morning",
        day_number=2,
        preferred_area="city-center",
    )
    neutral_score = service._slot_score(
        place=neutral,
        request=request,
        time_slot="morning",
        day_number=2,
        preferred_area="city-center",
    )

    assert focused_score - neutral_score >= 20


def test_short_place_is_preferred_over_long_place_for_evening_slot() -> None:
    service = RuleItineraryService()
    request = build_request()
    short_evening = build_place(id="short-evening", duration_hours=2, category=["food"])
    long_evening = build_place(id="long-evening", duration_hours=5, category=["food"])

    short_score = service._slot_score(
        place=short_evening,
        request=request,
        time_slot="evening",
        day_number=2,
        preferred_area="city-center",
    )
    long_score = service._slot_score(
        place=long_evening,
        request=request,
        time_slot="evening",
        day_number=2,
        preferred_area="city-center",
    )

    assert short_score > long_score


def test_activity_place_gets_afternoon_boost_for_longer_visit() -> None:
    service = RuleItineraryService()
    request = build_request(concepts=["activity"], style="tight")
    activity_place = build_place(
        category=["activity"],
        duration_hours=5,
        slot_bias={"afternoon": 3},
        pace=["tight"],
    )

    afternoon_score = service._slot_score(
        place=activity_place,
        request=request,
        time_slot="afternoon",
        day_number=2,
        preferred_area="city-center",
    )
    evening_score = service._slot_score(
        place=activity_place,
        request=request,
        time_slot="evening",
        day_number=2,
        preferred_area="city-center",
    )

    assert afternoon_score > evening_score
