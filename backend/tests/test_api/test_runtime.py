"""Tests for runtime task visibility and retry APIs."""

from app.services.runtime import create_task_run, emit_domain_event, mark_task_failed


class TestRuntimeAPI:
    async def test_list_tasks_and_events(self, client, auth_headers):
        chat = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "你好",
            "session_id": "runtime-api-session",
        })
        assert chat.status_code == 200

        tasks = await client.get("/api/v1/runtime/tasks", headers=auth_headers)
        assert tasks.status_code == 200
        task_items = tasks.json()
        assert any(item["session_id"] == "runtime-api-session" for item in task_items)

        events = await client.get(
            "/api/v1/runtime/events?session_id=runtime-api-session",
            headers=auth_headers,
        )
        assert events.status_code == 200
        assert any(item["event_type"] == "chat.completed" for item in events.json())

    async def test_get_task_events(self, client, auth_headers):
        chat = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "你好",
            "session_id": "runtime-task-events-session",
        })
        assert chat.status_code == 200

        tasks = await client.get(
            "/api/v1/runtime/tasks?status=succeeded",
            headers=auth_headers,
        )
        task = next(item for item in tasks.json() if item["session_id"] == "runtime-task-events-session")

        events = await client.get(
            f"/api/v1/runtime/tasks/{task['task_id']}/events",
            headers=auth_headers,
        )
        assert events.status_code == 200
        assert any(item["task_id"] == task["task_id"] for item in events.json())

    async def test_retry_failed_chat_task(self, client, auth_headers, session, test_user):
        task = await create_task_run(
            db=session,
            user_id=test_user.id,
            session_id="retry-session",
            task_type="chat",
            input_payload={"message": "你好", "travel_plan_id": None},
            max_retries=1,
        )
        await mark_task_failed(task, error="transient failure")
        await emit_domain_event(
            db=session,
            user_id=test_user.id,
            session_id="retry-session",
            task_id=task.task_id,
            event_type="chat.failed",
            payload={"error": "transient failure"},
        )
        await session.commit()

        retry = await client.post(
            f"/api/v1/runtime/tasks/{task.task_id}/retry",
            headers=auth_headers,
        )
        assert retry.status_code == 200
        assert retry.json()["session_id"] == "retry-session"

        tasks = await client.get("/api/v1/runtime/tasks", headers=auth_headers)
        retrying_original = next(item for item in tasks.json() if item["task_id"] == task.task_id)
        assert retrying_original["status"] == "retrying"
        assert retrying_original["retry_count"] == 1
        assert any(
            item["session_id"] == "retry-session" and item["status"] == "succeeded"
            for item in tasks.json()
        )

    async def test_retry_non_failed_task_returns_conflict(self, client, auth_headers):
        chat = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "你好",
            "session_id": "retry-conflict-session",
        })
        assert chat.status_code == 200
        tasks = await client.get("/api/v1/runtime/tasks", headers=auth_headers)
        task = next(item for item in tasks.json() if item["session_id"] == "retry-conflict-session")

        retry = await client.post(
            f"/api/v1/runtime/tasks/{task['task_id']}/retry",
            headers=auth_headers,
        )
        assert retry.status_code == 409
