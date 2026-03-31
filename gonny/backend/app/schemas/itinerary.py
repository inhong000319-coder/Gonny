from pydantic import BaseModel, ConfigDict


class ItineraryItemCreate(BaseModel):
    day_number: int
    time_slot: str
    place_name: str
    category: str
    notes: str | None = None


class ItineraryItemResponse(BaseModel):
    id: int
    trip_id: int
    day_number: int
    time_slot: str
    place_name: str
    category: str
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
