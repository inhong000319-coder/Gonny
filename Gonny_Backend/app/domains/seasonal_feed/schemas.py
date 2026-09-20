from typing import Literal

from pydantic import BaseModel, ConfigDict


Season = Literal["spring", "summer", "autumn", "winter"]


class FestivalItem(BaseModel):
    title: str
    # Internal city code (seoul/busan/jeju), not a display label - the
    # frontend localizes this the same way it already does for other
    # city codes elsewhere (e.g. rule_planner's RuleItineraryResponse.city).
    city: str
    start_date: str
    end_date: str
    address: str | None = None
    image_url: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class PopularDestinationItem(BaseModel):
    title: str
    city: str
    address: str | None = None
    image_url: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class SeasonalFeedResponse(BaseModel):
    season: Season
    festivals: list[FestivalItem]
    popular_destinations: list[PopularDestinationItem]
