from datetime import datetime, timezone
from sqlalchemy import Column, Index, Integer, String, DateTime, JSON, Date, Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class TravelPlan(Base):
    __tablename__ = "travel_plans"
    __table_args__ = (
        Index("ix_travel_plans_user_status", "user_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    destination = Column(String(200), nullable=False)
    days = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    budget = Column(Float, nullable=True)
    people_count = Column(Integer, default=1)
    preferences = Column(JSON, default=dict)
    itinerary = Column(JSON, nullable=True)
    status = Column(String(20), default="draft")  # draft / confirmed / completed
    feedback = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="travel_plans")
