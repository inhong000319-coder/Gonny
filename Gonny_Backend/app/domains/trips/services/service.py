from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.domains.trips.schemas import (
    ShareLinkCreateRequest,
    ShareLinkResponse,
    TripCreate,
    TripFavoriteUpdate,
)
from app.models.trip import Trip

SHARE_TOKEN_BYTES = 32


def _compute_share_expires_at(expires_in: str, *, now: datetime | None = None) -> datetime | None:
    """1d/7d -> a concrete UTC expiry; "unlimited" -> None (no expiry)."""
    reference = now or datetime.now(timezone.utc)
    if expires_in == "1d":
        return reference + timedelta(days=1)
    if expires_in == "7d":
        return reference + timedelta(days=7)
    return None


def _is_share_link_expired(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    """None means "no expiry" (unlimited), never expired.

    SQLite (used for local/dev DBs) doesn't preserve tzinfo on
    DateTime(timezone=True) columns, so a value read back from the DB can
    be naive even though it was written as timezone-aware - comparing it
    against an aware "now" would raise TypeError. Match awareness instead
    of assuming either side.
    """
    if expires_at is None:
        return False
    if now is not None:
        reference = now
    else:
        reference = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.utcnow()
    return expires_at < reference


class TripService:
    def create_trip(self, *, db: Session, request: TripCreate) -> Trip:
        db_trip = Trip(
            title=request.title or f"{request.destination} 여행",
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
                    detail="즐겨찾기 여행은 최대 3개까지 등록할 수 있어요.",
                )

        trip.is_favorite = payload.is_favorite
        db.commit()
        db.refresh(trip)
        return trip

    def create_share_link(
        self,
        *,
        db: Session,
        trip_id: int,
        payload: ShareLinkCreateRequest,
    ) -> ShareLinkResponse:
        """Issues (or re-issues) this trip's single share link. Read-only
        only for this MVP - there's no permission column, every link
        grants read-only access. Overwriting share_token in place is what
        makes the previous link stop working: it's no longer stored
        anywhere, so a lookup by the old value simply finds no row."""
        trip = self.get_trip_or_404(db=db, trip_id=trip_id)

        token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)
        expires_at = _compute_share_expires_at(payload.expires_in)

        trip.share_token = token
        trip.share_expires_at = expires_at
        db.commit()
        db.refresh(trip)

        return ShareLinkResponse(
            share_url=f"{settings.frontend_base_url}/share/{token}",
            token=token,
            expires_at=expires_at,
        )

    def get_trip_by_share_token(self, *, db: Session, token: str) -> Trip:
        trip = db.query(Trip).filter(Trip.share_token == token).first()
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공유 링크를 찾을 수 없습니다.")
        if _is_share_link_expired(trip.share_expires_at):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="링크가 만료되었습니다.")
        return trip


trip_service = TripService()
