from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.itinerary import ItineraryItemResponse


class TripStayInput(BaseModel):
    """One stay in TripCreate.stays (#135) - see TripService.
    _validate_and_resolve_stays for the save-time validation (sum of
    nights, allowed_partitions membership, known accommodation id,
    distinct adjacent accommodations). accommodation_id is typed optional
    to mirror the backend #133 contract's shape, but a None entry is
    always rejected (422) - a stays-based save is only ever for a result
    whose accommodations are already chosen."""

    nights: int
    accommodation_id: str | None = None


class TripCreate(BaseModel):
    title: str | None = None
    destination: str
    start_date: date
    end_date: date
    budget: int
    travel_style: str
    companion_type: str
    # Looked up by id against destination's accommodation list at save
    # time (see TripService.create_trip) - the client never sends a name
    # or type directly, both are server-filled snapshots. None (default)
    # saves no accommodation, same as every trip before this field existed.
    accommodation_id: str | None = None
    # #135 - multi-stay save. None (default) is the pre-#135 single-
    # accommodation path above, untouched. Mutually exclusive with
    # accommodation_id (422 if both are sent) - see TripService.
    # _validate_and_resolve_stays.
    stays: list[TripStayInput] | None = None


class TripStayResponse(BaseModel):
    stay_index: int
    start_night: int
    nights: int
    accommodation_id: str
    accommodation_name: str
    accommodation_type: str

    model_config = ConfigDict(from_attributes=True)


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
    satisfaction_rating: int | None = None
    retrospective_note: str | None = None
    # Snapshot taken at save time (see Trip.accommodation_id's docstring) -
    # null on any trip saved without an accommodation_id, including every
    # trip created before this field existed. Always mirrors stays[0] when
    # stays is non-empty (kept in lockstep at write time - see
    # TripService.create_trip/update_trip_accommodation).
    accommodation_id: str | None = None
    accommodation_name: str | None = None
    accommodation_type: str | None = None
    # #135 - always populated (never absent), [] only when there's truly
    # no accommodation at all. Mapped straight from Trip.stays when that
    # relationship has rows; when it's empty but the legacy
    # accommodation_name above is set (every trip saved before #135, or
    # saved since via the single accommodation_id path - see
    # TripService.create_trip's design note), _synthesize_legacy_stay
    # below fills in a single synthesized entry instead. The DB itself is
    # never changed by this synthesis.
    stays: list[TripStayResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _synthesize_legacy_stay(self) -> "TripResponse":
        if self.stays or not self.accommodation_name:
            return self
        total_nights = max((self.end_date - self.start_date).days, 1)
        self.stays = [
            TripStayResponse(
                stay_index=0,
                start_night=1,
                nights=total_nights,
                accommodation_id=self.accommodation_id or "",
                accommodation_name=self.accommodation_name,
                accommodation_type=self.accommodation_type or "",
            )
        ]
        return self


class TripDetailResponse(TripResponse):
    itinerary_items: list[ItineraryItemResponse]


class TripFavoriteUpdate(BaseModel):
    is_favorite: bool


# --- Accommodation change (after save) -----------------------------------
# A saved trip never keeps the generation-time accommodation_alternatives
# (those live only in RuleItineraryResponse, never persisted) - these two
# endpoints are how a client re-picks or clears the accommodation after
# the fact. See TripService.list_accommodation_options /
# update_trip_accommodation.


class TripAccommodationOption(BaseModel):
    """One candidate for PATCH /trips/{id}/accommodation's accommodation_id
    - deliberately narrower than AccommodationData (no coordinates/
    amenities/etc.), since this is a picker list, not the full catalog
    record."""

    id: str
    name: str
    accommodation_type: str
    area: str
    average_price_krw: int | None = None


class TripAccommodationUpdate(BaseModel):
    # No default - the body must always say explicitly either an id or
    # null, mirroring the endpoint's own contract
    # ({"accommodation_id": string | null}). null clears all three
    # snapshot columns; the client can never send name/type directly
    # (no such fields on this schema - same reasoning as TripCreate's
    # accommodation_id).
    accommodation_id: str | None
    # #135 - which stay this change targets. Defaults to 0 so every
    # existing single-accommodation PATCH call is unaffected. Ignored
    # entirely when accommodation_id is null (that always clears every
    # stay - see TripService.update_trip_accommodation).
    stay_index: int = 0


class ShareLinkCreateRequest(BaseModel):
    expires_in: Literal["1d", "7d", "unlimited"] = "7d"


class ShareLinkResponse(BaseModel):
    share_url: str
    token: str
    expires_at: datetime | None


class TripRetrospectiveUpdate(BaseModel):
    satisfaction_rating: int | None = Field(default=None, ge=1, le=5)
    retrospective_note: str | None = None


# --- Expenses -----------------------------------------------------------
# Response envelope matches the frontend's pre-existing ApiSuccessResponse<T>
# contract (features/budget/api/*.ts, features/budget/types/budget.ts) -
# those were written against this exact shape well before this endpoint
# existed, so matching it here avoids touching already-working frontend code.


class ExpenseCreate(BaseModel):
    category: str
    amount: int
    currency: str = "KRW"
    note: str | None = None
    spent_at: date | None = None


class ExpenseCreateResponse(BaseModel):
    expense_id: int
    category: str
    amount_krw: int
    # 숙박(LODGING_EXPENSE_CATEGORY) 지출을 뺀 금액 기준 - ExpenseSummaryData와 동일한 규칙.
    remaining_budget: int
    budget_usage_pct: float
    # 숙박 지출 합계(참고용) - remaining_budget/budget_usage_pct에는 포함되지 않는다.
    lodging_spent: int = 0


class ExpenseItem(BaseModel):
    expense_id: int
    category: str
    amount_krw: int
    note: str | None = None


class ExpenseListData(BaseModel):
    expenses: list[ExpenseItem]


class ExpenseSummaryData(BaseModel):
    total_budget: int
    # 숙박(LODGING_EXPENSE_CATEGORY) 지출을 뺀 금액 - remaining/usage_pct/
    # is_over_budget도 전부 이 값 기준이다. 숙박 지출 자체는 lodging_spent로
    # 따로 내려준다(예산 비교에는 포함되지 않음).
    total_spent: int
    remaining: int
    usage_pct: float
    is_over_budget: bool
    lodging_spent: int = 0


# --- Retrospective report (F14) -----------------------------------------


class TripCategoryBreakdownItem(BaseModel):
    category: str
    amount_krw: int


class TripReportResponse(BaseModel):
    ready: bool
    # Set only when ready=False (e.g. "trip hasn't ended yet") - every
    # field below is meaningless until then, so they all default to
    # empty/None rather than being required.
    message: str | None = None

    # 숙박(LODGING_EXPENSE_CATEGORY) 지출을 뺀 금액 - budget_diff_pct도 이 값
    # 기준이다. 숙박 지출 합계는 lodging_spent로 따로 내려준다.
    total_spent: int | None = None
    lodging_spent: int | None = None
    budget: int | None = None
    budget_diff_pct: float | None = None
    category_breakdown: list[TripCategoryBreakdownItem] = Field(default_factory=list)

    # See get_trip_report()'s docstring: itinerary item count is the most
    # honest proxy we have for "places visited" - there's no check-in concept.
    visited_count: int | None = None

    # distance_km is None ("정보 없음") whenever fewer than 2 consecutive
    # itinerary items could be matched to catalog coordinates - see
    # _compute_trip_distance(). matched/total counts are always reported
    # so the frontend can show *why* distance might be missing.
    distance_km: float | None = None
    matched_place_count: int = 0
    total_place_count: int = 0

    insights: list[str] = Field(default_factory=list)

    satisfaction_rating: int | None = None
    retrospective_note: str | None = None
