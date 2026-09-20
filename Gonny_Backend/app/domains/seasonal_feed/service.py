"""F15 seasonal feed: current season + this month's festivals + popular
destinations, all scoped to the cities our service actually plans trips
for (seoul/busan/jeju - see TOUR_API_AREA_CODE_BY_CITY). Independent of
rule_planner; this is a read-only TourAPI passthrough with no persistence.
"""

from __future__ import annotations

from datetime import date

from app.core.settings import settings
from app.services.external_clients import TOUR_API_AREA_CODE_BY_CITY, TourApiClient

from .schemas import FestivalItem, PopularDestinationItem, Season, SeasonalFeedResponse

SUPPORTED_CITIES = list(TOUR_API_AREA_CODE_BY_CITY)


def determine_current_season(reference_date: date | None = None) -> Season:
    """spring: Mar-May, summer: Jun-Aug, autumn: Sep-Nov, winter: Dec-Feb -
    per the requirements doc's literal definition, based on server date."""
    month = (reference_date or date.today()).month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def _normalize_tour_api_date(value: str) -> str | None:
    """TourAPI dates come as "YYYYMMDD"; normalize to "YYYY-MM-DD" for the
    frontend, or None if the field is missing/malformed (caller drops
    that item rather than showing a garbled date)."""
    value = (value or "").strip()
    if len(value) != 8 or not value.isdigit():
        return None
    return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"


def _to_festival_item(item: dict, city: str) -> FestivalItem | None:
    title = str(item.get("title", "")).strip()
    start_date = _normalize_tour_api_date(str(item.get("eventstartdate", "")))
    end_date = _normalize_tour_api_date(str(item.get("eventenddate", "")))
    if not title or not start_date or not end_date:
        return None
    return FestivalItem(
        title=title,
        city=city,
        start_date=start_date,
        end_date=end_date,
        address=str(item.get("addr1", "")).strip() or None,
        image_url=str(item.get("firstimage", "")).strip() or None,
    )


def _to_popular_destination_item(item: dict, city: str) -> PopularDestinationItem | None:
    title = str(item.get("title", "")).strip()
    if not title:
        return None
    return PopularDestinationItem(
        title=title,
        city=city,
        address=str(item.get("addr1", "")).strip() or None,
        image_url=str(item.get("firstimage", "")).strip() or None,
    )


class SeasonalFeedService:
    def __init__(self, tour_api_client: TourApiClient | None = None):
        self.tour_api_client = tour_api_client or TourApiClient(settings)

    def get_seasonal_feed(self) -> SeasonalFeedResponse:
        festivals: list[FestivalItem] = []
        popular_destinations: list[PopularDestinationItem] = []

        for city in SUPPORTED_CITIES:
            festivals.extend(self._fetch_city_festivals(city))
            popular_destinations.extend(self._fetch_city_popular_destinations(city))

        return SeasonalFeedResponse(
            season=determine_current_season(),
            festivals=festivals,
            popular_destinations=popular_destinations,
        )

    def _fetch_city_festivals(self, city: str) -> list[FestivalItem]:
        # Best-effort per city: TourApiClient's own methods already
        # return None rather than raising on failure, but this extra
        # guard means one city's unexpected error (or a future client
        # bug) can never take the whole feed down with it - matches this
        # feature's "API 실패 시 화면이 깨지지 않고 안전하게 처리" requirement.
        try:
            raw_festivals = self.tour_api_client.fetch_festivals_this_month(city)
        except Exception:
            return []

        items: list[FestivalItem] = []
        for raw_festival in raw_festivals or []:
            festival = _to_festival_item(raw_festival, city)
            if festival is not None:
                items.append(festival)
        return items

    def _fetch_city_popular_destinations(self, city: str) -> list[PopularDestinationItem]:
        try:
            raw_destinations = self.tour_api_client.fetch_popular_destinations(city)
        except Exception:
            return []

        items: list[PopularDestinationItem] = []
        for raw_destination in raw_destinations or []:
            destination = _to_popular_destination_item(raw_destination, city)
            if destination is not None:
                items.append(destination)
        return items


seasonal_feed_service = SeasonalFeedService()
