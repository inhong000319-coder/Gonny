from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ItineraryGenerationRequest(BaseModel):
    destination: str
    start_date: date
    end_date: date
    budget: int
    travel_style: str
    companion_type: str


class GeneratedItineraryItem(BaseModel):
    time_slot: Literal["morning", "afternoon", "evening"]
    place_name: str
    category: str
    notes: str

    model_config = ConfigDict(str_strip_whitespace=True)


class GeneratedItineraryDay(BaseModel):
    day_number: int
    items: list[GeneratedItineraryItem]


class GeneratedItineraryResponse(BaseModel):
    days: list[GeneratedItineraryDay]


class PlaceholderLLMResponse(BaseModel):
    days: list[GeneratedItineraryDay]
