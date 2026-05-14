from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import String, cast, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.share import TravelNote, TravelNoteComment, TravelNoteInteraction
from app.models.travel import TravelPlan
from app.models.user import User
from app.schemas.share import (
    TravelNoteAuthor,
    TravelNoteCommentCreate,
    TravelNoteCommentResponse,
    TravelNoteCreate,
    TravelNoteInteractionRequest,
    TravelNoteResponse,
    TravelNoteUpdate,
)
from app.services.recommendation.catalog import sync_travel_note_item
from app.services.recommendation import recommendation_service


class ShareService:
    async def list_notes(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        destination: str | None = None,
        tag: str | None = None,
        mine: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TravelNoteResponse]:
        query = select(TravelNote).options(selectinload(TravelNote.author))
        if mine:
            query = query.where(TravelNote.author_id == current_user.id)
        else:
            query = query.where(TravelNote.visibility == "public")

        if destination:
            query = query.where(TravelNote.destination.ilike(f"%{destination.strip()}%"))
        if tag:
            query = query.where(cast(TravelNote.tags, String).ilike(f"%{tag.strip()}%"))

        query = query.order_by(desc(TravelNote.is_featured), desc(TravelNote.created_at)).offset(offset).limit(limit)
        result = await db.execute(query)
        return [await self.serialize_note(db, note, current_user) for note in result.scalars().all()]

    async def recommended_notes(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        limit: int = 12,
    ) -> list[TravelNoteResponse]:
        feed = await recommendation_service.recommend(
            db,
            user=current_user,
            domain="travel",
            limit=max(limit * 2, limit),
            context={"entry": "share_recommended", "item_type": "travel_note"},
        )
        note_ids = [
            int(item["item_id"])
            for item in feed
            if item.get("item_type") == "travel_note" and str(item.get("item_id", "")).isdigit()
        ][:limit]
        if not note_ids:
            return await self.list_notes(db, current_user=current_user, limit=limit)
        result = await db.execute(
            select(TravelNote)
            .where(TravelNote.id.in_(note_ids), TravelNote.visibility == "public")
            .options(selectinload(TravelNote.author))
        )
        notes = {note.id: note for note in result.scalars().all()}
        return [await self.serialize_note(db, notes[note_id], current_user) for note_id in note_ids if note_id in notes]

    async def create_note(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        payload: TravelNoteCreate,
    ) -> TravelNoteResponse:
        if payload.travel_plan_id:
            plan = await db.get(TravelPlan, payload.travel_plan_id)
            if not plan or plan.user_id != current_user.id:
                raise HTTPException(status_code=404, detail="Travel plan not found")

        note = TravelNote(
            author_id=current_user.id,
            travel_plan_id=payload.travel_plan_id,
            title=payload.title.strip(),
            content=payload.content.strip(),
            destination=payload.destination.strip(),
            tags=self._clean_tags(payload.tags),
            images=payload.images[:12],
            visibility=payload.visibility,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note, ["author"])
        await sync_travel_note_item(db, note)
        await self._track_note_event(db, current_user.id, note, "share")
        await db.commit()
        await db.refresh(note, ["author"])
        return await self.serialize_note(db, note, current_user, include_comments=True)

    async def get_note(
        self,
        db: AsyncSession,
        *,
        note_id: int,
        current_user: User,
    ) -> TravelNoteResponse:
        note = await self.get_visible_note(db, note_id, current_user.id)
        note.view_count = (note.view_count or 0) + 1
        await self._track_note_event(db, current_user.id, note, "view")
        await sync_travel_note_item(db, note)
        await db.commit()
        await db.refresh(note, ["author"])
        return await self.serialize_note(db, note, current_user, include_comments=True)

    async def update_note(
        self,
        db: AsyncSession,
        *,
        note_id: int,
        current_user: User,
        payload: TravelNoteUpdate,
    ) -> TravelNoteResponse:
        note = await self.get_visible_note(db, note_id, current_user.id)
        self._require_owner(note, current_user, "edit")

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key in {"title", "content", "destination"} and isinstance(value, str):
                value = value.strip()
            if key == "tags" and isinstance(value, list):
                value = self._clean_tags(value)
            if key == "images" and isinstance(value, list):
                value = value[:12]
            setattr(note, key, value)

        await db.flush()
        await sync_travel_note_item(db, note)
        await db.commit()
        await db.refresh(note, ["author"])
        return await self.serialize_note(db, note, current_user, include_comments=True)

    async def delete_note(
        self,
        db: AsyncSession,
        *,
        note_id: int,
        current_user: User,
    ) -> None:
        note = await self.get_visible_note(db, note_id, current_user.id)
        self._require_owner(note, current_user, "delete")
        await db.delete(note)
        await db.commit()

    async def interact_with_note(
        self,
        db: AsyncSession,
        *,
        note_id: int,
        current_user: User,
        payload: TravelNoteInteractionRequest,
    ) -> TravelNoteResponse:
        note = await self.get_visible_note(db, note_id, current_user.id)
        interaction = await self._get_interaction(db, note.id, current_user.id, payload.interaction_type)
        delta = self._apply_interaction(interaction, payload)
        if interaction is None:
            interaction = TravelNoteInteraction(
                note_id=note.id,
                user_id=current_user.id,
                interaction_type=payload.interaction_type,
                active=payload.active,
            )
            db.add(interaction)

        counter_name = f"{payload.interaction_type}_count"
        if hasattr(note, counter_name) and delta:
            setattr(note, counter_name, max(0, (getattr(note, counter_name) or 0) + delta))

        await self._track_note_event(db, current_user.id, note, payload.interaction_type)
        await sync_travel_note_item(db, note)
        await db.commit()
        await db.refresh(note, ["author"])
        return await self.serialize_note(db, note, current_user, include_comments=True)

    async def comment_note(
        self,
        db: AsyncSession,
        *,
        note_id: int,
        current_user: User,
        payload: TravelNoteCommentCreate,
    ) -> TravelNoteResponse:
        note = await self.get_visible_note(db, note_id, current_user.id)
        comment = TravelNoteComment(note_id=note.id, user_id=current_user.id, content=payload.content.strip())
        note.comment_count = (note.comment_count or 0) + 1
        db.add(comment)
        await self._track_note_event(
            db,
            current_user.id,
            note,
            "comment",
            extra_context={"comment": payload.content[:200]},
        )
        await sync_travel_note_item(db, note)
        await db.commit()
        await db.refresh(note, ["author"])
        return await self.serialize_note(db, note, current_user, include_comments=True)

    async def get_visible_note(self, db: AsyncSession, note_id: int, user_id: int) -> TravelNote:
        result = await db.execute(
            select(TravelNote)
            .where(
                TravelNote.id == note_id,
                (TravelNote.visibility == "public") | (TravelNote.author_id == user_id),
            )
            .options(selectinload(TravelNote.author))
        )
        note = result.scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail="Travel note not found")
        return note

    async def serialize_note(
        self,
        db: AsyncSession,
        note: TravelNote,
        current_user: User,
        *,
        include_comments: bool = False,
    ) -> TravelNoteResponse:
        comments: list[TravelNoteCommentResponse] = []
        if include_comments:
            comments = await self._note_comments(db, note.id)

        return TravelNoteResponse(
            id=note.id,
            title=note.title,
            content=note.content,
            destination=note.destination or "",
            tags=note.tags or [],
            images=note.images or [],
            visibility=note.visibility,
            is_featured=bool(note.is_featured),
            view_count=note.view_count or 0,
            like_count=note.like_count or 0,
            save_count=note.save_count or 0,
            comment_count=note.comment_count or 0,
            share_count=note.share_count or 0,
            created_at=note.created_at,
            updated_at=note.updated_at,
            author=self._author_response(note.author),
            travel_plan_id=note.travel_plan_id,
            viewer_interactions=await self._viewer_interactions(db, note.id, current_user.id),
            comments=comments,
            metadata={
                "social_score": (note.like_count or 0) * 3
                + (note.save_count or 0) * 4
                + (note.comment_count or 0) * 2
                + (note.share_count or 0) * 4,
            },
        )

    async def _note_comments(self, db: AsyncSession, note_id: int) -> list[TravelNoteCommentResponse]:
        result = await db.execute(
            select(TravelNoteComment)
            .where(TravelNoteComment.note_id == note_id)
            .options(selectinload(TravelNoteComment.user))
            .order_by(TravelNoteComment.created_at.asc())
            .limit(50)
        )
        return [
            TravelNoteCommentResponse(
                id=comment.id,
                content=comment.content,
                author=self._author_response(comment.user),
                created_at=comment.created_at,
            )
            for comment in result.scalars().all()
        ]

    async def _viewer_interactions(self, db: AsyncSession, note_id: int, user_id: int) -> dict[str, bool]:
        result = await db.execute(
            select(TravelNoteInteraction).where(
                TravelNoteInteraction.note_id == note_id,
                TravelNoteInteraction.user_id == user_id,
                TravelNoteInteraction.active.is_(True),
            )
        )
        return {item.interaction_type: True for item in result.scalars().all()}

    async def _get_interaction(
        self,
        db: AsyncSession,
        note_id: int,
        user_id: int,
        interaction_type: str,
    ) -> TravelNoteInteraction | None:
        result = await db.execute(
            select(TravelNoteInteraction).where(
                TravelNoteInteraction.note_id == note_id,
                TravelNoteInteraction.user_id == user_id,
                TravelNoteInteraction.interaction_type == interaction_type,
            )
        )
        return result.scalar_one_or_none()

    async def _track_note_event(
        self,
        db: AsyncSession,
        user_id: int,
        note: TravelNote,
        event_type: str,
        *,
        extra_context: dict | None = None,
    ) -> None:
        context = {"title": note.title, "destination": note.destination, "tags": note.tags}
        if extra_context:
            context.update(extra_context)
        await recommendation_service.track(
            db,
            user_id=user_id,
            domain="travel",
            item_type="travel_note",
            item_id=note.id,
            event_type=event_type,
            context=context,
            commit=False,
        )

    @staticmethod
    def _author_response(user: User) -> TravelNoteAuthor:
        return TravelNoteAuthor(
            id=user.id,
            username=user.username,
            display_name=user.display_name or user.username,
            avatar_url=user.avatar_url,
        )

    @staticmethod
    def _clean_tags(tags: list[str]) -> list[str]:
        return [tag.strip() for tag in tags if tag.strip()][:12]

    @staticmethod
    def _require_owner(note: TravelNote, current_user: User, action: str) -> None:
        if note.author_id != current_user.id:
            raise HTTPException(status_code=403, detail=f"Cannot {action} this note")

    @staticmethod
    def _apply_interaction(
        interaction: TravelNoteInteraction | None,
        payload: TravelNoteInteractionRequest,
    ) -> int:
        if interaction:
            if interaction.active != payload.active:
                interaction.active = payload.active
                return 1 if payload.active else -1
            return 0
        return 1 if payload.active else 0


share_service = ShareService()
