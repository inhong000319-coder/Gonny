from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings
from app.domains.seasonal_feed.service import SeasonalFeedService, determine_current_season
from app.services.external_clients import TourApiClient


def build_settings(api_key: str | None = "test-key") -> Settings:
    return Settings(tour_api_key=api_key)


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _ok_payload(items: list[dict]) -> dict:
    return {"response": {"header": {"resultCode": "0000"}, "body": {"items": {"item": items}}}}


class FakeTourApiClient:
    def __init__(self, festivals_by_city=None, destinations_by_city=None, raise_error=False):
        self._festivals_by_city = festivals_by_city or {}
        self._destinations_by_city = destinations_by_city or {}
        self._raise_error = raise_error

    def fetch_festivals_this_month(self, city: str, num_rows: int = 10):
        if self._raise_error:
            raise RuntimeError("simulated failure")
        return self._festivals_by_city.get(city)

    def fetch_popular_destinations(self, city: str, num_rows: int = 6):
        if self._raise_error:
            raise RuntimeError("simulated failure")
        return self._destinations_by_city.get(city)


# determine_current_season()


def test_determine_current_season_covers_all_four_seasons() -> None:
    assert determine_current_season(date(2026, 3, 1)) == "spring"
    assert determine_current_season(date(2026, 5, 31)) == "spring"
    assert determine_current_season(date(2026, 6, 1)) == "summer"
    assert determine_current_season(date(2026, 8, 31)) == "summer"
    assert determine_current_season(date(2026, 9, 1)) == "autumn"
    assert determine_current_season(date(2026, 9, 20)) == "autumn"
    assert determine_current_season(date(2026, 11, 30)) == "autumn"
    assert determine_current_season(date(2026, 12, 1)) == "winter"
    assert determine_current_season(date(2026, 1, 15)) == "winter"
    assert determine_current_season(date(2026, 2, 28)) == "winter"


def test_determine_current_season_defaults_to_todays_date() -> None:
    assert determine_current_season() == determine_current_season(date.today())


# TourApiClient.fetch_festivals_this_month() / fetch_popular_destinations()


def test_fetch_festivals_this_month_returns_none_for_unsupported_city() -> None:
    client = TourApiClient(build_settings())
    assert client.fetch_festivals_this_month("tokyo") is None


def test_fetch_festivals_this_month_returns_none_without_api_key() -> None:
    client = TourApiClient(build_settings(api_key=None))
    assert client.fetch_festivals_this_month("seoul") is None


def test_fetch_festivals_this_month_filters_by_addr1_prefix_not_area_code() -> None:
    # searchFestival2's areaCode request param was verified live to have
    # the same silent-exclusion bug as searchKeyword2 (empty cat1/
    # areacode on real records - see TOUR_API_ADDRESS_PREFIX_BY_CITY), so
    # this method must NOT send areaCode and must filter by addr1 itself.
    client = TourApiClient(build_settings())
    captured_params: dict = {}

    def fake_get(self, url, params=None, **kwargs):
        captured_params.update(params or {})
        return _mock_response(
            _ok_payload(
                [
                    {
                        "title": "부산불꽃축제",
                        "addr1": "부산광역시 해운대구",
                        "eventstartdate": "20260901",
                        "eventenddate": "20260910",
                    },
                    {
                        "title": "서울국제작가축제",
                        "addr1": "서울특별시 종로구",
                        "eventstartdate": "20260905",
                        "eventenddate": "20260906",
                    },
                ]
            )
        )

    with patch("httpx.Client.get", fake_get):
        result = client.fetch_festivals_this_month("busan")

    assert result == [
        {
            "title": "부산불꽃축제",
            "addr1": "부산광역시 해운대구",
            "eventstartdate": "20260901",
            "eventenddate": "20260910",
        }
    ]
    assert "areaCode" not in captured_params
    today = date.today()
    assert captured_params["eventStartDate"] == today.replace(day=1).strftime("%Y%m%d")


def test_fetch_festivals_this_month_returns_none_on_request_failure() -> None:
    client = TourApiClient(build_settings())
    with patch("httpx.Client.get", side_effect=RuntimeError("boom")):
        assert client.fetch_festivals_this_month("seoul") is None


def test_fetch_popular_destinations_returns_none_for_unsupported_city() -> None:
    client = TourApiClient(build_settings())
    assert client.fetch_popular_destinations("tokyo") is None


def test_fetch_popular_destinations_uses_area_code_and_content_type_12() -> None:
    client = TourApiClient(build_settings())
    captured_params: dict = {}

    def fake_get(self, url, params=None, **kwargs):
        captured_params.update(params or {})
        return _mock_response(_ok_payload([{"title": "경복궁"}]))

    with patch("httpx.Client.get", fake_get):
        result = client.fetch_popular_destinations("seoul")

    assert result == [{"title": "경복궁"}]
    assert captured_params["areaCode"] == "1"
    assert captured_params["contentTypeId"] == "12"


def test_fetch_popular_destinations_returns_none_on_request_failure() -> None:
    client = TourApiClient(build_settings())
    with patch("httpx.Client.get", side_effect=RuntimeError("boom")):
        assert client.fetch_popular_destinations("busan") is None


# SeasonalFeedService.get_seasonal_feed()


def test_seasonal_feed_only_includes_seoul_busan_jeju() -> None:
    fake_client = FakeTourApiClient(
        destinations_by_city={
            "seoul": [{"title": "경복궁"}],
            "busan": [{"title": "해운대"}],
            "jeju": [{"title": "성산일출봉"}],
        }
    )
    service = SeasonalFeedService(tour_api_client=fake_client)

    feed = service.get_seasonal_feed()

    assert {destination.city for destination in feed.popular_destinations} == {"seoul", "busan", "jeju"}


def test_seasonal_feed_normalizes_festival_dates_and_drops_incomplete_items() -> None:
    fake_client = FakeTourApiClient(
        festivals_by_city={
            "seoul": [
                {"title": "서울 불꽃축제", "eventstartdate": "20260901", "eventenddate": "20260903"},
                {"title": "날짜 없는 축제"},  # missing dates - must be dropped, not crash
            ],
        }
    )
    service = SeasonalFeedService(tour_api_client=fake_client)

    feed = service.get_seasonal_feed()

    assert len(feed.festivals) == 1
    festival = feed.festivals[0]
    assert festival.title == "서울 불꽃축제"
    assert festival.start_date == "2026-09-01"
    assert festival.end_date == "2026-09-03"


def test_seasonal_feed_returns_empty_lists_when_client_returns_none() -> None:
    # Represents "no API key" / a handled TourAPI failure.
    fake_client = FakeTourApiClient()
    service = SeasonalFeedService(tour_api_client=fake_client)

    feed = service.get_seasonal_feed()

    assert feed.festivals == []
    assert feed.popular_destinations == []
    assert feed.season == determine_current_season()


def test_seasonal_feed_stays_safe_when_client_raises() -> None:
    fake_client = FakeTourApiClient(raise_error=True)
    service = SeasonalFeedService(tour_api_client=fake_client)

    feed = service.get_seasonal_feed()

    assert feed.festivals == []
    assert feed.popular_destinations == []
