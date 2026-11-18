from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class TripStay(Base):
    """One accommodation region of a saved trip (#133/#135 split-stay
    support) - see services/accommodation_split.py for the night/day
    mapping this mirrors (start_night..start_night+nights-1). A trip with
    one accommodation (the pre-#135 norm) either has no rows here at all
    (read-time synthesizes a length-1 view - see TripResponse) or exactly
    one row at stay_index=0, start_night=1."""

    __tablename__ = "trip_stays"
    __table_args__ = (UniqueConstraint("trip_id", "stay_index", name="uq_trip_stays_trip_id_stay_index"),)

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    stay_index = Column(Integer, nullable=False)
    start_night = Column(Integer, nullable=False)
    nights = Column(Integer, nullable=False)
    # Always set - a stay with no accommodation chosen simply has no row
    # (save-time validation rejects a None accommodation_id in a stays
    # list; see services/service.py's _validate_and_resolve_stays).
    accommodation_id = Column(String, nullable=False)
    accommodation_name = Column(String, nullable=False)
    accommodation_type = Column(String, nullable=False)

    trip = relationship("Trip", back_populates="stays")
