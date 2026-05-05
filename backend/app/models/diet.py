from datetime import datetime, timezone
from sqlalchemy import Column, Index, Integer, String, DateTime, JSON, ForeignKey, Float, Date
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    allergies = Column(JSON, default=list)
    chronic_conditions = Column(JSON, default=list)
    diet_goals = Column(JSON, default=list)
    dietary_restrictions = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="health_profile")


class MealRecord(Base):
    __tablename__ = "meal_records"
    __table_args__ = (
        Index("ix_meal_records_user_date", "user_id", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)  # breakfast / lunch / dinner / snack
    foods = Column(JSON, default=list)
    total_nutrition = Column(JSON, nullable=True)
    notes = Column(String(500), default="")
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="meal_records")


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), default="")
    duration_days = Column(Integer, default=1)
    meals = Column(JSON, nullable=True)
    total_nutrition = Column(JSON, nullable=True)
    tips = Column(JSON, default=list)
    status = Column(String(20), default="draft")  # draft / active / completed
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="diet_plans")
