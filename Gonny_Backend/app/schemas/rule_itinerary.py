from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


BudgetBand = Literal["low", "medium", "high"]
TripConcept = Literal["food", "shopping", "relax", "sightseeing", "culture", "nature"]
TripStyle = Literal["tight", "easy", "near-stay", "mobility-first"]
CompanionType = Literal["solo", "couple", "friend", "family"]
TimeSlot = Literal["morning", "afternoon", "evening"]


class RuleItineraryRequest(BaseModel):
    continent: str | None = None
    country: str | None = None
    city: str | None = None
    travelers: int | None = Field(default=2, ge=1, le=20)
    nights: int | None = Field(default=None, ge=1, le=30)
    days: int | None = Field(default=None, ge=1, le=31)
    duration_label: str | None = None
    budget_value: int | None = Field(default=None, ge=0)
    budget_band: BudgetBand | None = None
    concepts: list[TripConcept] | None = None
    style: TripStyle | None = None
    companion_type: CompanionType | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryItem(BaseModel):
    day_number: int
    time_slot: TimeSlot
    place_name: str
    category: str
    area: str
    notes: str

    model_config = ConfigDict(str_strip_whitespace=True)


class NormalizedRuleRequest(BaseModel):
    continent: str
    country: str
    city: str
    travelers: int
    nights: int
    days: int
    budget_band: BudgetBand
    concepts: list[TripConcept]
    style: TripStyle
    companion_type: CompanionType

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryResponse(BaseModel):
    continent: str
    country: str
    city: str
    travelers: int
    nights: int
    days: int
    budget_band: BudgetBand
    concepts: list[TripConcept]
    style: TripStyle
    companion_type: CompanionType
    items: list[RuleItineraryItem]

    model_config = ConfigDict(str_strip_whitespace=True)


class CatalogCityOption(BaseModel):
    continent: str
    country: str
    city: str
    aliases: list[str]


class RuleItineraryCatalogResponse(BaseModel):
    cities: list[CatalogCityOption]
