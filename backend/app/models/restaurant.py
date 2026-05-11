
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class RestaurantRecommendation(Base):
    __tablename__ = "restaurant_recommendations"
    __table_args__ = (
        Index("ix_restaurant_recs_user_session", "user_id", "session_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    city = Column(String(100), default="")
    query = Column(String(500), default="")
    response = Column(String(5000), default="")
    restaurants = Column(JSON, default=list)
    selected_restaurant = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User")
