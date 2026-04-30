from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripDetailResponse, TripFavoriteUpdate, TripResponse


router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=TripResponse)
def create_trip(trip: TripCreate, db: Session = Depends(get_db)):
    db_trip = Trip(
        title=trip.title or f"{trip.destination} 여행",
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        travel_style=trip.travel_style,
        companion_type=trip.companion_type,
    )
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip


@router.get("", response_model=list[TripResponse])
def list_trips(db: Session = Depends(get_db)):
    trips = db.query(Trip).order_by(Trip.id.desc()).all()
    return trips


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.patch("/{trip_id}/favorite", response_model=TripResponse)
def update_trip_favorite(trip_id: int, payload: TripFavoriteUpdate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if payload.is_favorite and not trip.is_favorite:
        favorite_count = db.query(func.count(Trip.id)).filter(Trip.is_favorite.is_(True)).scalar() or 0
        if favorite_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="즐겨찾기 여행은 최대 3개까지 등록할 수 있어요.",
            )

    trip.is_favorite = payload.is_favorite
    db.commit()
    db.refresh(trip)
    return trip
