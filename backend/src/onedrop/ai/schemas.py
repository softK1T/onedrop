"""Strict Pydantic contract for model output.

The model returns JSON only. Every payload is validated against this
discriminated union before any database work happens. Unknown fields are
rejected, so a hallucinated key fails the capture instead of silently writing
bad data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CurrencyCode = Literal["PLN", "EUR", "USD", "UAH"]
ExpenseCategoryCode = Literal[
    "food",
    "transport",
    "housing",
    "health",
    "entertainment",
    "shopping",
    "bills",
    "education",
    "travel",
    "other",
]
PriorityCode = Literal["low", "normal", "high"]
MealTypeCode = Literal["breakfast", "lunch", "dinner", "snack"]
MeasurementCode = Literal["boolean", "numeric"]

INTENT_TYPES: tuple[str, ...] = (
    "task.create",
    "event.create",
    "expense.create",
    "meal.create",
    "note.create",
    "habit.create",
    "habit.log",
    "unknown",
)


class StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskFields(StrictBase):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    priority: PriorityCode = "normal"
    category: str | None = Field(default=None, max_length=32)
    reminder_at: datetime | None = None


class EventFields(StrictBase):
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    reminder_at: datetime | None = None

    @model_validator(mode="after")
    def _check_range(self) -> EventFields:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must not be earlier than starts_at")
        return self


class ExpenseFields(StrictBase):
    amount_minor: int = Field(ge=0, le=1_000_000_000_000)
    currency: CurrencyCode
    category: ExpenseCategoryCode = "other"
    merchant: str | None = Field(default=None, max_length=120)
    occurred_at: datetime | None = None
    description: str | None = Field(default=None, max_length=500)


class MealFields(StrictBase):
    title: str = Field(min_length=1, max_length=200)
    meal_type: MealTypeCode = "snack"
    eaten_at: datetime | None = None
    calories: int | None = Field(default=None, ge=0, le=20_000)
    protein: int | None = Field(default=None, ge=0, le=2_000)
    fat: int | None = Field(default=None, ge=0, le=2_000)
    carbohydrates: int | None = Field(default=None, ge=0, le=2_000)
    estimated: bool = True


class NoteFields(StrictBase):
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class HabitCreateFields(StrictBase):
    name: str = Field(min_length=1, max_length=100)
    measurement_type: MeasurementCode = "boolean"
    target_value: int | None = Field(default=None, ge=0, le=100_000)
    unit: str | None = Field(default=None, max_length=20)
    schedule_days: list[int] = Field(default_factory=list, max_length=7)

    @model_validator(mode="after")
    def _check_days(self) -> HabitCreateFields:
        if any(day < 1 or day > 7 for day in self.schedule_days):
            raise ValueError("schedule_days must contain ISO weekday numbers 1-7")
        return self


class HabitLogFields(StrictBase):
    habit_name: str = Field(min_length=1, max_length=100)
    value: int = Field(default=1, ge=0, le=100_000)
    logged_at: datetime | None = None


class UnknownFields(StrictBase):
    reason: str = Field(default="not_recognised", max_length=200)


class IntentBase(StrictBase):
    confidence: float = Field(ge=0.0, le=1.0)
    source_fragment: str = Field(min_length=1, max_length=500)


class TaskCreateIntent(IntentBase):
    type: Literal["task.create"]
    fields: TaskFields


class EventCreateIntent(IntentBase):
    type: Literal["event.create"]
    fields: EventFields


class ExpenseCreateIntent(IntentBase):
    type: Literal["expense.create"]
    fields: ExpenseFields


class MealCreateIntent(IntentBase):
    type: Literal["meal.create"]
    fields: MealFields


class NoteCreateIntent(IntentBase):
    type: Literal["note.create"]
    fields: NoteFields


class HabitCreateIntent(IntentBase):
    type: Literal["habit.create"]
    fields: HabitCreateFields


class HabitLogIntent(IntentBase):
    type: Literal["habit.log"]
    fields: HabitLogFields


class UnknownIntent(IntentBase):
    type: Literal["unknown"]
    fields: UnknownFields = Field(default_factory=UnknownFields)


Intent = Annotated[
    TaskCreateIntent
    | EventCreateIntent
    | ExpenseCreateIntent
    | MealCreateIntent
    | NoteCreateIntent
    | HabitCreateIntent
    | HabitLogIntent
    | UnknownIntent,
    Field(discriminator="type"),
]


class CaptureResult(StrictBase):
    """Complete model answer for one capture."""

    language: str = Field(min_length=2, max_length=8)
    timezone: str = Field(min_length=3, max_length=64)
    intents: list[Intent] = Field(default_factory=list, max_length=12)
    needs_confirmation: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _check_clarification(self) -> CaptureResult:
        if self.needs_confirmation and not self.clarification_question:
            raise ValueError("clarification_question is required when needs_confirmation is true")
        return self

    @property
    def actionable_intents(self) -> list[Intent]:
        """Intents that can create records (everything except `unknown`)."""
        return [intent for intent in self.intents if intent.type != "unknown"]

    def min_confidence(self) -> float:
        actionable = self.actionable_intents
        if not actionable:
            return 0.0
        return min(intent.confidence for intent in actionable)


def parse_capture_result(payload: dict[str, Any]) -> CaptureResult:
    """Validate raw model output. Raises pydantic.ValidationError when invalid."""
    return CaptureResult.model_validate(payload)


def capture_result_json_schema() -> dict[str, Any]:
    """JSON schema handed to providers that support structured output."""
    return CaptureResult.model_json_schema()
