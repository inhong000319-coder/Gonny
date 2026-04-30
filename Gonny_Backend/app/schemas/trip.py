from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.itinerary import ItineraryItemResponse


class TripCreate(BaseModel):
    title: str | None = None
    destination: str
    start_date: date
    end_date: date
    budget: int
    travel_style: str
    companion_type: str


class TripResponse(BaseModel):
    id: int
    title: str
    destination: str
    start_date: date
    end_date: date
    budget: int
    travel_style: str
    companion_type: str
    is_favorite: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripDetailResponse(TripResponse):
    itinerary_items: list[ItineraryItemResponse]


class TripFavoriteUpdate(BaseModel):
    is_favorite: bool
