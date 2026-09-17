"""Durable delivery queue for notifications.

One row is one planned delivery with its own attempt counter. ``dedup_key`` is
unique, so the scheduler may run as often as it likes without ever queueing the
same message twice.
"""

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
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.reminders.models import (
    DEDUP_KEY_MAX_LENGTH,
    DeliveryStatus,
    kinds,
    statuses,
)


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class ScheduledNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A notification the worker still has to deliver."""

    __tablename__ = "scheduled_notification"
    __table_args__ = (
        CheckConstraint(_in_clause("kind", kinds()), name="kind_valid"),
        CheckConstraint(_in_clause("status", statuses()), name="status_valid"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        Index("ix_scheduled_notification_status_run_at", "status", "run_at"),
        Index("ix_scheduled_notification_user_id_run_at", "user_id", "run_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        default=DeliveryStatus.PENDING.value,
        server_default="pending",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedup_key: Mapped[str] = mapped_column(
        String(DEDUP_KEY_MAX_LENGTH), nullable=False, unique=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
