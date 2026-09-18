"""Canonical user reminder schedules.

``Reminder`` stores user intent. Delivery attempts live exclusively in
``scheduled_notification`` and reference this row, preventing two senders.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

REMINDER_KINDS = (
    "task_reminder",
    "event_reminder",
    "habit_reminder",
    "morning_digest",
    "budget_warning",
)
REMINDER_STATUSES = ("scheduled", "sent", "cancelled", "failed")
ENTITY_TYPES = ("task", "event", "habit")


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class Reminder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A canonical user schedule; it never sends notifications itself."""

    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint(_in_clause("kind", REMINDER_KINDS), name="kind_valid"),
        CheckConstraint(_in_clause("status", REMINDER_STATUSES), name="status_valid"),
        CheckConstraint(
            "entity_type IS NULL OR " + _in_clause("entity_type", ENTITY_TYPES),
            name="entity_type_valid",
        ),
        CheckConstraint(
            "(entity_type IS NULL) = (entity_id IS NULL)", name="entity_reference_complete"
        ),
        Index("ix_reminders_status_scheduled_at", "status", "scheduled_at"),
        Index("ix_reminders_user_id_scheduled_at", "user_id", "scheduled_at"),
        Index(
            "uq_reminders_active_entity",
            "user_id",
            "kind",
            "entity_id",
            unique=True,
            postgresql_where=text("status = 'scheduled' AND entity_id IS NOT NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="scheduled", server_default="scheduled"
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
