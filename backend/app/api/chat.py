from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.travel import (
    ChatRequest,
    ChatResponse,
    ChatSessionDetailResponse,
    ChatSessionListItem,
)
from app.services.chat_orchestrator import enqueue_chat_background, handle_chat, stream_chat_events
from app.services.conversation_service import (
    delete_conversation_session,
    get_conversation_session,
    list_conversation_sessions,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send chat message",
    description="Process a user message through the multi-agent system. Supports synchronous mode (blocks for the full response) and background mode (returns immediately with a task_id for polling).",
)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.background:
        return await enqueue_chat_background(payload, current_user, db)
    return await handle_chat(payload, current_user, db)


@router.post(
    "/stream",
    summary="Stream chat response via SSE",
    description="Same as POST /chat but returns a Server-Sent Events stream with token-by-token, thinking, and artifact events.",
)
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        stream_chat_events(payload, current_user, db),
        media_type="text/event-stream",
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionListItem],
    summary="List conversation sessions",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_conversation_sessions(current_user.id, db)


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    summary="Get conversation session detail",
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await get_conversation_session(session_id, current_user.id, db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    summary="Delete conversation session",
)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_conversation_session(session_id, current_user.id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
