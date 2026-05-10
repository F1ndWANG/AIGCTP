from datetime import datetime, timezone
from sqlalchemy import Column, Index, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_session_user", "session_id", "user_id"),
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    title = Column(String(200), default="")
    messages = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="conversations")
