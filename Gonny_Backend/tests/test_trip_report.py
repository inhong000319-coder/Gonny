from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
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
from app.domains.trips.schemas import ExpenseCreate, TripCategoryBreakdownItem, TripCreate, TripRetrospectiveUpdate
from app.domains.trips.services.service import (
    _build_report_insights,
    _compute_trip_distance,
    trip_service,
)
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
        "title": "테스트 여행",
        "destination": "seoul",
        "start_date": date(2020, 1, 1),
        "end_date": date(2020, 1, 3),
        "budget": 500000,
        "travel_style": "easy",
        "companion_type": "friend",
    }
    data.update(overrides)
    return trip_service.create_trip(db=db, request=TripCreate.model_validate(data))


def build_item(**overrides) -> ItineraryItem:
    data = {"id": 1, "trip_id": 1, "day_number": 1, "time_slot": "morning", "place_name": "sample", "category": "관광"}
    data.update(overrides)
    return ItineraryItem(**data)


# _compute_trip_distance() - uses the real seoul.json catalog data


def test_compute_trip_distance_matches_real_catalog_places() -> None:
    items = [
        build_item(id=1, day_number=1, time_slot="morning", place_name="Gyeongbokgung Palace"),
        build_item(id=2, day_number=1, time_slot="afternoon", place_name="Myeongdong"),
        build_item(id=3, day_number=1, time_slot="evening", place_name="Bukchon Hanok Village"),
    ]

    total_km, matched_count, total_count = _compute_trip_distance(items, "seoul")

    assert total_km is not None
    assert total_km > 0
    assert matched_count == 3
    assert total_count == 3


def test_compute_trip_distance_ignores_case_and_whitespace_differences() -> None:
    # 3 items -> 2 segments, clearing MIN_DISTANCE_SEGMENTS - with only 2
    # items (1 possible segment) the result would be None regardless of
    # whether matching works, so this needs a third point to actually
    # exercise the case/whitespace normalization.
    items = [
        build_item(id=1, day_number=1, time_slot="morning", place_name="  gyeongbokgung palace "),
        build_item(id=2, day_number=1, time_slot="afternoon", place_name="MYEONGDONG"),
        build_item(id=3, day_number=1, time_slot="evening", place_name="bukchon hanok village"),
    ]

    total_km, matched_count, _ = _compute_trip_distance(items, "seoul")

    assert total_km is not None
    assert matched_count == 3


def test_compute_trip_distance_none_when_fewer_than_two_segments() -> None:
    # Only one item can ever match (there's no consecutive pair at all).
    items = [build_item(id=1, day_number=1, time_slot="morning", place_name="Gyeongbokgung Palace")]

    total_km, matched_count, total_count = _compute_trip_distance(items, "seoul")

    assert total_km is None
    assert matched_count == 1
    assert total_count == 1


def test_compute_trip_distance_none_when_names_dont_match_catalog() -> None:
    items = [
        build_item(id=1, day_number=1, time_slot="morning", place_name="이름이 완전히 다른 장소 A"),
        build_item(id=2, day_number=1, time_slot="afternoon", place_name="이름이 완전히 다른 장소 B"),
    ]

    total_km, matched_count, total_count = _compute_trip_distance(items, "seoul")

    assert total_km is None
    assert matched_count == 0
    assert total_count == 2


def test_compute_trip_distance_none_for_unknown_city() -> None:
    items = [
        build_item(id=1, place_name="Gyeongbokgung Palace"),
        build_item(id=2, place_name="Myeongdong"),
    ]

    total_km, matched_count, total_count = _compute_trip_distance(items, "atlantis")

    assert total_km is None
    assert matched_count == 0
    assert total_count == 2


def test_compute_trip_distance_skips_unmatched_gap_but_still_counts_matched_pair() -> None:
    # Gyeongbokgung -> (unmatched) -> Myeongdong: only one leg has both
    # ends matched, and that's still below MIN_DISTANCE_SEGMENTS (2), so
    # the result must stay None even though matched_count is 2.
    items = [
        build_item(id=1, day_number=1, time_slot="morning", place_name="Gyeongbokgung Palace"),
        build_item(id=2, day_number=1, time_slot="afternoon", place_name="이름이 다른 미매칭 장소"),
        build_item(id=3, day_number=1, time_slot="evening", place_name="Myeongdong"),
    ]

    total_km, matched_count, total_count = _compute_trip_distance(items, "seoul")

    assert total_km is None
    assert matched_count == 2
    assert total_count == 3


# _build_report_insights() - pure function


def test_build_report_insights_includes_budget_and_visited_count() -> None:
    insights = _build_report_insights(
        budget=500000, total_spent=250000, visited_count=5, distance_km=None, category_breakdown=[]
    )

    assert any("50%" in text for text in insights)
    assert any("5곳" in text for text in insights)
    assert len(insights) == 2


def test_build_report_insights_adds_distance_and_top_category_when_available() -> None:
    insights = _build_report_insights(
        budget=500000,
        total_spent=250000,
        visited_count=5,
        distance_km=42.3,
        category_breakdown=[
            TripCategoryBreakdownItem(category="식비", amount_krw=150000),
            TripCategoryBreakdownItem(category="교통", amount_krw=50000),
        ],
    )

    assert any("42.3km" in text for text in insights)
    assert any("식비" in text for text in insights)
    assert len(insights) == 4


def test_build_report_insights_never_fabricates_missing_data() -> None:
    # No budget, no visits, no distance, no expenses - must return an
    # empty list rather than padding with made-up sentences.
    insights = _build_report_insights(
        budget=0, total_spent=0, visited_count=0, distance_km=None, category_breakdown=[]
    )

    assert insights == []


# TripService - DB-backed


def test_get_trip_report_not_ready_when_trip_has_not_ended(db_session: Session) -> None:
    trip = create_trip(db_session, end_date=date.today() + timedelta(days=1))

    report = trip_service.get_trip_report(db=db_session, trip_id=trip.id)

    assert report.ready is False
    assert report.message
    assert report.total_spent is None


def test_get_trip_report_ready_with_real_expenses_and_items(db_session: Session) -> None:
    trip = create_trip(db_session, budget=100000, end_date=date.today() - timedelta(days=1))
    trip_service.create_expense(
        db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=30000, note="점심")
    )
    trip_service.create_expense(
        db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="교통", amount=20000, note="택시")
    )
    item = ItineraryItem(trip_id=trip.id, day_number=1, time_slot="morning", place_name="아무 장소", category="관광")
    db_session.add(item)
    db_session.commit()

    report = trip_service.get_trip_report(db=db_session, trip_id=trip.id)

    assert report.ready is True
    assert report.total_spent == 50000
    assert report.budget == 100000
    assert report.budget_diff_pct == -50.0
    assert report.visited_count == 1
    assert {item.category: item.amount_krw for item in report.category_breakdown} == {"식비": 30000, "교통": 20000}
    assert len(report.insights) >= 2


def test_create_expense_returns_remaining_budget_and_usage_pct(db_session: Session) -> None:
    trip = create_trip(db_session, budget=100000)

    result = trip_service.create_expense(
        db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=25000)
    )

    assert result.remaining_budget == 75000
    assert result.budget_usage_pct == 25.0


def test_get_expense_summary_reflects_all_expenses(db_session: Session) -> None:
    trip = create_trip(db_session, budget=100000)
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="식비", amount=40000))
    trip_service.create_expense(db=db_session, trip_id=trip.id, payload=ExpenseCreate(category="쇼핑", amount=80000))

    summary = trip_service.get_expense_summary(db=db_session, trip_id=trip.id)

    assert summary.total_spent == 120000
    assert summary.remaining == -20000
    assert summary.is_over_budget is True


def test_update_trip_retrospective_persists_rating_and_note(db_session: Session) -> None:
    trip = create_trip(db_session)

    updated = trip_service.update_trip_retrospective(
        db=db_session,
        trip_id=trip.id,
        payload=TripRetrospectiveUpdate(satisfaction_rating=5, retrospective_note="최고의 여행이었어요."),
    )

    assert updated.satisfaction_rating == 5
    assert updated.retrospective_note == "최고의 여행이었어요."
