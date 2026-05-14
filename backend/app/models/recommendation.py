from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class RecommendationItem(Base):
    """Unified item catalog used by the recommendation pipeline.

    Domain tables remain the source of truth. This table stores a normalized,
    recommendation-friendly projection so recall/ranking can work across
    products, restaurants, travel plans, travel notes, and diet plans.
    """

    __tablename__ = "recommendation_items"
    __table_args__ = (
        Index("ix_rec_items_source", "domain", "item_type", "source_id", unique=True),
        Index("ix_rec_items_domain_active", "domain", "active"),
        Index("ix_rec_items_city_category", "city", "category"),
        Index("ix_rec_items_owner", "source_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(30), nullable=False, index=True)
    item_type = Column(String(30), nullable=False, index=True)
    source_id = Column(String(100), nullable=False, index=True)
    source_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(240), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    popularity_score = Column(Float, nullable=False, default=0.0)
    freshness_score = Column(Float, nullable=False, default=0.0)
    item_metadata = Column("metadata", JSON, nullable=True)
    image_url = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)
    active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    owner = relationship("User")


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
    impression_id = Column(String(64), nullable=True, index=True)
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


class RecommendationImpression(Base):
    """Per-item exposure log for attribution and offline evaluation."""

    __tablename__ = "recommendation_impressions"
    __table_args__ = (
        Index("ix_rec_impressions_user_domain_time", "user_id", "domain", "created_at"),
        Index("ix_rec_impressions_item", "domain", "item_type", "item_id"),
        Index("ix_rec_impressions_impression", "impression_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    impression_id = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    domain = Column(String(30), nullable=False, index=True)
    item_type = Column(String(30), nullable=False, index=True)
    item_id = Column(String(100), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    algorithm = Column(String(100), nullable=False, index=True)
    context = Column(JSON, nullable=True)
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user = relationship("User")


class RecommendationFeatureSnapshot(Base):
    """Aggregated item features derived from events and impressions."""

    __tablename__ = "recommendation_feature_snapshots"
    __table_args__ = (
        Index("ix_rec_feature_item", "domain", "item_type", "item_id", unique=True),
        Index("ix_rec_feature_domain", "domain", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(30), nullable=False, index=True)
    item_type = Column(String(30), nullable=False, index=True)
    item_id = Column(String(100), nullable=False, index=True)
    event_counts = Column(JSON, nullable=False, default=dict)
    features = Column(JSON, nullable=False, default=dict)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    social_score = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
