"""PR-A2: "다른 추천"(rank_slot_candidates) 순위에서 alternate 등급 장소에
소폭 감점(ALTERNATE_RANK_PENALTY)을 줘서 메인 후보가 있으면 먼저 나오고,
메인이 부족하거나 점수 차이가 작을 때만 alternate가 섞이게 하는 변경의
테스트. slot_score/메인 선택/우천 대체 후보 순위는 바뀌지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import ALTERNATE_TIER, CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, NormalizedRuleRequest, RuleItineraryRequest
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.slot_alternatives import ALTERNATE_RANK_PENALTY, rank_slot_candidates
from app.domains.rule_planner.services.weather_alerts import build_weather_report


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


def _rank(scored_places_by_id, request, *, alternate_rank_penalty: int = 0, limit: int = 3):
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
        alternate_rank_penalty=alternate_rank_penalty,
        limit=limit,
    )


# --- rank_slot_candidates: alternate_rank_penalty ---------------------------


def test_main_ranked_before_alternate_when_scores_tie():
    # 완전히 같은 태그(동점) - alternate의 id가 알파벳상 앞이라 감점이
    # 없으면(기존 id 동점 처리) alternate가 먼저 나왔을 것.
    main_place = _place("zzz-main", mvp_tier="standard")
    alt_place = _place("aaa-alt", mvp_tier=ALTERNATE_TIER)
    request = _normalized_request()

    without_penalty = _rank({main_place.id: main_place, alt_place.id: alt_place}, request, alternate_rank_penalty=0)
    assert [alt.place_id for alt in without_penalty] == ["aaa-alt", "zzz-main"]

    with_penalty = _rank(
        {main_place.id: main_place, alt_place.id: alt_place}, request, alternate_rank_penalty=ALTERNATE_RANK_PENALTY
    )
    assert [alt.place_id for alt in with_penalty] == ["zzz-main", "aaa-alt"]


def test_alternate_fills_remaining_slots_when_main_candidates_are_scarce():
    main_place = _place("only-main", mvp_tier="standard")
    alt_a = _place("alt-a", mvp_tier=ALTERNATE_TIER)
    alt_b = _place("alt-b", mvp_tier=ALTERNATE_TIER)
    request = _normalized_request()

    result = _rank(
        {main_place.id: main_place, alt_a.id: alt_a, alt_b.id: alt_b},
        request,
        alternate_rank_penalty=ALTERNATE_RANK_PENALTY,
        limit=3,
    )

    assert len(result) == 3
    assert result[0].place_id == "only-main"
    assert {result[1].place_id, result[2].place_id} == {"alt-a", "alt-b"}


def test_alternate_still_outranks_main_when_score_gap_exceeds_penalty():
    # slot_bias로 24점(8 * 3, slot_bias_score의 최대 가중치) 차이를 내서
    # ALTERNATE_RANK_PENALTY(15)를 넘게 만든다 - 감점은 절대 배제가 아니다.
    main_place = _place("weak-main", mvp_tier="standard")
    strong_alt = _place("strong-alt", mvp_tier=ALTERNATE_TIER, slot_bias={"morning": 8})
    request = _normalized_request()

    result = _rank(
        {main_place.id: main_place, strong_alt.id: strong_alt},
        request,
        alternate_rank_penalty=ALTERNATE_RANK_PENALTY,
    )

    assert [alt.place_id for alt in result] == ["strong-alt", "weak-main"]


def test_alternate_rank_penalty_default_zero_matches_passing_zero_explicitly():
    main_place = _place("zzz-main", mvp_tier="standard")
    alt_place = _place("aaa-alt", mvp_tier=ALTERNATE_TIER)
    request = _normalized_request()

    explicit_zero = _rank({main_place.id: main_place, alt_place.id: alt_place}, request, alternate_rank_penalty=0)
    default_omitted = rank_slot_candidates(
        scored_places_by_id={main_place.id: main_place, alt_place.id: alt_place},
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
    )

    assert [a.place_id for a in explicit_zero] == [a.place_id for a in default_omitted] == ["aaa-alt", "zzz-main"]


def test_rank_slot_candidates_exposed_fields_unaffected_by_penalty():
    # 감점은 정렬 키에만 적용되고 slot_score 자체나 노출 필드는 바뀌지
    # 않아야 한다 - 같은 장소에 대해 감점 적용 전/후 RuleSlotAlternative의
    # 나머지 필드(이 fixture에서 바뀔 수 있는 건 순서뿐)는 동일하다.
    main_place = _place("weak-main", mvp_tier="standard", booking="required")
    strong_alt = _place("strong-alt", mvp_tier=ALTERNATE_TIER, slot_bias={"morning": 8}, booking="recommended")
    request = _normalized_request()

    without_penalty = {
        a.place_id: a for a in _rank({main_place.id: main_place, strong_alt.id: strong_alt}, request)
    }
    with_penalty = {
        a.place_id: a
        for a in _rank(
            {main_place.id: main_place, strong_alt.id: strong_alt},
            request,
            alternate_rank_penalty=ALTERNATE_RANK_PENALTY,
        )
    }

    for place_id in ("weak-main", "strong-alt"):
        assert without_penalty[place_id].booking == with_penalty[place_id].booking
        assert without_penalty[place_id].average_cost_krw == with_penalty[place_id].average_cost_krw


# --- weather_alerts.py's indoor swap path is unaffected ---------------------


class _FakeCatalogProvider(PlaceCatalogProvider):
    """city="seoul" - WEATHER_QUERY_CITY_BY_CODE only has forecast lookups
    for seoul/busan/jeju (see weather_alerts.py), so a weather-path test
    needs one of those, unlike the other (weather-free) tests in this
    file which use a neutral "testcity"."""

    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(
            continent="asia", country="korea", city="seoul", default_days=3, places=places
        )

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="seoul", aliases=[])]


class FakeRainWeatherClient:
    def __init__(self, start_date):
        from datetime import timedelta

        self.start_date = start_date
        self._timedelta = timedelta

    def fetch_5day_forecast(self, destination, *, allow_mock_fallback: bool = True):
        return [
            {
                "forecast_date": self.start_date + self._timedelta(days=i),
                "condition": "rain",
                "min_temp_c": 10.0,
                "max_temp_c": 15.0,
                "precipitation_mm": 12.0,
            }
            for i in range(5)
        ]


def test_weather_swap_candidates_never_receive_alternate_rank_penalty():
    from datetime import date

    a_tuesday = date(2026, 9, 15)
    # 카탈로그 순서 + 동점(모든 ML 입력 태그가 같음) 조합으로 실제 배치를
    # 통제한다(test_rule_itinerary_closed_days.py 등과 같은 확립된 패턴):
    # outdoor-rainy, filler-0, filler-1(main 풀, 순서대로) -> 하루 3슬롯을
    # 정확히 채운다. main-indoor/alt-indoor는 둘 다 안 쓰이고 남아
    # outdoor-rainy의 스왑 후보 풀이 된다. alt-indoor는 alternate이고
    # theme_tags가 안 맞아 main 풀에는 처음부터 없다(PR-A의
    # is_main_pool_member).
    outdoor_rainy = _place("outdoor-rainy", setting="outdoor")
    filler_places = [_place("filler-0"), _place("filler-1")]
    main_indoor = _place("zzz-main-indoor", mvp_tier="standard", setting="indoor")
    alt_indoor = _place("aaa-alt-indoor", mvp_tier=ALTERNATE_TIER, setting="indoor", theme_tags=[])

    places = [outdoor_rainy, *filler_places, main_indoor, alt_indoor]
    request = RuleItineraryRequest.model_validate(
        {
            "continent": "asia",
            "country": "korea",
            "city": "seoul",
            "nights": 1,
            "days": 1,
            "budget_band": "medium",
            "concepts": ["culture"],
            "style": "easy",
            "companion_type": "friend",
            "start_date": a_tuesday,
        }
    )
    service = RuleItineraryService(
        catalog_provider=_FakeCatalogProvider(places),
        weather_client=FakeRainWeatherClient(start_date=a_tuesday),
    )

    response = service.generate(request)

    used_ids = {item.place_id for item in response.items}
    assert used_ids == {"outdoor-rainy", "filler-0", "filler-1"}

    affected_items = [item for alert in response.weather_alerts for item in alert.affected_items]
    assert affected_items, "outdoor-rainy should be placed and flagged as rain-affected"
    outdoor_item = next(item for item in affected_items if item.place_id == "outdoor-rainy")
    swap_ids = [c.place_id for c in outdoor_item.swap_candidates]
    assert set(swap_ids) == {"zzz-main-indoor", "aaa-alt-indoor"}
    # 우천 대체 경로는 alternate_rank_penalty=0 그대로 - 기존 id 동점
    # 처리(알파벳상 앞인 alt가 먼저)가 유지된다. 감점이 적용됐다면
    # zzz-main-indoor가 먼저였을 것.
    assert swap_ids == ["aaa-alt-indoor", "zzz-main-indoor"]


# --- compute_item_alternatives wires ALTERNATE_RANK_PENALTY by default ------


def test_generate_item_alternatives_prefer_main_over_tied_alternate():
    # filler-0,1,2가 main 풀에서 순서대로 3슬롯을 다 채우고, zzz-main과
    # aaa-alt(둘 다 동점, theme_tags 불일치로 alt는 main 풀에 없음)는 안
    # 쓰인 채 남아 모든 슬롯의 "다른 추천" 후보가 된다 - 감점이
    # compute_item_alternatives 경로에 기본 적용되므로 메인이 항상 먼저다.
    main_place = _place("zzz-main", mvp_tier="standard")
    alt_place = _place("aaa-alt", mvp_tier=ALTERNATE_TIER, theme_tags=[])
    filler_places = [_place(f"filler-{i}") for i in range(3)]
    places = filler_places + [main_place, alt_place]

    request = RuleItineraryRequest.model_validate(
        {
            "continent": "asia",
            "country": "korea",
            "city": "testcity",
            "nights": 1,
            "days": 1,
            "budget_band": "medium",
            "concepts": ["culture"],
            "style": "easy",
            "companion_type": "friend",
        }
    )
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))

    response = service.generate(request)

    used_ids = {item.place_id for item in response.items}
    assert used_ids == {"filler-0", "filler-1", "filler-2"}
    assert len(response.items) == 3
    for item in response.items:
        assert [a.place_id for a in item.alternatives] == ["zzz-main", "aaa-alt"]
