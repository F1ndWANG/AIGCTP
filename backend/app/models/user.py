from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), default="")
    avatar_url = Column(String(500), default="")
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    preferences_rel = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    travel_plans = relationship("TravelPlan", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    meal_records = relationship("MealRecord", back_populates="user", cascade="all, delete-orphan")
    diet_plans = relationship("DietPlan", back_populates="user", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(50), nullable=False)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="preferences_rel")
