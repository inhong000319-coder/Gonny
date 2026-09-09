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

# Numeric TourAPI areaCode values, used only for areaBasedList2 (browse-by-
# region), NOT for searchKeyword2 - these are a different mechanism.
# areaBasedList2's areaCode filter was verified live to work correctly
# (totalCount=235/65/56 for seoul/busan/jeju lodging), unlike
# searchKeyword2's areaCode, which silently drops records with an empty
# cat1 (see TOUR_API_ADDRESS_PREFIX_BY_CITY above for that bug).
TOUR_API_AREA_CODE_BY_CITY = {
    "seoul": "1",
    "busan": "6",
    "jeju": "39",
}

# TourAPI's lclsSystm2 classification codes for contentTypeId=32 (숙박),
# verified live via the lclsSystmCode2 endpoint (lclsSystm1=AC) - this is
# the authoritative list, not a guess. There is no Airbnb/에어비앤비
# category: TourAPI only carries officially registered tourism lodging
# businesses, not platform listings, so that type can't be represented
# here.
ACCOMMODATION_TYPE_LABELS_BY_LCLS2: dict[str, str] = {
    "AC01": "호텔",
    "AC02": "콘도미니엄",
    "AC03": "펜션·민박",
    "AC04": "모텔",
    "AC05": "캠핑",
    "AC06": "호스텔",
}

# detailIntro2 fields for contentTypeId=32, verified live (see a real
# hotel's response). Two shapes:
# - flag fields: "0"/"1" indicating whether the facility exists at all
# - text fields: free text where "가능"/"불가(능)" indicates availability
# No breakfast ("조식제공") or pool ("수영장") field exists anywhere in
# detailIntro2 or detailInfo2 for lodging - verified live, not just
# unmapped. Only fields TourAPI actually exposes are listed below.
LODGING_AMENITY_FLAG_FIELDS: dict[str, str] = {
    "seminar": "세미나실",
    "sports": "체육시설",
    "sauna": "사우나",
    "beauty": "미용실",
    "beverage": "음료서비스",
    "karaoke": "노래방",
    "barbecue": "바비큐",
    "campfire": "캠프파이어",
    "bicycle": "자전거대여",
    "fitness": "피트니스",
    "publicpc": "PC실",
    "publicbath": "대중목욕탕",
}
LODGING_AMENITY_TEXT_FIELDS: dict[str, str] = {
    "parkinglodging": "주차가능",
    "chkcooking": "취사가능",
}


def _text_field_indicates_available(value: str) -> bool:
    """"가능" is a substring of "불가능", so a naive `"가능" in value` check
    would misread "불가능"/"불가" as available. Checking the negative
    prefix first avoids that trap."""
    normalized = value.strip()
    if not normalized or normalized.startswith("불가") or normalized in {"없음", "불가"}:
        return False
    return "가능" in normalized


def extract_lodging_amenities(detail_item: dict) -> list[str]:
    """Builds the amenities list from a detailIntro2 (contentTypeId=32)
    item, using only fields TourAPI actually provides - see
    LODGING_AMENITY_FLAG_FIELDS/LODGING_AMENITY_TEXT_FIELDS."""
    amenities: list[str] = []
    for field, label in LODGING_AMENITY_TEXT_FIELDS.items():
        value = str(detail_item.get(field, "")).strip()
        if value and _text_field_indicates_available(value):
            amenities.append(label)
    for field, label in LODGING_AMENITY_FLAG_FIELDS.items():
        if str(detail_item.get(field, "")).strip() == "1":
            amenities.append(label)
    return amenities

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

# detailIntro2's operating-hours field names vary by contentTypeId - there
# is no single "usetime"/"restdate" pair used across all of them. Verified
# live against apis.data.go.kr for the types actually present in our
# catalog (see scripts/fetch_place_operating_hours.py's logged contentTypeId
# distribution for confirmation this covers what we actually have):
#   12 (관광지): usetime / restdate
#   14 (문화시설): usetimeculture / restdateculture
#   28 (레포츠): usetimeleports / restdateleports
#   38 (쇼핑): opentime / restdateshopping
#   39 (음식점): opentimefood / restdatefood
# contentTypeId=32 (숙박) has checkintime/checkouttime instead of a daily
# open_hours concept - deliberately not mapped here, not the same thing.
# Any other contentTypeId (e.g. 15/25, none seen in our catalog) simply
# isn't in this dict, so fetch_place_operating_hours() returns (None, None)
# for it rather than guessing at unverified field names.
DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE: dict[str, tuple[str, str]] = {
    "12": ("usetime", "restdate"),
    "14": ("usetimeculture", "restdateculture"),
    "28": ("usetimeleports", "restdateleports"),
    "38": ("opentime", "restdateshopping"),
    "39": ("opentimefood", "restdatefood"),
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

    def fetch_lodging_candidates(self, city: str, num_rows: int = 50) -> list[dict] | None:
        """Browse-by-region listing of contentTypeId=32 (숙박) items for a
        city via areaBasedList2. Returns raw TourAPI items (title,
        contentid, mapx/mapy, lclsSystm2, addr1, etc.) or None on any
        request/response failure.

        Unlike searchKeyword2, areaBasedList2's areaCode filter is safe to
        use here - see TOUR_API_AREA_CODE_BY_CITY.
        """
        area_code = TOUR_API_AREA_CODE_BY_CITY.get(city)
        if not self.api_key or area_code is None:
            return None

        url = f"{self.base_url}/areaBasedList2"
        params = {
            "serviceKey": self.api_key,
            "numOfRows": num_rows,
            "pageNo": 1,
            "MobileOS": "ETC",
            "MobileApp": "Gonny",
            "_type": "json",
            "contentTypeId": "32",
            "areaCode": area_code,
            "arrange": "Q",  # 수정일순 - stable, not popularity-skewed
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

    def fetch_lodging_details(self, content_id: str) -> dict | None:
        """Raw detailIntro2 (contentTypeId=32) item for one lodging
        content_id, or None on any failure. Callers extract
        checkintime/checkouttime/amenities from the returned dict (see
        extract_lodging_amenities and LODGING_AMENITY_*_FIELDS)."""
        if not self.api_key:
            return None

        url = f"{self.base_url}/detailIntro2"
        params = {
            "serviceKey": self.api_key,
            "MobileOS": "ETC",
            "MobileApp": "Gonny",
            "_type": "json",
            "contentId": content_id,
            "contentTypeId": "32",
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

        if not isinstance(items, list):
            items = [items]
        return items[0] if items else None

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
    ) -> tuple[float | None, float | None, str | None, str | None, str]:
        """Look up a place's coordinates (and TourAPI identity) by name
        within a known city.

        activity_types (our Korean activity_type labels, e.g. ["쇼핑"]) is
        optional and only used to break a tie among candidates that already
        matched the name exactly - see ACTIVITY_TYPE_TO_TOUR_API_CONTENT_TYPE_IDS.

        Returns (latitude, longitude, content_id, content_type_id, status)
        where status is one of:
        - "ok": exactly one confident match was found
        - "not_found": no candidate shared the place's name in that city
        - "ambiguous": multiple same-named candidates in that city
        - "api_error": the request failed or returned an unusable response
          (network error, non-2xx status, non-"0000" resultCode, or an
          unparseable body) - distinct from "ambiguous" so transient
          failures (e.g. rate limiting) aren't mistaken for a genuine
          naming conflict when reviewing results.

        On anything other than "ok", all four values are None. Coordinates
        (and content_id) are never guessed - callers should leave the
        place's coordinates unset and log it for manual follow-up.

        content_type_id is returned so callers can immediately follow up
        with fetch_place_operating_hours(content_id, content_type_id)
        without a second search - it isn't meant to be persisted alongside
        content_id (PlaceData only stores content_id).
        """
        address_prefix = TOUR_API_ADDRESS_PREFIX_BY_CITY.get(city)
        if not self.api_key or address_prefix is None:
            return None, None, None, None, "api_error"

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
                return None, None, None, None, "api_error"
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
            status = "not_found" if not candidates else "ambiguous"
            return None, None, None, None, status

        match = candidates[0]
        try:
            longitude = float(match["mapx"])
            latitude = float(match["mapy"])
        except (KeyError, TypeError, ValueError):
            return None, None, None, None, "api_error"

        content_id = str(match.get("contentid", "")).strip() or None
        content_type_id = str(match.get("contenttypeid", "")).strip() or None
        return latitude, longitude, content_id, content_type_id, "ok"

    def fetch_place_operating_hours(
        self,
        content_id: str,
        content_type_id: str,
    ) -> tuple[str | None, str | None, str]:
        """Look up open_hours/closed_days via detailIntro2 for a place we
        already have a content_id for (no re-search needed).

        Returns (open_hours, closed_days, status) where status is "ok" or
        "api_error". Both values are the raw TourAPI text verbatim (prose,
        HTML <br> tags and all) - never parsed into a structured schedule,
        since the source text isn't structured to begin with (see
        DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE for why the field names
        differ by contentTypeId). An empty/missing field becomes None; a
        field containing text like "연중무휴" (no closed days) is kept as
        that literal text, not collapsed into None - "no data" and "no
        closed days" are different facts and must stay distinguishable.

        A contentTypeId with no mapped fields (e.g. 32/숙박, which has
        checkintime/checkouttime instead of daily hours) returns
        (None, None, "ok") - that's a legitimate "this venue type has no
        open_hours concept", not a failure.
        """
        if not self.api_key:
            return None, None, "api_error"

        fields = DETAIL_INTRO_HOURS_FIELDS_BY_CONTENT_TYPE.get(content_type_id)
        if fields is None:
            return None, None, "ok"

        url = f"{self.base_url}/detailIntro2"
        params = {
            "serviceKey": self.api_key,
            "MobileOS": "ETC",
            "MobileApp": "Gonny",
            "_type": "json",
            "contentId": content_id,
            "contentTypeId": content_type_id,
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            payload = resp.json()["response"]
            if payload["header"]["resultCode"] != "0000":
                return None, None, "api_error"
            body = payload["body"]["items"]
            items = body["item"] if body else []
        except Exception:
            return None, None, "api_error"

        if not isinstance(items, list):
            items = [items]
        if not items:
            return None, None, "ok"

        item = items[0]
        hours_field, closed_field = fields
        open_hours = str(item.get(hours_field, "")).strip() or None
        closed_days = str(item.get(closed_field, "")).strip() or None
        return open_hours, closed_days, "ok"


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
