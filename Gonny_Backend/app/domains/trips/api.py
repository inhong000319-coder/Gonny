from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.trips.schemas import (
    ShareLinkCreateRequest,
    ShareLinkResponse,
    TripCreate,
    TripDetailResponse,
    TripFavoriteUpdate,
    TripResponse,
)
from app.domains.trips.services.service import trip_service


router = APIRouter(prefix="/trips", tags=["trips"])

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
