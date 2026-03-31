"""External API client wrappers with graceful fallback behavior."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from app.core.settings import Settings


def _condition_from_openweather(main_value: str) -> str:
    value = (main_value or "").lower()
    if "snow" in value:
        return "snow"
    if "rain" in value or "drizzle" in value or "thunder" in value:
        return "rain"
    if "cloud" in value:
        return "cloudy"
    return "clear"


class OpenWeatherClient:
    """Fetch weather forecasts for F04."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openweather_api_key

    def fetch_5day_forecast(self, destination: str) -> list[dict]:
        if not self.api_key:
            return self._mock_forecast()

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"q": destination, "appid": self.api_key, "units": "metric"}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return self._mock_forecast()

        result: list[dict] = []
        seen_dates = set()
        for item in payload.get("list", []):
            dt_txt = item.get("dt_txt")
            if not dt_txt:
                continue
            forecast_date = datetime.fromisoformat(dt_txt).date()
            if forecast_date in seen_dates:
                continue
            seen_dates.add(forecast_date)
            result.append(
                {
                    "forecast_date": forecast_date,
                    "condition": _condition_from_openweather(item["weather"][0]["main"]),
                    "min_temp_c": item["main"]["temp_min"],
                    "max_temp_c": item["main"]["temp_max"],
                }
            )
            if len(result) >= 5:
                break

        return result or self._mock_forecast()

    @staticmethod
    def _mock_forecast() -> list[dict]:
        today = datetime.utcnow().date()
        return [
            {"forecast_date": today, "condition": "clear", "min_temp_c": 9.0, "max_temp_c": 16.0},
            {"forecast_date": today + timedelta(days=1), "condition": "cloudy", "min_temp_c": 8.0, "max_temp_c": 14.0},
            {"forecast_date": today + timedelta(days=2), "condition": "rain", "min_temp_c": 7.0, "max_temp_c": 12.0},
        ]


class TourApiClient:
    """Fetch seasonal destination feed for F15."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.tour_api_key
        self.base_url = settings.tour_api_base_url.rstrip("/")

    def fetch_season_feed(self, keyword: str | None = None) -> list[dict]:
        """Fetch a compact list from TourAPI if key is available.

        This uses areaBasedList1 for stable response shape and returns a reduced model.
        """

        if not self.api_key:
            return []

        url = f"{self.base_url}/areaBasedList1"
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 6,
            "pageNo": 1,
            "MobileOS": "ETC",
            "MobileApp": "Gonny",
            "_type": "json",
            "arrange": "P",
            "contentTypeId": 12,  # tourist spots
        }
        if keyword:
            params["keyword"] = keyword

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            body = resp.json()["response"]["body"]["items"]["item"]
        except Exception:
            return []

        if not isinstance(body, list):
            body = [body]

        rows: list[dict] = []
        for item in body[:6]:
            rows.append(
                {
                    "title": item.get("title", "Tour spot"),
                    "region": item.get("addr1", "Korea"),
                    "reason": "Live feed from TourAPI popularity ranking",
                    "tags": ["tour", "live"],
                    "source": "TourAPI",
                }
            )
        return rows


class ODSayClient:
    """Fetch transit duration for F07 when coordinates are available."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.odsay_api_key
        self.base_url = settings.odsay_api_base_url.rstrip("/")

    def estimate_duration_min(self, sx: float, sy: float, ex: float, ey: float) -> int | None:
        if not self.api_key:
            return None

        url = f"{self.base_url}/searchPubTransPathT"
        params = {
            "SX": sx,
            "SY": sy,
            "EX": ex,
            "EY": ey,
            "apiKey": self.api_key,
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            paths = resp.json().get("result", {}).get("path", [])
        except Exception:
            return None

        if not paths:
            return None
        first_path = paths[0]
        info = first_path.get("info", {})
        total_time = info.get("totalTime")
        if isinstance(total_time, int):
            return total_time
        return None
