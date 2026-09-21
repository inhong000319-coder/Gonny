from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, default="새 여행", server_default="새 여행")
    destination = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Integer, nullable=False)
    travel_style = Column(String, nullable=False)
    companion_type = Column(String, nullable=False)
    is_favorite = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Single-link sharing (read-only only, MVP scope): re-issuing a link
    # overwrites this in place, so the previous token simply no longer
    # matches any row - no separate revocation/history needed. NULL means
    # "never shared". share_expires_at NULL means "no expiry" (unlimited).
    share_token = Column(String, nullable=True, unique=True, index=True)
    share_expires_at = Column(DateTime(timezone=True), nullable=True)
    # F14 retrospective report (see app/domains/trips/services/service.py's
    # get_trip_report) - both optional, set via PATCH /trips/{id}/retrospective.
    satisfaction_rating = Column(Integer, nullable=True)
    retrospective_note = Column(String, nullable=True)

    itinerary_items = relationship(
        "ItineraryItem",
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    expenses = relationship(
        "Expense",
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    travel_journals = relationship(
        "TravelJournal",
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    trip_todos = relationship(
        "TripTodo",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripTodo.sort_order.asc()",
    )
    place_reviews = relationship(
        "PlaceReview",
        back_populates="trip",
        cascade="all, delete-orphan",
    )
