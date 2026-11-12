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
from app.domains.rule_planner.services.accommodation_scoring import load_city_accommodations
from app.domains.trips.schemas import (
    ExpenseCreate,
    ShareLinkCreateRequest,
    TripAccommodationUpdate,
    TripCreate,
    TripFavoriteUpdate,
)
from app.domains.trips.services.service import trip_service
from app.main import app
from app.models.itinerary import ItineraryItem


@pytest.fixture()
def db_session():
    # StaticPool - see tests/test_trip_accommodation.py's db_session for
    # why (TestClient's worker thread needs the same in-memory connection
    # this fixture ran create_all() against).
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
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
        "title": "숙소 변경 테스트 여행",
        "destination": "seoul",
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 3),
        "budget": 500000,
        "travel_style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return trip_service.create_trip(db=db, request=TripCreate.model_validate(data))


def first_accommodation_id(city: str) -> str:
    accommodations = load_city_accommodations(city)
    assert accommodations, f"{city}에 숙소 데이터가 없습니다 - 테스트 전제가 깨짐"
    return accommodations[0].id


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


# --- GET /trips/{id}/accommodation-options --------------------------------


@pytest.mark.parametrize("city", ["seoul", "busan", "jeju"])
def test_list_accommodation_options_not_empty_and_deterministically_sorted(db_session: Session, city: str) -> None:
    trip = create_trip(db_session, destination=city)

    options = trip_service.list_accommodation_options(db=db_session, trip_id=trip.id)

    assert options, city
    keys = [(o.accommodation_type, o.area, o.name) for o in options]
    assert keys == sorted(keys), city

    options_again = trip_service.list_accommodation_options(db=db_session, trip_id=trip.id)
    assert [o.id for o in options] == [o.id for o in options_again], city


@pytest.mark.parametrize("city", ["seoul", "busan", "jeju"])
def test_list_accommodation_options_never_exposes_a_price(db_session: Session, city: str) -> None:
    # 가격이 실제로 확인된 숙소(27곳)가 있어도 이 목록에서는 보여주지 않는다
    # - 시기별 편차가 커 리스크가 크다는 판단. 데이터 자체(average_price_krw)는
    # 그대로 두고 응답에서만 None으로 내린다.
    trip = create_trip(db_session, destination=city)
    assert any(a.average_price_krw is not None for a in load_city_accommodations(city)), city

    options = trip_service.list_accommodation_options(db=db_session, trip_id=trip.id)

    assert options, city
    assert all(option.average_price_krw is None for option in options), city


def test_list_accommodation_options_endpoint_response_has_only_the_five_fields(client_with_db: TestClient) -> None:
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
        },
    ).json()

    response = client_with_db.get(f"/trips/{created['id']}/accommodation-options")

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    for option in body:
        assert set(option.keys()) == {"id", "name", "accommodation_type", "area", "average_price_krw"}


def test_list_accommodation_options_404_for_missing_trip(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        trip_service.list_accommodation_options(db=db_session, trip_id=999)

    assert exc_info.value.status_code == 404


def test_list_accommodation_options_empty_for_city_without_accommodation_data(db_session: Session) -> None:
    trip = create_trip(db_session, destination="nowhere-city")

    options = trip_service.list_accommodation_options(db=db_session, trip_id=trip.id)

    assert options == []


# --- PATCH /trips/{id}/accommodation: 변경 ---------------------------------


def test_update_trip_accommodation_to_valid_id_updates_snapshot(db_session: Session) -> None:
    original_id = first_accommodation_id("seoul")
    trip = create_trip(db_session, destination="seoul", accommodation_id=original_id)
    accommodations = load_city_accommodations("seoul")
    new_choice = next(a for a in accommodations if a.id != original_id)

    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=new_choice.id)
    )

    assert updated.accommodation_id == new_choice.id
    assert updated.accommodation_name == new_choice.name
    assert updated.accommodation_type == new_choice.accommodation_type


def test_update_trip_accommodation_reflected_in_get_trips_and_detail_and_share_and_pdf(db_session: Session) -> None:
    trip = create_trip(db_session, destination="seoul")
    new_choice_id = first_accommodation_id("seoul")
    accommodations = load_city_accommodations("seoul")
    new_choice = next(a for a in accommodations if a.id == new_choice_id)

    share = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=new_choice.id)
    )

    # GET /trips
    listed = trip_service.list_trips(db=db_session)
    listed_trip = next(t for t in listed if t.id == trip.id)
    assert listed_trip.accommodation_name == new_choice.name

    # GET /trips/{id}
    fetched = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id)
    assert fetched.accommodation_name == new_choice.name

    # GET /share/{token}
    shared = trip_service.get_trip_by_share_token(db=db_session, token=share.token)
    assert shared.accommodation_name == new_choice.name

    # PDF
    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)
    assert pdf_bytes.startswith(b"%PDF")


def test_update_trip_accommodation_endpoint_reflects_in_responses(client_with_db: TestClient) -> None:
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
        },
    ).json()
    new_choice_id = first_accommodation_id("seoul")

    response = client_with_db.patch(f"/trips/{created['id']}/accommodation", json={"accommodation_id": new_choice_id})

    assert response.status_code == 200
    body = response.json()
    assert body["accommodation_id"] == new_choice_id
    assert body["accommodation_name"]
    assert body["accommodation_type"]

    detail = client_with_db.get(f"/trips/{created['id']}").json()
    assert detail["accommodation_id"] == new_choice_id

    listed = client_with_db.get("/trips").json()
    assert next(t for t in listed if t["id"] == created["id"])["accommodation_id"] == new_choice_id


# --- PATCH /trips/{id}/accommodation: 해제 ---------------------------------


def test_update_trip_accommodation_to_null_clears_all_three_fields(db_session: Session) -> None:
    seoul_id = first_accommodation_id("seoul")
    trip = create_trip(db_session, destination="seoul", accommodation_id=seoul_id)
    assert trip.accommodation_name is not None

    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=None)
    )

    assert updated.accommodation_id is None
    assert updated.accommodation_name is None
    assert updated.accommodation_type is None


def test_update_trip_accommodation_to_null_removes_accommodation_line_from_pdf(db_session: Session) -> None:
    import subprocess
    import tempfile
    import os
    import shutil

    seoul_id = first_accommodation_id("seoul")
    trip = create_trip(db_session, destination="seoul", accommodation_id=seoul_id)

    pdf_with = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)

    trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=None)
    )
    pdf_without = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)

    assert pdf_with != pdf_without
    assert len(pdf_without) < len(pdf_with)

    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext(poppler) not available in this environment")

    def extract_text(pdf_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            path = f.name
        try:
            result = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True, check=True)
            return result.stdout.decode("utf-8")
        finally:
            os.remove(path)

    assert "숙소:" in extract_text(pdf_with)
    assert "숙소:" not in extract_text(pdf_without)


# --- PATCH /trips/{id}/accommodation: 검증 오류 (422) ----------------------


def test_update_trip_accommodation_unknown_id_422(db_session: Session) -> None:
    trip = create_trip(db_session, destination="seoul")

    with pytest.raises(HTTPException) as exc_info:
        trip_service.update_trip_accommodation(
            db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id="does-not-exist-hotel")
        )

    assert exc_info.value.status_code == 422
    assert "does-not-exist-hotel" in exc_info.value.detail


def test_update_trip_accommodation_other_city_id_422(db_session: Session) -> None:
    trip = create_trip(db_session, destination="seoul")
    busan_id = first_accommodation_id("busan")

    with pytest.raises(HTTPException) as exc_info:
        trip_service.update_trip_accommodation(
            db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=busan_id)
        )

    assert exc_info.value.status_code == 422


def test_update_trip_accommodation_endpoint_unknown_id_returns_422(client_with_db: TestClient) -> None:
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
        },
    ).json()

    response = client_with_db.patch(
        f"/trips/{created['id']}/accommodation", json={"accommodation_id": "does-not-exist-hotel"}
    )

    assert response.status_code == 422


def test_client_cannot_send_accommodation_name_or_type_on_patch() -> None:
    # TripAccommodationUpdate에 name/type 필드가 아예 없다 - 보내더라도
    # 조용히 무시된다(서버가 항상 카탈로그에서 다시 채운다).
    payload = {
        "accommodation_id": "some-id",
        "accommodation_name": "클라이언트가 보낸 가짜 이름",
        "accommodation_type": "클라이언트가 보낸 가짜 유형",
    }
    parsed = TripAccommodationUpdate.model_validate(payload)
    assert not hasattr(parsed, "accommodation_name")
    assert not hasattr(parsed, "accommodation_type")


# --- PATCH 전후 다른 필드는 그대로 -----------------------------------------


def test_update_trip_accommodation_does_not_affect_other_fields(db_session: Session) -> None:
    seoul_id = first_accommodation_id("seoul")
    trip = create_trip(db_session, destination="seoul", accommodation_id=seoul_id)

    db_session.add(
        ItineraryItem(trip_id=trip.id, day_number=1, time_slot="morning", place_name="경복궁", category="culture")
    )
    db_session.commit()
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=30000))
    trip_service.update_trip_favorite(db=db_session, trip_id=trip.id, payload=TripFavoriteUpdate(is_favorite=True))
    share = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    before_items = [i.id for i in db_session.query(ItineraryItem).filter(ItineraryItem.trip_id == trip.id).all()]
    before_expenses_total = trip_service._expense_totals(db=db_session, trip_id=trip.id)[0]
    before_is_favorite = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id).is_favorite
    before_share_token = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id).share_token

    new_choice_id = next(a.id for a in load_city_accommodations("seoul") if a.id != seoul_id)
    trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=new_choice_id)
    )

    after_items = [i.id for i in db_session.query(ItineraryItem).filter(ItineraryItem.trip_id == trip.id).all()]
    after_expenses_total = trip_service._expense_totals(db=db_session, trip_id=trip.id)[0]
    after_trip = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id)

    assert after_items == before_items
    assert after_expenses_total == before_expenses_total
    assert after_trip.is_favorite == before_is_favorite is True
    assert after_trip.share_token == before_share_token == share.token
