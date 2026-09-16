from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.services.repository import DestinationCatalogRepository
from app.domains.rule_planner.services.community_feedback import (
    PlaceFeedbackSignal,
    community_feedback_bonus,
    load_place_feedback_signals,
)
from app.domains.rule_planner.services.slot_scoring import legacy_base_score
from app.domains.rule_planner.services.travel_estimate import (
    coordinate_area_transition_bonus,
    estimate_accommodation_transition_minutes,
    estimate_day_total_minutes,
)
from app.schemas.place_catalog import PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest
from app.domains.rule_planner.services.service import RuleItineraryService


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "sample-hotel",
        "name": "Sample Hotel",
        "city": "seoul",
        "area": "city-center",
        "accommodation_type": "호텔",
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)

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


def test_real_busan_onsen_places_receive_neighbor_area_bonus() -> None:
    # heosimchung (area=dongnae) and shinsegae-spaland (area=centum) are
    # real catalog entries added alongside the rest of the Busan onsen
    # data, but centum/dongnae were initially missing from
    # BUSAN_AREA_NEIGHBORS - meaning neighbor_area_bonus() could never
    # apply to either of them. Both must now receive it when the previous
    # slot's place sits in haeundae, which genuinely borders both.
    service = RuleItineraryService()
    repository = DestinationCatalogRepository()
    places_by_id = {place.id: place for catalog in repository.load_catalogs() for place in catalog.places}
    request = build_request(city="busan", concepts=["onsen"])

    # No coordinates set, so coordinate_area_transition_bonus() returns
    # None and slot_score() falls back to the string-based area bonuses
    # (same_area_continuity_bonus/neighbor_area_bonus) being tested here.
    haeundae_previous_place = build_place(id="haeundae-anchor", area="haeundae")
    unrelated_previous_place = build_place(id="nampo-anchor", area="nampo")

    for onsen_id in ("heosimchung", "shinsegae-spaland"):
        onsen_place = places_by_id[onsen_id]

        neighbor_score = service._slot_score(
            place=onsen_place,
            request=request,
            time_slot="afternoon",
            day_number=2,
            preferred_area=None,
            previous_place=haeundae_previous_place,
        )
        unrelated_score = service._slot_score(
            place=onsen_place,
            request=request,
            time_slot="afternoon",
            day_number=2,
            preferred_area=None,
            previous_place=unrelated_previous_place,
        )

        assert neighbor_score > unrelated_score, (
            f"{onsen_id} (area={onsen_place.area}) did not score higher when the previous "
            "place was in haeundae vs. an unrelated area - neighbor_area_bonus likely isn't applying."
        )


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


# Accommodation<->place travel time in the daily total (see
# services/travel_estimate.py's estimate_accommodation_transition_minutes)


def test_estimate_accommodation_transition_minutes_none_without_accommodation() -> None:
    place = build_place(latitude=37.5665, longitude=126.9780)
    assert estimate_accommodation_transition_minutes(None, place) is None


def test_estimate_accommodation_transition_minutes_none_without_coordinates() -> None:
    accommodation_no_coords = build_accommodation()
    place_with_coords = build_place(latitude=37.5665, longitude=126.9780)
    assert estimate_accommodation_transition_minutes(accommodation_no_coords, place_with_coords) is None

    accommodation_with_coords = build_accommodation(latitude=37.5665, longitude=126.9780)
    place_no_coords = build_place()
    assert estimate_accommodation_transition_minutes(accommodation_with_coords, place_no_coords) is None


def test_day_total_minutes_adds_both_accommodation_legs_when_far_away() -> None:
    # Places sit right next to each other (central Seoul); the accommodation
    # is ~40km away (well outside the city center), so its to-first/
    # from-last legs should dominate the total.
    places = [
        build_place(id="place-1", duration_hours=2, latitude=37.5665, longitude=126.9780),
        build_place(id="place-2", duration_hours=2, latitude=37.5670, longitude=126.9785),
    ]
    far_accommodation = build_accommodation(latitude=37.9000, longitude=127.3000)

    without_accommodation = estimate_day_total_minutes(places)
    with_far_accommodation = estimate_day_total_minutes(places, far_accommodation)

    assert with_far_accommodation > without_accommodation


def test_day_total_minutes_unaffected_by_accommodation_without_coordinates() -> None:
    places = [build_place(id="place-1", duration_hours=2, latitude=37.5665, longitude=126.9780)]
    accommodation_no_coords = build_accommodation()

    assert estimate_day_total_minutes(places, accommodation_no_coords) == estimate_day_total_minutes(places)


def test_day_duration_warning_more_likely_when_accommodation_is_far_from_activity_area() -> None:
    # Duration alone (8h) sits under the 10h threshold; only once the
    # to/from-accommodation legs are added should the warning appear.
    service = RuleItineraryService()
    places = [
        build_place(id="near-place-1", duration_hours=4, latitude=37.5665, longitude=126.9780),
        build_place(id="near-place-2", duration_hours=4, latitude=37.5670, longitude=126.9785),
    ]
    far_accommodation = build_accommodation(latitude=37.9000, longitude=127.3000)

    warnings_without_accommodation = service._build_day_duration_warnings({1: places})
    warnings_with_far_accommodation = service._build_day_duration_warnings({1: places}, far_accommodation)

    assert warnings_without_accommodation == []
    assert len(warnings_with_far_accommodation) == 1
    assert warnings_with_far_accommodation[0].day_number == 1


def test_day_duration_warning_unaffected_when_no_accommodation_recommended() -> None:
    service = RuleItineraryService()
    short_places = [build_place(id=f"short-place-{i}", duration_hours=2) for i in range(3)]  # 6h

    assert service._build_day_duration_warnings({1: short_places}, None) == []


# Community feedback bonus (see services/community_feedback.py)


def test_community_feedback_bonus_none_when_signal_missing() -> None:
    assert community_feedback_bonus(None, "morning", "friend") is None


def test_community_feedback_bonus_none_below_review_count_threshold() -> None:
    signal = PlaceFeedbackSignal(review_count=4, average_rating=5.0)

    assert community_feedback_bonus(signal, "morning", "friend") is None


def test_community_feedback_bonus_uses_slot_detail_when_reliable() -> None:
    signal = PlaceFeedbackSignal(
        review_count=10,
        average_rating=3.0,
        slot_scores={"morning": 5.0},
        slot_review_counts={"morning": 3},
    )

    bonus = community_feedback_bonus(signal, "morning", "friend")

    assert bonus == 10  # (5.0 - 3) * 5


def test_community_feedback_bonus_falls_back_to_average_when_detail_unreliable() -> None:
    # Only 2 reviews back the "morning" bucket - below MIN_DETAIL_REVIEWS
    # (3), so this should fall back to the overall average rather than use
    # the unreliable slot-specific rating.
    signal = PlaceFeedbackSignal(
        review_count=10,
        average_rating=4.0,
        slot_scores={"morning": 5.0},
        slot_review_counts={"morning": 2},
    )

    bonus = community_feedback_bonus(signal, "morning", "friend")

    assert bonus == 5  # (4.0 - 3) * 5, not the (5.0 - 3) * 5 = 10 the slot data would give


def test_community_feedback_bonus_ignores_unrecognized_slot_and_companion_values() -> None:
    # slot_scores/companion_scores can contain free-text values from
    # PlaceReviewCreate (no server-side validation on visit_time_slot/
    # companion_type) - e.g. Korean text or typos instead of our system's
    # morning/afternoon/evening and solo/couple/friend/family. These must
    # never be looked up even if they happen to be present with plenty of
    # reviews behind them.
    signal = PlaceFeedbackSignal(
        review_count=10,
        average_rating=3.0,
        slot_scores={"저녁": 5.0},
        slot_review_counts={"저녁": 10},
        companion_scores={"unknown-companion": 1.0},
        companion_review_counts={"unknown-companion": 10},
    )

    bonus = community_feedback_bonus(signal, "evening", "friend")

    # Neither bogus bucket is used, so this falls back to the overall
    # average (3.0 -> 0), not the 5.0/1.0 values sitting under the wrong keys.
    assert bonus == 0


def test_slot_score_applies_community_feedback_bonus_when_reliable_data_exists() -> None:
    service = RuleItineraryService()
    request = build_request()
    place = build_place()
    reliable_signal = PlaceFeedbackSignal(
        review_count=10,
        average_rating=5.0,
        slot_scores={"morning": 5.0},
        slot_review_counts={"morning": 5},
    )

    score_with_feedback = service._slot_score(
        place=place,
        request=request,
        time_slot="morning",
        day_number=2,
        preferred_area="city-center",
        community_signal=reliable_signal,
    )
    score_without_feedback = service._slot_score(
        place=place,
        request=request,
        time_slot="morning",
        day_number=2,
        preferred_area="city-center",
    )

    assert score_with_feedback - score_without_feedback == 10


def test_slot_score_unaffected_by_review_data_below_threshold() -> None:
    # Proves the feature is inert until a place accumulates enough reviews:
    # a signal that exists but doesn't clear MIN_TOTAL_REVIEWS must produce
    # an identical score to having no signal at all (the current real-world
    # state, since there are 0 reviews everywhere today).
    service = RuleItineraryService()
    request = build_request()
    place = build_place()
    thin_signal = PlaceFeedbackSignal(review_count=2, average_rating=5.0)

    score_with_thin_signal = service._slot_score(
        place=place,
        request=request,
        time_slot="morning",
        day_number=2,
        preferred_area="city-center",
        community_signal=thin_signal,
    )
    score_with_no_signal = service._slot_score(
        place=place,
        request=request,
        time_slot="morning",
        day_number=2,
        preferred_area="city-center",
    )

    assert score_with_thin_signal == score_with_no_signal


def test_load_place_feedback_signals_empty_without_database() -> None:
    # This test suite runs without DATABASE_URL configured, matching the
    # real current deployment state (0 reviews, feature effectively
    # disabled) - load_place_feedback_signals must degrade to {} rather
    # than raise.
    assert load_place_feedback_signals(["gyeongbokgung", "myeongdong"]) == {}
