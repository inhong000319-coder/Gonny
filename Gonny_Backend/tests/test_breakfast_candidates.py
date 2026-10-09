from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.services.breakfast import is_breakfast_candidate


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
