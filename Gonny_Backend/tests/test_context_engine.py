"""Unit tests for role-B feature logic."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure local app package is importable even in embedded Python mode.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.context import (
    CompanionPreferenceInput,
    DurationEstimateRequest,
    ItinerarySpotInput,
    MealSlotInput,
    PreferenceMergeRequest,
    RestaurantRecommendRequest,
    TransportLegInput,
    TransportRecommendRequest,
)
from app.services.context_engine import (
    estimate_duration,
    merge_companion_preferences,
    recommend_restaurants,
    recommend_transport,
)


def test_f03_duration_warns_when_overloaded() -> None:
    request = DurationEstimateRequest(
        spots=[ItinerarySpotInput(name=f"spot-{idx}", category="attraction") for idx in range(8)],
        transport_mode="walk",
        avg_move_distance_km=2.0,
    )
    response = estimate_duration(request)
    assert response.total_duration_min > 600
    assert response.warning is not None


def test_f05_merges_companion_preferences() -> None:
    request = PreferenceMergeRequest(
        companions=[
            CompanionPreferenceInput(name="A", tags=["food", "culture"]),
            CompanionPreferenceInput(name="B", tags=["food", "activity"], is_child=True),
        ],
        base_trip_tags=["nature"],
    )
    response = merge_companion_preferences(request)
    assert response.weights[0].tag in {"food", "activity"}
    total = sum(item.weight_percent for item in response.weights)
    assert abs(total - 100.0) < 0.01


def test_f07_transport_returns_total_duration() -> None:
    request = TransportRecommendRequest(
        transport_mode="mixed",
        legs=[
            TransportLegInput(origin="A", destination="B", distance_km=1.0),
            TransportLegInput(origin="B", destination="C", distance_km=12.0),
        ],
    )
    response = recommend_transport(request)
    assert response.total_duration_min > 0
    assert len(response.legs) == 2


def test_f08_restaurants_assign_each_meal_slot() -> None:
    request = RestaurantRecommendRequest(
        destination="Seoul",
        preferred_cuisines=["korean", "western"],
        meal_slots=[
            MealSlotInput(day_label="D1", meal_type="lunch"),
            MealSlotInput(day_label="D1", meal_type="dinner"),
        ],
    )
    response = recommend_restaurants(request)
    assert len(response.options) == 2
