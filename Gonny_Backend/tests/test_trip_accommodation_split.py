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
    ShareLinkCreateRequest,
    TripAccommodationUpdate,
    TripCreate,
    TripStayInput,
)
from app.domains.trips.services.service import trip_service
from app.main import app
from app.models.trip import Trip
from app.models.trip_stay import TripStay


@pytest.fixture()
def db_session():
    # StaticPool - see tests/test_trip_accommodation.py's db_session for
    # why (TestClient's worker thread needs the same in-memory connection
    # this fixture ran create_all() against).
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def seoul_ids(n: int) -> list[str]:
    accommodations = load_city_accommodations("seoul")
    assert len(accommodations) >= n, "서울 숙소 데이터가 테스트 전제보다 적음"
    return [a.id for a in accommodations[:n]]


def create_trip(db: Session, **overrides):
    data = {
        "title": "숙소 분할 테스트 여행",
        "destination": "seoul",
        # 3박4일 - allowed_partitions(3) == [(3,), (1, 2), (2, 1)]
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 4),
        "budget": 500000,
        "travel_style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return trip_service.create_trip(db=db, request=TripCreate.model_validate(data))


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


# --- (1) 분할 저장 성공 / 응답 stays 구조 / 레거시 컬럼 = 첫 stay -----------


def test_create_trip_with_stays_saves_rows_and_mirrors_first_in_legacy_columns(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)

    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])

    stays = sorted(db_session.query(TripStay).filter(TripStay.trip_id == trip.id).all(), key=lambda s: s.stay_index)
    assert len(stays) == 2
    assert [s.stay_index for s in stays] == [0, 1]
    assert [s.start_night for s in stays] == [1, 2]
    assert [s.nights for s in stays] == [1, 2]
    assert stays[0].accommodation_id == id_a
    assert stays[1].accommodation_id == id_b

    assert trip.accommodation_id == id_a
    assert trip.accommodation_name == stays[0].accommodation_name


def test_create_trip_endpoint_response_has_stays_structure(client_with_db: TestClient) -> None:
    id_a, id_b = seoul_ids(2)
    payload = {
        "destination": "seoul",
        "start_date": "2026-06-01",
        "end_date": "2026-06-04",
        "budget": 300000,
        "travel_style": "easy",
        "companion_type": "friend",
        "stays": [{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}],
    }
    response = client_with_db.post("/trips", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["stays"]) == 2
    assert body["stays"][0] == {
        "stay_index": 0,
        "start_night": 1,
        "nights": 1,
        "accommodation_id": id_a,
        "accommodation_name": body["stays"][0]["accommodation_name"],
        "accommodation_type": body["stays"][0]["accommodation_type"],
    }
    assert body["stays"][1]["stay_index"] == 1
    assert body["stays"][1]["start_night"] == 2
    assert body["stays"][1]["nights"] == 2
    # 호환 필드는 첫 stay와 같다
    assert body["accommodation_id"] == id_a
    assert body["accommodation_name"] == body["stays"][0]["accommodation_name"]


def test_single_element_stays_list_also_creates_one_row(db_session: Session) -> None:
    (id_a,) = seoul_ids(1)

    trip = create_trip(db_session, stays=[{"nights": 3, "accommodation_id": id_a}])

    stays = db_session.query(TripStay).filter(TripStay.trip_id == trip.id).all()
    assert len(stays) == 1
    assert stays[0].start_night == 1
    assert stays[0].nights == 3
    assert trip.accommodation_id == id_a


# --- (2) 검증 실패 경로 ----------------------------------------------------


def test_create_trip_stays_nights_sum_mismatch_422(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 1, "accommodation_id": id_b}])
    assert exc_info.value.status_code == 422


def test_create_trip_stays_disallowed_partition_422(db_session: Session) -> None:
    # 5박인데 중간 숙소가 1박인 (2,1,2) - allowed_partitions가 허용하지 않음.
    id_a, id_b, id_c = seoul_ids(3)
    with pytest.raises(HTTPException) as exc_info:
        create_trip(
            db_session,
            end_date=date(2026, 6, 6),  # 5박6일
            stays=[
                {"nights": 2, "accommodation_id": id_a},
                {"nights": 1, "accommodation_id": id_b},
                {"nights": 2, "accommodation_id": id_c},
            ],
        )
    assert exc_info.value.status_code == 422


def test_create_trip_stays_unknown_accommodation_id_422(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, stays=[{"nights": 3, "accommodation_id": "does-not-exist-hotel"}])
    assert exc_info.value.status_code == 422
    assert "does-not-exist-hotel" in exc_info.value.detail


def test_create_trip_stays_adjacent_same_accommodation_422(db_session: Session) -> None:
    (id_a,) = seoul_ids(1)
    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_a}])
    assert exc_info.value.status_code == 422


def test_create_trip_accommodation_id_and_stays_together_422(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    with pytest.raises(HTTPException) as exc_info:
        create_trip(
            db_session,
            accommodation_id=id_a,
            stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}],
        )
    assert exc_info.value.status_code == 422


def test_create_trip_stays_with_none_accommodation_id_422(db_session: Session) -> None:
    (id_a,) = seoul_ids(1)
    with pytest.raises(HTTPException) as exc_info:
        create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": None}])
    assert exc_info.value.status_code == 422


# --- (3) 레거시 여행의 합성 stay 응답 ---------------------------------------


def test_legacy_single_accommodation_trip_synthesizes_one_stay(db_session: Session) -> None:
    (id_a,) = seoul_ids(1)
    trip = create_trip(db_session, accommodation_id=id_a)  # 기존 단일 경로 - stay 행 없음

    assert db_session.query(TripStay).filter(TripStay.trip_id == trip.id).count() == 0

    fetched = trip_service.get_trip_or_404(db=db_session, trip_id=trip.id)
    from app.domains.trips.schemas import TripResponse

    response = TripResponse.model_validate(fetched)
    assert len(response.stays) == 1
    assert response.stays[0].stay_index == 0
    assert response.stays[0].start_night == 1
    assert response.stays[0].nights == 3  # 3박4일
    assert response.stays[0].accommodation_id == id_a


def test_trip_without_any_accommodation_has_empty_stays(db_session: Session) -> None:
    trip = create_trip(db_session)

    from app.domains.trips.schemas import TripResponse

    response = TripResponse.model_validate(trip)
    assert response.stays == []


def test_legacy_trip_endpoint_response_has_synthesized_stays(client_with_db: TestClient) -> None:
    (id_a,) = seoul_ids(1)
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-04",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
            "accommodation_id": id_a,
        },
    ).json()

    detail = client_with_db.get(f"/trips/{created['id']}").json()
    assert len(detail["stays"]) == 1
    assert detail["stays"][0]["nights"] == 3
    assert detail["stays"][0]["accommodation_id"] == id_a


# --- (4) PATCH: stay_index 변경 / 인접 중복 / 없는 index / 전체 해제 / 합성 변경 --


def test_patch_accommodation_changes_targeted_stay_only(db_session: Session) -> None:
    id_a, id_b, id_c = seoul_ids(3)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])

    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=id_c, stay_index=1)
    )

    stays = sorted(db_session.query(TripStay).filter(TripStay.trip_id == trip.id).all(), key=lambda s: s.stay_index)
    assert stays[0].accommodation_id == id_a  # stay 0은 그대로
    assert stays[1].accommodation_id == id_c  # stay 1만 바뀜
    # stay_index=1을 바꿨으니 레거시 컬럼(stay 0 기준)은 그대로
    assert updated.accommodation_id == id_a


def test_patch_accommodation_stay_index_zero_also_updates_legacy_columns(db_session: Session) -> None:
    id_a, id_b, id_c = seoul_ids(3)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])

    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=id_c, stay_index=0)
    )

    assert updated.accommodation_id == id_c
    stays = sorted(db_session.query(TripStay).filter(TripStay.trip_id == trip.id).all(), key=lambda s: s.stay_index)
    assert stays[0].accommodation_id == id_c


def test_patch_accommodation_rejects_adjacent_duplicate(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])

    with pytest.raises(HTTPException) as exc_info:
        trip_service.update_trip_accommodation(
            db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=id_b, stay_index=0)
        )
    assert exc_info.value.status_code == 422


def test_patch_accommodation_missing_stay_index_404(db_session: Session) -> None:
    id_a, id_b, id_c = seoul_ids(3)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])

    with pytest.raises(HTTPException) as exc_info:
        trip_service.update_trip_accommodation(
            db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=id_c, stay_index=5)
        )
    assert exc_info.value.status_code == 404


def test_patch_accommodation_missing_stay_index_on_legacy_trip_404(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, accommodation_id=id_a)  # 행 없음(레거시 경로)

    with pytest.raises(HTTPException) as exc_info:
        trip_service.update_trip_accommodation(
            db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=id_b, stay_index=1)
        )
    assert exc_info.value.status_code == 404


def test_patch_accommodation_null_clears_all_stay_rows(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])

    updated = trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=None)
    )

    assert updated.accommodation_id is None
    assert updated.accommodation_name is None
    assert db_session.query(TripStay).filter(TripStay.trip_id == trip.id).count() == 0


def test_patch_accommodation_materializes_a_row_for_a_legacy_synthesized_stay(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, accommodation_id=id_a)  # 행 없음
    assert db_session.query(TripStay).filter(TripStay.trip_id == trip.id).count() == 0

    trip_service.update_trip_accommodation(
        db=db_session, trip_id=trip.id, payload=TripAccommodationUpdate(accommodation_id=id_b, stay_index=0)
    )

    stays = db_session.query(TripStay).filter(TripStay.trip_id == trip.id).all()
    assert len(stays) == 1
    assert stays[0].stay_index == 0
    assert stays[0].start_night == 1
    assert stays[0].nights == 3
    assert stays[0].accommodation_id == id_b


# --- (5) 공유 조회 응답에 stays ---------------------------------------------


def test_shared_trip_response_includes_stays(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])
    share = trip_service.create_share_link(db=db_session, trip_id=trip.id, payload=ShareLinkCreateRequest(expires_in="7d"))

    fetched = trip_service.get_trip_by_share_token(db=db_session, token=share.token)

    from app.domains.trips.schemas import TripDetailResponse

    response = TripDetailResponse.model_validate(fetched)
    assert len(response.stays) == 2
    assert response.stays[1].accommodation_id == id_b


def test_shared_trip_endpoint_response_includes_stays(client_with_db: TestClient) -> None:
    id_a, id_b = seoul_ids(2)
    created = client_with_db.post(
        "/trips",
        json={
            "destination": "seoul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-04",
            "budget": 300000,
            "travel_style": "easy",
            "companion_type": "friend",
            "stays": [{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}],
        },
    ).json()
    share = client_with_db.post(f"/trips/{created['id']}/share", json={"expires_in": "7d"}).json()

    response = client_with_db.get(f"/share/{share['token']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["stays"]) == 2


# --- (6) PDF: 숙소 1곳 / 2곳 이상 ------------------------------------------


def _extract_pdf_text(pdf_bytes: bytes) -> str | None:
    import os
    import shutil
    import subprocess
    import tempfile

    if shutil.which("pdftotext") is None:
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    try:
        result = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True, check=True)
        return result.stdout.decode("utf-8")
    finally:
        os.remove(path)


def test_pdf_single_stay_keeps_pre_existing_one_line_format(db_session: Session) -> None:
    (id_a,) = seoul_ids(1)
    trip = create_trip(db_session, stays=[{"nights": 3, "accommodation_id": id_a}])

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)
    assert pdf_bytes.startswith(b"%PDF")

    text = _extract_pdf_text(pdf_bytes)
    if text is None:
        pytest.skip("pdftotext(poppler) not available in this environment")
    assert f"숙소: {trip.accommodation_name}" in text
    assert "숙소 1 (" not in text


def test_pdf_multi_stay_has_one_numbered_line_per_stay(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])
    stays = sorted(db_session.query(TripStay).filter(TripStay.trip_id == trip.id).all(), key=lambda s: s.stay_index)

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)
    assert pdf_bytes.startswith(b"%PDF")

    text = _extract_pdf_text(pdf_bytes)
    if text is None:
        pytest.skip("pdftotext(poppler) not available in this environment")
    assert f"숙소 1 (1박째): {stays[0].accommodation_name}" in text
    assert f"숙소 2 (2~3박째): {stays[1].accommodation_name}" in text
    assert "숙소:" not in text  # 단일 줄 포맷은 안 쓴다


def test_pdf_legacy_single_accommodation_unchanged(db_session: Session) -> None:
    # 레거시(행 없음) 경로도 합성된 stay가 1개이므로 기존 한 줄 포맷 그대로.
    (id_a,) = seoul_ids(1)
    trip = create_trip(db_session, accommodation_id=id_a)

    pdf_bytes = trip_service.generate_trip_pdf(db=db_session, trip_id=trip.id)
    text = _extract_pdf_text(pdf_bytes)
    if text is None:
        pytest.skip("pdftotext(poppler) not available in this environment")
    assert f"숙소: {trip.accommodation_name}" in text


# --- (7) 여행 삭제 시 stay 행 삭제(cascade) ----------------------------------


def test_deleting_trip_cascades_to_trip_stays(db_session: Session) -> None:
    id_a, id_b = seoul_ids(2)
    trip = create_trip(db_session, stays=[{"nights": 1, "accommodation_id": id_a}, {"nights": 2, "accommodation_id": id_b}])
    trip_id = trip.id
    assert db_session.query(TripStay).filter(TripStay.trip_id == trip_id).count() == 2

    db_session.delete(trip)
    db_session.commit()

    assert db_session.query(Trip).filter(Trip.id == trip_id).first() is None
    assert db_session.query(TripStay).filter(TripStay.trip_id == trip_id).count() == 0
