"""Task request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PriorityCode = Literal["low", "normal", "high"]
StatusCode = Literal["open", "done", "cancelled"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    priority: PriorityCode = "normal"
    category: str | None = Field(default=None, max_length=32)
    reminder_at: datetime | None = None


class TaskUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    priority: PriorityCode | None = None
    status: StatusCode | None = None
    category: str | None = Field(default=None, max_length=32)
    reminder_at: datetime | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    due_at: datetime | None
    priority: str
    status: str
    category: str | None
    reminder_at: datetime | None
    completed_at: datetime | None
    source_inbox_item_id: UUID | None
    created_at: datetime


class TaskPage(BaseModel):
    items: list[TaskResponse]
    limit: int
    offset: int
    has_more: bool
    filter: str
