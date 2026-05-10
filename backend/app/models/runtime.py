from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class TaskRun(Base):
    """Durable execution record for high-availability workflows."""

    __tablename__ = "task_runs"
    __table_args__ = (
        Index("ix_task_runs_user_status", "user_id", "status"),
        Index("ix_task_runs_session_status", "session_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="running", index=True)
    input = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error = Column(String(2000), default="")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User")


class DomainEvent(Base):
    """Append-only business event for audit, replay, and async integration."""

    __tablename__ = "domain_events"
    __table_args__ = (
        Index("ix_domain_events_user_type", "user_id", "event_type"),
        Index("ix_domain_events_session_type", "session_id", "event_type"),
        Index("ix_domain_events_aggregate", "aggregate_type", "aggregate_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    task_id = Column(String(100), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), default="", index=True)
    aggregate_id = Column(String(100), default="", index=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User")
