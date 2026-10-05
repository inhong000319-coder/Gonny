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
    ACCOMMODATION_TYPE_MATCH_BONUS,
    PRICE_EXACT_MATCH_BONUS,
    PRICE_FAR_PENALTY,
    accommodation_score,
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


# (a) accommodation_types preference bonus


def test_selected_type_matching_stay_gets_type_bonus() -> None:
    hotel = build_accommodation(accommodation_type="호텔")
    unselected = accommodation_score(hotel, build_request(), None)

    selected = accommodation_score(hotel, build_request(accommodation_types=["호텔"]), None)

    assert selected == unselected + ACCOMMODATION_TYPE_MATCH_BONUS


def test_selected_type_non_matching_stay_gets_no_change_and_no_penalty() -> None:
    motel = build_accommodation(accommodation_type="모텔")
    unselected = accommodation_score(motel, build_request(), None)

    selected = accommodation_score(motel, build_request(accommodation_types=["호텔"]), None)

    assert selected == unselected


def test_empty_type_selection_matches_baseline_score_exactly() -> None:
    stay = build_accommodation(accommodation_type="펜션·민박", average_price_krw=109000)
    baseline = accommodation_score(stay, build_request(), None)

    assert accommodation_score(stay, build_request(accommodation_types=[]), None) == baseline


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

    assert seoul.accommodation_type_counts == {"호텔": 8, "모텔": 3, "호스텔": 3, "펜션·민박": 1}
