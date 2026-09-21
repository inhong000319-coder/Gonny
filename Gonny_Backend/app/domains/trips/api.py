from typing import Generic, TypeVar

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.trips.schemas import (
    ExpenseCreate,
    ExpenseCreateResponse,
    ExpenseListData,
    ExpenseSummaryData,
    ShareLinkCreateRequest,
    ShareLinkResponse,
    TripCreate,
    TripDetailResponse,
    TripFavoriteUpdate,
    TripReportResponse,
    TripResponse,
    TripRetrospectiveUpdate,
)
from app.domains.trips.services.service import trip_service


router = APIRouter(prefix="/trips", tags=["trips"])

T = TypeVar("T")


class ApiSuccessResponse(BaseModel, Generic[T]):
    """{success, data, message} envelope - matches the frontend's
    pre-existing ApiSuccessResponse<T> contract for the expense endpoints
    (features/budget/api/*.ts), written before these endpoints existed."""

    success: bool = True
    data: T
    message: str = "성공"

# Separate, unprefixed router for the public /share/{token} lookup - it's
# not a /trips/{trip_id} sub-resource (no trip_id is known to the caller,
# only the opaque token), and unlike every other endpoint in this router
# it's meant to be reachable by someone who never logged in.
share_router = APIRouter(tags=["trip-share"])


@router.post("", response_model=TripResponse)
def create_trip(trip: TripCreate, db: Session = Depends(get_db)):
    return trip_service.create_trip(db=db, request=trip)


@router.get("", response_model=list[TripResponse])
def list_trips(db: Session = Depends(get_db)):
    return trip_service.list_trips(db=db)


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    return trip_service.get_trip_or_404(db=db, trip_id=trip_id)


@router.patch("/{trip_id}/favorite", response_model=TripResponse)
def update_trip_favorite(
    trip_id: int,
    payload: TripFavoriteUpdate,
    db: Session = Depends(get_db),
):
    return trip_service.update_trip_favorite(db=db, trip_id=trip_id, payload=payload)


@router.post("/{trip_id}/share", response_model=ShareLinkResponse)
def create_share_link(
    trip_id: int,
    payload: ShareLinkCreateRequest,
    db: Session = Depends(get_db),
):
    return trip_service.create_share_link(db=db, trip_id=trip_id, payload=payload)


@share_router.get("/share/{token}", response_model=TripDetailResponse)
def get_shared_trip(token: str, db: Session = Depends(get_db)):
    return trip_service.get_trip_by_share_token(db=db, token=token)


@router.patch("/{trip_id}/retrospective", response_model=TripResponse)
def update_trip_retrospective(
    trip_id: int,
    payload: TripRetrospectiveUpdate,
    db: Session = Depends(get_db),
):
    return trip_service.update_trip_retrospective(db=db, trip_id=trip_id, payload=payload)


@router.post("/{trip_id}/expenses", response_model=ApiSuccessResponse[ExpenseCreateResponse])
def create_expense(
    trip_id: int,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
):
    data = trip_service.create_expense(db=db, trip_id=trip_id, payload=payload)
    return ApiSuccessResponse(data=data)


@router.get("/{trip_id}/expenses", response_model=ApiSuccessResponse[ExpenseListData])
def list_expenses(trip_id: int, db: Session = Depends(get_db)):
    data = trip_service.list_expenses(db=db, trip_id=trip_id)
    return ApiSuccessResponse(data=data)


@router.get("/{trip_id}/expenses/summary", response_model=ApiSuccessResponse[ExpenseSummaryData])
def get_expense_summary(trip_id: int, db: Session = Depends(get_db)):
    data = trip_service.get_expense_summary(db=db, trip_id=trip_id)
    return ApiSuccessResponse(data=data)


@router.get("/{trip_id}/report", response_model=TripReportResponse)
def get_trip_report(trip_id: int, db: Session = Depends(get_db)):
    return trip_service.get_trip_report(db=db, trip_id=trip_id)


@router.get("/{trip_id}/pdf")
def get_trip_pdf(trip_id: int, db: Session = Depends(get_db)):
    pdf_bytes = trip_service.generate_trip_pdf(db=db, trip_id=trip_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="trip_{trip_id}.pdf"'},
    )
