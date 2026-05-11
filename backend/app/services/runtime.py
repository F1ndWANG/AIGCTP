"""Durable task and domain-event services.

These records provide the foundation for retries, async workers, audit trails,
and operational visibility without changing the public API.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import _utcnow
from app.models.runtime import DomainEvent, TaskRun


async def create_task_run(
    *,
    db: AsyncSession,
    user_id: int,
    session_id: str,
    task_type: str,
    input_payload: dict[str, Any],
    max_retries: int = 0,
) -> TaskRun:
    task = TaskRun(
        task_id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        task_type=task_type,
        status="running",
        input=input_payload,
        max_retries=max_retries,
        started_at=_utcnow(),
    )
    db.add(task)
    await db.flush()
    return task


async def mark_task_succeeded(
    task: TaskRun,
    *,
    result_payload: dict[str, Any] | None = None,
) -> None:
    task.status = "succeeded"
    task.result = result_payload or {}
    task.error = ""
    task.finished_at = _utcnow()


async def mark_task_failed(
    task: TaskRun,
    *,
    error: str,
    result_payload: dict[str, Any] | None = None,
) -> None:
    task.status = "failed"
    task.error = error[:2000]
    task.result = result_payload or {}
    task.finished_at = _utcnow()


async def emit_domain_event(
    *,
    db: AsyncSession,
    user_id: int,
    session_id: str,
    event_type: str,
    payload: dict[str, Any],
    task_id: str | None = None,
    aggregate_type: str = "",
    aggregate_id: str | int | None = None,
) -> DomainEvent:
    event = DomainEvent(
        event_id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id or ""),
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return event


async def list_task_runs(
    *,
    db: AsyncSession,
    user_id: int,
    status: str | None = None,
    limit: int = 50,
) -> list[TaskRun]:
    query = select(TaskRun).where(TaskRun.user_id == user_id)
    if status:
        query = query.where(TaskRun.status == status)
    query = query.order_by(TaskRun.created_at.desc()).limit(limit)
    return list((await db.execute(query)).scalars().all())


async def get_task_run(
    *,
    db: AsyncSession,
    user_id: int,
    task_id: str,
) -> TaskRun | None:
    result = await db.execute(
        select(TaskRun).where(TaskRun.user_id == user_id, TaskRun.task_id == task_id)
    )
    return result.scalar_one_or_none()


async def list_domain_events(
    *,
    db: AsyncSession,
    user_id: int,
    session_id: str | None = None,
    task_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[DomainEvent]:
    query = select(DomainEvent).where(DomainEvent.user_id == user_id)
    if session_id:
        query = query.where(DomainEvent.session_id == session_id)
    if task_id:
        query = query.where(DomainEvent.task_id == task_id)
    if event_type:
        query = query.where(DomainEvent.event_type == event_type)
    query = query.order_by(DomainEvent.created_at.desc()).limit(limit)
    return list((await db.execute(query)).scalars().all())


async def prepare_task_retry(task: TaskRun) -> None:
    if task.status != "failed":
        raise ValueError("Only failed tasks can be retried")
    if task.retry_count >= task.max_retries:
        raise ValueError("Task retry limit reached")
    task.retry_count += 1
    task.status = "retrying"
    task.updated_at = _utcnow()
