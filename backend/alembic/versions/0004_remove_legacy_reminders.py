"""Remove the obsolete reminders queue and entity-level reminder timestamps.

Revision ID: 0004_remove_legacy_reminders
Revises: 0003_notifications
Create Date: 2026-09-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_remove_legacy_reminders"
down_revision: str | None = "0003_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_reminders_user_id_scheduled_at", table_name="reminders")
    op.drop_index("ix_reminders_status_scheduled_at", table_name="reminders")
    op.drop_table("reminders")
    op.drop_column("tasks", "reminder_at")
    op.drop_column("events", "reminder_at")


def downgrade() -> None:
    op.add_column("events", sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=True),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="scheduled", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reminders"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_reminders_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_reminders_idempotency_key"),
        sa.CheckConstraint(
            "kind IN ('task', 'event', 'habit', 'morning_digest', 'budget_warning')",
            name="ck_reminders_kind_valid",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'sent', 'cancelled', 'failed')",
            name="ck_reminders_status_valid",
        ),
    )
    op.create_index(
        "ix_reminders_status_scheduled_at", "reminders", ["status", "scheduled_at"]
    )
    op.create_index(
        "ix_reminders_user_id_scheduled_at", "reminders", ["user_id", "scheduled_at"]
    )
