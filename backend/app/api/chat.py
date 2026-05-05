import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
import json

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.travel import TravelPlan
from app.schemas.travel import ChatRequest, ChatResponse, TravelPlanResponse, ChatSessionListItem, ChatSessionDetailResponse
from app.agents.supervisor import run_agent, run_agent_stream
from app.services.truncation import truncate_messages
from app.core.cache import get_json, set_json, delete as cache_delete
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_id = payload.session_id or str(uuid.uuid4())

    # Load or create conversation (try Redis cache first)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    conversation = result.scalar_one_or_none()

    if conversation:
        messages = conversation.messages
        context = conversation.context or {}
        # Warm from Redis cache if DB is empty (first load)
        cached = await get_json(f"conversation:{session_id}")
        if cached and not messages:
            messages = cached.get("messages", [])
            context.update(cached.get("context", {}))
    else:
        messages = []
        context = {"user_preferences": current_user.preferences or {}}
        conversation = Conversation(
            user_id=current_user.id,
            session_id=session_id,
            title=payload.message[:50],
            messages=[],
            context=context,
        )
        db.add(conversation)

    # Load existing travel plan context if adjusting
    if payload.travel_plan_id:
        plan_result = await db.execute(
            select(TravelPlan).where(
                TravelPlan.id == payload.travel_plan_id,
                TravelPlan.user_id == current_user.id,
            )
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            context["current_travel_plan"] = {
                "id": plan.id,
                "destination": plan.destination,
                "days": plan.days,
                "itinerary": plan.itinerary,
            }

    # Add user message
    messages.append({"role": "user", "content": payload.message, "session_id": session_id})

    # Truncate conversation history if too long
    messages = await truncate_messages(messages)

    # Run AI agent
    agent_result = await run_agent(
        user_message=payload.message,
        messages=messages,
        context=context,
        user_id=current_user.id,
        db=db,
    )

    # Add assistant response
    messages.append({"role": "assistant", "content": agent_result["response"], "session_id": session_id})

    # Save or update travel plan
    travel_plan_resp = None
    if agent_result.get("travel_plan"):
        plan_data = agent_result["travel_plan"]

        if payload.travel_plan_id:
            # Update existing plan (adjustment flow)
            result = await db.execute(
                select(TravelPlan).where(
                    TravelPlan.id == payload.travel_plan_id,
                    TravelPlan.user_id == current_user.id,
                )
            )
            existing_plan = result.scalar_one_or_none()
            if existing_plan:
                existing_plan.destination = plan_data.get("destination", existing_plan.destination)
                existing_plan.days = plan_data.get("days", existing_plan.days)
                existing_plan.itinerary = plan_data.get("itinerary", existing_plan.itinerary)
                existing_plan.preferences = plan_data.get("preferences", existing_plan.preferences)
                flag_modified(existing_plan, "itinerary")
                flag_modified(existing_plan, "preferences")
                await db.flush()
                await db.refresh(existing_plan)
                travel_plan_resp = TravelPlanResponse.model_validate(existing_plan)
                context["current_travel_plan"] = {
                    "id": existing_plan.id,
                    "destination": existing_plan.destination,
                    "days": existing_plan.days,
                    "itinerary": existing_plan.itinerary,
                }
        else:
            # Create new plan
            new_plan = TravelPlan(
                user_id=current_user.id,
                destination=plan_data.get("destination", ""),
                days=plan_data.get("days", 3),
                itinerary=plan_data.get("itinerary", {}),
                preferences=plan_data.get("preferences", {}),
                status="draft",
            )
            db.add(new_plan)
            await db.flush()
            await db.refresh(new_plan)
            travel_plan_resp = TravelPlanResponse.model_validate(new_plan)
            context["current_travel_plan"] = {
                "id": new_plan.id,
                "destination": new_plan.destination,
                "days": new_plan.days,
                "itinerary": new_plan.itinerary,
            }

    # Update conversation — flag_modified ensures JSON column change is tracked
    conversation.messages = list(messages)
    conversation.context = dict(context)
    flag_modified(conversation, "context")
    flag_modified(conversation, "messages")
    await db.commit()

    # Write to Redis cache
    await set_json(
        f"conversation:{session_id}",
        {"messages": list(messages), "context": dict(context)},
        ttl=settings.REDIS_TTL_CONVERSATION,
    )

    return ChatResponse(
        session_id=session_id,
        message=agent_result["response"],
        travel_plan=travel_plan_resp,
    )


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_id = payload.session_id or str(uuid.uuid4())

    # Load or create conversation (try Redis cache first)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    conversation = result.scalar_one_or_none()

    if conversation:
        messages = conversation.messages
        context = conversation.context or {}
        cached = await get_json(f"conversation:{session_id}")
        if cached and not messages:
            messages = cached.get("messages", [])
            context.update(cached.get("context", {}))
    else:
        messages = []
        context = {"user_preferences": current_user.preferences or {}}
        conversation = Conversation(
            user_id=current_user.id,
            session_id=session_id,
            title=payload.message[:50],
            messages=[],
            context=context,
        )
        db.add(conversation)

    # Load existing travel plan context if adjusting
    if payload.travel_plan_id:
        plan_result = await db.execute(
            select(TravelPlan).where(
                TravelPlan.id == payload.travel_plan_id,
                TravelPlan.user_id == current_user.id,
            )
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            context["current_travel_plan"] = {
                "id": plan.id,
                "destination": plan.destination,
                "days": plan.days,
                "itinerary": plan.itinerary,
            }

    # Add user message
    messages.append({"role": "user", "content": payload.message, "session_id": session_id})

    # Truncate conversation history if too long
    messages = await truncate_messages(messages)

    async def event_generator():
        nonlocal messages, conversation, context

        full_response = ""
        travel_plan_data = None
        travel_plan_resp = None

        async for event in run_agent_stream(
            user_message=payload.message,
            messages=messages,
            context=context,
            user_id=current_user.id,
            db=db,
        ):
            if event["type"] == "token":
                full_response += event["content"]
                yield f"data: {json.dumps({'type': 'token', 'content': event['content']}, ensure_ascii=False)}\n\n"

            elif event["type"] == "result":
                full_response = event["content"]["response"]
                travel_plan_data = event["content"].get("travel_plan")
                yield f"data: {json.dumps({'type': 'result', 'content': full_response}, ensure_ascii=False)}\n\n"

            elif event["type"] == "done":
                # Save assistant response
                messages.append({"role": "assistant", "content": full_response, "session_id": session_id})

                # Save or update travel plan
                if travel_plan_data:
                    if payload.travel_plan_id:
                        result = await db.execute(
                            select(TravelPlan).where(
                                TravelPlan.id == payload.travel_plan_id,
                                TravelPlan.user_id == current_user.id,
                            )
                        )
                        existing_plan = result.scalar_one_or_none()
                        if existing_plan:
                            existing_plan.destination = travel_plan_data.get("destination", existing_plan.destination)
                            existing_plan.days = travel_plan_data.get("days", existing_plan.days)
                            existing_plan.itinerary = travel_plan_data.get("itinerary", existing_plan.itinerary)
                            existing_plan.preferences = travel_plan_data.get("preferences", existing_plan.preferences)
                            flag_modified(existing_plan, "itinerary")
                            flag_modified(existing_plan, "preferences")
                            await db.flush()
                            await db.refresh(existing_plan)
                            plan_dict = {
                                "id": existing_plan.id,
                                "destination": existing_plan.destination,
                                "days": existing_plan.days,
                                "itinerary": existing_plan.itinerary,
                                "status": existing_plan.status,
                                "created_at": existing_plan.created_at.isoformat() if existing_plan.created_at else None,
                                "updated_at": existing_plan.updated_at.isoformat() if existing_plan.updated_at else None,
                            }
                            yield f"data: {json.dumps({'type': 'plan', 'content': plan_dict}, ensure_ascii=False)}\n\n"
                            context["current_travel_plan"] = {
                                "id": plan_dict["id"],
                                "destination": plan_dict["destination"],
                                "days": plan_dict["days"],
                                "itinerary": plan_dict["itinerary"],
                            }
                    else:
                        new_plan = TravelPlan(
                            user_id=current_user.id,
                            destination=travel_plan_data.get("destination", ""),
                            days=travel_plan_data.get("days", 3),
                            itinerary=travel_plan_data.get("itinerary", {}),
                            preferences=travel_plan_data.get("preferences", {}),
                            status="draft",
                        )
                        db.add(new_plan)
                        await db.flush()
                        await db.refresh(new_plan)
                        plan_dict = {
                            "id": new_plan.id,
                            "destination": new_plan.destination,
                            "days": new_plan.days,
                            "itinerary": new_plan.itinerary,
                            "status": new_plan.status,
                            "created_at": new_plan.created_at.isoformat() if new_plan.created_at else None,
                            "updated_at": new_plan.updated_at.isoformat() if new_plan.updated_at else None,
                        }
                        yield f"data: {json.dumps({'type': 'plan', 'content': plan_dict}, ensure_ascii=False)}\n\n"
                        context["current_travel_plan"] = {
                            "id": plan_dict["id"],
                            "destination": plan_dict["destination"],
                            "days": plan_dict["days"],
                            "itinerary": plan_dict["itinerary"],
                        }

                # Update conversation
                conversation.messages = list(messages)
                conversation.context = dict(context)
                flag_modified(conversation, "context")
                flag_modified(conversation, "messages")
                await db.commit()

                # Write to Redis cache
                await set_json(
                    f"conversation:{session_id}",
                    {"messages": list(messages), "context": dict(context)},
                    ttl=settings.REDIS_TTL_CONVERSATION,
                )

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/sessions", response_model=list[ChatSessionListItem])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    rows = result.scalars().all()

    # Deduplicate by session_id — keep latest row per session
    seen = {}
    for row in rows:
        if row.session_id not in seen:
            seen[row.session_id] = row

    items = []
    for conv in seen.values():
        messages = conv.messages or []
        count = len(messages)
        last_preview = ""
        if messages:
            last_msg = messages[-1]
            last_preview = (last_msg.get("content") or "")[:60]
        items.append(ChatSessionListItem(
            session_id=conv.session_id,
            title=conv.title or "",
            message_count=count,
            last_preview=last_preview,
            updated_at=conv.updated_at,
        ))
    return items


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatSessionDetailResponse(
        session_id=conv.session_id,
        title=conv.title or "",
        messages=conv.messages or [],
        context=conv.context or {},
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == current_user.id)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    for row in rows:
        await db.delete(row)
    await db.commit()
    await cache_delete(f"conversation:{session_id}")
