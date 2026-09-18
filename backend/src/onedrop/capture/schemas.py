"""Capture request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from onedrop.ai.schemas import CaptureResult


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextCaptureRequest(StrictModel):
    text: str = Field(min_length=1, max_length=4000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class CaptureCorrectionRequest(StrictModel):
    """A user-confirmed structured result that replaces a capture's records."""

    result: CaptureResult

    @model_validator(mode="after")
    def _check_result(self) -> CaptureCorrectionRequest:
        if self.result.needs_confirmation:
            raise ValueError("corrected result must not require confirmation")
        if not self.result.actionable_intents:
            raise ValueError("corrected result must contain an actionable intent")
        return self


class CaptureAcceptedResponse(BaseModel):
    """Immediate acknowledgement: processing continues in the worker."""

    inbox_item_id: UUID
    status: str
    message: str = "Accepted, parsing your message"


class CreatedEntityResponse(BaseModel):
    entity_type: str
    entity_id: UUID


class OperationResponse(BaseModel):
    """Polling response for `GET /operations/{id}`."""

    inbox_item_id: UUID
    status: str
    input_type: str
    created: list[CreatedEntityResponse] = Field(default_factory=list)
    clarification_question: str | None = None
    error: str | None = None
    transcript: str | None = None
    ai_result: dict[str, Any] | None = None
    processing_ms: int | None = None
    created_at: datetime


class FeedbackRequest(StrictModel):
    rating: int = Field(ge=-1, le=1)
    comment: str | None = Field(default=None, max_length=500)


class UndoResponse(BaseModel):
    inbox_item_id: UUID
    reverted: int
    status: str


class InboxItemResponse(BaseModel):
    id: UUID
    input_type: str
    status: str
    raw_text: str | None
    transcript: str | None
    clarification_question: str | None
    error: str | None
    provider: str | None
    model: str | None
    processing_ms: int | None
    created_at: datetime


class InboxPage(BaseModel):
    items: list[InboxItemResponse]
    limit: int
    offset: int
    has_more: bool
