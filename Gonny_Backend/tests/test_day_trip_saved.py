"""#140 - 당일치기(start_date == end_date) 여행의 저장/조회/숙소/공유/
PDF/리포트/지출.

기존 in-memory SQLite 패턴(tests/test_trip_accommodation_split.py 등과
동일)을 그대로 쓴다 - 완전히 격리된 임시 DB라 실제 .env/DATABASE_URL을
전혀 읽지 않는다.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import Base
from app.db.session import get_db

# Trip's relationships reference these by class name - all must be
# imported so SQLAlchemy can resolve them when configuring Trip's mapper
# (same imports app/main.py does before Base.metadata.create_all).
import app.models.itinerary  # noqa: F401
import app.models.place_review  # noqa: F401
import app.models.travel_journal  # noqa: F401
import app.models.trip_stay  # noqa: F401
from app.domains.rule_planner.services.accommodation_scoring import load_city_accommodations
from app.domains.trips.schemas import (
    ExpenseCreate,
    ShareLinkCreateRequest,
    TripAccommodationUpdate,
    TripCreate,
    TripDetailResponse,
    TripResponse,
)
from app.domains.trips.services.service import trip_service
from app.main import app
from app.models.itinerary import ItineraryItem


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client_with_db(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def create_day_trip(db: Session, **overrides):
    data = {
        "title": "당일치기 테스트 여행",
        "destination": "seoul",
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 1),  # 당일치기
        "budget": 100000,
        "travel_style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return trip_service.create_trip(db=db, request=TripCreate.model_validate(data))


def seoul_id() -> str:
    accommodations = load_city_accommodations("seoul")
    assert accommodations, "서울 숙소 데이터가 테스트 전제보다 적음"
    return accommodations[0].id


# --- 저장 ------------------------------------------------------------------


def test_create_day_trip_succeeds_with_no_accommodation(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    assert trip.start_date == trip.end_date
    assert trip.accommodation_id is None
    assert trip.accommodation_name is None


def test_create_day_trip_with_accommodation_id_is_rejected(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        create_day_trip(db_session, accommodation_id=seoul_id())
    assert exc_info.value.status_code == 422
    assert "당일치기" in exc_info.value.detail


def test_create_day_trip_with_stays_is_rejected(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        create_day_trip(db_session, stays=[{"nights": 0, "accommodation_id": seoul_id()}])
    assert exc_info.value.status_code == 422
    assert "당일치기" in exc_info.value.detail


def test_create_day_trip_endpoint_rejects_accommodation_id(client_with_db: TestClient) -> None:
    response = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-01",
            "budget": 100000,
            "travel_style": "easy",
            "companion_type": "friend",
            "accommodation_id": seoul_id(),
        },
    )
    assert response.status_code == 422


# --- 조회(상세/목록) - stays는 빈 배열 ---------------------------------------


def test_day_trip_detail_response_has_empty_stays(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    fetched = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id)

    response = TripDetailResponse.model_validate(fetched)
    assert response.stays == []
    assert response.accommodation_name is None


def test_day_trip_list_response_has_empty_stays(db_session: Session) -> None:
    create_day_trip(db_session)
    listed = trip_service.list_trips(db=db_session)
    response = TripResponse.model_validate(listed[0])
    assert response.stays == []


# --- 숙소 후보/변경 ----------------------------------------------------------


def test_day_trip_accommodation_options_is_empty(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    options = trip_service.list_accommodation_options(db=db_session, trip_id=trip.id)
    assert options == []


def test_day_trip_patch_accommodation_set_is_rejected(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    with pytest.raises(HTTPException) as exc_info:
        trip_service.update_trip_accommodation(
            db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=seoul_id())
        )
    assert exc_info.value.status_code == 422
    assert "당일치기" in exc_info.value.detail


def test_day_trip_patch_accommodation_clear_is_a_harmless_noop(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=None)
    )
    assert updated.accommodation_id is None


def test_day_trip_accommodation_options_endpoint_returns_empty_list(client_with_db: TestClient) -> None:
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-01",
            "budget": 100000,
            "travel_style": "easy",
            "companion_type": "friend",
        },
    ).json()

    response = client_with_db.get(f"/trips/{created['id']}/accommodation-options")
    assert response.status_code == 200
    assert response.json() == []


def test_day_trip_patch_accommodation_endpoint_returns_422(client_with_db: TestClient) -> None:
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-01",
            "budget": 100000,
            "travel_style": "easy",
            "companion_type": "friend",
        },
    ).json()

    response = client_with_db.patch(
        f"/trips/{created['id']}/accommodation", json={"accommodation_id": seoul_id()}
    )
    assert response.status_code == 422


# --- 공유 조회 ---------------------------------------------------------------


def test_day_trip_shared_response_has_empty_stays(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    share = trip_service.create_share_link(db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d"))

    shared = trip_service.get_trip_by_share_token(db=db_session, token=share.token)
    response = TripDetailResponse.model_validate(shared)
    assert response.stays == []


# --- PDF ---------------------------------------------------------------------


def test_day_trip_pdf_generates_without_error(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    db_session.add(
        ItineraryItem(trip_id=trip.id, day_number=1, time_slot="morning", place_name="경복궁", category="culture")
    )
    db_session.commit()

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)
    assert pdf_bytes.startswith(b"%PDF")
    assert b"%%EOF" in pdf_bytes


# --- 리포트/지출 -------------------------------------------------------------


def test_day_trip_report_ready_false_for_future_trip(db_session: Session) -> None:
    trip = create_day_trip(db_session, start_date=date(2027, 1, 1), end_date=date(2027, 1, 1))
    report = trip_service.get_trip_report(db=db_session, trip_id=trip.id)
    assert report.ready is False


def test_day_trip_report_ready_true_for_past_trip(db_session: Session) -> None:
    trip = create_day_trip(db_session, start_date=date(2020, 1, 1), end_date=date(2020, 1, 1))
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=20000))

    report = trip_service.get_trip_report(db=db_session, trip_id=trip.id)
    assert report.ready is True
    assert report.total_spent == 20000
    assert report.budget_diff_pct is not None


def test_day_trip_expense_summary_works(db_session: Session) -> None:
    trip = create_day_trip(db_session)
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=15000))

    summary = trip_service.get_expense_summary(db=db_session, trip_id=trip.id)
    assert summary.total_spent == 15000
    assert summary.total_budget == trip.budget


# --- 예전 방식(nights>=1)으로 저장된 여행은 그대로 ----------------------------


def test_pre_existing_multi_night_trip_detail_unaffected(db_session: Session) -> None:
    seoul = seoul_id()
    trip = trip_service.create_trip(
        db=db_session,
        request=TripCreate.model_validate(
            {
                "destination": "seoul",
                "start_date": date(2026, 6, 1),
                "end_date": date(2026, 6, 3),
                "budget": 300000,
                "travel_style": "easy",
                "companion_type": "friend",
                "accommodation_id": seoul,
            }
        ),
    )

    fetched = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id)
    response = TripDetailResponse.model_validate(fetched)
    assert len(response.stays) == 1
    assert response.stays[0].accommodation_id == seoul
    assert response.accommodation_id == seoul

    options = trip_service.list_accommodation_options(db=db_session, trip_id=trip.id)
    assert options != []

    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=None)
    )
    assert updated.accommodation_id is None
