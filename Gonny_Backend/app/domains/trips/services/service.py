from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.trips.schemas import TripCreate, TripFavoriteUpdate
from app.models.trip import Trip


class TripService:
    def create_trip(self, *, db: Session, request: TripCreate) -> Trip:
        db_trip = Trip(
            title=request.title or f"{request.destination} \uc5ec\ud589",
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            budget=request.budget,
            travel_style=request.travel_style,
            companion_type=request.companion_type,
        )
        db.add(db_trip)
        db.commit()
        db.refresh(db_trip)
        return db_trip

    def list_trips(self, *, db: Session) -> list[Trip]:
        return db.query(Trip).order_by(Trip.id.desc()).all()

    def get_trip_or_404(self, *, db: Session, trip_id: int) -> Trip:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        return trip

    def update_trip_favorite(
        self,
        *,
        db: Session,
        trip_id: int,
        payload: TripFavoriteUpdate,
    ) -> Trip:
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        if payload.is_favorite and not trip.is_favorite:
            favorite_count = db.query(func.count(Trip.id)).filter(Trip.is_favorite.is_(True)).scalar() or 0
            if favorite_count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="\uc990\uaca8\ucc3e\uae30 \uc5ec\ud589\uc740 \ucd5c\ub300 3\uac1c\uae4c\uc9c0 \ub4f1\ub85d\ud560 \uc218 \uc788\uc5b4\uc694.",
                )

        trip.is_favorite = payload.is_favorite
        db.commit()
        db.refresh(trip)
        return trip


trip_service = TripService()
