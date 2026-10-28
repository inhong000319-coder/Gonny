from datetime import date
from datetime import date as _CalendarDate
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
# Per-day transport mode the user actually picks for the trip (no "walk" -
# that's a per-leg day_travel option, not a day-level plan). Drives scoring
# (see slot_scoring.py, accommodation_scoring.py) - see
# services/request_normalizer.py for the length-matches-days validation.
DayTransportMode = Literal["transit", "car"]
TravelLegPointKind = Literal["accommodation", "place", "meal"]
# First day's arrival time-of-day. None/"morning" means "no restriction" -
# every code path reading this must treat them identically (same as
# transport_by_day=None meaning "no mode-aware scoring"). See
# services/arrival_departure.py for what each value excludes.
ArrivalPeriod = Literal["morning", "afternoon", "evening", "night"]
# Last day's departure time-of-day. None/"evening_or_later" means "no
# restriction" - see services/arrival_departure.py.
DeparturePeriod = Literal["before_lunch", "afternoon", "evening_or_later"]


class RuleFixedSlotAssignment(BaseModel):
    """One (day, slot) -> place pin for POST /rule-itinerary/recalculate -
    see RuleItineraryRecalculateRequest. Every allowed slot of every day
    must be pinned exactly once (see services/recalculate.py's
    validation) - there is no partial-fix mode."""

    day_number: int
    time_slot: TimeSlot
    place_id: str

    model_config = ConfigDict(str_strip_whitespace=True)


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
    # One entry per day (index 0 = day 1), or None to skip mode-aware
    # scoring entirely. Length is checked against the normalized day count
    # in services/request_normalizer.py, not here - this model doesn't know
    # the trip's duration yet.
    transport_by_day: list[DayTransportMode] | None = None
    # Trip start date. Optional - without it there's no way to map a
    # day_number to a weekday, so closed-day exclusion (see
    # RuleClosedDayExclusion) simply never triggers.
    start_date: date | None = None
    # Day-1 arrival / last-day departure time-of-day, and whether to add a
    # breakfast recommendation. All optional and all default to "no
    # restriction" - see services/arrival_departure.py for the exact
    # slot/meal availability each value implies.
    arrival_period: ArrivalPeriod | None = None
    departure_period: DeparturePeriod | None = None
    include_breakfast: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryRecalculateRequest(RuleItineraryRequest):
    """POST /rule-itinerary/recalculate - every RuleItineraryRequest field
    (same trip-level context: city/budget/concepts/.../start_date) plus a
    full, explicit slot-by-slot place pinning. See services/recalculate.py
    for the validation this goes through before RuleItineraryService.
    _build_items ever sees it (unknown/inactive/food place, disallowed or
    missing/duplicate slot, cross-day or partial-day place reuse, closed-
    day place) and RuleItineraryService.recalculate for how it's used.
    Inherits RuleItineraryRequest's own fields/model_config rather than
    duplicating them, so the two request shapes can never drift apart."""

    fixed_slots: list[RuleFixedSlotAssignment]
    # None = pick the accommodation the normal way (same as generate()).
    # When set, must be one of the city's own accommodations (see
    # services/recalculate.py) - the recommendation is pinned to it and
    # the alternatives are the top 3 of the same ranking with this one
    # excluded, same spirit as fixed_slots pinning an activity place.
    accommodation_id: str | None = None


class RuleReason(BaseModel):
    """One fact-based reason a place was recommended - see
    services/reasons.py. Never carries a score number or internal
    weighting, only a stable code (for the frontend to key off of) and a
    ready-to-display Korean label."""

    code: str
    label: str

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleSlotAlternative(BaseModel):
    """One other place that could have filled this same slot - see
    services/slot_alternatives.py. Computed as a read-only post-process
    after the real selection is final, so its presence/order never
    changes which place RuleItineraryItem itself picked."""

    place_id: str
    place_name: str
    category: str
    area: str
    notes: str
    average_cost_krw: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryItem(BaseModel):
    day_number: int
    time_slot: TimeSlot
    # Added alongside POST /rule-itinerary/recalculate (additive, backward
    # compatible) - set on every item (normal and full-day alike) by
    # RuleItineraryService._build_items, so a client can round-trip a
    # generate() response straight into a recalculate() request's
    # fixed_slots without needing a separate name/id lookup.
    place_id: str | None = None
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
    # Up to 3 fact-based reasons this place was recommended - see
    # services/reasons.py. Empty list is valid (a place can have none).
    reasons: list[RuleReason] = Field(default_factory=list)
    # Up to 3 other places that scored well for this same slot - see
    # services/slot_alternatives.py. Always empty for a full-day item (all
    # 3 slots are the same place, so there's no meaningful "instead of
    # this" swap) and whenever generate() was called with
    # include_alternatives=False (e.g. compare_transport's scenario runs).
    alternatives: list[RuleSlotAlternative] = Field(default_factory=list)

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
    meal_type: Literal["breakfast", "lunch", "dinner"]
    place_name: str
    area: str
    notes: str
    travel_minutes_from_previous: int | None = None
    # True only for breakfast - the catalog has almost no verified opening
    # hours for food places (see services/breakfast.py), so a breakfast
    # recommendation is picked by keyword signal alone and may not
    # actually be open that early. Always False for lunch/dinner.
    hours_unverified: bool = False
    # Same contract as RuleItineraryItem.reasons - meals only ever get a
    # travel-based or meal-time-fit reason (see services/reasons.py), never
    # an hours-related one, since hours_unverified already covers that.
    reasons: list[RuleReason] = Field(default_factory=list)

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


WeatherCheckStatus = Literal["checked", "out_of_range", "past", "unavailable", "no_start_date"]


class RuleDayWeatherStatus(BaseModel):
    day_number: int
    date: _CalendarDate | None = None
    status: WeatherCheckStatus
    condition: Literal["clear", "cloudy", "rain", "snow"] | None = None
    min_temp_c: float | None = None
    max_temp_c: float | None = None

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
    # Validated (length == days) in request_normalizer.normalize_rule_request.
    # None means "no mode-aware scoring" - every code path reading this must
    # treat None exactly like before this field existed.
    transport_by_day: list[DayTransportMode] | None = None
    start_date: date | None = None
    arrival_period: ArrivalPeriod | None = None
    departure_period: DeparturePeriod | None = None
    include_breakfast: bool = False

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


class RuleDaySummary(BaseModel):
    """One day's at-a-glance load - place/area counts and estimated time,
    with no invented "intensity tier" label (see services/reasons.py's
    day-summary builder - the frontend decides how to phrase/bucket these
    numbers, this just reports them)."""

    day_number: int
    # Activity places only (meals excluded) - see day_place_map.
    place_count: int
    area_count: int
    # Sum of each activity place's duration_hours * 60. Meals excluded,
    # same as place_count.
    activity_minutes: int
    # None when there's no RuleDayTravel entry for this day, or it has no
    # legs at all (nothing to sum) - never 0 in that case, since 0 would
    # misleadingly claim "no travel time" rather than "no data".
    travel_minutes: int | None = None
    # True when the day's RuleDayTravel.missing_leg_count > 0 - travel_minutes
    # only reflects the legs that could be estimated.
    travel_is_partial: bool = False
    # Echoes request.transport_by_day[day_number - 1], or None if the
    # request didn't set one - see travel_minutes for how a None here still
    # resolves to a concrete number via a default mode assumption.
    transport_mode: DayTransportMode | None = None

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
    featured_video: FeaturedVideoData | None = None
    items: list[RuleItineraryItem]
    day_duration_warnings: list[RuleDayDurationWarning] = Field(default_factory=list)
    closed_day_exclusions: list[RuleClosedDayExclusion] = Field(default_factory=list)
    weather_alerts: list[RuleWeatherAlert] = Field(default_factory=list)
    weather_status: list[RuleDayWeatherStatus] = Field(default_factory=list)
    accommodation_recommendation: AccommodationData | None = None
    # Up to 3 other stays, ranked 2nd-4th by the exact same pool/score/tie-
    # break as accommodation_recommendation itself (see
    # accommodation_scoring.rank_accommodations) - never a separately
    # computed ranking. Empty whenever include_alternatives=False (e.g.
    # compare_transport's scenario runs) or there's no recommendation at all.
    accommodation_alternatives: list[AccommodationData] = Field(default_factory=list)
    meal_recommendations: list[RuleMealRecommendation] = Field(default_factory=list)
    estimated_cost: RuleCostEstimate | None = None
    day_travel: list[RuleDayTravel] = Field(default_factory=list)
    # Echoes the request's per-day mode back (or None) so the frontend can
    # use it as the day_travel toggle's starting selection.
    transport_by_day: list[DayTransportMode] | None = None
    # Echoes the request's arrival/departure/breakfast choices back, same
    # spirit as transport_by_day above.
    arrival_period: ArrivalPeriod | None = None
    departure_period: DeparturePeriod | None = None
    include_breakfast: bool = False
    day_summaries: list[RuleDaySummary] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleItineraryCatalogResponse(BaseModel):
    cities: list[CatalogCityOption]


TransportComparisonScenario = Literal["all_transit", "all_car"]


class RuleTransportScenarioTotals(BaseModel):
    """Trip-wide travel totals for one transport scenario (the actual
    request, or an all-transit/all-car what-if) - see
    services/compare_transport.py. Numbers are read straight from that
    scenario's own RuleDaySummary.travel_minutes, never recomputed."""

    transport_by_day: list[DayTransportMode] | None
    total_travel_minutes: int | None
    any_partial: bool

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleTransportComparisonDay(BaseModel):
    day_number: int
    base_mode: DayTransportMode | None
    scenario_mode: DayTransportMode | None
    base_travel_minutes: int | None
    scenario_travel_minutes: int | None
    base_partial: bool
    scenario_partial: bool
    # Place names present on this day in one side but not the other,
    # compared at (day_number, time_slot) granularity (see
    # services/compare_transport.py for why place_name is the identity
    # key - RuleItineraryItem has no catalog id field).
    only_in_base: list[str] = Field(default_factory=list)
    only_in_scenario: list[str] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleTransportComparison(BaseModel):
    scenario: TransportComparisonScenario
    transport_by_day: list[DayTransportMode]
    total_travel_minutes: int | None
    any_partial: bool
    # scenario total - base total; None whenever either side is None (see
    # RuleTransportScenarioTotals.total_travel_minutes).
    travel_minutes_delta: int | None
    # True iff every day's (time_slot -> place_name) set is identical to
    # base - see RuleTransportComparisonDay.only_in_base/only_in_scenario.
    same_places: bool
    days: list[RuleTransportComparisonDay]
    # Count of days where any meal's place_name differs from base (a day
    # with 2 changed meals still counts once).
    meal_changes: int

    model_config = ConfigDict(str_strip_whitespace=True)


class RuleTransportComparisonResponse(BaseModel):
    base: RuleTransportScenarioTotals
    comparisons: list[RuleTransportComparison] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)
