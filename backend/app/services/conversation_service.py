"""Conversation persistence and context assembly."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.cache import delete as cache_delete
from app.core.cache import get_json, set_json
from app.core.config import settings
from app.models.conversation import Conversation
from app.models.travel import TravelPlan
from app.schemas.travel import ChatSessionDetailResponse, ChatSessionListItem
from app.services.preference_learner import build_user_profile, format_profile_for_prompt


async def load_or_create_conversation(
    session_id: str,
    user_id: int,
    title: str,
    user_preferences: dict[str, Any],
    db: AsyncSession,
) -> tuple[Conversation, list[dict[str, Any]], dict[str, Any]]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    conversation = result.scalar_one_or_none()

    if conversation:
        messages = conversation.messages or []
        context = conversation.context or {}
        cached = await get_json(f"conversation:{session_id}")
        if cached and not messages:
            messages = cached.get("messages", [])
            context.update(cached.get("context", {}))
    else:
        messages = []
        context = {"user_preferences": user_preferences or {}}
        conversation = Conversation(
            user_id=user_id,
            session_id=session_id,
            title=title[:50],
            messages=[],
            context=context,
        )
        db.add(conversation)

    profile = build_user_profile(user_preferences)
    if profile:
        context["user_profile"] = profile
        profile_text = format_profile_for_prompt(profile)
        if profile_text:
            context["_profile_text"] = profile_text

    context.setdefault("_pref_extraction_count", 0)
    return conversation, messages, context


async def load_travel_plan_context(
    travel_plan_id: int | None,
    user_id: int,
    context: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    if not travel_plan_id:
        return context

    result = await db.execute(
        select(TravelPlan).where(
            TravelPlan.id == travel_plan_id,
            TravelPlan.user_id == user_id,
        )
    )
    plan = result.scalar_one_or_none()
    if plan:
        context["current_travel_plan"] = {
            "id": plan.id,
            "destination": plan.destination,
            "days": plan.days,
            "itinerary": plan.itinerary,
        }
    return context


async def save_conversation(
    conversation: Conversation,
    messages: list[dict[str, Any]],
    context: dict[str, Any],
    session_id: str,
    db: AsyncSession,
) -> None:
    conversation.messages = list(messages)
    conversation.context = dict(context)
    flag_modified(conversation, "context")
    flag_modified(conversation, "messages")
    await db.flush()

    await set_json(
        f"conversation:{session_id}",
        {"messages": list(messages), "context": dict(context)},
        ttl=settings.REDIS_TTL_CONVERSATION,
    )


async def list_conversation_sessions(
    user_id: int,
    db: AsyncSession,
) -> list[ChatSessionListItem]:
    latest_subq = (
        select(
            Conversation.id,
            func.row_number()
            .over(
                partition_by=Conversation.session_id,
                order_by=Conversation.updated_at.desc(),
            )
            .label("rn"),
        )
        .where(Conversation.user_id == user_id)
        .subquery()
    )
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id.in_(select(latest_subq.c.id).where(latest_subq.c.rn == 1)))
        .order_by(Conversation.updated_at.desc())
    )

    items = []
    for conv in result.scalars().all():
        messages = conv.messages or []
        last_preview = (messages[-1].get("content") or "")[:60] if messages else ""
        items.append(
            ChatSessionListItem(
                session_id=conv.session_id,
                title=conv.title or "",
                message_count=len(messages),
                last_preview=last_preview,
                updated_at=conv.updated_at,
            )
        )
    return items


async def get_conversation_session(
    session_id: str,
    user_id: int,
    db: AsyncSession,
) -> ChatSessionDetailResponse | None:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return None
    return ChatSessionDetailResponse(
        session_id=conv.session_id,
        title=conv.title or "",
        messages=conv.messages or [],
        context=conv.context or {},
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


async def delete_conversation_session(session_id: str, user_id: int, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id,
        )
    )
    rows = result.scalars().all()
    if not rows:
        return False
    for row in rows:
        await db.delete(row)
    await db.commit()
    await cache_delete(f"conversation:{session_id}")
    return True
