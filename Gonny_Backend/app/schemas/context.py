"""Schemas for travel-context features (F03~F08, F15)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


TripCategory = Literal[
    "attraction",
    "museum",
    "restaurant",
    "cafe",
    "shopping",
    "activity",
    "nature",
    "custom",
]

TransportMode = Literal["public", "car", "walk", "mixed"]
WeatherCondition = Literal["clear", "cloudy", "rain", "snow"]


class ItinerarySpotInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category: TripCategory = "custom"
    manual_duration_min: int | None = Field(default=None, ge=15, le=360)


class DurationEstimateRequest(BaseModel):
    spots: list[ItinerarySpotInput] = Field(..., min_length=1, max_length=40)
    transport_mode: TransportMode = "mixed"
    avg_move_distance_km: float = Field(default=3.0, ge=0.1, le=50.0)


class SpotDurationResult(BaseModel):
    name: str
    category: TripCategory
    stay_duration_min: int
    move_duration_min_from_previous: int = 0
    total_slot_duration_min: int


class DurationEstimateResponse(BaseModel):
    spots: list[SpotDurationResult]
    total_duration_min: int
    warning: str | None = None


class WeatherForecastInput(BaseModel):
    forecast_date: date
    condition: WeatherCondition
    min_temp_c: float = Field(..., ge=-60, le=60)
    max_temp_c: float = Field(..., ge=-60, le=60)


class WeatherPlanSlot(BaseModel):
    day_label: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=120)
    is_outdoor: bool = True


class WeatherAdjustmentRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=80)
    forecasts: list[WeatherForecastInput] = Field(default_factory=list, max_length=10)
    plan_slots: list[WeatherPlanSlot] = Field(default_factory=list, max_length=40)


class WeatherAlternative(BaseModel):
    title: str
    category: str
    reason: str


class WeatherAdjustmentItem(BaseModel):
    forecast_date: date
    condition: WeatherCondition
    alert_message: str
    alternatives: list[WeatherAlternative]


class WeatherAdjustmentResponse(BaseModel):
    destination: str
    generated_from_live_weather: bool
    adjustments: list[WeatherAdjustmentItem]


PreferenceTag = Literal["food", "nature", "culture", "shopping", "healing", "activity"]


class CompanionPreferenceInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    tags: list[PreferenceTag] = Field(default_factory=list, max_length=6)
    is_child: bool = False


class PreferenceMergeRequest(BaseModel):
    companions: list[CompanionPreferenceInput] = Field(..., min_length=1, max_length=4)
    base_trip_tags: list[PreferenceTag] = Field(default_factory=list, max_length=6)


class PreferenceWeight(BaseModel):
    tag: PreferenceTag
    weight_percent: float


class PreferenceMergeResponse(BaseModel):
    weights: list[PreferenceWeight]
    summary: str


AccommodationType = Literal[
    "hotel",
    "resort",
    "pension",
    "guesthouse",
    "airbnb",
    "camping",
]

BudgetLevel = Literal["value", "mid", "premium"]


class AccommodationRecommendRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=80)
    nights: int = Field(..., ge=1, le=30)
    budget_level: BudgetLevel = "mid"
    preferred_types: list[AccommodationType] = Field(default_factory=list, max_length=6)
    companions_count: int = Field(default=1, ge=1, le=8)


class AccommodationOption(BaseModel):
    name: str
    accommodation_type: AccommodationType
    price_per_night_krw: int
    distance_to_center_km: float
    highlights: list[str]
    booking_url: str


class AccommodationRecommendResponse(BaseModel):
    destination: str
    options: list[AccommodationOption]


class TransportLegInput(BaseModel):
    origin: str = Field(..., min_length=1, max_length=120)
    destination: str = Field(..., min_length=1, max_length=120)
    distance_km: float = Field(default=3.0, ge=0.1, le=200.0)
    origin_lat: float | None = Field(default=None, ge=-90, le=90)
    origin_lng: float | None = Field(default=None, ge=-180, le=180)
    destination_lat: float | None = Field(default=None, ge=-90, le=90)
    destination_lng: float | None = Field(default=None, ge=-180, le=180)


class TransportRecommendRequest(BaseModel):
    transport_mode: TransportMode
    legs: list[TransportLegInput] = Field(..., min_length=1, max_length=40)
    avoid_parking_difficult: bool = False


class TransportLegPlan(BaseModel):
    origin: str
    destination: str
    recommended_mode: TransportMode
    estimated_duration_min: int
    note: str | None = None


class TransportRecommendResponse(BaseModel):
    legs: list[TransportLegPlan]
    total_duration_min: int


MealType = Literal["breakfast", "lunch", "dinner", "cafe"]
CuisineType = Literal["korean", "western", "japanese", "chinese", "brunch", "pub", "vegan"]


class MealSlotInput(BaseModel):
    day_label: str = Field(..., min_length=1, max_length=20)
    meal_type: MealType
    location_hint: str | None = Field(default=None, max_length=100)


class RestaurantRecommendRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=80)
    preferred_cuisines: list[CuisineType] = Field(default_factory=list, max_length=7)
    budget_level: BudgetLevel = "mid"
    dietary_note: str | None = Field(default=None, max_length=120)
    meal_slots: list[MealSlotInput] = Field(..., min_length=1, max_length=20)


class RestaurantOption(BaseModel):
    day_label: str
    meal_type: MealType
    name: str
    cuisine: CuisineType
    estimated_price_krw: int
    rating: float = Field(..., ge=0, le=5)
    reservation_recommended: bool
    map_url: str


class RestaurantRecommendResponse(BaseModel):
    destination: str
    options: list[RestaurantOption]


Season = Literal["spring", "summer", "autumn", "winter"]


class SeasonalFeedItem(BaseModel):
    title: str
    region: str
    season: Season
    reason: str
    tags: list[str]
    source: str


class SeasonalFeedResponse(BaseModel):
    season: Season
    destination: str | None = None
    generated_from_live_api: bool = False
    items: list[SeasonalFeedItem]

