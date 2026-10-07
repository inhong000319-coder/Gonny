from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import CatalogCityOption, FeaturedVideoData


BudgetBand = Literal["low", "medium", "high"]
TripConcept = Literal["food", "shopping", "relax", "sightseeing", "culture", "nature", "activity", "nightlife", "onsen"]
TripStyle = Literal["tight", "easy", "near-stay", "mobility-first"]
CompanionType = Literal["solo", "couple", "friend", "family"]
AccommodationTypeLabel = Literal["호텔", "모텔", "호스텔", "펜션·민박", "콘도미니엄"]
TimeSlot = Literal["morning", "afternoon", "evening"]
TransportMode = Literal["walk", "transit", "car"]
TravelEstimateSource = Literal["estimate", "api"]
TravelLegPointKind = Literal["accommodation", "place", "meal"]


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
    # Lodging-only budget. Left unset, accommodation scoring uses budget_band.
    accommodation_budget_band: BudgetBand | None = None
    accommodation_types: list[AccommodationTypeLabel] | None = None
    # Trip start date. Optional - without it there's no way to map a
    # day_number to a weekday, so closed-day exclusion (see
    # RuleClosedDayExclusion) simply never triggers.
    start_date: date | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryItem(BaseModel):
    day_number: int
    time_slot: TimeSlot
    place_name: str
    category: str
    area: str
    notes: str
    # Straight-line travel-time estimate from the previous slot's place to
    # this one (see travel_estimate.estimate_travel_minutes_between) - None
    # for a day's first slot (no previous place) or a full-day place (all
    # slots are the same place, so there's no real transition to report).
    travel_minutes_from_previous: int | None = None
    # Copied from the source PlaceData.average_cost_krw - see that field's docstring
    # for the 0 (free) vs None (unknown) distinction. Not set for food places.
    average_cost_krw: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleTravelOption(BaseModel):
    mode: TransportMode
    minutes: int

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleTravelLeg(BaseModel):
    """One point-to-point leg of a day's travel, with every transport
    mode's estimated time. source is always "estimate" for now
    (straight-line + mode profile, see services/travel_estimate.py) -
    "api" is reserved for a future real-routing provider."""

    day_number: int
    from_name: str
    to_name: str
    from_kind: TravelLegPointKind
    to_kind: TravelLegPointKind
    distance_km: float
    options: list[RuleTravelOption]
    source: TravelEstimateSource = "estimate"

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleDayTravel(BaseModel):
    day_number: int
    legs: list[RuleTravelLeg]
    # Each total sums, leg by leg, the smaller of that leg's own mode time
    # and its walk option's time (when the leg has one) - a leg short
    # enough to walk is assumed walked regardless of which mode is being
    # totaled.
    transit_total_minutes: int
    car_total_minutes: int
    # How many legs this day *should* have structurally (one per adjacent
    # pair in the day's place/meal sequence, plus 2 if an accommodation was
    # recommended for the trip) - counted independent of whether either end
    # actually has coordinates. missing_leg_count = expected - len(legs), so
    # a day whose totals only reflect part of its real travel (because some
    # place/accommodation lacks coordinates) can be told apart from one
    # that's genuinely fully estimated. See
    # RuleItineraryService._build_day_travel.
    expected_leg_count: int
    missing_leg_count: int

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleMealRecommendation(BaseModel):
    # Field shape deliberately mirrors RuleItineraryItem (minus category,
    # which every meal implicitly is "food") so the frontend can reuse
    # rendering patterns - see accommodation_recommendation for the same
    # "recommended independently of the 3-slot competition" spirit, just
    # repeated per day instead of once for the whole trip (see
    # RuleItineraryService._recommend_meals).
    day_number: int
    meal_type: Literal["lunch", "dinner"]
    place_name: str
    area: str
    notes: str
    travel_minutes_from_previous: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleDayDurationWarning(BaseModel):
    day_number: int
    estimated_total_minutes: int
    message: str

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleClosedDayExclusion(BaseModel):
    day_number: int
    place_name: str
    message: str

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleWeatherAlert(BaseModel):
    day_number: int
    condition: Literal["rain", "snow"]
    precipitation_mm: float
    affected_place_names: list[str]
    suggested_alternatives: list[str] = Field(default_factory=list)

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
    # Used only by accommodation scoring. Activities, meals and weather keep
    # reading budget_band.
    accommodation_budget_band: BudgetBand
    # Preference only: matching adds a score bonus, never filters candidates.
    accommodation_types: list[AccommodationTypeLabel] = Field(default_factory=list)
    start_date: date | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def _default_accommodation_budget_band(cls, data):
        if isinstance(data, dict) and data.get("accommodation_budget_band") is None:
            return {**data, "accommodation_budget_band": data.get("budget_band")}
        return data


class RuleCostEstimate(BaseModel):
    """Estimated trip cost range covering tourist admission fees and the
    recommended accommodation only. Restaurant meals and transportation are
    deliberately excluded.

    min_krw sums confirmed prices. max_krw adds a conservative per-place cap
    for admissions whose fee is unknown. The accommodation is included only
    when its nightly rate is confirmed.
    """

    min_krw: int
    max_krw: int
    priced_place_count: int
    unpriced_place_count: int
    accommodation_included: bool
    nights: int
    travelers: int


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
    featured_video: FeaturedVideoData | None = None
    items: list[RuleItineraryItem]
    day_duration_warnings: list[RuleDayDurationWarning] = Field(default_factory=list)
    closed_day_exclusions: list[RuleClosedDayExclusion] = Field(default_factory=list)
    weather_alerts: list[RuleWeatherAlert] = Field(default_factory=list)
    accommodation_recommendation: AccommodationData | None = None
    meal_recommendations: list[RuleMealRecommendation] = Field(default_factory=list)
    estimated_cost: RuleCostEstimate | None = None
    day_travel: list[RuleDayTravel] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryCatalogResponse(BaseModel):
    cities: list[CatalogCityOption]
