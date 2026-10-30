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
from app.domains.trips.schemas import TripCreate
from app.domains.trips.services.service import trip_service
from app.main import app


@pytest.fixture()
def db_session():
    # StaticPool: TestClient (client_with_db fixture below) runs the
    # request handler in a worker thread via anyio.to_thread - without
    # StaticPool, SQLite's default per-thread pooling would hand that
    # thread a *different* connection, which for ":memory:" is a
    # completely separate, empty database (no "trips" table). StaticPool
    # keeps every checkout on the one connection this fixture already
    # ran create_all() against, regardless of which thread asks.
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
        "title": "숙소 테스트 여행",
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


# --- 저장: accommodation_id 없음 (기존 동작 불변) -------------------------


def test_create_trip_without_accommodation_id_leaves_fields_null(db_session: Session) -> None:
    trip = create_trip(db_session)

    assert trip.accommodation_id is None
    assert trip.accommodation_name is None
    assert trip.accommodation_type is None


# --- 저장: 유효한 accommodation_id (서울·부산·제주 각 1건) ------------------


@pytest.mark.parametrize("city", ["seoul", "busan", "jeju"])
def test_create_trip_with_valid_accommodation_id_snapshots_name_and_type(db_session: Session, city: str) -> None:
    accommodations = load_city_accommodations(city)
    chosen = accommodations[0]

    trip = create_trip(db_session, destination=city, accommodation_id=chosen.id)

    assert trip.accommodation_id == chosen.id
    assert trip.accommodation_name == chosen.name
    assert trip.accommodation_type == chosen.accommodation_type

    # 생성 응답에도 반영됨(서비스 메서드가 바로 그 Trip 객체를 반환)
    fetched = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id)
    assert fetched.accommodation_id == chosen.id
    assert fetched.accommodation_name == chosen.name

    # GET /trips 목록에도 반영됨
    listed = trip_service.list_trips(db=db_session)
    listed_trip = next(t for t in listed if t.id == trip.id)
    assert listed_trip.accommodation_name == chosen.name


def test_client_cannot_send_accommodation_name_directly() -> None:
    # TripCreate 스키마 자체에 accommodation_name/type 필드가 없다 -
    # 보내더라도 조용히 무시된다(서버가 항상 카탈로그에서 다시 채운다).
    payload = {
        "destination": "seoul",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "budget": 100000,
        "travel_style": "easy",
        "companion_type": "friend",
        "accommodation_name": "클라이언트가 보낸 가짜 이름",
    }
    parsed = TripCreate.model_validate(payload)
    assert not hasattr(parsed, "accommodation_name")


# --- 검증 오류 (422) ------------------------------------------------------


def test_create_trip_unknown_accommodation_id_422(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, destination="seoul", accommodation_id="does-not-exist-hotel")

    assert exc_info.value.status_code == 422
    assert "does-not-exist-hotel" in exc_info.value.detail


def test_create_trip_other_city_accommodation_id_422(db_session: Session) -> None:
    busan_id = first_accommodation_id("busan")

    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, destination="seoul", accommodation_id=busan_id)

    assert exc_info.value.status_code == 422


def test_create_trip_city_without_accommodation_data_422(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, destination="nowhere-city", accommodation_id="any-id")

    assert exc_info.value.status_code == 422


# --- 공유 링크 조회 --------------------------------------------------------


def test_shared_trip_includes_accommodation_fields(db_session: Session) -> None:
    from app.domains.trips.schemas import ShareLinkCreateRequest

    seoul_id = first_accommodation_id("seoul")
    trip = create_trip(db_session, destination="seoul", accommodation_id=seoul_id)
    share = trip_service.create_share_link(
        db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d")
    )

    fetched = trip_service.get_trip_by_share_token(db=db_session, token=share.token)

    assert fetched.accommodation_id == seoul_id
    assert fetched.accommodation_name is not None


# --- PDF -------------------------------------------------------------------


def test_pdf_with_accommodation_differs_from_without(db_session: Session) -> None:
    seoul_id = first_accommodation_id("seoul")
    trip_without = create_trip(db_session, destination="seoul")
    trip_with = create_trip(db_session, destination="seoul", accommodation_id=seoul_id)

    pdf_without = trip_service.generate_trip_pdf(db=db_session, trip_id=trip_without.id)
    pdf_with = trip_service.generate_trip_pdf(db=db_session, trip_id=trip_with.id)

    assert pdf_without.startswith(b"%PDF")
    assert pdf_with.startswith(b"%PDF")
    assert pdf_with != pdf_without
    # 숙소가 있는 PDF가 한 줄 더 많으므로 최소한 더 크다(엄밀한 텍스트
    # 추출 검증은 PDF 내용 스트림이 압축/서브셋 글꼴이라 바이트 검색으로
    # 신뢰할 수 없어, 별도 pdftotext 스크립트로 수행 - 보고서 참고).
    assert len(pdf_with) > len(pdf_without)


def test_pdf_without_accommodation_matches_pre_feature_shape(db_session: Session) -> None:
    # 숙소 없는 여행의 PDF는 변경 전과 같은 내용이어야 한다 - 직접적인
    # "변경 전 바이트와 비교"는 할 수 없으므로(이번 커밋에서만 재현 가능),
    # 대신 숙소 필드가 전부 None일 때 _build_trip_pdf_bytes가 예외 없이
    # 동작하고 유효한 PDF를 반환함을 확인한다(기존 test_trip_pdf.py의
    # 동일 계열 테스트와 같은 수준의 보증).
    trip = create_trip(db_session, destination="seoul")
    assert trip.accommodation_name is None

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)

    assert pdf_bytes.startswith(b"%PDF")
    assert b"%%EOF" in pdf_bytes


# --- 응답 계약 (엔드포인트별) ------------------------------------------------


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


def test_create_trip_endpoint_response_has_accommodation_fields(client_with_db: TestClient) -> None:
    seoul_id = first_accommodation_id("seoul")
    payload = {
        "destination": "seoul",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "budget": 300000,
        "travel_style": "easy",
        "companion_type": "friend",
        "accommodation_id": seoul_id,
    }
    response = client_with_db.post("/trips", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["accommodation_id"] == seoul_id
    assert body["accommodation_name"]
    assert body["accommodation_type"]
    # 기존 필드도 그대로
    assert body["destination"] == "seoul"
    assert body["is_favorite"] is False


def test_create_trip_endpoint_unknown_accommodation_id_returns_422(client_with_db: TestClient) -> None:
    payload = {
        "destination": "seoul",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "budget": 300000,
        "travel_style": "easy",
        "companion_type": "friend",
        "accommodation_id": "does-not-exist-hotel",
    }
    response = client_with_db.post("/trips", json=payload)

    assert response.status_code == 422


def test_get_trips_list_endpoint_includes_accommodation_fields(client_with_db: TestClient) -> None:
    seoul_id = first_accommodation_id("seoul")
    client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
            "accommodation_id": seoul_id,
        },
    )

    response = client_with_db.get("/trips")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["accommodation_id"] == seoul_id


def test_get_trip_detail_endpoint_includes_accommodation_fields(client_with_db: TestClient) -> None:
    seoul_id = first_accommodation_id("seoul")
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
            "accommodation_id": seoul_id,
        },
    ).json()

    response = client_with_db.get(f"/trips/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["accommodation_id"] == seoul_id
    assert "itinerary_items" in body  # TripDetailResponse 고유 필드 그대로


def test_create_trip_endpoint_without_accommodation_id_unchanged(client_with_db: TestClient) -> None:
    payload = {
        "destination": "seoul",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "budget": 300000,
        "travel_style": "easy",
        "companion_type": "friend",
    }
    response = client_with_db.post("/trips", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["accommodation_id"] is None
    assert body["accommodation_name"] is None
    assert body["accommodation_type"] is None
