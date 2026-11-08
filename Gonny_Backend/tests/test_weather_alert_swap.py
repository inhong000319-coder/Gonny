from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.closed_days import is_confirmed_closed_on
from app.domains.rule_planner.services.service import RuleItineraryService
from app.domains.rule_planner.services.weather_alerts import build_weather_alerts

# 2026-09-15 is a Tuesday (weekday() == 1) - matches tests/test_slot_alternatives.py.
A_TUESDAY = date(2026, 9, 15)


class FakeRainWeatherClient:
    """Forces a run of moderate rain (12mm/3h -> 4mm/h, at/above the
    3mm/h "보통 비" threshold) starting at start_date, for every city -
    no real network access."""

    def __init__(self, start_date: date, days: int = 5, precipitation_mm: float = 12.0):
        self.start_date = start_date
        self.days = days
        self.precipitation_mm = precipitation_mm

    def fetch_5day_forecast(self, destination, *, allow_mock_fallback: bool = True):
        return [
            {
                "forecast_date": self.start_date + timedelta(days=i),
                "condition": "rain",
                "min_temp_c": 10.0,
                "max_temp_c": 15.0,
                "precipitation_mm": self.precipitation_mm,
            }
            for i in range(self.days)
        ]


def _place(place_id: str, *, priority: int, **overrides) -> PlaceData:
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
        "average_cost_krw": 1000 * priority,
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog - same pattern as
    test_slot_alternatives.py's fake provider."""

    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(
            continent="asia", country="korea", city="seoul", default_days=3, places=places
        )

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="seoul", aliases=[])]


def _filler_places(count: int = 8) -> list[PlaceData]:
    # setting이 None(실외도 실내도 아님)이라 swap_candidates의 "실내만"
    # 조건에 절대 걸리지 않는 배경 채움 장소들 - 슬롯을 메우되 스왑 후보
    # 풀을 어지럽히지 않는다. priority를 fixture의 다른 장소들보다 낮게
    # 둬서 진짜 슬롯 경쟁에서 밀리게 한다.
    return [_place(f"filler-{i}", priority=5) for i in range(count)]


def _weather_rule_set_catalog() -> list[PlaceData]:
    return _filler_places(8) + [
        _place("outdoor-rainy", priority=9, setting="outdoor"),
        # 일정에 먼저 배치돼(all_used_ids) 스왑 후보 풀에서 빠져야 하는
        # 실내 장소 - 진짜 슬롯 하나를 확실히 차지하도록 가장 높은
        # priority를 준다.
        _place("indoor-already-used", priority=10, setting="indoor"),
        # 스왑 후보로 등장해야 하는 "좋은" 실내 후보 - 진짜 슬롯 경쟁에서는
        # filler에도 밀리도록 priority를 낮게 둔다(그래야 all_used_ids에
        # 안 들어가 스왑 후보 풀에 그대로 남는다).
        _place("indoor-good", priority=2, setting="indoor"),
        # 아래 네 곳은 각자의 제외 규칙(비활성/식당/time_fit/휴무)으로
        # 스왑 후보에서 빠져야 하므로, 진짜 슬롯도 이기지 못하게 가장
        # 낮은 priority를 준다(이겨서 all_used_ids에 들어가 버리면
        # "이미 쓰인 장소라서 제외"와 섞여 그 규칙 자체를 못 검증한다).
        _place("indoor-inactive", priority=1, setting="indoor", is_active=False),
        _place("indoor-food", priority=1, setting="indoor", activity_type=["미식"]),
        _place("indoor-morning-only", priority=1, setting="indoor", time_fit=["morning"]),
        _place("indoor-closed-tuesday", priority=1, setting="indoor", closed_days="매주 화요일 휴무"),
    ]


def _descending_priority_filler_places(count: int = 10) -> list[PlaceData]:
    # tests/test_slot_alternatives.py의 종일(full-day) 픽스처와 동일한
    # priority 분포(10..1 내림차순) - _pick_full_day_place가 일반 슬롯에선
    # 절대 못 이기는 낮은 priority의 종일 후보를 그래도 종일로 뽑으려면
    # 일반 경쟁자들이 이 분포를 갖고 있어야 함이 이미 검증된 조합이다.
    names = [f"desc-filler-{i}" for i in range(count)]
    return [_place(name, priority=min(10, 10 - index)) for index, name in enumerate(names)]


def _build_request(*, start_date: date | None, days: int = 2, nights: int = 1, concepts=None, **overrides):
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "seoul",
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


def _generate(places, request, *, weather_client=None, **kwargs):
    service = RuleItineraryService(
        catalog_provider=_FakeCatalogProvider(places),
        weather_client=weather_client or FakeRainWeatherClient(start_date=A_TUESDAY),
    )
    return service.generate(request, **kwargs)


def _all_affected_items(response):
    return [item for alert in response.weather_alerts for item in alert.affected_items]


# --- swap_candidates respect every rule at once -----------------------------


# 실제 서울/부산/제주 카탈로그를 쓴다 - 합성(synthetic) priority 기반
# 픽스처로는 어떤 장소가 실제로 슬롯에 뽑힐지 신뢰성 있게 통제할 수
# 없다는 것을 확인했다(base_score가 scikit-learn 적합도 모델의 예측값이라
# priority 하나만으로 결과를 보장하지 못함 - 종일(full-day) 픽스처처럼
# 이미 검증된 분포가 있는 경우만 예외). 실제 카탈로그 + 강제 비 예보
# 조합은 항상 실외/혼합 장소가 실제로 뽑히고 비로 영향을 받으므로
# 훨씬 안정적이다.
def test_swap_candidates_respect_all_rules_at_once():
    service = RuleItineraryService(weather_client=FakeRainWeatherClient(start_date=A_TUESDAY))
    catalog = service.catalog_provider.get_city_catalog(
        continent="asia", country="korea", city="seoul", visible_only=True
    )
    places_by_id = {p.id: p for p in catalog.places}
    request = RuleItineraryRequest(
        city="seoul",
        nights=2,
        days=3,
        travelers=2,
        companion_type="friend",
        budget_band="medium",
        concepts=["sightseeing", "food"],
        style="easy",
        start_date=A_TUESDAY,
    )

    response = service.generate(request)

    affected_items = _all_affected_items(response)
    assert affected_items, "real seoul catalog + forced rain should produce at least one affected item"

    used_place_ids = {item.place_id for item in response.items}
    tuesday_weekday = A_TUESDAY.weekday()  # 1 == Tuesday

    for item in affected_items:
        assert len(item.swap_candidates) <= 3
        for candidate in item.swap_candidates:
            place = places_by_id[candidate.place_id]

            # indoor만
            assert place.setting == "indoor"
            # active만
            assert place.is_active
            # 식당 아님
            assert "food" not in place.concept_tags
            # 그 슬롯 time_fit 포함
            assert item.time_slot in place.time_fit
            # 그 요일 휴무 아님
            assert not is_confirmed_closed_on(place.closed_days, tuesday_weekday)
            # 일정에 이미 쓰인 장소 아님
            assert candidate.place_id not in used_place_ids


# --- full-day items: entry exists per slot, but swap_candidates is empty ---


def test_full_day_affected_item_has_empty_swap_candidates():
    places = _descending_priority_filler_places(10) + [
        _place(
            "funday-outdoor",
            priority=1,
            setting="outdoor",
            activity_type=["액티비티"],
            full_day_recommended=True,
        ),
    ]
    request = _build_request(start_date=A_TUESDAY, days=3, nights=2, concepts=["activity"])

    response = _generate(places, request)

    full_day_items = [item for item in response.items if item.place_name == "funday-outdoor"]
    assert len(full_day_items) == 3, "fixture should make day 2 a full-day item"
    full_day_number = full_day_items[0].day_number

    affected_items = [
        item
        for alert in response.weather_alerts
        if alert.day_number == full_day_number
        for item in alert.affected_items
        if item.place_id == "funday-outdoor"
    ]
    assert len(affected_items) == 3, "one affected_item per slot the full-day place occupies"
    assert {item.time_slot for item in affected_items} == {"morning", "afternoon", "evening"}
    assert all(item.swap_candidates == [] for item in affected_items)


# --- gating: include_alternatives / include_weather -------------------------


def _real_seoul_request(*, start_date):
    return RuleItineraryRequest(
        city="seoul",
        nights=2,
        days=3,
        travelers=2,
        companion_type="friend",
        budget_band="medium",
        concepts=["sightseeing", "food"],
        style="easy",
        start_date=start_date,
    )


def test_include_alternatives_false_yields_empty_affected_items_but_keeps_other_weather_fields():
    service = RuleItineraryService(weather_client=FakeRainWeatherClient(start_date=A_TUESDAY))
    request = _real_seoul_request(start_date=A_TUESDAY)

    response = service.generate(request, include_alternatives=False)

    assert response.weather_alerts, "weather_alerts itself must still be populated"
    assert all(alert.affected_items == [] for alert in response.weather_alerts)
    # 기존 필드는 그대로 채워짐
    assert all(alert.affected_place_names for alert in response.weather_alerts)


def test_include_weather_false_yields_no_weather_alerts_at_all():
    places = _weather_rule_set_catalog()
    request = _build_request(start_date=A_TUESDAY, days=1, nights=1)

    response = _generate(places, request, include_weather=False)

    assert response.weather_alerts == []
    assert response.weather_status == []


# --- existing fields/behavior are untouched ---------------------------------


def test_legacy_build_weather_alerts_call_still_returns_empty_affected_items():
    # 기존 호출부(테스트 포함)가 쓰는 4개 인자짜리 build_weather_alerts -
    # WeatherSwapContext를 전혀 모르므로 affected_items는 항상 [].
    outdoor_place = _place("outdoor-place", priority=5, setting="outdoor")
    catalog = CityPlaceCatalog(continent="asia", country="korea", city="seoul", places=[outdoor_place])
    request = RuleItineraryRequest.model_validate(
        {
            "continent": "asia",
            "country": "korea",
            "city": "seoul",
            "travelers": 2,
            "nights": 1,
            "days": 1,
            "budget_band": "medium",
            "concepts": ["sightseeing"],
            "style": "easy",
            "companion_type": "friend",
            "start_date": A_TUESDAY,
        }
    )
    weather_client = FakeRainWeatherClient(start_date=A_TUESDAY)

    alerts = build_weather_alerts(
        request=request,
        day_place_map={1: [outdoor_place]},
        city_catalog=catalog,
        weather_client=weather_client,
    )

    assert len(alerts) == 1
    assert alerts[0].affected_items == []
    # 기존 필드 값도 그대로
    assert alerts[0].affected_place_names == [outdoor_place.name]


def test_compare_transport_response_unaffected_by_weather_swap_feature():
    # compare_transport는 include_weather=False로 generate()를 돌리므로
    # (PR #104 보고서 이후 불변 사실) 이 기능과 완전히 무관해야 한다.
    service = RuleItineraryService()
    request = RuleItineraryRequest(
        city="seoul",
        nights=2,
        days=3,
        travelers=2,
        companion_type="couple",
        budget_band="medium",
        concepts=["sightseeing", "food"],
        style="easy",
    )

    comparison = service.compare_transport(request)
    assert comparison.base is not None
    assert set(comparison.model_dump().keys()) == {"base", "comparisons"}


# --- determinism -------------------------------------------------------------


def test_swap_candidate_ordering_is_deterministic_across_repeated_calls():
    request = _real_seoul_request(start_date=A_TUESDAY)

    first_service = RuleItineraryService(weather_client=FakeRainWeatherClient(start_date=A_TUESDAY))
    second_service = RuleItineraryService(weather_client=FakeRainWeatherClient(start_date=A_TUESDAY))
    first = first_service.generate(request)
    second = second_service.generate(request)

    first_ids = [[c.place_id for c in item.swap_candidates] for item in _all_affected_items(first)]
    second_ids = [[c.place_id for c in item.swap_candidates] for item in _all_affected_items(second)]
    assert first_ids == second_ids
    assert first_ids, "fixture should produce at least one swap_candidates list to compare"
