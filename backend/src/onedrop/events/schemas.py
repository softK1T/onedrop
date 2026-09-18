"""Event request and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

StatusCode = Literal["planned", "done", "cancelled"]
RangeCode = Literal["day", "week"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_range(self) -> EventCreate:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must not be earlier than starts_at")
        return self


class EventUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: StatusCode | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None
    location: str | None
    description: str | None
    status: str
    source_inbox_item_id: UUID | None
    created_at: datetime


class EventWithConflicts(BaseModel):
    """Saved event plus the ids of events it overlaps with.

    Overlaps are reported, never blocking: the user decides.
    """

    event: EventResponse
    conflicts: list[UUID] = Field(default_factory=list)


class EventPage(BaseModel):
    items: list[EventResponse]
    range: RangeCode
    anchor_date: date
    limit: int
    offset: int
    has_more: bool
