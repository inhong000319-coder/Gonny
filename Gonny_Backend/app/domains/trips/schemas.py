from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    satisfaction_rating: int | None = None
    retrospective_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TripDetailResponse(TripResponse):
    itinerary_items: list[ItineraryItemResponse]


class TripFavoriteUpdate(BaseModel):
    is_favorite: bool


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
    remaining_budget: int
    budget_usage_pct: float


class ExpenseItem(BaseModel):
    expense_id: int
    category: str
    amount_krw: int
    note: str | None = None


class ExpenseListData(BaseModel):
    expenses: list[ExpenseItem]


class ExpenseSummaryData(BaseModel):
    total_budget: int
    total_spent: int
    remaining: int
    usage_pct: float
    is_over_budget: bool


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

    total_spent: int | None = None
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
