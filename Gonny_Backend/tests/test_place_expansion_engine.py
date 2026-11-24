"""PR-A: 부산 장소 확장(대안 전용 장소 + 기본 추천 장소)을 받을 수 있도록
엔진·스키마를 바꾼 변경의 테스트.

destinations/*.json은 전혀 건드리지 않으므로, 모든 시나리오는 임시
PlaceData/CityPlaceCatalog(가짜 카탈로그)로 구성한다 - 기존
test_rule_itinerary_closed_days.py/test_slot_alternatives.py/
test_weather_alert_swap.py와 같은 패턴.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import HTTPException

from app.domains.destination_catalog.schemas import ALTERNATE_TIER, CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.destination_catalog.services.repository import DestinationCatalogRepository
from app.domains.rule_planner.schemas import (
    CatalogCityOption,
    NormalizedRuleRequest,
    RuleFixedSlotAssignment,
    RuleItineraryRequest,
)
from app.domains.rule_planner.services.constants import CONCEPT_LABEL_KO
from app.domains.rule_planner.services.fitness_model import get_fitness_scorer
from app.domains.rule_planner.services.place_pool import (
    is_in_season,
    is_main_pool_member,
    theme_tags_for_request,
)
from app.domains.rule_planner.services.recalculate import build_fixed_slots_lookup
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.slot_alternatives import rank_slot_candidates
from app.domains.rule_planner.services.slot_scoring import THEME_MATCH_BONUS, slot_score

A_JULY_DAY = date(2026, 7, 1)
A_DECEMBER_DAY = date(2026, 12, 1)


def _place(place_id: str, *, priority: int = 5, **overrides) -> PlaceData:
    data = {
        "id": place_id,
        "name": place_id,
        "activity_type": ["문화·역사"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "test-area",
        "duration_hours": 2,
        "priority": priority,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": f"{place_id} summary",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def _normalized_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "testcity",
        "travelers": 2,
        "nights": 1,
        "days": 1,
        "budget_band": "medium",
        "concepts": ["culture"],
        "style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


class _FakeCatalogProvider(PlaceCatalogProvider):
    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(
            continent="asia", country="korea", city="testcity", default_days=3, places=places
        )

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="testcity", aliases=[])]


def _generate(places: list[PlaceData], request: RuleItineraryRequest, **kwargs):
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))
    return service.generate(request, **kwargs)


def _build_request(*, start_date: date | None, days: int = 1, nights: int = 1, concepts=None, **overrides):
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "testcity",
        "nights": nights,
        "days": days,
        "budget_band": "medium",
        "concepts": concepts or ["culture"],
        "style": "easy",
        "companion_type": "friend",
        "start_date": start_date,
    }
    data.update(overrides)
    return RuleItineraryRequest.model_validate(data)


# --- PlaceData schema: new optional fields ----------------------------------


def test_place_data_new_fields_default_to_empty_or_none():
    place = _place("plain")
    assert place.season_months == []
    assert place.booking is None
    assert place.theme_tags == []


def test_season_months_validator_dedupes_and_sorts():
    place = _place("seasonal", season_months=[8, 6, 8, 7])
    assert place.season_months == [6, 7, 8]


@pytest.mark.parametrize("bad_month", [0, 13, -1])
def test_season_months_validator_rejects_out_of_range(bad_month):
    with pytest.raises(ValueError):
        _place("bad-season", season_months=[bad_month])


def test_create_place_request_accepts_new_fields():
    from app.domains.destination_catalog.schemas import CreatePlaceRequest

    request = CreatePlaceRequest.model_validate(
        {
            "id": "new-place",
            "name": "새 장소",
            "activity_type": ["문화·역사"],
            "budget_level": ["medium"],
            "suitable_for": ["couple"],
            "time_fit": ["morning"],
            "area": "test-area",
            "duration_hours": 2,
            "priority": 5,
            "pace": ["easy"],
            "mobility": ["walkable"],
            "summary": "test",
            "season_months": [6, 7, 8],
            "booking": "required",
            "theme_tags": ["walk"],
        }
    )
    assert request.season_months == [6, 7, 8]
    assert request.booking == "required"
    assert request.theme_tags == ["walk"]


def test_existing_real_catalog_json_loads_with_new_fields_defaulted():
    from app.domains.destination_catalog.services.provider import LocalJsonPlaceCatalogProvider

    provider = LocalJsonPlaceCatalogProvider()
    for city in ["seoul", "busan", "jeju"]:
        catalog = provider.get_city_catalog(continent=None, country=None, city=city, visible_only=True)
        for place in catalog.places:
            assert place.season_months == []
            assert place.booking is None
            assert place.theme_tags == []


# --- place_pool.py pure functions -------------------------------------------


def test_is_in_season_true_when_no_season_months_restriction():
    place = _place("any", season_months=[])
    assert is_in_season(place, A_DECEMBER_DAY) is True


def test_is_in_season_true_when_day_date_unknown():
    place = _place("seasonal", season_months=[6, 7, 8])
    assert is_in_season(place, None) is True


def test_is_in_season_matches_and_rejects_by_month():
    place = _place("seasonal", season_months=[6, 7, 8, 9])
    assert is_in_season(place, A_JULY_DAY) is True
    assert is_in_season(place, A_DECEMBER_DAY) is False


def test_theme_tags_for_request_maps_only_walk_and_sports():
    request = _normalized_request(concepts=["walk", "sports", "food"])
    assert theme_tags_for_request(request) == {"walk", "sports"}


def test_theme_tags_for_request_empty_when_no_matching_concepts():
    request = _normalized_request(concepts=["food", "culture"])
    assert theme_tags_for_request(request) == set()


def test_is_main_pool_member_true_for_standard_tier_regardless_of_theme_tags():
    place = _place("standard", mvp_tier="standard", theme_tags=[])
    request = _normalized_request(concepts=["food"])
    assert is_main_pool_member(place, request) is True


def test_is_main_pool_member_false_for_alternate_without_matching_theme_tag():
    place = _place("alt", mvp_tier=ALTERNATE_TIER, theme_tags=["sports"])
    request = _normalized_request(concepts=["food", "culture"])
    assert is_main_pool_member(place, request) is False


def test_is_main_pool_member_true_for_alternate_with_matching_theme_tag():
    place = _place("alt", mvp_tier=ALTERNATE_TIER, theme_tags=["walk"])
    request = _normalized_request(concepts=["walk"])
    assert is_main_pool_member(place, request) is True


# --- slot_scoring.py: THEME_MATCH_BONUS -------------------------------------


def test_slot_score_adds_theme_match_bonus_only_when_tags_overlap():
    request = _normalized_request(concepts=["walk"])
    with_tag = _place("with-tag", theme_tags=["walk"])
    without_tag = _place("without-tag", theme_tags=[])

    score_with = slot_score(place=with_tag, request=request, time_slot="morning", day_number=1, preferred_area=None)
    score_without = slot_score(
        place=without_tag, request=request, time_slot="morning", day_number=1, preferred_area=None
    )

    assert score_with - score_without == THEME_MATCH_BONUS


def test_slot_score_no_bonus_when_request_has_no_matching_concept():
    request = _normalized_request(concepts=["food"])
    with_tag = _place("with-tag", theme_tags=["walk"])
    without_tag = _place("without-tag", theme_tags=[])

    score_with = slot_score(place=with_tag, request=request, time_slot="morning", day_number=1, preferred_area=None)
    score_without = slot_score(
        place=without_tag, request=request, time_slot="morning", day_number=1, preferred_area=None
    )

    assert score_with == score_without


# --- main pool membership (engine-level) ------------------------------------


def test_alternate_place_absent_from_items_without_theme_promotion():
    places = [
        _place("alt", mvp_tier=ALTERNATE_TIER, theme_tags=["walk"]),
        _place("filler-a"),
        _place("filler-b"),
        _place("filler-c"),
    ]
    request = _build_request(start_date=None, concepts=["culture"])

    response = _generate(places, request)

    assert "alt" not in {item.place_id for item in response.items}


def test_alternate_place_present_in_items_when_theme_promoted():
    places = [
        # Listed first so stable-sort ties favor it once it passes the
        # main-pool filter (every candidate here shares identical ML
        # input tags, so base_score/slot_score tie - see
        # test_rule_itinerary_closed_days.py's fixtures for the same
        # established pattern).
        _place("alt", mvp_tier=ALTERNATE_TIER, theme_tags=["walk"]),
        _place("filler-a"),
        _place("filler-b"),
        _place("filler-c"),
    ]
    request = _build_request(start_date=None, concepts=["walk"])

    response = _generate(places, request)

    assert "alt" in {item.place_id for item in response.items}


# --- alternate places stay available as alternatives/swap candidates -------


def _rank_slot_candidates_for(scored_places_by_id, request, *, day_date=None):
    return rank_slot_candidates(
        scored_places_by_id=scored_places_by_id,
        exclude_ids=set(),
        request=request,
        time_slot="morning",
        day_number=1,
        day_weekday=None,
        preferred_area=None,
        previous_place=None,
        next_place=None,
        feedback_signals=None,
        localize_place_name=lambda place: place.name,
        localize_area=lambda area: area,
        resolve_item_category=lambda place, req: "sightseeing",
        build_note=lambda **kwargs: "note",
        day_date=day_date,
    )


def test_rank_slot_candidates_includes_alternate_tier_place_without_promotion():
    alt_place = _place("alt", mvp_tier=ALTERNATE_TIER, theme_tags=[], time_fit=["morning"])
    request = _normalized_request(concepts=["culture"])

    alternatives = _rank_slot_candidates_for({alt_place.id: alt_place}, request)

    assert alt_place.id in {alt.place_id for alt in alternatives}


# --- season filter in rank_slot_candidates (alternatives/weather swap) -----


def test_rank_slot_candidates_excludes_out_of_season_place():
    seasonal = _place("seasonal", season_months=[6, 7, 8, 9], time_fit=["morning"])
    request = _normalized_request()

    alternatives = _rank_slot_candidates_for({seasonal.id: seasonal}, request, day_date=A_DECEMBER_DAY)

    assert alternatives == []


def test_rank_slot_candidates_includes_in_season_place():
    seasonal = _place("seasonal", season_months=[6, 7, 8, 9], time_fit=["morning"])
    request = _normalized_request()

    alternatives = _rank_slot_candidates_for({seasonal.id: seasonal}, request, day_date=A_JULY_DAY)

    assert seasonal.id in {alt.place_id for alt in alternatives}


def test_rank_slot_candidates_day_date_none_never_filters_on_season():
    seasonal = _place("seasonal", season_months=[6, 7, 8, 9], time_fit=["morning"])
    request = _normalized_request()

    alternatives = _rank_slot_candidates_for({seasonal.id: seasonal}, request, day_date=None)

    assert seasonal.id in {alt.place_id for alt in alternatives}


# --- season filter in _build_items (engine-level, main items) --------------


def test_season_restricted_place_excluded_from_main_items_outside_season():
    places = [
        _place("summer-only", season_months=[6, 7, 8, 9]),
        _place("filler-a"),
        _place("filler-b"),
        _place("filler-c"),
    ]
    request = _build_request(start_date=A_DECEMBER_DAY)

    response = _generate(places, request)

    assert "summer-only" not in {item.place_id for item in response.items}


def test_season_restricted_place_allowed_in_season():
    places = [
        _place("summer-only", season_months=[6, 7, 8, 9]),
        _place("filler-a"),
        _place("filler-b"),
        _place("filler-c"),
    ]
    request = _build_request(start_date=A_JULY_DAY)

    response = _generate(places, request)

    assert "summer-only" in {item.place_id for item in response.items}


def test_season_filter_disabled_without_start_date():
    places = [
        _place("summer-only", season_months=[6, 7, 8, 9]),
        _place("filler-a"),
        _place("filler-b"),
        _place("filler-c"),
    ]
    request = _build_request(start_date=None)

    response = _generate(places, request)

    assert "summer-only" in {item.place_id for item in response.items}


def test_month_boundary_is_evaluated_per_calendar_day():
    # 8/30 시작 5일 - 날짜별로 월이 바뀌는 경계에서 is_in_season이 날짜
    # 단위로 정확히 판단하는지(요청 전체가 아니라 day_number마다 다시
    # 계산되는지) 확인한다.
    place = _place("august-only", season_months=[8])
    assert is_in_season(place, date(2026, 8, 30)) is True
    assert is_in_season(place, date(2026, 8, 31)) is True
    assert is_in_season(place, date(2026, 9, 1)) is False
    assert is_in_season(place, date(2026, 9, 2)) is False
    assert is_in_season(place, date(2026, 9, 3)) is False


# --- fixed_slots validation allows pinning an alternate place --------------


def test_build_fixed_slots_lookup_allows_alternate_place():
    # 모든 허용 슬롯을 지정해야 하므로(부분 고정 불가) 같은 alt 장소를
    # 하루 전체(종일) 패턴으로 3슬롯 모두에 지정한다 - 검증 목적은
    # mvp_tier="alternate"가 거부되지 않는지 확인하는 것뿐이다.
    place = _place("alt", mvp_tier=ALTERNATE_TIER, theme_tags=[])
    catalog = CityPlaceCatalog(continent="asia", country="korea", city="testcity", places=[place])
    request = _normalized_request(days=1)

    resolved = build_fixed_slots_lookup(
        fixed_slots=[
            RuleFixedSlotAssignment(day_number=1, time_slot="morning", place_id="alt"),
            RuleFixedSlotAssignment(day_number=1, time_slot="afternoon", place_id="alt"),
            RuleFixedSlotAssignment(day_number=1, time_slot="evening", place_id="alt"),
        ],
        request=request,
        city_catalog=catalog,
    )

    assert resolved[(1, "morning")].id == "alt"


# --- ML model: new concepts never raise -------------------------------------


def test_fitness_scorer_predict_handles_new_concepts_without_exception():
    place = _place("plain")
    for concepts in (["walk"], ["sports"], ["walk", "sports", "food"]):
        request = _normalized_request(concepts=concepts)
        score = get_fitness_scorer().predict(place, request)
        assert isinstance(score, float)


def test_rule_itinerary_request_accepts_walk_and_sports_concepts():
    request = RuleItineraryRequest.model_validate(
        {
            "city": "busan",
            "nights": 1,
            "days": 1,
            "concepts": ["walk", "sports"],
            "budget_band": "medium",
            "style": "easy",
            "companion_type": "friend",
        }
    )
    assert request.concepts == ["walk", "sports"]


def test_concept_label_ko_has_walk_and_sports():
    assert CONCEPT_LABEL_KO["walk"] == "걷기·산책"
    assert CONCEPT_LABEL_KO["sports"] == "레저·스포츠"


# --- booking field flows through to items/alternatives ----------------------


def test_booking_field_populated_on_item_when_place_has_it():
    places = [
        _place("booked-place", booking="required"),
        _place("filler-a"),
        _place("filler-b"),
    ]
    request = _build_request(start_date=None)

    response = _generate(places, request)

    booked_item = next(item for item in response.items if item.place_id == "booked-place")
    assert booked_item.booking == "required"
    other_items = [item for item in response.items if item.place_id != "booked-place"]
    assert all(item.booking is None for item in other_items)


def test_booking_field_defaults_to_none_for_existing_places_without_it():
    places = [_place("plain-a"), _place("plain-b"), _place("plain-c")]
    request = _build_request(start_date=None)

    response = _generate(places, request)

    assert all(item.booking is None for item in response.items)


# --- recommended_max_days excludes alternate-tier places --------------------


def _write_catalog_json(tmp_path: Path, *, standard_count: int, alternate_count: int) -> None:
    places = [_place(f"standard-{i}") for i in range(standard_count)]
    places += [_place(f"alt-{i}", mvp_tier=ALTERNATE_TIER) for i in range(alternate_count)]
    catalog = CityPlaceCatalog(continent="asia", country="korea", city="testcity", places=places)
    (tmp_path / "testcity.json").write_text(
        json.dumps(catalog.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )


def test_recommended_max_days_excludes_alternate_tier_places(tmp_path):
    _write_catalog_json(tmp_path, standard_count=7, alternate_count=3)
    repo = DestinationCatalogRepository(data_dir=tmp_path)

    options = repo.list_city_options()

    assert len(options) == 1
    # 7개 standard만 센다: 7 // 3 == 2. alternate 3곳을 포함했다면 10 // 3 == 3이 됐을 것.
    assert options[0].recommended_max_days == 2


def test_recommended_max_days_unchanged_when_no_alternate_places(tmp_path):
    _write_catalog_json(tmp_path, standard_count=9, alternate_count=0)
    repo = DestinationCatalogRepository(data_dir=tmp_path)

    options = repo.list_city_options()

    assert options[0].recommended_max_days == 3
