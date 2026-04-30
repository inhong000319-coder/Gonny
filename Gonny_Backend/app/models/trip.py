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

    itinerary_items = relationship(
        "ItineraryItem",
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
