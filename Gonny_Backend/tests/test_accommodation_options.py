from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from pydantic import ValidationError

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleItineraryRequest
from app.domains.rule_planner.services.accommodation_scoring import (
    PRICE_EXACT_MATCH_BONUS,
    PRICE_FAR_PENALTY,
    accommodation_score,
    select_accommodation_recommendation,
)
from app.domains.rule_planner.services.request_normalizer import normalize_rule_request
from app.domains.rule_planner.services.service import RuleItineraryService


def build_accommodation(**overrides) -> AccommodationData:
    data = {
        "id": "sample-hotel",
        "name": "Sample Hotel",
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


# Accommodation type selection narrows the candidate pool


def test_selected_type_is_recommended_even_when_another_type_scores_higher() -> None:
    request = build_request(accommodation_types=["펜션·민박"])
    higher_scoring_hotel = build_accommodation(id="hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"])
    selected_pension = build_accommodation(id="pension", accommodation_type="펜션·민박", budget_level=["low"], suitable_for=["solo"])
    candidates = [higher_scoring_hotel, selected_pension]

    assert accommodation_score(higher_scoring_hotel, build_request(), None) > accommodation_score(selected_pension, build_request(), None)
    assert select_accommodation_recommendation(candidates, request, None).id == "pension"


def test_multiple_selected_types_choose_best_among_them() -> None:
    request = build_request(accommodation_types=["호텔", "모텔"])
    hostel_best_overall = build_accommodation(id="hostel", accommodation_type="호스텔", budget_level=["high"], suitable_for=["couple"])
    hotel = build_accommodation(id="hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"])
    motel = build_accommodation(id="motel", accommodation_type="모텔", budget_level=["low"], suitable_for=["solo"])

    selected = select_accommodation_recommendation([hostel_best_overall, hotel, motel], request, None)

    assert selected.id == "hotel"


def test_selected_type_missing_from_pool_falls_back_to_full_pool() -> None:
    request = build_request(accommodation_types=["호스텔"])
    hotel = build_accommodation(id="hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"])
    motel = build_accommodation(id="motel", accommodation_type="모텔", budget_level=["low"], suitable_for=["solo"])

    selected = select_accommodation_recommendation([hotel, motel], request, None)

    assert selected is not None
    assert selected.id == select_accommodation_recommendation([hotel, motel], build_request(), None).id


def test_no_selected_types_gives_same_recommendation_as_before() -> None:
    hotel = build_accommodation(id="hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"])
    motel = build_accommodation(id="motel", accommodation_type="모텔", budget_level=["low"], suitable_for=["solo"])
    candidates = [hotel, motel]

    assert select_accommodation_recommendation(candidates, build_request(accommodation_types=[]), None).id == "hotel"
    assert select_accommodation_recommendation(candidates, build_request(), None).id == "hotel"
    assert accommodation_score(motel, build_request(accommodation_types=["모텔"]), None) == accommodation_score(
        motel, build_request(), None
    )


def test_coordinate_preference_still_applies_with_type_filter() -> None:
    request = build_request(accommodation_types=["모텔"])
    coordinate_hotel = build_accommodation(
        id="coord-hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"],
        latitude=37.5665, longitude=126.9780,
    )
    no_coordinate_motel = build_accommodation(
        id="no-coord-motel", accommodation_type="모텔", budget_level=["medium"], suitable_for=["couple"],
        latitude=None, longitude=None,
    )

    selected = select_accommodation_recommendation([coordinate_hotel, no_coordinate_motel], request, None)

    assert selected.id == "coord-hotel"


def test_type_filter_applies_inside_coordinate_pool() -> None:
    request = build_request(accommodation_types=["모텔"])
    coordinate_hotel = build_accommodation(
        id="coord-hotel", accommodation_type="호텔", budget_level=["medium"], suitable_for=["couple"],
        latitude=37.5665, longitude=126.9780,
    )
    coordinate_motel = build_accommodation(
        id="coord-motel", accommodation_type="모텔", budget_level=["low"], suitable_for=["solo"],
        latitude=37.5670, longitude=126.9790,
    )

    selected = select_accommodation_recommendation([coordinate_hotel, coordinate_motel], request, None)

    assert selected.id == "coord-motel"


# (b) lodging budget vs activity budget


def test_accommodation_budget_band_drives_price_comparison_not_activity_band() -> None:
    cheap_stay = build_accommodation(average_price_krw=40000)
    request = build_request(budget_band="high", accommodation_budget_band="low")

    score = accommodation_score(cheap_stay, request, None)

    # Companion term is +5 (couple matches). Budget term should be exact-band.
    assert score == PRICE_EXACT_MATCH_BONUS + 5
    assert accommodation_score(cheap_stay, build_request(budget_band="high"), None) == PRICE_FAR_PENALTY + 5


def test_normalizing_keeps_activity_budget_band_when_lodging_budget_differs() -> None:
    request = RuleItineraryRequest(city="seoul", budget_band="medium", accommodation_budget_band="low")

    normalized = normalize_rule_request(request)

    assert normalized.budget_band == "medium"
    assert normalized.accommodation_budget_band == "low"


def test_missing_lodging_budget_falls_back_to_activity_budget() -> None:
    request = RuleItineraryRequest(city="seoul", budget_band="high")

    normalized = normalize_rule_request(request)

    assert normalized.accommodation_budget_band == "high"
    assert normalized.budget_band == "high"


def test_normalizer_deduplicates_accommodation_types_and_defaults_to_empty() -> None:
    with_types = normalize_rule_request(
        RuleItineraryRequest(city="seoul", accommodation_types=["호텔", "호텔", "모텔"])
    )
    without_types = normalize_rule_request(RuleItineraryRequest(city="seoul"))

    assert with_types.accommodation_types == ["호텔", "모텔"]
    assert without_types.accommodation_types == []


# (c) unknown accommodation type values are rejected at request validation


def test_unknown_accommodation_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RuleItineraryRequest(city="seoul", accommodation_types=["캠핑"])


# (d) catalog options carry per-city accommodation type counts


def test_catalog_options_include_accommodation_type_counts_for_seoul() -> None:
    options = RuleItineraryService().list_catalog_options()
    seoul = next(option for option in options if option.city == "seoul")

    assert seoul.accommodation_type_counts == {"호텔": 11, "호스텔": 3, "펜션·민박": 1}
