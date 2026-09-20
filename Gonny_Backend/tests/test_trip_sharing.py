from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import Base

# Trip's relationships reference these by class name - all must be
# imported so SQLAlchemy can resolve them when configuring Trip's mapper
# (same imports app/main.py does before Base.metadata.create_all).
import app.models.itinerary  # noqa: F401
import app.models.place_review  # noqa: F401
import app.models.travel_journal  # noqa: F401
from app.domains.trips.schemas import ShareLinkCreateRequest, TripCreate
from app.domains.trips.services.service import (
    _compute_share_expires_at,
    _is_share_link_expired,
    trip_service,
)


@pytest.fixture()
def db_session():
    # Fresh in-memory SQLite per test - no DATABASE_URL/external DB needed,
    # matches Base's real table definitions exactly.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def create_trip(db: Session):
    return trip_service.create_trip(
        db=db,
        request=TripCreate(
            title="테스트 여행",
            destination="seoul",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
            budget=500000,
            travel_style="easy",
            companion_type="friend",
        ),
    )


# _compute_share_expires_at() / _is_share_link_expired() - pure functions


def test_compute_share_expires_at_1d_and_7d() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert _compute_share_expires_at("1d", now=now) == now + timedelta(days=1)
    assert _compute_share_expires_at("7d", now=now) == now + timedelta(days=7)


def test_compute_share_expires_at_unlimited_returns_none() -> None:
    assert _compute_share_expires_at("unlimited") is None


def test_is_share_link_expired_none_never_expires() -> None:
    assert _is_share_link_expired(None) is False


def test_is_share_link_expired_compares_against_now() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    assert _is_share_link_expired(datetime(2026, 1, 5, tzinfo=timezone.utc), now=now) is True
    assert _is_share_link_expired(datetime(2026, 1, 20, tzinfo=timezone.utc), now=now) is False


def test_is_share_link_expired_handles_naive_datetime_from_sqlite() -> None:
    # SQLite doesn't preserve tzinfo on DateTime(timezone=True) columns -
    # a value read back can be naive even though written as aware. Must
    # not raise when comparing.
    naive_past = datetime(2020, 1, 1)
    assert _is_share_link_expired(naive_past) is True


# TripService.create_share_link() / get_trip_by_share_token() - DB-backed


def test_create_share_link_issues_a_token_and_url(db_session: Session) -> None:
    trip = create_trip(db_session)

    result = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    assert result.token
    assert result.share_url.endswith(f"/share/{result.token}")
    assert result.expires_at is not None


def test_create_share_link_unlimited_has_no_expiry(db_session: Session) -> None:
    trip = create_trip(db_session)

    result = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="unlimited")
    )

    assert result.expires_at is None


def test_get_trip_by_share_token_returns_the_trip(db_session: Session) -> None:
    trip = create_trip(db_session)
    result = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    fetched = trip_service.get_trip_by_share_token(db=db_session, token=result.token)

    assert fetched.id == trip.id


def test_get_trip_by_share_token_404s_for_unknown_token(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        trip_service.get_trip_by_share_token(db=db_session, token="not-a-real-token")

    assert exc_info.value.status_code == 404


def test_get_trip_by_share_token_404s_when_expired(db_session: Session) -> None:
    trip = create_trip(db_session)
    result = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="1d")
    )
    # Force it into the past directly, rather than waiting a day.
    trip.share_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        trip_service.get_trip_by_share_token(db=db_session, token=result.token)

    assert exc_info.value.status_code == 404


def test_reissuing_a_share_link_invalidates_the_previous_token(db_session: Session) -> None:
    trip = create_trip(db_session)
    first = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    second = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    assert second.token != first.token
    # The old token is simply gone from the row - not tracked/blocklisted
    # anywhere else - so looking it up now finds nothing.
    with pytest.raises(HTTPException) as exc_info:
        trip_service.get_trip_by_share_token(db=db_session, token=first.token)
    assert exc_info.value.status_code == 404

    # The new token works.
    fetched = trip_service.get_trip_by_share_token(db=db_session, token=second.token)
    assert fetched.id == trip.id
