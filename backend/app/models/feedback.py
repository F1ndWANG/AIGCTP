from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(String(20), nullable=False)  # travel_plan / diet / restaurant / commerce / general
    message_id = Column(String(100), default="")       # session message identifier
    feedback = Column(String(10), nullable=False)      # "like" or "dislike"
    content_snapshot = Column(JSON, default=dict)       # snapshot of recommended content
    context = Column(JSON, default=dict)                # session context at time of feedback
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", backref="recommendation_logs")
