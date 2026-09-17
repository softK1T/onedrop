"""Habit request and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MeasurementCode = Literal["boolean", "numeric"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HabitCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    measurement_type: MeasurementCode = "boolean"
    target_value: int | None = Field(default=None, ge=0, le=100_000)
    unit: str | None = Field(default=None, max_length=20)
    schedule_days: list[int] = Field(default_factory=list, max_length=7)
    reminder_hour: int | None = Field(default=None, ge=0, le=23)

    @field_validator("schedule_days")
    @classmethod
    def _check_days(cls, value: list[int]) -> list[int]:
        if any(day < 1 or day > 7 for day in value):
            raise ValueError("schedule_days must contain ISO weekday numbers 1-7")
        return value


class HabitUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    measurement_type: MeasurementCode | None = None
    target_value: int | None = Field(default=None, ge=0, le=100_000)
    unit: str | None = Field(default=None, max_length=20)
    schedule_days: list[int] | None = Field(default=None, max_length=7)
    reminder_hour: int | None = Field(default=None, ge=0, le=23)
    active: bool | None = None


class HabitLogRequest(StrictModel):
    value: int = Field(default=1, ge=0, le=100_000)
    logged_at: datetime | None = None


class HabitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    measurement_type: str
    target_value: int | None
    unit: str | None
    active: bool
    reminder_hour: int | None
    source_inbox_item_id: UUID | None
    created_at: datetime


class HabitLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    habit_id: UUID
    value: int
    logged_at: datetime
    source_inbox_item_id: UUID | None


class HabitProgressResponse(BaseModel):
    habit_id: UUID
    name: str
    period_start: date
    period_end: date
    scheduled_days: list[int]
    expected: int
    completed: int
    missed: int
    percent: int | None


class HabitPage(BaseModel):
    items: list[HabitResponse]
    limit: int
    offset: int
    has_more: bool


class HabitLogPage(BaseModel):
    items: list[HabitLogResponse]
    limit: int
    offset: int
    has_more: bool
