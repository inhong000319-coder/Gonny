from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PlaceReview(Base):
    __tablename__ = "place_reviews"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    journal_id = Column(Integer, ForeignKey("travel_journals.id"), nullable=True, index=True)
    city = Column(String, nullable=False, index=True)
    place_id = Column(String, nullable=True, index=True)
    place_name = Column(String, nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    visit_time_slot = Column(String, nullable=True)
    companion_type = Column(String, nullable=True)
    recommended = Column(Boolean, nullable=False, default=True, server_default="true")
    would_revisit = Column(Boolean, nullable=False, default=True, server_default="true")
    tags = Column(JSON, nullable=False, default=list)
    review_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trip = relationship("Trip", back_populates="place_reviews")
    journal = relationship("TravelJournal", back_populates="place_reviews")
    reactions = relationship(
        "PlaceReviewReaction",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="PlaceReviewReaction.reaction_type.asc()",
    )


class PlaceStat(Base):
    __tablename__ = "place_stats"
    __table_args__ = (UniqueConstraint("city", "place_name", name="uq_place_stats_city_place_name"),)

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=False, index=True)
    place_name = Column(String, nullable=False, index=True)
    place_id = Column(String, nullable=True, index=True)
    review_count = Column(Integer, nullable=False, default=0, server_default="0")
    average_rating = Column(Float, nullable=False, default=0.0, server_default="0")
    recommendation_rate = Column(Float, nullable=False, default=0.0, server_default="0")
    revisit_rate = Column(Float, nullable=False, default=0.0, server_default="0")
    top_tags = Column(JSON, nullable=False, default=list)
    slot_scores = Column(JSON, nullable=False, default=dict)
    companion_scores = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PlaceReviewReaction(Base):
    __tablename__ = "place_review_reactions"
    __table_args__ = (UniqueConstraint("review_id", "reaction_type", name="uq_place_review_reaction_type"),)

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("place_reviews.id"), nullable=False, index=True)
    reaction_type = Column(String, nullable=False, index=True)
    count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    review = relationship("PlaceReview", back_populates="reactions")
