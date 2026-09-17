"""Note endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.db.repositories.notes import MAX_PAGE_SIZE, MAX_SEARCH_LENGTH
from onedrop.notes.schemas import (
    ConvertToTaskRequest,
    NoteCreate,
    NotePage,
    NoteResponse,
    NoteUpdate,
    PinRequest,
)
from onedrop.notes.service import NoteService
from onedrop.tasks.schemas import TaskResponse

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=NotePage)
async def list_notes(
    session: DbSession,
    user: CurrentUser,
    search: Annotated[str | None, Query(max_length=MAX_SEARCH_LENGTH)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotePage:
    """Notes with optional full-text-ish search. Pinned notes come first."""
    items, has_more = await NoteService(session).list(
        user.id, search=search, limit=limit, offset=offset
    )
    return NotePage(
        items=[NoteResponse.model_validate(item) for item in items],
        search=search,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate, session: DbSession, user: CurrentUser
) -> NoteResponse:
    note = await NoteService(session).create(user.id, payload)
    return NoteResponse.model_validate(note)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> NoteResponse:
    note = await NoteService(session).get(user.id, note_id)
    return NoteResponse.model_validate(note)


@router.patch("/{note_id}", response_model=NoteResponse)
async def patch_note(
    note_id: uuid.UUID, payload: NoteUpdate, session: DbSession, user: CurrentUser
) -> NoteResponse:
    note = await NoteService(session).patch(user.id, note_id, payload)
    return NoteResponse.model_validate(note)


@router.post("/{note_id}/pin", response_model=NoteResponse)
async def pin_note(
    note_id: uuid.UUID, payload: PinRequest, session: DbSession, user: CurrentUser
) -> NoteResponse:
    """Pin or unpin a note."""
    note = await NoteService(session).set_pinned(user.id, note_id, payload.pinned)
    return NoteResponse.model_validate(note)


@router.post(
    "/{note_id}/convert-to-task",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convert_note_to_task(
    note_id: uuid.UUID,
    payload: ConvertToTaskRequest,
    session: DbSession,
    user: CurrentUser,
) -> TaskResponse:
    """Turn a note into a task, keeping or removing the original note."""
    task = await NoteService(session).convert_to_task(
        user.id, note_id, due_at=payload.due_at, keep_note=payload.keep_note
    )
    return TaskResponse.model_validate(task)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> Response:
    await NoteService(session).delete(user.id, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
