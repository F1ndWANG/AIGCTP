from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base, _utcnow


class TravelNote(Base):
    __tablename__ = "travel_notes"
    __table_args__ = (
        Index("ix_travel_notes_visibility_destination", "visibility", "destination"),
        Index("ix_travel_notes_author_created", "author_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    travel_plan_id = Column(Integer, ForeignKey("travel_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    destination = Column(String(100), default="", index=True)
    tags = Column(JSON, default=list)
    images = Column(JSON, default=list)
    visibility = Column(String(20), default="public", index=True)
    is_featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    author = relationship("User")
    travel_plan = relationship("TravelPlan")


class TravelNoteInteraction(Base):
    __tablename__ = "travel_note_interactions"
    __table_args__ = (
        UniqueConstraint("note_id", "user_id", "interaction_type", name="uq_travel_note_interaction"),
        Index("ix_travel_note_interactions_user_type", "user_id", "interaction_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("travel_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type = Column(String(30), nullable=False, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    note = relationship("TravelNote")
    user = relationship("User")


class TravelNoteComment(Base):
    __tablename__ = "travel_note_comments"
    __table_args__ = (
        Index("ix_travel_note_comments_note_created", "note_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("travel_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    note = relationship("TravelNote")
    user = relationship("User")
