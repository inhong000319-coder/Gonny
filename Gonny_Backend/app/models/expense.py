from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Expense(Base):
    """A single spend entry a user logs against a trip's budget.

    amount_krw is always treated as KRW - this app has no live FX
    conversion anywhere (see InspirationPage's still-static "실시간 환율"
    card), so currency is stored as free-form metadata only, never used
    to convert amount_krw.
    """

    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    amount_krw = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="KRW", server_default="KRW")
    note = Column(String, nullable=True)
    spent_at = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    trip = relationship("Trip", back_populates="expenses")
