from __future__ import annotations

import sys
from datetime import date, timedelta
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
import app.models.place_review  # noqa: F401
import app.models.travel_journal  # noqa: F401
from app.domains.trips.schemas import ExpenseCreate, TripCreate
from app.domains.trips.services.service import trip_service
from app.models.itinerary import ItineraryItem


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def create_trip(db: Session, **overrides):
    data = {
        "title": "서울 PDF 테스트",
        "destination": "seoul",
        "start_date": date(2020, 1, 1),
        "end_date": date(2020, 1, 3),
        "budget": 300000,
        "travel_style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return trip_service.create_trip(db=db, request=TripCreate.model_validate(data))


def test_generate_trip_pdf_raises_404_for_missing_trip(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        trip_service.generate_trip_pdf(db=db_session, trip_id=999)

    assert exc_info.value.status_code == 404


def test_generate_trip_pdf_returns_valid_pdf_bytes_with_real_data(db_session: Session) -> None:
    trip = create_trip(db_session, budget=100000)
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=30000))
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="교통", amount=20000))
    db_session.add(
        ItineraryItem(
            trip_id=trip.id, day_number=1, time_slot="morning", place_name="경복궁", category="관광"
        )
    )
    db_session.add(
        ItineraryItem(
            trip_id=trip.id, day_number=1, time_slot="afternoon", place_name="명동", category="쇼핑"
        )
    )
    db_session.commit()

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0
    assert b"%%EOF" in pdf_bytes
    # The font must be a genuinely embedded TrueType program (FontFile2),
    # not a reference to a non-embedded CID font like the old
    # UnicodeCIDFont("HYSMyeongJo-Medium") - that approach let text
    # extraction work but left rendering dependent on the *viewer* having
    # a Korean font installed, which silently produced blank text in
    # viewers (e.g. poppler on a font-less Linux host) that had no local
    # substitute. See this file's font registration comment for the full
    # story; actual glyph rendering is additionally verified visually via
    # pdf2image/poppler (see PR description) since a byte-level check like
    # this can't see rendered pixels.
    assert b"/FontFile2" in pdf_bytes
    assert b"HYSMyeongJo" not in pdf_bytes


def test_generate_trip_pdf_works_even_when_trip_has_not_ended(db_session: Session) -> None:
    # Unlike get_trip_report(), the PDF export isn't gated on end_date -
    # a printable plan is useful before the trip too.
    trip = create_trip(db_session, end_date=date.today() + timedelta(days=30))

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_trip_pdf_handles_empty_itinerary_and_expenses(db_session: Session) -> None:
    trip = create_trip(db_session)

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)

    assert pdf_bytes.startswith(b"%PDF")
