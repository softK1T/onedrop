"""Planner domain models: tasks and calendar events."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import EventStatus, Priority, TaskStatus, values


class Task(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('" + "', '".join(values(Priority)) + "')", name="priority_valid"
        ),
        CheckConstraint(
            "status IN ('" + "', '".join(values(TaskStatus)) + "')", name="status_valid"
        ),
        Index("ix_tasks_user_id_due_at", "user_id", "due_at"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default=Priority.NORMAL.value, server_default=Priority.NORMAL.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TaskStatus.OPEN.value, server_default=TaskStatus.OPEN.value)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True)


class Event(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("status IN ('" + "', '".join(values(EventStatus)) + "')", name="status_valid"),
        Index("ix_events_user_id_starts_at", "user_id", "starts_at"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=EventStatus.PLANNED.value, server_default=EventStatus.PLANNED.value)
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True)
