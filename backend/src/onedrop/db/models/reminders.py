"""Outbound reminders. Scheduled in UTC, de-duplicated by idempotency key."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import ReminderKind, ReminderStatus, values


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class Reminder(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint(_in_clause("kind", values(ReminderKind)), name="kind_valid"),
        CheckConstraint(_in_clause("status", values(ReminderStatus)), name="status_valid"),
        Index("ix_reminders_status_scheduled_at", "status", "scheduled_at"),
        Index("ix_reminders_user_id_scheduled_at", "user_id", "scheduled_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        default=ReminderStatus.SCHEDULED.value,
        server_default="scheduled",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
