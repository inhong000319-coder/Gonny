from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.community_feedback import MIN_TOTAL_REVIEWS, PlaceFeedbackSignal
from app.domains.rule_planner.services.reasons import (
    MAX_LABEL_REPEATS_PER_DAY,
    MAX_REASONS_PER_PLACE,
    NEAR_PREVIOUS_MAX_MINUTES,
    build_activity_reason_candidates,
    build_meal_reason_candidates,
    select_day_reasons,
)


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["sightseeing"],
        "budget_level": ["medium"],
        "suitable_for": ["couple"],
        "time_fit": ["afternoon"],
        "area": "gangnam",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy"],
        "mobility": ["walkable"],
        "summary": "sample",
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
        "concepts": ["sightseeing", "culture"],
        "style": "easy",
        "companion_type": "couple",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "stay",
        "name": "Stay",
        "city": "seoul",
        "area": "gangnam",
        "accommodation_type": "호텔",
        "latitude": 37.50,
        "longitude": 127.00,
    }
    data.update(overrides)
    return AccommodationData.model_validate(data)


def minimal_activity_kwargs(**overrides) -> dict:
    data = {
        "request": build_request(),
        "time_slot": "afternoon",
        "day_number": 2,
        "travel_minutes_from_previous": None,
        "is_first_of_day": False,
        "accommodation": None,
        "is_rain_alert_day": False,
        "feedback_signal": None,
    }
    data.update(overrides)
    return data


# --- (1) each reason code's generation / non-generation condition ----------


def test_near_previous_fires_within_threshold() -> None:
    place = build_place()
    candidates = build_activity_reason_candidates(
        place, **minimal_activity_kwargs(travel_minutes_from_previous=NEAR_PREVIOUS_MAX_MINUTES)
    )
    assert ("near_previous", f"직전 장소에서 {NEAR_PREVIOUS_MAX_MINUTES}분") in [(r.code, r.label) for r in candidates]


def test_near_previous_does_not_fire_beyond_threshold() -> None:
    place = build_place()
    candidates = build_activity_reason_candidates(
        place, **minimal_activity_kwargs(travel_minutes_from_previous=NEAR_PREVIOUS_MAX_MINUTES + 1)
    )
    assert all(r.code != "near_previous" for r in candidates)


def test_near_previous_uses_accommodation_distance_for_first_of_day() -> None:
    place = build_place(latitude=37.505, longitude=127.001)  # very close to the accommodation below
    accommodation = build_accommodation(latitude=37.50, longitude=127.00)
    candidates = build_activity_reason_candidates(
        place,
        **minimal_activity_kwargs(
            travel_minutes_from_previous=None,  # no previous place exists for the day's first slot
            is_first_of_day=True,
            accommodation=accommodation,
        ),
    )
    matches = [r for r in candidates if r.code == "near_previous"]
    assert len(matches) == 1
    assert matches[0].label.startswith("숙소에서 ")


def test_near_previous_absent_for_first_of_day_without_accommodation() -> None:
    place = build_place()
    candidates = build_activity_reason_candidates(
        place,
        **minimal_activity_kwargs(travel_minutes_from_previous=None, is_first_of_day=True, accommodation=None),
    )
    assert all(r.code != "near_previous" for r in candidates)


def test_transit_friendly_requires_transit_day_and_subway_friendly_mobility() -> None:
    place = build_place(mobility=["subway-friendly"])
    request = build_request(transport_by_day=["transit", "transit", "transit"])
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request, day_number=1))
    assert ("transit_friendly", "지하철로 가기 편해요") in [(r.code, r.label) for r in candidates]


def test_transit_friendly_absent_on_a_car_day() -> None:
    place = build_place(mobility=["subway-friendly"])
    request = build_request(transport_by_day=["car", "car", "car"])
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request, day_number=1))
    assert all(r.code != "transit_friendly" for r in candidates)


def test_transit_friendly_absent_without_subway_friendly_mobility() -> None:
    place = build_place(mobility=["walkable"])
    request = build_request(transport_by_day=["transit", "transit", "transit"])
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request, day_number=1))
    assert all(r.code != "transit_friendly" for r in candidates)


def test_concept_match_uses_first_matching_requested_concept() -> None:
    place = build_place(activity_type=["culture"])
    request = build_request(concepts=["sightseeing", "culture"])
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
    assert ("concept_match", "선택하신 '문화' 취향과 맞아요") in [(r.code, r.label) for r in candidates]


def test_concept_match_absent_without_intersection() -> None:
    place = build_place(activity_type=["nightlife"])
    request = build_request(concepts=["sightseeing", "culture"])
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
    assert all(r.code != "concept_match" for r in candidates)


def test_companion_fit_requires_membership() -> None:
    place = build_place(suitable_for=["couple"])
    request = build_request(companion_type="couple")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
    assert ("companion_fit", "커플 여행에 잘 맞아요") in [(r.code, r.label) for r in candidates]

    other_place = build_place(suitable_for=["family"])
    other_candidates = build_activity_reason_candidates(other_place, **minimal_activity_kwargs(request=request))
    assert all(r.code != "companion_fit" for r in other_candidates)


def test_time_fit_requires_slot_membership() -> None:
    place = build_place(time_fit=["morning"])
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(time_slot="morning"))
    assert ("time_fit", "오전에 가기 좋아요") in [(r.code, r.label) for r in candidates]

    candidates_wrong_slot = build_activity_reason_candidates(place, **minimal_activity_kwargs(time_slot="evening"))
    assert all(r.code != "time_fit" for r in candidates_wrong_slot)


def test_pace_fit_requires_style_in_pace_for_easy_and_tight() -> None:
    place = build_place(pace=["tight"])
    request = build_request(style="tight")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
    assert ("pace_fit", "원하신 여행 속도에 맞아요") in [(r.code, r.label) for r in candidates]


def test_pace_fit_absent_when_pace_does_not_include_style() -> None:
    place = build_place(pace=["tight"])
    request = build_request(style="easy")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
    assert all(r.code != "pace_fit" for r in candidates)


def test_pace_fit_never_fires_for_near_stay_or_mobility_first() -> None:
    # Those 2 styles are judged by mobility (walkable/nearby) elsewhere in
    # the existing scoring, not pace - reasons.py deliberately does not
    # invent a new pace-based criterion for them.
    place = build_place(pace=["easy", "tight"])
    for style in ("near-stay", "mobility-first"):
        request = build_request(style=style)
        candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
        assert all(r.code != "pace_fit" for r in candidates), style


def test_budget_fit_requires_membership() -> None:
    place = build_place(budget_level=["low"])
    request = build_request(budget_band="low")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(request=request))
    assert ("budget_fit", "예산 범위 안이에요") in [(r.code, r.label) for r in candidates]

    request_mismatch = build_request(budget_band="high")
    candidates_mismatch = build_activity_reason_candidates(
        place, **minimal_activity_kwargs(request=request_mismatch)
    )
    assert all(r.code != "budget_fit" for r in candidates_mismatch)


def test_indoor_ok_requires_indoor_setting_and_rain_alert_day() -> None:
    place = build_place(setting="indoor")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(is_rain_alert_day=True))
    assert ("indoor_ok", "비 소식이 있는 날에도 즐기기 좋아요") in [(r.code, r.label) for r in candidates]


def test_indoor_ok_absent_without_rain_alert_day() -> None:
    place = build_place(setting="indoor")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(is_rain_alert_day=False))
    assert all(r.code != "indoor_ok" for r in candidates)


def test_indoor_ok_absent_for_outdoor_place_even_on_rain_alert_day() -> None:
    place = build_place(setting="outdoor")
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(is_rain_alert_day=True))
    assert all(r.code != "indoor_ok" for r in candidates)


# --- (3) community_good requires the minimum review count ------------------


def test_community_good_requires_minimum_review_count() -> None:
    place = build_place()
    below_threshold = PlaceFeedbackSignal(review_count=MIN_TOTAL_REVIEWS - 1, average_rating=4.8)
    candidates = build_activity_reason_candidates(
        place, **minimal_activity_kwargs(feedback_signal=below_threshold)
    )
    assert all(r.code != "community_good" for r in candidates)

    at_threshold = PlaceFeedbackSignal(review_count=MIN_TOTAL_REVIEWS, average_rating=4.8)
    candidates_ok = build_activity_reason_candidates(place, **minimal_activity_kwargs(feedback_signal=at_threshold))
    assert ("community_good", "방문객 후기가 좋은 곳이에요") in [(r.code, r.label) for r in candidates_ok]


def test_community_good_absent_without_any_signal() -> None:
    place = build_place()
    candidates = build_activity_reason_candidates(place, **minimal_activity_kwargs(feedback_signal=None))
    assert all(r.code != "community_good" for r in candidates)


# --- (2) at most 3 reasons per place, in priority order ---------------------


def test_at_most_three_reasons_selected_in_priority_order() -> None:
    # Built to satisfy every single candidate condition at once.
    place = build_place(
        activity_type=["culture"],
        suitable_for=["couple"],
        time_fit=["afternoon"],
        pace=["easy"],
        budget_level=["medium"],
        mobility=["subway-friendly"],
        setting="indoor",
    )
    request = build_request(
        concepts=["culture"],
        companion_type="couple",
        style="easy",
        budget_band="medium",
        transport_by_day=["transit", "transit", "transit"],
    )
    signal = PlaceFeedbackSignal(review_count=MIN_TOTAL_REVIEWS, average_rating=4.9)
    candidates = build_activity_reason_candidates(
        place,
        **minimal_activity_kwargs(
            request=request,
            day_number=1,
            travel_minutes_from_previous=5,
            is_rain_alert_day=True,
            feedback_signal=signal,
        ),
    )
    # Every one of a-i should be a candidate here.
    assert len(candidates) == 9

    selected = select_day_reasons([candidates])[0]
    assert len(selected) == MAX_REASONS_PER_PLACE
    # Priority order a, b, c are the first 3 candidates built.
    assert [r.code for r in selected] == [c.code for c in candidates[:MAX_REASONS_PER_PLACE]]


# --- day-wide repeated-label cap --------------------------------------------


def test_repeated_label_is_replaced_by_the_next_priority_candidate_after_the_cap() -> None:
    from app.domains.rule_planner.schemas import RuleReason

    shared_label = [RuleReason(code="concept_match", label="선택하신 '문화' 취향과 맞아요")]
    fallback = [RuleReason(code="budget_fit", label="예산 범위 안이에요")]

    day_candidates = [shared_label, shared_label, shared_label + fallback]
    selected = select_day_reasons(day_candidates)

    assert [r.code for r in selected[0]] == ["concept_match"]
    assert [r.code for r in selected[1]] == ["concept_match"]
    # The 3rd place hit the repeat cap on concept_match (already used by
    # MAX_LABEL_REPEATS_PER_DAY=2 earlier places), so it falls through to
    # the next candidate instead - never ends up with 0 reasons just
    # because its first choice was already overused.
    assert MAX_LABEL_REPEATS_PER_DAY == 2
    assert [r.code for r in selected[2]] == ["budget_fit"]


def test_fewer_than_three_candidates_is_allowed() -> None:
    # Deliberately mismatches every condition: no activity_type overlap
    # with request.concepts, companion/budget/pace outside the request,
    # and a time_fit that excludes the queried slot.
    place = build_place(
        activity_type=["nightlife"],
        suitable_for=["solo"],
        time_fit=["evening"],
        pace=["tight"],
        budget_level=["high"],
        mobility=["walkable"],
    )
    request = build_request(
        concepts=["sightseeing", "culture"], companion_type="family", style="easy", budget_band="low"
    )
    candidates = build_activity_reason_candidates(
        place, **minimal_activity_kwargs(request=request, time_slot="morning")
    )
    assert candidates == []
    selected = select_day_reasons([candidates])[0]
    assert selected == []


# --- meal reasons: only near_previous + time_fit, never hours-related ------


def test_meal_reasons_only_ever_contain_travel_and_time_fit_codes() -> None:
    place = build_place(time_fit=["afternoon"])
    candidates = build_meal_reason_candidates(
        place,
        associated_time_slot="afternoon",
        travel_minutes_from_previous=5,
        is_first_of_day=False,
        accommodation=None,
    )
    assert {r.code for r in candidates} <= {"near_previous", "time_fit"}


def test_breakfast_meal_reason_uses_accommodation_distance_when_first_of_day() -> None:
    place = build_place(latitude=37.501, longitude=127.001)
    accommodation = build_accommodation(latitude=37.50, longitude=127.00)
    candidates = build_meal_reason_candidates(
        place,
        associated_time_slot="morning",
        travel_minutes_from_previous=None,
        is_first_of_day=True,
        accommodation=accommodation,
    )
    travel_candidates = [r for r in candidates if r.code == "near_previous"]
    assert len(travel_candidates) == 1
    assert travel_candidates[0].label.startswith("숙소에서 ")


def test_breakfast_without_known_accommodation_distance_has_no_travel_reason() -> None:
    place = build_place()
    candidates = build_meal_reason_candidates(
        place,
        associated_time_slot="morning",
        travel_minutes_from_previous=None,
        is_first_of_day=True,
        accommodation=None,
    )
    assert all(r.code != "near_previous" for r in candidates)


# --- (4) hours_unverified meals never get an hours-related reason text -----


def test_no_reason_label_ever_mentions_opening_hours() -> None:
    # Breakfast's hours_unverified=True is represented on
    # RuleMealRecommendation itself (see service.py), not as a reason -
    # confirm no reason-building path ever produces hours-related text.
    place = build_place(time_fit=["morning"], setting="indoor")
    activity_candidates = build_activity_reason_candidates(
        place, **minimal_activity_kwargs(time_slot="morning", is_rain_alert_day=True)
    )
    meal_candidates = build_meal_reason_candidates(
        place,
        associated_time_slot="morning",
        travel_minutes_from_previous=5,
        is_first_of_day=False,
        accommodation=None,
    )
    for reason in activity_candidates + meal_candidates:
        assert "영업" not in reason.label
