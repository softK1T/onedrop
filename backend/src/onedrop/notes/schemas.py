"""Note request and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteCreate(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    pinned: bool = False


class NoteUpdate(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10_000)
    tags: list[str] | None = Field(default=None, max_length=10)
    pinned: bool | None = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    content: str
    tags: list[str]
    pinned: bool
    source_inbox_item_id: UUID | None
    created_at: datetime
    updated_at: datetime


class NotePage(BaseModel):
    items: list[NoteResponse]
    search: str | None
    limit: int
    offset: int
    has_more: bool


class PinRequest(StrictModel):
    pinned: bool


class ConvertToTaskRequest(StrictModel):
    due_at: datetime | None = None
    keep_note: bool = True
