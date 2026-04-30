from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TravelJournal(Base):
    __tablename__ = "travel_journals"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    diary_text = Column(Text, nullable=False)
    reflection_text = Column(Text, nullable=True)
    content_blocks = Column(JSON, nullable=False, default=list)
    image_urls = Column(JSON, nullable=False, default=list)
    overall_rating = Column(Integer, nullable=True)
    share_with_community = Column(Boolean, nullable=False, default=False, server_default="false")
    view_count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trip = relationship("Trip", back_populates="travel_journals")
    todos = relationship(
        "TravelJournalTodo",
        back_populates="journal",
        cascade="all, delete-orphan",
        order_by="TravelJournalTodo.sort_order.asc()",
    )
    comments = relationship(
        "TravelJournalComment",
        back_populates="journal",
        cascade="all, delete-orphan",
        order_by="TravelJournalComment.created_at.desc(), TravelJournalComment.id.desc()",
    )
    reactions = relationship(
        "TravelJournalReaction",
        back_populates="journal",
        cascade="all, delete-orphan",
        order_by="TravelJournalReaction.reaction_type.asc()",
    )
    place_reviews = relationship("PlaceReview", back_populates="journal")


class TripTodo(Base):
    __tablename__ = "trip_todos"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    day_number = Column(Integer, nullable=False, default=1, server_default="1")
    is_done = Column(Boolean, nullable=False, default=False, server_default="false")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trip = relationship("Trip", back_populates="trip_todos")


class TravelJournalTodo(Base):
    __tablename__ = "travel_journal_todos"

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("travel_journals.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    is_done = Column(Boolean, nullable=False, default=False, server_default="false")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")

    journal = relationship("TravelJournal", back_populates="todos")


class TravelJournalComment(Base):
    __tablename__ = "travel_journal_comments"

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("travel_journals.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(String, nullable=True, index=True)
    author_name = Column(String, nullable=True)
    author_role = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    journal = relationship("TravelJournal", back_populates="comments")
    reactions = relationship(
        "TravelJournalCommentReaction",
        back_populates="comment",
        cascade="all, delete-orphan",
        order_by="TravelJournalCommentReaction.reaction_type.asc()",
    )


class TravelJournalReaction(Base):
    __tablename__ = "travel_journal_reactions"
    __table_args__ = (UniqueConstraint("journal_id", "reaction_type", name="uq_journal_reaction_type"),)

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("travel_journals.id"), nullable=False, index=True)
    reaction_type = Column(String, nullable=False, index=True)
    count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    journal = relationship("TravelJournal", back_populates="reactions")


class TravelJournalCommentReaction(Base):
    __tablename__ = "travel_journal_comment_reactions"
    __table_args__ = (UniqueConstraint("comment_id", "reaction_type", name="uq_comment_reaction_type"),)

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("travel_journal_comments.id"), nullable=False, index=True)
    reaction_type = Column(String, nullable=False, index=True)
    count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    comment = relationship("TravelJournalComment", back_populates="reactions")
