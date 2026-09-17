"""User identity, settings, auth sessions and Telegram update log."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from onedrop.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import Currency, values


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locale: Mapped[str] = mapped_column(
        String(8), nullable=False, default="en", server_default="en"
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    settings: Mapped[UserSettings | None] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )


class UserSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint(
            "base_currency IN ('" + "', '".join(values(Currency)) + "')",
            name="base_currency_supported",
        ),
        CheckConstraint(
            "morning_digest_hour >= 0 AND morning_digest_hour <= 23",
            name="morning_digest_hour_range",
        ),
        CheckConstraint(
            "quiet_hours_start >= 0 AND quiet_hours_start <= 23",
            name="quiet_hours_start_range",
        ),
        CheckConstraint(
            "quiet_hours_end >= 0 AND quiet_hours_end <= 23",
            name="quiet_hours_end_range",
        ),
        CheckConstraint(
            "task_reminder_lead_minutes >= 0 AND task_reminder_lead_minutes <= 1440",
            name="task_reminder_lead_minutes_range",
        ),
        CheckConstraint(
            "event_reminder_lead_minutes >= 0 AND event_reminder_lead_minutes <= 1440",
            name="event_reminder_lead_minutes_range",
        ),
        CheckConstraint(
            "budget_warning_threshold_percent >= 1 "
            "AND budget_warning_threshold_percent <= 100",
            name="budget_warning_threshold_percent_range",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Europe/Warsaw", server_default="Europe/Warsaw"
    )
    base_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="PLN", server_default="PLN"
    )
    monthly_budget_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    task_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    event_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    habit_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    morning_digest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    budget_warnings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    morning_digest_hour: Mapped[int] = mapped_column(
        Integer, nullable=False, default=8, server_default="8"
    )
    quiet_hours_start: Mapped[int] = mapped_column(
        Integer, nullable=False, default=22, server_default="22"
    )
    quiet_hours_end: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7, server_default="7"
    )
    task_reminder_lead_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    event_reminder_lead_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, server_default="60"
    )
    budget_warning_threshold_percent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=80, server_default="80"
    )
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allow_training: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="settings")


class AuthSession(UUIDPrimaryKeyMixin, Base):
    """Refresh session; only the hash of the refresh token is stored."""

    __tablename__ = "sessions"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TelegramUpdate(UUIDPrimaryKeyMixin, Base):
    """Idempotency log for Telegram updates."""

    __tablename__ = "telegram_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="received", server_default="received"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
