from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.itinerary import ItineraryItemResponse


class TripCreate(BaseModel):
    destination: str
    start_date: date
    end_date: date
    budget: int
    travel_style: str
    companion_type: str


class TripResponse(BaseModel):
    id: int
    destination: str
    start_date: date
    end_date: date
    budget: int
    travel_style: str
    companion_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripDetailResponse(TripResponse):
    itinerary_items: list[ItineraryItemResponse]
