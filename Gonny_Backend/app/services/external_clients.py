"""External API client wrappers with graceful fallback behavior."""

from __future__ import annotations

import re
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


# Korean address prefixes for the rule_planner's visible cities, used to
# filter searchKeyword2 results client-side by addr1.
#
# TourAPI's own areaCode parameter looks like the "correct" way to scope a
# keyword search to a city, but it silently excludes any record whose cat1
# classification field is empty - and a meaningful share of real records
# have that field blank (verified live: e.g. "감천문화마을"/"허심청"/
# "용두산공원" all have cat1="" and return totalCount=0 with areaCode=6,
# even though they're real Busan tourist spots with correct addr1/mapx/
# mapy). addr1 is reliably populated on every record seen, so filtering on
# it ourselves is more complete than trusting areaCode.
TOUR_API_ADDRESS_PREFIX_BY_CITY = {
    "seoul": "서울",
    "busan": "부산",
    "jeju": "제주",
}

# TourAPI contentTypeId reference: 12=관광지, 14=문화시설, 15=축제공연행사,
# 25=여행코스, 28=레포츠, 32=숙박, 38=쇼핑, 39=음식점. Used only to break
# ties among candidates whose titles already matched exactly (see
# find_place_coordinates) - e.g. "부산타워" resolves to two identically
# titled candidates, one contentTypeId=12 (the tower itself) and one
# contentTypeId=38 (a gift shop inside it); our activity_type says which
# is the real match. Not applied to loose/substring candidates: verified
# live that doing so would resolve "홍대" to a phone-case shop that
# happens to be misclassified as contentTypeId=12.
ACTIVITY_TYPE_TO_TOUR_API_CONTENT_TYPE_IDS: dict[str, set[str]] = {
    "문화·역사": {"12", "14"},
    "미식": {"39"},
    "쇼핑": {"38"},
    "액티비티": {"12", "28"},
    "자연·트레킹": {"12"},
    "휴양·힐링": {"12", "32"},
    "나이트라이프": {"39", "28"},
    "온천": {"12", "32"},
}

_TOUR_API_CITY_TITLE_PREFIX = re.compile(r"^(서울|부산|제주)\s*")
_TOUR_API_TITLE_ANNOTATION_SUFFIX = re.compile(r"\s*[\[(][^\[\]()]*[\])]\s*$")


def _normalize_tour_api_title(title: str) -> str:
    """Strip decorative city-name prefixes ("부산 감천문화마을") and
    trailing bracketed annotations ("성산일출봉 [유네스코 세계자연유산]")
    that TourAPI titles commonly carry, so these still count as an exact
    match against our plain place name. Deliberately conservative: it only
    strips these two specific, observed patterns - it does not touch
    franchise/branch suffixes like "~점"/"~역" since those can't be
    distinguished from a genuinely different business sharing a substring
    (e.g. a phone case shop named "...홍대점" is not "홍대")."""
    normalized = _TOUR_API_CITY_TITLE_PREFIX.sub("", title.strip())
    normalized = _TOUR_API_TITLE_ANNOTATION_SUFFIX.sub("", normalized)
    return normalized.strip()


def _collapse_whitespace(text: str) -> str:
    """Removes all whitespace, for a spacing-insensitive comparison.

    TourAPI titles and our place names don't always agree on spacing for
    the same real place (e.g. our "해운대 해수욕장" vs TourAPI's
    "해운대해수욕장") - collapsing both sides makes that a match without
    weakening the comparison in any other way.
    """
    return re.sub(r"\s+", "", text)


class TourApiClient:
    """Fetch seasonal destination feed for F15, and place coordinates."""

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

    def _search_keyword2(self, keyword: str) -> list[dict] | None:
        """Raw searchKeyword2 call for one keyword string. Returns None on
        any request/response failure (caller maps this to "api_error")."""
        url = f"{self.base_url}/searchKeyword2"
        params = {
            "serviceKey": self.api_key,
            # Popular/generic keywords (e.g. "명동") can have 100+ matches
            # nationwide with the real single-word listing ranked well past
            # position 30 among franchise-branch results like "OO 명동점" -
            # verified live that raising this to 100 was enough to surface it.
            "numOfRows": 100,
            "pageNo": 1,
            "MobileOS": "ETC",
            "MobileApp": "Gonny",
            "_type": "json",
            "keyword": keyword,
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            payload = resp.json()["response"]
            if payload["header"]["resultCode"] != "0000":
                return None
            body = payload["body"]["items"]
            items = body["item"] if body else []
        except Exception:
            return None

        return items if isinstance(items, list) else [items]

    def find_place_coordinates(
        self,
        name: str,
        city: str,
        activity_types: list[str] | None = None,
    ) -> tuple[float | None, float | None, str]:
        """Look up a place's coordinates by name within a known city.

        activity_types (our Korean activity_type labels, e.g. ["쇼핑"]) is
        optional and only used to break a tie among candidates that already
        matched the name exactly - see ACTIVITY_TYPE_TO_TOUR_API_CONTENT_TYPE_IDS.

        Returns (latitude, longitude, status) where status is one of:
        - "ok": exactly one confident match was found
        - "not_found": no candidate shared the place's name in that city
        - "ambiguous": multiple same-named candidates in that city
        - "api_error": the request failed or returned an unusable response
          (network error, non-2xx status, non-"0000" resultCode, or an
          unparseable body) - distinct from "ambiguous" so transient
          failures (e.g. rate limiting) aren't mistaken for a genuine
          naming conflict when reviewing results.

        On anything other than "ok", latitude/longitude are both None.
        Coordinates are never guessed - callers should leave the place's
        coordinates unset and log it for manual follow-up.
        """
        address_prefix = TOUR_API_ADDRESS_PREFIX_BY_CITY.get(city)
        if not self.api_key or address_prefix is None:
            return None, None, "api_error"

        # TourAPI's own search matching on whitespace is inconsistent, not
        # just a title-formatting quirk on the response side: verified live
        # that "해운대 해수욕장" (with space) returns totalCount=0 while
        # "해운대해수욕장" (no space) finds it - but "롯데월드 어드벤처"
        # (with space) finds 3 results while "롯데월드어드벤처" (no space)
        # returns 0. There's no way to predict which form TourAPI indexed a
        # given title under, so query both when the name has a space and
        # merge the results.
        query_variants = [name]
        collapsed_query = re.sub(r"\s+", "", name)
        if collapsed_query != name:
            query_variants.append(collapsed_query)

        items: list[dict] = []
        seen_content_ids: set[str] = set()
        for query in query_variants:
            fetched = self._search_keyword2(query)
            if fetched is None:
                return None, None, "api_error"
            for item in fetched:
                content_id = str(item.get("contentid", ""))
                if content_id and content_id in seen_content_ids:
                    continue
                if content_id:
                    seen_content_ids.add(content_id)
                items.append(item)

        # Filter to the target city ourselves via addr1 - see
        # TOUR_API_ADDRESS_PREFIX_BY_CITY for why the areaCode request
        # param isn't used here.
        items = [item for item in items if str(item.get("addr1", "")).startswith(address_prefix)]

        normalized_name = name.strip()
        collapsed_name = _collapse_whitespace(normalized_name)
        exact_matches = [
            item
            for item in items
            # Compare the raw title first: normalizing could otherwise
            # break a title where the city name is part of the place's
            # actual name (e.g. "부산타워" normalizes to "타워", which no
            # longer matches keyword "부산타워").
            if str(item.get("title", "")).strip() == normalized_name
            or _normalize_tour_api_title(str(item.get("title", ""))) == normalized_name
            or _collapse_whitespace(str(item.get("title", ""))) == collapsed_name
        ]
        candidates = exact_matches
        if len(candidates) > 1 and activity_types:
            allowed_content_type_ids: set[str] = set()
            for activity_type in activity_types:
                allowed_content_type_ids |= ACTIVITY_TYPE_TO_TOUR_API_CONTENT_TYPE_IDS.get(activity_type, set())
            if allowed_content_type_ids:
                narrowed = [item for item in candidates if str(item.get("contenttypeid")) in allowed_content_type_ids]
                # Only accept the narrowed set if it lands on exactly one
                # candidate - if multiple still share a plausible
                # contentTypeId (e.g. two museum buildings, both "문화시설"),
                # this stays ambiguous rather than guessing between them.
                if len(narrowed) == 1:
                    candidates = narrowed
        if not candidates:
            candidates = [
                item
                for item in items
                if normalized_name in str(item.get("title", ""))
                or str(item.get("title", "")) in normalized_name
                or collapsed_name in _collapse_whitespace(str(item.get("title", "")))
                or _collapse_whitespace(str(item.get("title", ""))) in collapsed_name
            ]

        if len(candidates) != 1:
            return None, None, "not_found" if not candidates else "ambiguous"

        match = candidates[0]
        try:
            longitude = float(match["mapx"])
            latitude = float(match["mapy"])
        except (KeyError, TypeError, ValueError):
            return None, None, "api_error"

        return latitude, longitude, "ok"


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
