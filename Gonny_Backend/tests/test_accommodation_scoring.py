from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.rule_planner.services.accommodation_scoring import (
    BUDGET_MATCH_BONUS,
    BUDGET_MISMATCH_PENALTY,
    COMPANION_MATCH_BONUS,
    PRICE_ADJACENT_PENALTY,
    PRICE_EXACT_MATCH_BONUS,
    PRICE_FAR_PENALTY,
    accommodation_score,
    classify_price_band,
    compute_day_endpoints,
    compute_reference_point,
    load_city_accommodations,
    select_accommodation_recommendation,
)
from app.domains.rule_planner.services.policies.city import price_exact_match_bonus
from app.schemas.place_catalog import CityPlaceCatalog, PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService

# Roughly central Seoul, used as a stand-in "reference point" in tests
# that don't need a real itinerary to derive one.
SEOUL_REFERENCE_POINT = (37.5665, 126.9780)


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "sample-hotel",
        "name": "Sample Hotel",
        "city": "seoul",
        "area": "gangnam",
        "accommodation_type": "호텔",
        "budget_level": ["medium"],
        "suitable_for": ["solo", "couple"],
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


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["sightseeing"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "gangnam",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample summary",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


# accommodation_score()


def test_budget_match_scores_higher_than_mismatch() -> None:
    request = build_request(budget_band="high")
    matching = build_accommodation(budget_level=["high"])
    mismatched = build_accommodation(id="other", budget_level=["low"])

    assert accommodation_score(matching, request, None) > accommodation_score(mismatched, request, None)


def test_companion_match_scores_higher_than_mismatch() -> None:
    request = build_request(companion_type="family")
    matching = build_accommodation(suitable_for=["family"])
    mismatched = build_accommodation(id="other", suitable_for=["solo"])

    assert accommodation_score(matching, request, None) > accommodation_score(mismatched, request, None)


def test_closer_accommodation_scores_higher_than_farther_one() -> None:
    request = build_request()
    # ~200m from the reference point.
    nearby = build_accommodation(id="nearby", latitude=37.5680, longitude=126.9790)
    # ~40km away (well past FAR_DISTANCE_KM).
    far = build_accommodation(id="far", latitude=37.9000, longitude=127.3000)

    nearby_score = accommodation_score(nearby, request, SEOUL_REFERENCE_POINT)
    far_score = accommodation_score(far, request, SEOUL_REFERENCE_POINT)

    assert nearby_score > far_score


def test_accommodation_type_does_not_affect_score() -> None:
    request = build_request()
    hotel = build_accommodation(accommodation_type="호텔")
    hostel = build_accommodation(id="other", accommodation_type="호스텔")

    assert accommodation_score(hotel, request, None) == accommodation_score(hostel, request, None)


def test_missing_coordinates_contribute_no_location_bonus_or_penalty() -> None:
    request = build_request()
    without_coords = build_accommodation(latitude=None, longitude=None)

    with_reference = accommodation_score(without_coords, request, SEOUL_REFERENCE_POINT)
    without_reference = accommodation_score(without_coords, request, None)

    assert with_reference == without_reference


# Budget fit: real nightly price vs. budget_level tag fallback


def _budget_contribution(accommodation: AccommodationData, request: NormalizedRuleRequest) -> int:
    # build_accommodation()'s default suitable_for includes "couple", and
    # build_request() uses companion_type="couple", so the companion term is
    # constant (+COMPANION_MATCH_BONUS). No reference point, so location is 0.
    # Subtracting the companion term leaves only the budget-fit contribution.
    return accommodation_score(accommodation, request, None) - COMPANION_MATCH_BONUS


def test_priced_stay_in_exact_band_gets_exact_match_bonus() -> None:
    # city="busan" deliberately - busan doesn't override price_exact_match_
    # bonus(), so this tests the shared PRICE_EXACT_MATCH_BONUS value
    # itself (seoul/jeju override it to 6 - see their own per-city tests
    # below).
    request = build_request(city="busan", budget_band="medium")
    priced_medium = build_accommodation(city="busan", average_price_krw=109000)

    assert _budget_contribution(priced_medium, request) == PRICE_EXACT_MATCH_BONUS


def test_priced_stay_one_band_away_gets_adjacent_penalty() -> None:
    request = build_request(budget_band="medium")
    priced_low = build_accommodation(average_price_krw=40000)
    priced_high = build_accommodation(id="high", average_price_krw=500000)

    assert _budget_contribution(priced_low, request) == PRICE_ADJACENT_PENALTY
    assert _budget_contribution(priced_high, request) == PRICE_ADJACENT_PENALTY


def test_priced_stay_two_bands_away_gets_far_penalty() -> None:
    low_request = build_request(budget_band="low")
    high_request = build_request(budget_band="high")

    assert _budget_contribution(build_accommodation(average_price_krw=500000), low_request) == PRICE_FAR_PENALTY
    assert _budget_contribution(build_accommodation(id="cheap", average_price_krw=40000), high_request) == PRICE_FAR_PENALTY


def test_real_price_overrides_a_contradicting_budget_level_tag() -> None:
    # The tag says high-end, but the researched rate is in the low band - the
    # price wins, so a "low" request gets the exact-match bonus, not the tag's
    # mismatch penalty.
    # city="busan" for the same reason as the exact-match-bonus test above.
    request = build_request(city="busan", budget_band="low")
    tagged_high_but_cheap = build_accommodation(city="busan", budget_level=["high"], average_price_krw=40000)

    assert _budget_contribution(tagged_high_but_cheap, request) == PRICE_EXACT_MATCH_BONUS


def test_unpriced_stay_falls_back_to_budget_level_tag_match() -> None:
    request = build_request(budget_band="medium")
    unpriced_matching = build_accommodation(budget_level=["medium"], average_price_krw=None)

    assert _budget_contribution(unpriced_matching, request) == BUDGET_MATCH_BONUS


def test_unpriced_stay_falls_back_to_budget_level_tag_mismatch() -> None:
    request = build_request(budget_band="medium")
    unpriced_mismatched = build_accommodation(budget_level=["low"], average_price_krw=None)

    assert _budget_contribution(unpriced_mismatched, request) == BUDGET_MISMATCH_PENALTY


@pytest.mark.parametrize(
    ("price_krw", "expected_band"),
    [
        (42862, "low"),
        (70000, "low"),
        (70001, "medium"),
        (109000, "medium"),
        (200000, "medium"),
        (200001, "high"),
        (880000, "high"),
    ],
)
def test_classify_price_band_uses_tertile_boundaries(price_krw: int, expected_band: str) -> None:
    assert classify_price_band(price_krw) == expected_band


# price_exact_match_bonus() - per-city override (seoul/jeju=6, busan=10 default)


def test_price_exact_match_bonus_is_lowered_for_seoul_and_jeju_but_not_busan() -> None:
    assert price_exact_match_bonus("seoul") == 6
    assert price_exact_match_bonus("jeju") == 6
    assert price_exact_match_bonus("busan") == 10


def test_price_exact_match_bonus_defaults_to_10_when_city_is_unset_or_unknown() -> None:
    assert price_exact_match_bonus(None) == 10
    assert price_exact_match_bonus("tokyo") == 10
    assert price_exact_match_bonus("") == 10


def test_budget_fit_score_routes_the_exact_match_case_through_the_per_city_hook() -> None:
    request_seoul = build_request(city="seoul", budget_band="medium")
    request_jeju = build_request(city="jeju", budget_band="medium")
    request_busan = build_request(city="busan", budget_band="medium")
    priced_match_seoul = build_accommodation(city="seoul", average_price_krw=109000)
    priced_match_jeju = build_accommodation(city="jeju", average_price_krw=109000)
    priced_match_busan = build_accommodation(city="busan", average_price_krw=109000)

    assert _budget_contribution(priced_match_seoul, request_seoul) == 6
    assert _budget_contribution(priced_match_jeju, request_jeju) == 6
    assert _budget_contribution(priced_match_busan, request_busan) == 10


def test_adjacent_and_far_price_penalties_are_unchanged_in_every_city() -> None:
    # Only the exact-match case is routed through the per-city hook - the
    # adjacent/far penalties (and the unpriced match/mismatch bonuses below)
    # must stay identical across all three cities, exactly as before this
    # change.
    for city in ("seoul", "busan", "jeju"):
        medium_request = build_request(city=city, budget_band="medium")
        low_request = build_request(city=city, budget_band="low")
        high_request = build_request(city=city, budget_band="high")

        priced_low = build_accommodation(city=city, average_price_krw=40000)
        priced_high = build_accommodation(city=city, id="high", average_price_krw=500000)
        assert _budget_contribution(priced_low, medium_request) == PRICE_ADJACENT_PENALTY
        assert _budget_contribution(priced_high, medium_request) == PRICE_ADJACENT_PENALTY

        assert _budget_contribution(build_accommodation(city=city, average_price_krw=500000), low_request) == PRICE_FAR_PENALTY
        assert _budget_contribution(build_accommodation(city=city, id="cheap", average_price_krw=40000), high_request) == PRICE_FAR_PENALTY


def test_unpriced_stay_scores_are_unchanged_in_every_city() -> None:
    for city in ("seoul", "busan", "jeju"):
        request = build_request(city=city, budget_band="medium")
        unpriced_matching = build_accommodation(city=city, budget_level=["medium"], average_price_krw=None)
        unpriced_mismatched = build_accommodation(city=city, budget_level=["low"], average_price_krw=None)

        assert _budget_contribution(unpriced_matching, request) == BUDGET_MATCH_BONUS
        assert _budget_contribution(unpriced_mismatched, request) == BUDGET_MISMATCH_PENALTY


# select_accommodation_recommendation()


def test_select_prefers_coordinate_having_candidates_when_any_exist() -> None:
    request = build_request(budget_band="low", companion_type="solo")
    # Scores better on budget/companion fit but has no coordinates.
    no_coords_but_better_fit = build_accommodation(
        id="no-coords",
        budget_level=["low"],
        suitable_for=["solo"],
        latitude=None,
        longitude=None,
    )
    # Worse fit on budget/companion but does have coordinates.
    with_coords_worse_fit = build_accommodation(
        id="with-coords",
        budget_level=["high"],
        suitable_for=["family"],
        latitude=37.5665,
        longitude=126.9780,
    )

    selected = select_accommodation_recommendation(
        [no_coords_but_better_fit, with_coords_worse_fit], request, None
    )

    assert selected.id == "with-coords"


def test_select_falls_back_to_full_pool_when_nobody_has_coordinates() -> None:
    request = build_request(budget_band="low", companion_type="solo")
    better_fit = build_accommodation(id="better", budget_level=["low"], suitable_for=["solo"], latitude=None, longitude=None)
    worse_fit = build_accommodation(id="worse", budget_level=["high"], suitable_for=["family"], latitude=None, longitude=None)

    selected = select_accommodation_recommendation([better_fit, worse_fit], request, None)

    assert selected.id == "better"


def test_select_returns_none_for_empty_list() -> None:
    assert select_accommodation_recommendation([], build_request(), None) is None


def test_select_breaks_an_exact_score_tie_by_id_not_catalog_order() -> None:
    # Identical budget/companion fit AND identical coordinates (so their
    # distance term ties too) - a genuine accommodation_score() tie. Without
    # an explicit tie-break, Python's stable sort would just pick whichever
    # one happened to come first in the input list - this must NOT happen:
    # the same accommodation ("aa-earlier-id", the lexicographically
    # smaller id) must win regardless of input order.
    request = build_request(budget_band="medium", companion_type="couple")
    same_point = (37.5665, 126.9780)
    later_id = build_accommodation(id="zz-later-id", latitude=same_point[0], longitude=same_point[1])
    earlier_id = build_accommodation(id="aa-earlier-id", latitude=same_point[0], longitude=same_point[1])

    picked_from_one_order = select_accommodation_recommendation([later_id, earlier_id], request, same_point)
    picked_from_reversed_order = select_accommodation_recommendation([earlier_id, later_id], request, same_point)

    assert picked_from_one_order.id == "aa-earlier-id"
    assert picked_from_reversed_order.id == "aa-earlier-id"


def test_select_breaks_a_tie_by_distance_before_id_when_distance_differs() -> None:
    # Same total score but NOT the same distance - the nearer one must win
    # even though its id sorts later, confirming distance is checked before
    # id. Equal scores are forced without day_endpoints (reference_point
    # tiers only): both candidates sit in the 1.0~3.0km NEARBY tier
    # (CLOSE_DISTANCE_KM < d <= NEARBY_DISTANCE_KM), which pays the exact
    # same +6 bonus despite their different raw distances - same
    # budget/companion fit on top makes the totals identical.
    from app.domains.rule_planner.services.travel_estimate import haversine_distance_km

    request = build_request(budget_band="medium", companion_type="couple")
    reference_point = (37.5665, 126.9780)
    nearer_but_later_id = build_accommodation(id="zz-nearer", latitude=37.5790, longitude=126.9780)
    farther_but_earlier_id = build_accommodation(id="aa-farther", latitude=37.5890, longitude=126.9780)

    nearer_km = haversine_distance_km(*reference_point, nearer_but_later_id.latitude, nearer_but_later_id.longitude)
    farther_km = haversine_distance_km(*reference_point, farther_but_earlier_id.latitude, farther_but_earlier_id.longitude)
    assert 1.0 < nearer_km < farther_km <= 3.0  # both in the same NEARBY tier, but genuinely different distances

    score_nearer = accommodation_score(nearer_but_later_id, request, reference_point, None)
    score_farther = accommodation_score(farther_but_earlier_id, request, reference_point, None)
    assert score_nearer == score_farther  # the tie this test needs

    picked = select_accommodation_recommendation([farther_but_earlier_id, nearer_but_later_id], request, reference_point)
    assert picked.id == "zz-nearer"


# compute_reference_point()


def test_reference_point_uses_most_visited_area() -> None:
    catalog = CityPlaceCatalog(
        continent="asia",
        country="korea",
        city="seoul",
        places=[
            build_place(id="a", area="gangnam", latitude=37.50, longitude=127.02),
            build_place(id="b", area="gangnam", latitude=37.52, longitude=127.04),
            build_place(id="c", area="hongdae", latitude=37.55, longitude=126.92),
        ],
    )
    day_place_map = {
        1: [catalog.places[0], catalog.places[1]],
        2: [catalog.places[0]],  # gangnam visited 3 times total, hongdae once
        3: [catalog.places[2]],
    }

    reference_point = compute_reference_point(day_place_map, catalog)

    assert reference_point == pytest.approx((37.51, 127.03))  # average of the two gangnam places


def test_reference_point_none_when_no_places_visited() -> None:
    catalog = CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=[])

    assert compute_reference_point({}, catalog) is None


# load_city_accommodations()


def test_load_city_accommodations_returns_empty_list_for_unknown_city() -> None:
    assert load_city_accommodations("nonexistent-city") == []


def test_load_city_accommodations_reads_real_seoul_data() -> None:
    accommodations = load_city_accommodations("seoul")

    # scripts/add_tour_api_lodging.py grew seoul from 15 to 63.
    assert len(accommodations) == 63
    assert all(isinstance(item, AccommodationData) for item in accommodations)


# End-to-end integration


def test_generate_includes_an_accommodation_recommendation() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(city="seoul", concepts=["culture", "food"], nights=2, days=3)
    )

    assert response.accommodation_recommendation is not None
    assert response.accommodation_recommendation.city == "seoul"


# compute_day_endpoints()


def test_compute_day_endpoints_returns_first_and_last_place_per_day() -> None:
    day_place_map = {
        1: [
            build_place(id="a", latitude=33.50, longitude=126.50),
            build_place(id="b", latitude=33.51, longitude=126.51),
            build_place(id="c", latitude=33.52, longitude=126.52),
        ],
        2: [build_place(id="d", latitude=33.60, longitude=126.60)],
    }

    endpoints = compute_day_endpoints(day_place_map)

    assert (33.50, 126.50) in endpoints
    assert (33.52, 126.52) in endpoints
    assert (33.60, 126.60) in endpoints
    # Day 2 has a single place - it must not be counted twice.
    assert endpoints.count((33.60, 126.60)) == 1


def test_compute_day_endpoints_skips_places_without_coordinates() -> None:
    day_place_map = {1: [build_place(id="a", latitude=None, longitude=None)]}

    assert compute_day_endpoints(day_place_map) == []


# accommodation_distance_score (per-day-endpoint distance scoring - seoul/busan/jeju)


def test_jeju_accommodation_prefers_smaller_day_endpoints_distance_sum() -> None:
    request = build_request(city="jeju")
    # Both candidates are far enough from any single reference_point tier
    # to land in FAR_LOCATION_PENALTY under the old reference_point-only
    # scoring (see test_closer_accommodation_scores_higher_than_farther_one)
    # - the day_endpoints-based score is what should separate them here.
    day_endpoints = [(33.51, 126.53), (33.45, 126.92)]  # jeju-city-ish, seongsan-ish
    closer = build_accommodation(id="closer", city="jeju", area="east-jeju", latitude=33.50, longitude=126.60)
    farther = build_accommodation(id="farther", city="jeju", area="west-jeju", latitude=33.30, longitude=126.25)

    closer_score = accommodation_score(closer, request, None, day_endpoints)
    farther_score = accommodation_score(farther, request, None, day_endpoints)

    assert closer_score > farther_score


def test_jeju_accommodation_distance_score_ignores_reference_point() -> None:
    # Once day_endpoints is non-empty for Jeju, the score should come
    # entirely from it, not from the old single reference_point tiers -
    # passing a reference_point right on top of the accommodation must not
    # change the score.
    request = build_request(city="jeju")
    accommodation = build_accommodation(city="jeju", area="east-jeju", latitude=33.50, longitude=126.60)
    day_endpoints = [(33.51, 126.53)]

    score_without_reference_point = accommodation_score(accommodation, request, None, day_endpoints)
    score_with_reference_point = accommodation_score(
        accommodation, request, (accommodation.latitude, accommodation.longitude), day_endpoints
    )

    assert score_without_reference_point == score_with_reference_point


def test_select_accommodation_for_seoul_uses_day_endpoints_instead_of_reference_point() -> None:
    # Seoul now defines accommodation_distance_score (policies/city/seoul.py),
    # so once day_endpoints is non-empty the pick flips to whichever
    # candidate is closer to those endpoints, even if the single
    # reference_point tiered bonus would have favored the other one.
    request = build_request(city="seoul")
    nearby = build_accommodation(id="nearby", city="seoul", latitude=37.5680, longitude=126.9790)
    far = build_accommodation(id="far", city="seoul", latitude=37.9000, longitude=127.3000)
    day_endpoints = [(37.9000, 127.3000)]  # right on top of "far"

    without_day_endpoints = select_accommodation_recommendation(
        [nearby, far], request, SEOUL_REFERENCE_POINT
    )
    with_day_endpoints = select_accommodation_recommendation(
        [nearby, far], request, SEOUL_REFERENCE_POINT, day_endpoints
    )

    assert without_day_endpoints.id == "nearby"
    assert with_day_endpoints.id == "far"


def test_seoul_accommodation_distance_score_is_unrounded() -> None:
    from app.domains.rule_planner.services.policies.city.seoul import accommodation_distance_score

    # 1/3 km average * -4.0/km = -1.33333...; round()ing this (as jeju does)
    # would collapse many distinct distances onto the same few integers,
    # which is what caused seoul's measured 49% top1/top2 tie rate before
    # this hook existed - see local_only/reports/headroom_and_variants_analysis.md.
    score = accommodation_distance_score([1 / 3])
    assert score == pytest.approx(-4 / 3)
    assert score != round(score)


def test_seoul_accommodation_distance_score_empty_endpoints_is_zero() -> None:
    from app.domains.rule_planner.services.policies.city.seoul import accommodation_distance_score

    assert accommodation_distance_score([]) == 0.0


def test_busan_accommodation_distance_score_matches_seoul_coefficient_and_shape() -> None:
    from app.domains.rule_planner.services.policies.city.busan import accommodation_distance_score as busan_score
    from app.domains.rule_planner.services.policies.city.seoul import accommodation_distance_score as seoul_score

    assert busan_score([2.0, 4.0]) == seoul_score([2.0, 4.0]) == -12.0
    assert busan_score([]) == 0.0


def test_select_accommodation_for_busan_uses_day_endpoints_instead_of_reference_point() -> None:
    request = build_request(city="busan")
    nearby = build_accommodation(id="nearby", city="busan", latitude=35.1595, longitude=129.1605)
    far = build_accommodation(id="far", city="busan", latitude=35.5000, longitude=129.5000)
    reference_point = (35.1595, 129.1605)  # right on top of "nearby"
    day_endpoints = [(35.5000, 129.5000)]  # right on top of "far"

    without_day_endpoints = select_accommodation_recommendation([nearby, far], request, reference_point)
    with_day_endpoints = select_accommodation_recommendation([nearby, far], request, reference_point, day_endpoints)

    assert without_day_endpoints.id == "nearby"
    assert with_day_endpoints.id == "far"


def test_jeju_accommodation_distance_score_is_unrounded() -> None:
    # jeju used to round() this score (-0.6/km), which measurably collapsed
    # distinct candidates onto the same few integers - 22.9~30% of requests
    # landed in an exact top1/top2 tie (local_only/reports/
    # accommodation_concentration_causes.md), each one then decided by
    # catalog file order alone (see the explicit tie-break test below).
    # ACCOMMODATION_DISTANCE_PENALTY_PER_KM itself stays -0.6, unchanged.
    from app.domains.rule_planner.services.policies.city.jeju import (
        ACCOMMODATION_DISTANCE_PENALTY_PER_KM,
        accommodation_distance_score as jeju_score,
    )

    assert ACCOMMODATION_DISTANCE_PENALTY_PER_KM == -0.6
    score = jeju_score([1 / 3])
    assert score == pytest.approx(1 / 3 * -0.6)
    assert score != round(score)


def test_jeju_accommodation_distance_score_empty_endpoints_is_zero() -> None:
    from app.domains.rule_planner.services.policies.city.jeju import accommodation_distance_score as jeju_score

    assert jeju_score([]) == 0.0


def test_generate_recommends_different_accommodation_for_different_budget_and_companion() -> None:
    service = RuleItineraryService()
    low_solo_response = service.generate(
        RuleItineraryRequest(
            city="seoul", concepts=["culture", "food"], nights=2, days=3, budget_band="low", companion_type="solo"
        )
    )
    high_family_response = service.generate(
        RuleItineraryRequest(
            city="seoul", concepts=["culture", "food"], nights=2, days=3, budget_band="high", companion_type="family"
        )
    )

    assert low_solo_response.accommodation_recommendation is not None
    assert high_family_response.accommodation_recommendation is not None
    assert low_solo_response.accommodation_recommendation.id != high_family_response.accommodation_recommendation.id
