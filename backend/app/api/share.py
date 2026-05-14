from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.share import (
    TravelNoteCommentCreate,
    TravelNoteCreate,
    TravelNoteInteractionRequest,
    TravelNoteResponse,
    TravelNoteUpdate,
)
from app.services.share_service import share_service

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("/notes", response_model=list[TravelNoteResponse])
async def list_travel_notes(
    current_user: CurrentUser,
    db: DbSession,
    destination: str | None = Query(None),
    tag: str | None = Query(None),
    mine: bool = Query(False),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    return await share_service.list_notes(
        db,
        current_user=current_user,
        destination=destination,
        tag=tag,
        mine=mine,
        limit=limit,
        offset=offset,
    )


@router.post("/notes", response_model=TravelNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_travel_note(
    payload: TravelNoteCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    return await share_service.create_note(db, current_user=current_user, payload=payload)


@router.get("/notes/recommended", response_model=list[TravelNoteResponse])
async def recommended_travel_notes(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(12, ge=1, le=30),
):
    return await share_service.recommended_notes(db, current_user=current_user, limit=limit)


@router.get("/notes/{note_id}", response_model=TravelNoteResponse)
async def get_travel_note(
    note_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    return await share_service.get_note(db, note_id=note_id, current_user=current_user)


@router.put("/notes/{note_id}", response_model=TravelNoteResponse)
async def update_travel_note(
    note_id: int,
    payload: TravelNoteUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    return await share_service.update_note(db, note_id=note_id, current_user=current_user, payload=payload)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_travel_note(
    note_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    await share_service.delete_note(db, note_id=note_id, current_user=current_user)


@router.post("/notes/{note_id}/interactions", response_model=TravelNoteResponse)
async def interact_with_travel_note(
    note_id: int,
    payload: TravelNoteInteractionRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return await share_service.interact_with_note(db, note_id=note_id, current_user=current_user, payload=payload)


@router.post("/notes/{note_id}/comments", response_model=TravelNoteResponse, status_code=status.HTTP_201_CREATED)
async def comment_travel_note(
    note_id: int,
    payload: TravelNoteCommentCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    return await share_service.comment_note(db, note_id=note_id, current_user=current_user, payload=payload)
