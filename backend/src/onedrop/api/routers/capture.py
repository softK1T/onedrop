"""Universal capture endpoints for the Mini App."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.capture.media_service import MediaCaptureService
from onedrop.capture.schemas import (
    CaptureAcceptedResponse,
    CreatedEntityResponse,
    OperationResponse,
    TextCaptureRequest,
)
from onedrop.capture.service import CaptureService
from onedrop.db.models.enums import InputType
from onedrop.db.repositories.inbox import InboxRepository
from onedrop.errors import NotFoundError
from onedrop.queue import enqueue
from onedrop.storage import validate_media

router = APIRouter(tags=["capture"])

MAX_IDEMPOTENCY_LENGTH = 128


def _key(provided: str | None) -> str:
    return (provided or f"api:{uuid.uuid4().hex}")[:MAX_IDEMPOTENCY_LENGTH]


@router.post(
    "/capture/text",
    response_model=CaptureAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def capture_text(
    payload: TextCaptureRequest, session: DbSession, user: CurrentUser
) -> CaptureAcceptedResponse:
    """Accept text and queue AI processing."""
    item = await CaptureService(session).create_text_capture(
        user_id=user.id, text=payload.text, idempotency_key=_key(payload.idempotency_key)
    )
    await enqueue("process_capture", str(item.id), job_id=f"capture:{item.id}")
    return CaptureAcceptedResponse(inbox_item_id=item.id, status=item.status)


@router.post(
    "/capture/voice",
    response_model=CaptureAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def capture_voice(
    session: DbSession,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str | None, Form()] = None,
) -> CaptureAcceptedResponse:
    """Accept a voice recording, store it and queue transcription."""
    data = await file.read()
    mime_type = file.content_type or "audio/ogg"
    validate_media(mime_type=mime_type, size_bytes=len(data), kind="audio")
    item = await MediaCaptureService(session).create_media_capture(
        user_id=user.id,
        data=data,
        mime_type=mime_type,
        input_type=InputType.VOICE.value,
        idempotency_key=_key(idempotency_key),
    )
    await enqueue("process_voice_capture", str(item.id), job_id=f"voice:{item.id}")
    return CaptureAcceptedResponse(inbox_item_id=item.id, status=item.status)


@router.post(
    "/capture/image",
    response_model=CaptureAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def capture_image(
    session: DbSession,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str | None, Form()] = None,
) -> CaptureAcceptedResponse:
    """Accept a food photo and queue an approximate nutrition estimate."""
    data = await file.read()
    mime_type = file.content_type or "image/jpeg"
    validate_media(mime_type=mime_type, size_bytes=len(data), kind="image")
    item = await MediaCaptureService(session).create_media_capture(
        user_id=user.id,
        data=data,
        mime_type=mime_type,
        input_type=InputType.PHOTO.value,
        idempotency_key=_key(idempotency_key),
    )
    await enqueue("process_image_capture", str(item.id), job_id=f"image:{item.id}")
    return CaptureAcceptedResponse(inbox_item_id=item.id, status=item.status)


@router.get("/operations/{operation_id}", response_model=OperationResponse)
async def get_operation(
    operation_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> OperationResponse:
    """Poll one capture: status, created records, clarification question."""
    repository = InboxRepository(session)
    item = await repository.get(operation_id, user_id=user.id)
    if item is None:
        raise NotFoundError("Operation not found")
    links = await repository.links(item.id)
    return OperationResponse(
        inbox_item_id=item.id,
        status=item.status,
        input_type=item.input_type,
        created=[
            CreatedEntityResponse(entity_type=link.entity_type, entity_id=link.entity_id)
            for link in links
        ],
        clarification_question=item.clarification_question,
        error=item.error,
        transcript=item.transcript,
        ai_result=item.ai_result,
        processing_ms=item.processing_ms,
        created_at=item.created_at,
    )
