"""Tests for durable task and domain-event services."""

from sqlalchemy import select

from app.models.runtime import DomainEvent, TaskRun
from app.services.runtime import (
    create_task_run,
    emit_domain_event,
    mark_task_succeeded,
)


async def test_create_task_and_emit_domain_event(session, test_user):
    task = await create_task_run(
        db=session,
        user_id=test_user.id,
        session_id="runtime-session",
        task_type="chat",
        input_payload={"message": "hello"},
    )
    await mark_task_succeeded(task, result_payload={"ok": True})
    event = await emit_domain_event(
        db=session,
        user_id=test_user.id,
        session_id="runtime-session",
        task_id=task.task_id,
        event_type="chat.completed",
        aggregate_type="conversation",
        aggregate_id="runtime-session",
        payload={"ok": True},
    )
    await session.commit()

    task_row = (await session.execute(select(TaskRun).where(TaskRun.task_id == task.task_id))).scalar_one()
    event_row = (await session.execute(select(DomainEvent).where(DomainEvent.event_id == event.event_id))).scalar_one()

    assert task_row.status == "succeeded"
    assert task_row.result["ok"] is True
    assert event_row.event_type == "chat.completed"
    assert event_row.payload["ok"] is True
