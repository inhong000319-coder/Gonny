from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import Settings
from app.services.external_clients import OpenWeatherClient, TourApiClient


def build_settings(api_key: str | None = "test-key") -> Settings:
    return Settings(openweather_api_key=api_key)


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    # TourApiClient checks `marker in resp.text` before parsing JSON (quota
    # detection) - a bare MagicMock().text would make that check misbehave,
    # so give every mocked response a plain string .text that never
    # contains the quota marker.
    import json as _json

    response.text = _json.dumps(payload)
    return response


def build_area_based_list_payload(*, result_code: str = "0000", total_count: int = 1) -> dict:
    return {
        "response": {
            "header": {"resultCode": result_code, "resultMsg": "OK"},
            "body": {
                "totalCount": total_count,
                "items": {"item": [{"contentid": "1", "title": "샘플"}]},
            },
        }
    }


def test_fetch_5day_forecast_picks_midday_block_and_includes_precipitation_mm() -> None:
    # The 00:00 block is "clear" and the 21:00 block is "clear" too - only
    # the 12:00 block (closest to midday) is rain. If the client naively
    # took the first block per day, it would report "clear" for this date.
    payload = {
        "list": [
            {
                "dt_txt": "2026-01-01 00:00:00",
                "weather": [{"main": "Clear"}],
                "main": {"temp_min": 1.0, "temp_max": 2.0},
            },
            {
                "dt_txt": "2026-01-01 12:00:00",
                "weather": [{"main": "Rain"}],
                "main": {"temp_min": 3.0, "temp_max": 5.0},
                "rain": {"3h": 6.0},
            },
            {
                "dt_txt": "2026-01-01 21:00:00",
                "weather": [{"main": "Clear"}],
                "main": {"temp_min": 0.0, "temp_max": 1.0},
            },
        ]
    }
    client = OpenWeatherClient(build_settings())

    with patch("httpx.Client.get", return_value=_mock_response(payload)):
        result = client.fetch_5day_forecast("Seoul,KR", allow_mock_fallback=False)

    assert len(result) == 1
    assert result[0]["condition"] == "rain"
    assert result[0]["precipitation_mm"] == 6.0


def test_fetch_5day_forecast_reads_snow_field_and_defaults_missing_precipitation_to_zero() -> None:
    payload = {
        "list": [
            {
                "dt_txt": "2026-01-01 12:00:00",
                "weather": [{"main": "Snow"}],
                "main": {"temp_min": -5.0, "temp_max": -2.0},
                "snow": {"3h": 1.2},
            },
            {
                "dt_txt": "2026-01-02 12:00:00",
                "weather": [{"main": "Clouds"}],
                "main": {"temp_min": 1.0, "temp_max": 4.0},
            },
        ]
    }
    client = OpenWeatherClient(build_settings())

    with patch("httpx.Client.get", return_value=_mock_response(payload)):
        result = client.fetch_5day_forecast("Seoul,KR", allow_mock_fallback=False)

    by_condition = {item["condition"]: item for item in result}
    assert by_condition["snow"]["precipitation_mm"] == 1.2
    assert by_condition["cloudy"]["precipitation_mm"] == 0.0


def test_fetch_5day_forecast_returns_empty_list_without_mock_fallback_when_no_api_key() -> None:
    client = OpenWeatherClient(build_settings(api_key=None))

    assert client.fetch_5day_forecast("Seoul,KR", allow_mock_fallback=False) == []


def test_fetch_5day_forecast_returns_empty_list_without_mock_fallback_on_request_failure() -> None:
    client = OpenWeatherClient(build_settings())

    with patch("httpx.Client.get", side_effect=RuntimeError("simulated network failure")):
        assert client.fetch_5day_forecast("Seoul,KR", allow_mock_fallback=False) == []


def test_fetch_5day_forecast_still_falls_back_to_mock_by_default() -> None:
    # Backward-compatible default behavior for callers that just want
    # something to display (allow_mock_fallback defaults to True).
    client = OpenWeatherClient(build_settings(api_key=None))

    result = client.fetch_5day_forecast("Seoul,KR")

    assert result
    assert all("precipitation_mm" in item for item in result)


# --- TourApiClient.fetch_area_based_list2 (areaCode vs lDongRegnCd) ---------


def build_tour_api_client() -> TourApiClient:
    return TourApiClient(Settings(tour_api_key="test-tour-key"))


def test_fetch_area_based_list2_sends_area_code_when_ldong_regn_cd_omitted() -> None:
    # 기존 호출부(collect_place_candidates.py 적용 전, fetch_popular_destinations
    # 등)와 동작이 완전히 같아야 한다 - ldong_regn_cd를 안 주면 areaCode만 보낸다.
    client = build_tour_api_client()
    mock_get = MagicMock(return_value=_mock_response(build_area_based_list_payload()))

    with patch("httpx.Client.get", mock_get):
        items, total_count, status = client.fetch_area_based_list2("12", "6", 1, 100)

    assert status == "ok"
    assert total_count == 1
    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params["areaCode"] == "6"
    assert "lDongRegnCd" not in sent_params


def test_fetch_area_based_list2_sends_ldong_regn_cd_when_given() -> None:
    client = build_tour_api_client()
    mock_get = MagicMock(return_value=_mock_response(build_area_based_list_payload(total_count=348)))

    with patch("httpx.Client.get", mock_get):
        items, total_count, status = client.fetch_area_based_list2("12", None, 1, 100, ldong_regn_cd="26")

    assert status == "ok"
    assert total_count == 348
    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params["lDongRegnCd"] == "26"
    assert "areaCode" not in sent_params


def test_fetch_area_based_list2_ldong_regn_cd_takes_priority_over_area_code() -> None:
    # 둘 다 넘기면(실수로든) lDongRegnCd가 우선한다 - 호출부가 명시적으로
    # area_code=None을 안 넘겨도 안전하게 동작하게 하기 위함.
    client = build_tour_api_client()
    mock_get = MagicMock(return_value=_mock_response(build_area_based_list_payload()))

    with patch("httpx.Client.get", mock_get):
        client.fetch_area_based_list2("12", "6", 1, 100, ldong_regn_cd="26")

    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params["lDongRegnCd"] == "26"
    assert "areaCode" not in sent_params
