"""Application-level chat orchestration.

This layer owns the request workflow: conversation state, agent invocation,
artifact persistence, and preference learning. HTTP handlers should stay thin.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import travel_agent
from app.agents.result import AgentResult
from app.agents.supervisor import run_agent, run_agent_stream
from app.core.database import async_session
from app.models.user import User
from app.schemas.travel import ChatRequest, ChatResponse
from app.services.artifact_service import (
    build_chat_response,
    save_or_update_travel_plan,
    save_restaurant_recommendation,
)
from app.services.conversation_service import (
    load_or_create_conversation,
    load_travel_plan_context,
    save_conversation,
)
from app.services.preference_learner import (
    extract_preferences,
    flush_to_db,
    merge_preferences,
    should_flush,
)
from app.services.runtime import (
    create_task_run,
    emit_domain_event,
    mark_task_failed,
    mark_task_succeeded,
)
from app.services.recommendation import recommendation_service
from app.services.truncation import truncate_messages
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


async def _track_recommendation_safe(
    db: AsyncSession,
    *,
    user_id: int,
    domain: str,
    item_type: str,
    item_id: str | int,
    event_type: str,
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> None:
    try:
        async with async_session() as event_db:
            await recommendation_service.track(
                event_db,
                user_id=user_id,
                domain=domain,
                item_type=item_type,
                item_id=item_id,
                event_type=event_type,
                context=context or {},
                session_id=session_id,
                commit=True,
            )
    except Exception as exc:
        logger.debug("Recommendation event skipped: %s", exc)


async def _learn_from_message(
    user_message: str,
    context: dict[str, Any],
    user_id: int,
    db: AsyncSession,
) -> None:
    if len(user_message.strip()) < 10:
        return
    current_plan = context.get("current_travel_plan") or {}
    constraints = travel_agent.infer_travel_constraints(
        user_message,
        current_plan.get("itinerary", {}) if isinstance(current_plan, dict) else {},
    )
    if constraints.get("avoid_pois"):
        return
    try:
        signals = await extract_preferences(user_message)
        if not signals:
            return
        accumulated = context.get("_learned_preferences", {})
        merged = merge_preferences(accumulated, signals)
        context["_learned_preferences"] = merged

        count = context.get("_pref_extraction_count", 0) + 1
        context["_pref_extraction_count"] = count

        if should_flush(count):
            await flush_to_db(user_id, merged, db)
    except Exception as exc:
        logger.debug("Preference learning skipped: %s", exc)


async def handle_chat(
    payload: ChatRequest,
    current_user: User,
    db: AsyncSession,
    existing_task: Any | None = None,
) -> ChatResponse:
    session_id = payload.session_id or str(uuid.uuid4())
    task = existing_task
    if task is None:
        task = await create_task_run(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            task_type="chat",
            input_payload={"message": payload.message, "travel_plan_id": payload.travel_plan_id},
            max_retries=3,
        )
    try:
        conversation, messages, context = await load_or_create_conversation(
            session_id,
            current_user.id,
            payload.message,
            current_user.preferences,
            db,
        )
        context = await load_travel_plan_context(payload.travel_plan_id, current_user.id, context, db)
        _update_travel_memory_from_message(context, payload.message)
        await _track_recommendation_safe(
            db,
            user_id=current_user.id,
            domain="home",
            item_type="chat_message",
            item_id=session_id,
            event_type="chat_mention",
            context={"message": payload.message, "travel_plan_id": payload.travel_plan_id},
            session_id=session_id,
        )

        messages.append({"role": "user", "content": payload.message, "session_id": session_id})
        messages = await truncate_messages(messages)

        legacy_result = await run_agent(
            user_message=payload.message,
            messages=messages,
            context=context,
            user_id=current_user.id,
            db=db,
        )
        result = AgentResult.from_legacy(legacy_result)
        messages.append({"role": "assistant", "content": result.response, "session_id": session_id})

        travel_plan_resp = None
        if result.travel_plan:
            travel_plan_resp, ctx_update = await save_or_update_travel_plan(
                result.travel_plan,
                current_user.id,
                payload.travel_plan_id,
                db,
            )
            if ctx_update:
                context["current_travel_plan"] = ctx_update

        restaurant_record = await save_restaurant_recommendation(
            result=result,
            user_id=current_user.id,
            session_id=session_id,
            query=payload.message,
            db=db,
        )
        if restaurant_record:
            result.restaurant_recommendation_id = restaurant_record.id
            result.restaurant_recommendation = restaurant_record

        await _emit_result_events(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            task_id=task.task_id,
            result=result,
            travel_plan=travel_plan_resp,
            restaurant_record=restaurant_record,
        )
        await mark_task_succeeded(task, result_payload=_task_result_payload(result))

        _sync_artifacts_to_context(context, result)
        await save_conversation(conversation, messages, context, session_id, db)
        await _learn_from_message(payload.message, context, current_user.id, db)

        await db.commit()  # single commit for the entire chat flow
        return build_chat_response(session_id, result, travel_plan_resp)
    except Exception as exc:
        original_exc = exc
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.warning("Rollback failed during error handling: %s", rb_exc)
        try:
            from app.models.runtime import TaskRun
            from sqlalchemy import select

            stmt = select(TaskRun).where(TaskRun.task_id == task.task_id)
            result = await db.execute(stmt)
            t = result.scalar_one_or_none()
            if t:
                t.status = "failed"
                t.error = str(original_exc)[:2000]
                t.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
        except Exception as inner_exc:
            logger.warning("Task status update failed after chat error: %s", inner_exc)
            await db.rollback()
        raise original_exc


async def enqueue_chat_background(
    payload: ChatRequest,
    current_user: User,
    db: AsyncSession,
) -> ChatResponse:
    """Enqueue a chat message for background processing via arq.

    The HTTP handler returns immediately with a ``task_id`` the client
    can poll via ``GET /api/v1/runtime/tasks/{task_id}``.
    """
    from app.services.job_enqueue import enqueue_job

    session_id = payload.session_id or str(uuid.uuid4())

    task = await create_task_run(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        task_type="chat_background",
        input_payload={"message": payload.message, "travel_plan_id": payload.travel_plan_id},
        max_retries=2,
    )
    await db.commit()

    job_id = await enqueue_job(
        "background_chat_job",
        user_id=current_user.id,
        session_id=session_id,
        message=payload.message,
        travel_plan_id=payload.travel_plan_id,
        task_id=task.task_id,
    )

    if job_id is None:
        await mark_task_failed(task, error="Failed to enqueue background job")
        await db.commit()
        return build_chat_response(session_id, AgentResult(response="后台任务提交失败，请稍后重试。"))

    return ChatResponse(
        session_id=session_id,
        message="已提交后台处理任务，你可以稍后查看结果。",
        artifacts={"task_id": task.task_id, "job_id": job_id, "status": "pending"},
    )


async def stream_chat_events(
    payload: ChatRequest,
    current_user: User,
    db: AsyncSession,
) -> AsyncIterator[str]:
    session_id = payload.session_id or str(uuid.uuid4())
    task = await create_task_run(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        task_type="chat_stream",
        input_payload={"message": payload.message, "travel_plan_id": payload.travel_plan_id},
        max_retries=3,
    )
    conversation, messages, context = await load_or_create_conversation(
        session_id,
        current_user.id,
        payload.message,
        current_user.preferences,
        db,
    )
    context = await load_travel_plan_context(payload.travel_plan_id, current_user.id, context, db)
    _update_travel_memory_from_message(context, payload.message)

    messages.append({"role": "user", "content": payload.message, "session_id": session_id})
    messages = await truncate_messages(messages)

    full_response = ""
    result = AgentResult(response="")
    travel_plan_resp = None
    stream_error = ""

    try:
        async for event in run_agent_stream(
            user_message=payload.message,
            messages=messages,
            context=context,
            user_id=current_user.id,
            db=db,
        ):
            event_type = event["type"]
            if event_type == "token":
                full_response += event["content"]
                yield _sse({"type": "token", "content": event["content"]})
            elif event_type == "result":
                result = AgentResult.from_legacy(event["content"])
                full_response = result.response
                yield _sse({"type": "result", "content": result.response})
                for artifact_event in _artifact_events(result):
                    yield _sse(artifact_event)
            elif event_type == "thinking":
                yield _sse({"type": "thinking", "content": event["content"]})
            elif event_type == "done":
                break
    except Exception as exc:
        logger.warning("Agent stream error: %s", exc)
        stream_error = str(exc)
        yield _sse({"type": "error", "content": str(exc)})

    messages.append({"role": "assistant", "content": full_response, "session_id": session_id})

    try:
        if result.travel_plan:
            travel_plan_resp, ctx_update = await save_or_update_travel_plan(
                result.travel_plan,
                current_user.id,
                payload.travel_plan_id,
                db,
            )
            if ctx_update:
                context["current_travel_plan"] = ctx_update
                plan_dict = travel_plan_resp.model_dump(mode="json") if travel_plan_resp else ctx_update
                yield _sse({"type": "plan", "content": plan_dict})

        restaurant_record = await save_restaurant_recommendation(
            result=result,
            user_id=current_user.id,
            session_id=session_id,
            query=payload.message,
            db=db,
        )
        if restaurant_record:
            result.restaurant_recommendation_id = restaurant_record.id
            result.restaurant_recommendation = restaurant_record
            yield _sse({"type": "restaurants", "content": restaurant_record.model_dump(mode="json")})

        await _emit_result_events(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            task_id=task.task_id,
            result=result,
            travel_plan=travel_plan_resp,
            restaurant_record=restaurant_record,
        )
        if stream_error:
            await mark_task_failed(task, error=stream_error, result_payload=_task_result_payload(result))
        else:
            await mark_task_succeeded(task, result_payload=_task_result_payload(result))

        _sync_artifacts_to_context(context, result)
        await save_conversation(conversation, messages, context, session_id, db)
        await _learn_from_message(payload.message, context, current_user.id, db)
        await db.commit()
    except Exception as exc:
        logger.warning("Chat stream persistence error: %s", exc)
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.warning("Rollback failed during stream error handling: %s", rb_exc)
        try:
            await mark_task_failed(task, error=str(exc), result_payload=_task_result_payload(result))
            await db.commit()
        except Exception:
            await db.rollback()
        yield _sse({"type": "error", "content": "对话结果保存失败，请重试。"})
    yield _sse({"type": "done"})


def _sync_artifacts_to_context(context: dict[str, Any], result: AgentResult) -> None:
    if result.products:
        context["current_products"] = result.products
    if result.restaurant_recommendation:
        if hasattr(result.restaurant_recommendation, "model_dump"):
            context["current_restaurant_recommendation"] = result.restaurant_recommendation.model_dump(mode="json")
        else:
            context["current_restaurant_recommendation"] = result.restaurant_recommendation
    if result.diet_plan:
        context["current_diet_plan"] = result.diet_plan
    if result.cart_items:
        context["current_cart_items"] = result.cart_items


def _update_travel_memory_from_message(context: dict[str, Any], user_message: str) -> None:
    current_plan = context.get("current_travel_plan") or {}
    current_itinerary = current_plan.get("itinerary", {}) if isinstance(current_plan, dict) else {}
    constraints = travel_agent.infer_travel_constraints(user_message, current_itinerary)
    if not constraints.get("avoid_pois") and not constraints.get("requested_pois"):
        return
    context["travel_memory"] = travel_agent.merge_travel_memory(
        context.get("travel_memory"),
        avoid_pois=constraints.get("avoid_pois"),
        requested_pois=constraints.get("requested_pois"),
        last_adjustment=user_message,
    )


def _artifact_events(result: AgentResult) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if result.products:
        events.append({"type": "products", "content": result.products})
    if result.restaurant_recommendation:
        events.append({"type": "restaurants", "content": result.restaurant_recommendation})
    elif result.restaurants:
        events.append({"type": "restaurants", "content": result.restaurants})
    if result.diet_plan:
        events.append({"type": "diet_plan", "content": result.diet_plan})
    if result.cart_items:
        events.append({"type": "cart_items", "content": result.cart_items})
    return events


async def _emit_result_events(
    *,
    db: AsyncSession,
    user_id: int,
    session_id: str,
    task_id: str,
    result: AgentResult,
    travel_plan: Any | None,
    restaurant_record: Any | None,
) -> None:
    await emit_domain_event(
        db=db,
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        event_type="chat.completed",
        aggregate_type="conversation",
        aggregate_id=session_id,
        payload=_task_result_payload(result),
    )
    if travel_plan:
        await _track_recommendation_safe(
            db,
            user_id=user_id,
            domain="travel",
            item_type="travel_plan",
            item_id=travel_plan.id,
            event_type="chat_mention",
            context=travel_plan.model_dump(mode="json"),
            session_id=session_id,
        )
        await emit_domain_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            event_type="travel_plan.saved",
            aggregate_type="travel_plan",
            aggregate_id=travel_plan.id,
            payload=travel_plan.model_dump(mode="json"),
        )
    if restaurant_record:
        await _track_recommendation_safe(
            db,
            user_id=user_id,
            domain="restaurant",
            item_type="restaurant_recommendation",
            item_id=restaurant_record.id,
            event_type="chat_mention",
            context=restaurant_record.model_dump(mode="json"),
            session_id=session_id,
        )
        await emit_domain_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            event_type="restaurant_recommendation.saved",
            aggregate_type="restaurant_recommendation",
            aggregate_id=restaurant_record.id,
            payload=restaurant_record.model_dump(mode="json"),
        )
    if result.products:
        for product in result.products[:8]:
            product_id = product.get("id") or product.get("product_id") or product.get("name")
            if product_id:
                await _track_recommendation_safe(
                    db,
                    user_id=user_id,
                    domain="commerce",
                    item_type="product",
                    item_id=product_id,
                    event_type="chat_mention",
                    context=product,
                    session_id=session_id,
                )
        await emit_domain_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            event_type="commerce.products_recommended",
            aggregate_type="conversation",
            aggregate_id=session_id,
            payload={"products": result.products},
        )
    if result.cart_items:
        await emit_domain_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            event_type="commerce.cart_items_added",
            aggregate_type="cart",
            aggregate_id=session_id,
            payload={"cart_items": result.cart_items},
        )
    if result.diet_plan:
        await _track_recommendation_safe(
            db,
            user_id=user_id,
            domain="diet",
            item_type="diet_plan",
            item_id=session_id,
            event_type="chat_mention",
            context={"diet_plan": result.diet_plan},
            session_id=session_id,
        )
        await emit_domain_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            event_type="diet.plan_generated",
            aggregate_type="conversation",
            aggregate_id=session_id,
            payload={"diet_plan": result.diet_plan},
        )


def _task_result_payload(result: AgentResult) -> dict[str, Any]:
    return {
        "response_preview": result.response[:300],
        "has_travel_plan": result.travel_plan is not None,
        "product_count": len(result.products),
        "restaurant_count": len(result.restaurants),
        "restaurant_recommendation_id": result.restaurant_recommendation_id,
        "has_diet_plan": result.diet_plan is not None,
        "cart_item_count": len(result.cart_items),
        "artifact_keys": sorted(result.artifacts.keys()),
    }


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
