"""Inbox endpoints: list, read, retry, undo, feedback."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.capture.schemas import (
    CaptureAcceptedResponse,
    FeedbackRequest,
    InboxItemResponse,
    InboxPage,
    UndoResponse,
)
from onedrop.capture.service import CaptureService
from onedrop.db.models.enums import InboxStatus
from onedrop.db.repositories.inbox import MAX_PAGE_SIZE, InboxRepository
from onedrop.errors import NotFoundError
from onedrop.queue import enqueue

router = APIRouter(prefix="/inbox", tags=["inbox"])


def _to_response(item: object) -> InboxItemResponse:
    return InboxItemResponse.model_validate(item, from_attributes=True)


@router.get("", response_model=InboxPage)
async def list_inbox(
    session: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> InboxPage:
    """Paginated capture history, newest first."""
    if status_filter is not None and status_filter not in {s.value for s in InboxStatus}:
        status_filter = None
    repository = InboxRepository(session)
    items = await repository.list_for_user(
        user.id, limit=limit + 1, offset=offset, status=status_filter
    )
    has_more = len(items) > limit
    return InboxPage(
        items=[_to_response(item) for item in items[:limit]],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/{item_id}", response_model=InboxItemResponse)
async def get_inbox_item(
    item_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> InboxItemResponse:
    item = await InboxRepository(session).get(item_id, user_id=user.id)
    if item is None:
        raise NotFoundError("Inbox item not found")
    return _to_response(item)


@router.post("/{item_id}/retry", response_model=CaptureAcceptedResponse)
async def retry_inbox_item(
    item_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> CaptureAcceptedResponse:
    """Re-queue a failed capture. The AI ledger prevents double charging."""
    repository = InboxRepository(session)
    item = await repository.get(item_id, user_id=user.id)
    if item is None:
        raise NotFoundError("Inbox item not found")
    await repository.set_status(item.id, InboxStatus.QUEUED.value, error=None)
    await session.commit()
    function = {
        "text": "process_capture",
        "voice": "process_voice_capture",
        "photo": "process_image_capture",
    }[item.input_type]
    await enqueue(function, str(item.id), job_id=f"retry:{item.id}:{item.attempts}")
    return CaptureAcceptedResponse(
        inbox_item_id=item.id, status=InboxStatus.QUEUED.value, message="Retry queued"
    )


@router.post("/{item_id}/undo", response_model=UndoResponse)
async def undo_inbox_item(
    item_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> UndoResponse:
    """Revert every record created by this capture, atomically."""
    reverted = await CaptureService(session).undo(user_id=user.id, inbox_item_id=item_id)
    return UndoResponse(
        inbox_item_id=item_id, reverted=reverted, status=InboxStatus.UNDONE.value
    )


@router.post("/{item_id}/feedback", response_model=InboxItemResponse)
async def add_feedback(
    item_id: uuid.UUID, payload: FeedbackRequest, session: DbSession, user: CurrentUser
) -> InboxItemResponse:
    """Store a thumbs up/down used to improve prompts and fixtures."""
    repository = InboxRepository(session)
    item = await repository.get(item_id, user_id=user.id)
    if item is None:
        raise NotFoundError("Inbox item not found")
    await repository.add_feedback(
        user_id=user.id,
        inbox_item_id=item.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    await session.commit()
    return _to_response(item)
