from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CachedPOI(Base):
    """Cache for external POI data (Amap / Google Places)"""
    __tablename__ = "cached_pois"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False, default="amap")
    poi_id = Column(String(100), nullable=True)
    name = Column(String(200), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, default=list)
    rating = Column(Float, nullable=True)
    address = Column(String(500), default="")
    phone = Column(String(50), default="")
    opening_hours = Column(String(200), default="")
    image_urls = Column(JSON, default=list)
    raw_data = Column(JSON, default=dict)
    cached_at = Column(DateTime, default=_utcnow)
