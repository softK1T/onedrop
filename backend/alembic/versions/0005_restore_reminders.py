"""Restore canonical reminder schedules and entity reminder timestamps.

Revision ID: 0005_restore_reminders
Revises: 0004_remove_legacy_reminders
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_restore_reminders"
down_revision: str | None = "0004_remove_legacy_reminders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = "'task_reminder', 'event_reminder', 'habit_reminder', 'morning_digest', 'budget_warning'"
STATUSES = "'scheduled', 'sent', 'cancelled', 'failed'"
ENTITY_TYPES = "'task', 'event', 'habit'"


def upgrade() -> None:
    op.add_column("tasks", sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=True),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="scheduled", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_reminders"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_reminders_user_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("idempotency_key", name="uq_reminders_idempotency_key"),
        sa.CheckConstraint(f"kind IN ({KINDS})", name="ck_reminders_kind_valid"),
        sa.CheckConstraint(f"status IN ({STATUSES})", name="ck_reminders_status_valid"),
        sa.CheckConstraint(f"entity_type IS NULL OR entity_type IN ({ENTITY_TYPES})", name="ck_reminders_entity_type_valid"),
        sa.CheckConstraint("(entity_type IS NULL) = (entity_id IS NULL)", name="ck_reminders_entity_reference_complete"),
    )
    op.create_index("ix_reminders_status_scheduled_at", "reminders", ["status", "scheduled_at"])
    op.create_index("ix_reminders_user_id_scheduled_at", "reminders", ["user_id", "scheduled_at"])
    op.create_index(
        "uq_reminders_active_entity",
        "reminders",
        ["user_id", "kind", "entity_id"],
        unique=True,
        postgresql_where=sa.text("status = 'scheduled' AND entity_id IS NOT NULL"),
    )
    op.add_column("scheduled_notification", sa.Column("reminder_id", sa.Uuid(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_scheduled_notification_reminder_id_reminders",
        "scheduled_notification",
        "reminders",
        ["reminder_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_scheduled_notification_reminder_id", "scheduled_notification", ["reminder_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_scheduled_notification_reminder_id", "scheduled_notification", type_="unique")
    op.drop_constraint("fk_scheduled_notification_reminder_id_reminders", "scheduled_notification", type_="foreignkey")
    op.drop_column("scheduled_notification", "reminder_id")
    op.drop_index("uq_reminders_active_entity", table_name="reminders")
    op.drop_index("ix_reminders_user_id_scheduled_at", table_name="reminders")
    op.drop_index("ix_reminders_status_scheduled_at", table_name="reminders")
    op.drop_table("reminders")
    op.drop_column("events", "reminder_at")
    op.drop_column("tasks", "reminder_at")
