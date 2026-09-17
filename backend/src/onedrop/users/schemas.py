"""User profile and settings schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CurrencyCode = Literal["PLN", "EUR", "USD", "UAH"]
LocaleCode = Literal["en", "ru", "pl", "uk"]
MAX_LEAD_MINUTES = 1440


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timezone: str
    base_currency: str
    monthly_budget_minor: int | None
    reminders_enabled: bool
    task_reminders: bool
    event_reminders: bool
    habit_reminders: bool
    morning_digest: bool
    budget_warnings: bool
    morning_digest_hour: int
    quiet_hours_start: int
    quiet_hours_end: int
    task_reminder_lead_minutes: int
    event_reminder_lead_minutes: int
    budget_warning_threshold_percent: int
    allow_training: bool
    onboarding_completed: bool
    consent_at: datetime | None


class UserSettingsUpdate(StrictModel):
    timezone: str | None = Field(default=None, min_length=3, max_length=64)
    base_currency: CurrencyCode | None = None
    locale: LocaleCode | None = None
    monthly_budget_minor: int | None = Field(default=None, ge=0, le=1_000_000_000)
    reminders_enabled: bool | None = None
    task_reminders: bool | None = None
    event_reminders: bool | None = None
    habit_reminders: bool | None = None
    morning_digest: bool | None = None
    budget_warnings: bool | None = None
    morning_digest_hour: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_start: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end: int | None = Field(default=None, ge=0, le=23)
    task_reminder_lead_minutes: int | None = Field(
        default=None, ge=0, le=MAX_LEAD_MINUTES
    )
    event_reminder_lead_minutes: int | None = Field(
        default=None, ge=0, le=MAX_LEAD_MINUTES
    )
    budget_warning_threshold_percent: int | None = Field(default=None, ge=1, le=100)
    allow_training: bool | None = None
    onboarding_completed: bool | None = None
    accept_consent: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    telegram_user_id: int
    first_name: str | None
    username: str | None
    locale: str
    created_at: datetime
    settings: UserSettingsResponse


class UsageResponse(BaseModel):
    """Remaining AI allowance, shown in the bot and the Mini App."""

    plan: str
    bonus_used: int
    bonus_limit: int
    period_scope: str
    period_used: int
    period_limit: int
    remaining: int
    photo_recognition: bool
    morning_digest: bool
    csv_export: bool


class ExportResponse(BaseModel):
    """Full export of everything OneDrop stores about the caller."""

    generated_at: datetime
    user: dict[str, Any]
    settings: dict[str, Any]
    counts: dict[str, int]
    tasks: list[dict[str, Any]]
    events: list[dict[str, Any]]
    expenses: list[dict[str, Any]]
    meals: list[dict[str, Any]]
    habits: list[dict[str, Any]]
    habit_logs: list[dict[str, Any]]
    notes: list[dict[str, Any]]
    inbox_items: list[dict[str, Any]]


class DeleteAccountResponse(BaseModel):
    deleted: bool
    media_objects_removed: int
