from datetime import date

from app.domains.destination_catalog.schemas import CityPlaceCatalog, PlaceData
from app.domains.destination_catalog.services.provider import PlaceCatalogProvider
from app.domains.rule_planner.schemas import CatalogCityOption, RuleItineraryRequest
from app.domains.rule_planner.services.closed_days import (
    ClosureCertainty,
    is_confirmed_closed_on,
    parse_closed_days,
)
from app.domains.rule_planner.services.service import RuleItineraryService

# 2026-09-15 is a Tuesday (weekday() == 1); 2026-09-16 is a Wednesday.
A_TUESDAY = date(2026, 9, 15)
A_WEDNESDAY = date(2026, 9, 16)


def _place(place_id: str, *, priority: int, closed_days: str | None) -> PlaceData:
    return PlaceData(
        id=place_id,
        name=place_id,
        activity_type=["문화·역사"],
        budget_level=["low", "medium", "high"],
        suitable_for=["solo", "couple", "friend", "family"],
        time_fit=["morning", "afternoon", "evening"],
        area="test-area",
        duration_hours=2,
        priority=priority,
        pace=["easy", "tight"],
        mobility=["walkable"],
        summary=f"{place_id} summary",
        closed_days=closed_days,
    )


class _FakeCatalogProvider(PlaceCatalogProvider):
    """Deterministic in-memory catalog for closed-day exclusion tests -
    avoids depending on the real (and much larger) Seoul catalog's
    trained-model scoring for test determinism."""

    def __init__(self, places: list[PlaceData]):
        self._catalog = CityPlaceCatalog(
            continent="asia",
            country="korea",
            city="testcity",
            default_days=3,
            places=places,
        )

    def get_city_catalog(self, *, continent, country, city, visible_only=False) -> CityPlaceCatalog:
        return self._catalog

    def list_city_options(self, *, visible_only=False) -> list[CatalogCityOption]:
        return [CatalogCityOption(continent="asia", country="korea", city="testcity", aliases=[])]


def _generate(places: list[PlaceData], start_date: date | None):
    service = RuleItineraryService(catalog_provider=_FakeCatalogProvider(places))
    request = RuleItineraryRequest(
        continent="asia",
        country="korea",
        city="testcity",
        nights=1,
        days=1,
        budget_band="medium",
        concepts=["culture"],
        style="easy",
        companion_type="friend",
        start_date=start_date,
    )
    return service.generate(request)


# --- closed_days parser unit tests -----------------------------------------


def test_parses_plain_weekly_closure():
    info = parse_closed_days("매주 화요일 휴무")
    assert info.certainty == ClosureCertainty.CLOSED_ON_WEEKDAYS
    assert info.closed_weekdays == frozenset({1})


def test_parses_multiple_weekdays_in_weekly_closure():
    info = parse_closed_days("매주 월,수요일 휴무")
    assert info.certainty == ClosureCertainty.CLOSED_ON_WEEKDAYS
    assert info.closed_weekdays == frozenset({0, 2})


def test_parses_no_closure_markers_as_open_every_day():
    assert parse_closed_days("연중무휴").certainty == ClosureCertainty.OPEN_EVERY_DAY
    assert parse_closed_days("휴무일 없음").certainty == ClosureCertainty.OPEN_EVERY_DAY


def test_gyeongbokgung_real_text_parses_as_tuesday_closure():
    # Actual closed_days text from app/data/destinations/seoul.json - the
    # holiday-swap caveat is ignored (no holiday calendar available), but
    # the underlying "매주 화요일" pattern must still resolve correctly.
    text = "매주 화요일 ※ 단, 정기휴일이 공휴일 및 대체공휴일과 겹칠 경우에는 개방하며, 그 다음의 첫 번째 비공휴일이 정기휴일임"
    info = parse_closed_days(text)
    assert info.certainty == ClosureCertainty.CLOSED_ON_WEEKDAYS
    assert info.closed_weekdays == frozenset({1})


def test_seasonal_or_ambiguous_text_is_reported_as_unknown():
    assert parse_closed_days("계절별로 상이함").certainty == ClosureCertainty.UNKNOWN
    assert parse_closed_days("매주 화요일 (계절별로 변경될 수 있음)").certainty == ClosureCertainty.UNKNOWN
    assert parse_closed_days("점포별로 상이함").certainty == ClosureCertainty.UNKNOWN
    assert parse_closed_days(None).certainty == ClosureCertainty.UNKNOWN
    assert parse_closed_days("").certainty == ClosureCertainty.UNKNOWN


def test_monthly_pattern_is_not_mistaken_for_weekly_closure():
    # "매달"/"매월" (monthly), not "매주" (weekly) - must not be parsed as a
    # flat weekly closure.
    assert parse_closed_days("매달 첫째 주 월요일").certainty == ClosureCertainty.UNKNOWN
    assert parse_closed_days("매월 첫째, 셋째 화요일").certainty == ClosureCertainty.UNKNOWN


def test_is_confirmed_closed_on_matches_only_the_closed_weekday():
    assert is_confirmed_closed_on("매주 화요일 휴무", 1) is True
    assert is_confirmed_closed_on("매주 화요일 휴무", 2) is False
    assert is_confirmed_closed_on("시설별로 상이함", 1) is False


# --- itinerary placement integration tests ----------------------------------


def test_confirmed_closed_place_is_excluded_from_its_closed_weekday():
    places = [
        _place("closed-tuesday-palace", priority=10, closed_days="매주 화요일 휴무"),
        _place("filler-a", priority=5, closed_days=None),
        _place("filler-b", priority=4, closed_days=None),
        _place("filler-c", priority=3, closed_days=None),
    ]

    response = _generate(places, start_date=A_TUESDAY)

    placed_names = {item.place_name for item in response.items}
    assert "closed-tuesday-palace" not in placed_names

    exclusion_place_names = {exclusion.place_name for exclusion in response.closed_day_exclusions}
    assert "closed-tuesday-palace" in exclusion_place_names
    exclusion = next(e for e in response.closed_day_exclusions if e.place_name == "closed-tuesday-palace")
    assert exclusion.day_number == 1
    assert "화요일" in exclusion.message


def test_confirmed_closed_place_is_placed_normally_on_other_days():
    places = [
        _place("closed-tuesday-palace", priority=10, closed_days="매주 화요일 휴무"),
        _place("filler-a", priority=5, closed_days=None),
        _place("filler-b", priority=4, closed_days=None),
        _place("filler-c", priority=3, closed_days=None),
    ]

    response = _generate(places, start_date=A_WEDNESDAY)

    placed_names = {item.place_name for item in response.items}
    assert "closed-tuesday-palace" in placed_names
    assert response.closed_day_exclusions == []


def test_ambiguous_closed_days_text_does_not_block_placement():
    places = [
        # Mentions a weekday but is explicitly marked as seasonal/variable -
        # must fall back to "unknown" and never be excluded (false-positive
        # guard, mirrors the real Gyeongbokgung-style caveat text).
        _place("ambiguous-museum", priority=10, closed_days="매주 화요일 (계절별로 상이)"),
        _place("filler-a", priority=5, closed_days=None),
        _place("filler-b", priority=4, closed_days=None),
        _place("filler-c", priority=3, closed_days=None),
    ]

    response = _generate(places, start_date=A_TUESDAY)

    placed_names = {item.place_name for item in response.items}
    assert "ambiguous-museum" in placed_names
    assert response.closed_day_exclusions == []


def test_no_start_date_never_triggers_exclusion():
    places = [
        _place("closed-tuesday-palace", priority=10, closed_days="매주 화요일 휴무"),
        _place("filler-a", priority=5, closed_days=None),
        _place("filler-b", priority=4, closed_days=None),
        _place("filler-c", priority=3, closed_days=None),
    ]

    response = _generate(places, start_date=None)

    placed_names = {item.place_name for item in response.items}
    assert "closed-tuesday-palace" in placed_names
    assert response.closed_day_exclusions == []
