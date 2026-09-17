"""Tasks and events."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import EventStatus, Priority, TaskStatus, values


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class Task(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(_in_clause("status", values(TaskStatus)), name="status_valid"),
        CheckConstraint(_in_clause("priority", values(Priority)), name="priority_valid"),
        Index("ix_tasks_user_id_due_at", "user_id", "due_at"),
        Index("ix_tasks_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(
        String(8), nullable=False, default=Priority.NORMAL.value, server_default="normal"
    )
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default=TaskStatus.OPEN.value, server_default="open"
    )
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )


class Event(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(_in_clause("status", values(EventStatus)), name="status_valid"),
        CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="time_range_valid"),
        Index("ix_events_user_id_starts_at", "user_id", "starts_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default=EventStatus.PLANNED.value, server_default="planned"
    )
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )
