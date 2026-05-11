from sqlalchemy import Column, Index, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"
    __table_args__ = (
        Index("ix_rec_logs_user_type", "user_id", "content_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(String(20), nullable=False)  # travel_plan / diet / restaurant / commerce / general
    message_id = Column(String(100), default="")       # session message identifier
    feedback = Column(String(10), nullable=False)      # "like" or "dislike"
    content_snapshot = Column(JSON, default=dict)       # snapshot of recommended content
    context = Column(JSON, default=dict)                # session context at time of feedback
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", backref="recommendation_logs")
