from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    time_slot = Column(String, nullable=False)
    place_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

    trip = relationship("Trip", back_populates="itinerary_items")
