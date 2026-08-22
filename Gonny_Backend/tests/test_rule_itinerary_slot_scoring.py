from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.services.repository import DestinationCatalogRepository
from app.domains.rule_planner.services.slot_scoring import legacy_base_score
from app.domains.rule_planner.services.travel_estimate import coordinate_area_transition_bonus
from app.schemas.place_catalog import PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest
from app.services.rule_itinerary_service import RuleItineraryService

ONSEN_PLACE_IDS = [
    "heosimchung",
    "shinsegae-spaland",
    "club-d-oasis",
    "woori-sulfur-spa",
    "bongil-spa-land",
]


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["sightseeing"],
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
    short_evening = build_place(id="short-evening", duration_hours=2, activity_type=["food"])
    long_evening = build_place(id="long-evening", duration_hours=5, activity_type=["food"])

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
        activity_type=["activity"],
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


# base_score() now delegates to the trained fitness model (see
# services/fitness_model.py), so its output is no longer a deterministic sum
# of hand-picked constants. The exact concept_overlap-bonus checks that used
# to target base_score() are preserved below against legacy_base_score(),
# which still contains the original rule-based formula unchanged.


def test_legacy_base_score_nightlife_place_gets_concept_overlap_bonus() -> None:
    request = build_request(concepts=["nightlife"])
    nightlife_place = build_place(activity_type=["나이트라이프"])
    neutral_place = build_place(id="neutral-place", activity_type=["미식"])

    nightlife_score = legacy_base_score(nightlife_place, request)
    neutral_score = legacy_base_score(neutral_place, request)

    assert nightlife_score - neutral_score == 8


def test_legacy_base_score_onsen_place_gets_concept_overlap_bonus() -> None:
    request = build_request(concepts=["onsen"])
    onsen_place = build_place(activity_type=["온천"])
    neutral_place = build_place(id="neutral-place", activity_type=["미식"])

    onsen_score = legacy_base_score(onsen_place, request)
    neutral_score = legacy_base_score(neutral_place, request)

    assert onsen_score - neutral_score == 8


def test_ml_base_score_favors_nightlife_place_for_nightlife_concept() -> None:
    # Directional check, not an exact value: base_score() is now a model
    # prediction, so we only assert it captures the same concept-fit signal
    # legacy_base_score() encoded with a fixed +8. 11 real places carry the
    # 나이트라이프 tag in training data, so the model has signal to learn from.
    service = RuleItineraryService()
    request = build_request(concepts=["nightlife"])
    nightlife_place = build_place(activity_type=["나이트라이프"])
    neutral_place = build_place(id="neutral-place", activity_type=["미식"])

    nightlife_score = service._base_score(nightlife_place, request)
    neutral_score = service._base_score(neutral_place, request)

    assert nightlife_score > neutral_score


def test_ml_base_score_favors_real_onsen_places_for_onsen_concept() -> None:
    # Uses the real catalog entries (seoul.json/busan.json) rather than a
    # synthetic build_place(), since the point is to confirm the 5 real
    # onsen places added to the catalog actually get scored up by the
    # trained model, not just a hypothetical place with an 온천 tag.
    service = RuleItineraryService()
    repository = DestinationCatalogRepository()
    places_by_id = {place.id: place for catalog in repository.load_catalogs() for place in catalog.places}
    request = build_request(concepts=["onsen"])

    neutral_place = places_by_id["haeundae-beach"]
    neutral_score = service._base_score(neutral_place, request)

    for place_id in ONSEN_PLACE_IDS:
        onsen_place = places_by_id[place_id]
        onsen_score = service._base_score(onsen_place, request)
        assert onsen_score > neutral_score, f"{place_id} ({onsen_score}) did not outscore neutral place ({neutral_score})"


def test_ml_base_score_returns_plausible_int_score() -> None:
    # Sanity-checks the model/encoder wiring end to end rather than an exact
    # value, since fitness_score training targets ranged 0-100 but a
    # regressor can extrapolate slightly outside that range.
    service = RuleItineraryService()
    request = build_request(concepts=["food"])
    place = build_place(activity_type=["미식"])

    score = service._base_score(place, request)

    assert isinstance(score, int)
    assert -20 <= score <= 120


# Coordinate-based travel estimate (see services/travel_estimate.py)


def test_coordinate_area_transition_bonus_applies_when_both_places_have_coordinates() -> None:
    # ~100m apart in real-world terms (central Seoul), but different area
    # strings with no defined neighbor relationship - string-based logic
    # would score this pair's transition as 0.
    previous_place = build_place(id="coord-prev", area="area-a", latitude=37.5665, longitude=126.9780)
    nearby_place = build_place(id="coord-nearby", area="area-b", latitude=37.5670, longitude=126.9785)

    bonus = coordinate_area_transition_bonus(previous_place, nearby_place)

    assert bonus is not None
    assert bonus > 0


def test_coordinate_area_transition_bonus_falls_back_to_none_without_coordinates() -> None:
    previous_place = build_place(id="coord-prev", area="area-a", latitude=37.5665, longitude=126.9780)
    place_without_coords = build_place(id="no-coords", area="area-b")

    assert coordinate_area_transition_bonus(previous_place, place_without_coords) is None
    assert coordinate_area_transition_bonus(None, place_without_coords) is None


def test_slot_score_prefers_coordinate_estimate_over_string_area_match() -> None:
    # Two places in different, unrelated area strings (no same-area or
    # neighbor bonus would apply under the old string-only logic) but very
    # close together by coordinates should still get a continuity bonus
    # now that coordinates are available for both.
    service = RuleItineraryService()
    request = build_request()

    previous_with_coords = build_place(id="prev-coords", area="area-a", latitude=37.5665, longitude=126.9780)
    nearby_cross_area = build_place(id="nearby-cross-area", area="area-b", latitude=37.5670, longitude=126.9785)
    coordinate_score = service._slot_score(
        place=nearby_cross_area,
        request=request,
        time_slot="afternoon",
        day_number=2,
        preferred_area=None,
        previous_place=previous_with_coords,
    )

    # Same area pairing but with no coordinates on either place, so this
    # transition falls back to the pre-existing string-based logic, which
    # gives 0 for this unrelated area-a/area-b pair.
    previous_without_coords = build_place(id="prev-no-coords", area="area-a")
    cross_area_without_coords = build_place(id="cross-area-no-coords", area="area-b")
    string_only_score = service._slot_score(
        place=cross_area_without_coords,
        request=request,
        time_slot="afternoon",
        day_number=2,
        preferred_area=None,
        previous_place=previous_without_coords,
    )

    assert coordinate_score > string_only_score


# Daily total duration warning (see service._build_day_duration_warnings)


def test_day_duration_warning_flagged_when_total_exceeds_threshold() -> None:
    service = RuleItineraryService()
    long_places = [build_place(id=f"long-place-{i}", duration_hours=4) for i in range(3)]  # 12h, no coords

    warnings = service._build_day_duration_warnings({1: long_places})

    assert len(warnings) == 1
    assert warnings[0].day_number == 1
    assert warnings[0].estimated_total_minutes == 12 * 60


def test_day_duration_warning_not_flagged_under_threshold() -> None:
    service = RuleItineraryService()
    short_places = [build_place(id=f"short-place-{i}", duration_hours=2) for i in range(3)]  # 6h

    warnings = service._build_day_duration_warnings({1: short_places})

    assert warnings == []
