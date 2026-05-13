from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class RecommendationEvent(Base):
    """Unified user behavior event used by the recommendation pipeline."""

    __tablename__ = "recommendation_events"
    __table_args__ = (
        Index("ix_rec_events_user_domain_time", "user_id", "domain", "created_at"),
        Index("ix_rec_events_item", "domain", "item_type", "item_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    domain = Column(String(30), nullable=False, index=True)
    item_type = Column(String(30), nullable=False, index=True)
    item_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(30), nullable=False, index=True)
    weight = Column(Float, nullable=False, default=1.0)
    context = Column(JSON, nullable=True)
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user = relationship("User")


class RecommendationEmbedding(Base):
    """Item text embedding cache. V1 also stores local token vectors when no API key exists."""

    __tablename__ = "recommendation_embeddings"
    __table_args__ = (
        Index("ix_rec_embeddings_item", "domain", "item_type", "item_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(30), nullable=False, index=True)
    item_type = Column(String(30), nullable=False, index=True)
    item_id = Column(String(100), nullable=False, index=True)
    text_hash = Column(String(64), nullable=False, index=True)
    embedding = Column(JSON, nullable=False)
    model = Column(String(100), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class RecommendationFeedLog(Base):
    """Recommendation request trace for offline evaluation and future model training."""

    __tablename__ = "recommendation_feed_logs"
    __table_args__ = (
        Index("ix_rec_feed_logs_user_domain_time", "user_id", "domain", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    domain = Column(String(30), nullable=False, index=True)
    request_context = Column(JSON, nullable=True)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user = relationship("User")
