"""Runtime operations API for task visibility and retry."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.runtime import DomainEventResponse, TaskRunResponse
from app.schemas.travel import ChatRequest, ChatResponse
from app.services.chat_orchestrator import handle_chat
from app.services.runtime import (
    get_task_run,
    list_domain_events,
    list_task_runs,
    prepare_task_retry,
)

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/tasks", response_model=list[TaskRunResponse])
async def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_task_runs(
        db=db,
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
    )


@router.get("/tasks/{task_id}", response_model=TaskRunResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_run(db=db, user_id=current_user.id, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/events", response_model=list[DomainEventResponse])
async def list_events(
    session_id: str | None = None,
    task_id: str | None = None,
    event_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_domain_events(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        task_id=task_id,
        event_type=event_type,
        limit=limit,
    )


@router.get("/tasks/{task_id}/events", response_model=list[DomainEventResponse])
async def list_task_events(
    task_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_run(db=db, user_id=current_user.id, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return await list_domain_events(
        db=db,
        user_id=current_user.id,
        task_id=task_id,
        limit=limit,
    )


@router.post("/tasks/{task_id}/retry", response_model=ChatResponse)
async def retry_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_run(db=db, user_id=current_user.id, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.task_type not in ("chat", "chat_stream"):
        raise HTTPException(status_code=400, detail="Only chat tasks can be retried")
    try:
        await prepare_task_retry(task)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()

    message = (task.input or {}).get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Task input does not contain a message")
    return await handle_chat(
        ChatRequest(
            message=message,
            session_id=task.session_id,
            travel_plan_id=(task.input or {}).get("travel_plan_id"),
        ),
        current_user,
        db,
    )
