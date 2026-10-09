from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.services.breakfast import BREAKFAST_EXCLUDED_PLACE_IDS, is_breakfast_candidate
from app.domains.rule_planner.services.service import RuleItineraryService


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Restaurant",
        "activity_type": ["미식"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["evening"],
        "area": "city-center",
        "duration_hours": 1,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "평점 정보만 확인되어 상세 근거는 약함",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def test_market_named_place_is_a_breakfast_candidate() -> None:
    place = build_place(name="망원시장", summary="Neighborhood market for budget-friendly food.")
    assert is_breakfast_candidate(place) is True


def test_market_mentioned_only_as_a_nearby_landmark_is_not_a_candidate() -> None:
    # "동문시장 인근" (near Dongmun Market) describes the restaurant's
    # location, not that the restaurant itself is a market - this is the
    # exact false-positive pattern found in the jeju catalog.
    place = build_place(name="사랑분식", summary="동문시장 인근")
    assert is_breakfast_candidate(place) is False


def test_cafe_in_name_is_a_candidate() -> None:
    place = build_place(name="카페시나몬", summary="석촌호수로 소재")
    assert is_breakfast_candidate(place) is True


def test_brunch_mentioned_only_in_summary_is_still_a_candidate() -> None:
    # 채도 (busan) - the brunch signal only appears in the summary, not
    # the name, unlike the market keyword which is name-only.
    place = build_place(name="채도", summary="남포동 2층 소재 브런치 전문점")
    assert is_breakfast_candidate(place) is True


def test_bakery_keyword_is_a_candidate() -> None:
    place = build_place(name="니커버커베이글", summary="40년 경력 장인 베이커리")
    assert is_breakfast_candidate(place) is True


def test_highlight_tags_and_mood_keywords_are_also_checked() -> None:
    place = build_place(
        name="델문도 김녕",
        summary="Scenic rest stop on the east coast.",
        highlight_tags=["동제주 카페 카드", "오션뷰 휴식"],
        mood_keywords=["여유로운"],
    )
    assert is_breakfast_candidate(place) is True


def test_ordinary_dinner_restaurant_is_not_a_candidate() -> None:
    place = build_place(name="장충동왕족발", summary="족발 전문점, 평점 매우 높음")
    assert is_breakfast_candidate(place) is False


# --- explicit exclusions (district/street/beach places, not restaurants) ---


def test_excluded_ids_are_rejected_even_with_matching_keywords() -> None:
    for excluded_id in BREAKFAST_EXCLUDED_PLACE_IDS:
        place = build_place(
            id=excluded_id,
            name="아무 카페",
            summary="브런치와 조식을 즐기기 좋은 카페거리",
            highlight_tags=["카페"],
            mood_keywords=["모닝"],
        )
        assert is_breakfast_candidate(place) is False, excluded_id


def test_same_keywords_outside_the_excluded_ids_still_match() -> None:
    # Proves the exclusion is id-based, not a change to the keyword rule
    # itself - identical content under a different id is still a candidate.
    place = build_place(
        id="not-excluded",
        name="아무 카페",
        summary="브런치와 조식을 즐기기 좋은 카페거리",
        highlight_tags=["카페"],
        mood_keywords=["모닝"],
    )
    assert is_breakfast_candidate(place) is True


# --- real-catalog candidate counts after the exclusion ----------------------


def test_real_catalog_candidate_counts_after_exclusion() -> None:
    provider = RuleItineraryService().catalog_provider
    expected_counts = {"seoul": 6, "busan": 5, "jeju": 3}

    for city, expected_count in expected_counts.items():
        catalog = provider.get_city_catalog(continent="asia", country="korea", city=city, visible_only=True)
        food_places = [place for place in catalog.places if "food" in place.concept_tags]
        candidates = [place for place in food_places if is_breakfast_candidate(place)]

        assert len(candidates) == expected_count, (city, [place.id for place in candidates])
        assert BREAKFAST_EXCLUDED_PLACE_IDS.isdisjoint({place.id for place in candidates})
