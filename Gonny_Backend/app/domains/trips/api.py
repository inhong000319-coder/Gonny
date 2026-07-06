from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.trips.schemas import TripCreate, TripDetailResponse, TripFavoriteUpdate, TripResponse
from app.domains.trips.services.service import trip_service


router = APIRouter(prefix="/trips", tags=["trips"])


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
