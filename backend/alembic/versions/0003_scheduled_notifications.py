"""Durable notification deliveries and reminder preferences.

Revision ID: 0003_notifications
Revises: 0002_domain
Create Date: 2026-09-17

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_notifications"
down_revision: str | None = "0002_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = (
    "'morning_digest', 'task_reminder', 'event_reminder', "
    "'habit_reminder', 'budget_warning'"
)
STATUSES = "'pending', 'sent', 'failed', 'cancelled'"


def upgrade() -> None:
    op.create_table(
        "scheduled_notification",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dedup_key", sa.String(length=200), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_notification"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_scheduled_notification_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("dedup_key", name="uq_scheduled_notification_dedup_key"),
        sa.CheckConstraint(
            f"kind IN ({KINDS})", name="ck_scheduled_notification_kind_valid"
        ),
        sa.CheckConstraint(
            f"status IN ({STATUSES})", name="ck_scheduled_notification_status_valid"
        ),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_scheduled_notification_attempts_non_negative"
        ),
    )
    op.create_index(
        "ix_scheduled_notification_status_run_at",
        "scheduled_notification",
        ["status", "run_at"],
    )
    op.create_index(
        "ix_scheduled_notification_user_id_run_at",
        "scheduled_notification",
        ["user_id", "run_at"],
    )

    op.add_column(
        "user_settings",
        sa.Column("quiet_hours_start", sa.Integer(), server_default="22", nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("quiet_hours_end", sa.Integer(), server_default="7", nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "task_reminder_lead_minutes", sa.Integer(), server_default="30", nullable=False
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "event_reminder_lead_minutes", sa.Integer(), server_default="60", nullable=False
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "budget_warning_threshold_percent",
            sa.Integer(),
            server_default="80",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_settings_quiet_hours_start_range",
        "user_settings",
        "quiet_hours_start >= 0 AND quiet_hours_start <= 23",
    )
    op.create_check_constraint(
        "ck_user_settings_quiet_hours_end_range",
        "user_settings",
        "quiet_hours_end >= 0 AND quiet_hours_end <= 23",
    )
    op.create_check_constraint(
        "ck_user_settings_task_reminder_lead_minutes_range",
        "user_settings",
        "task_reminder_lead_minutes >= 0 AND task_reminder_lead_minutes <= 1440",
    )
    op.create_check_constraint(
        "ck_user_settings_event_reminder_lead_minutes_range",
        "user_settings",
        "event_reminder_lead_minutes >= 0 AND event_reminder_lead_minutes <= 1440",
    )
    op.create_check_constraint(
        "ck_user_settings_budget_warning_threshold_percent_range",
        "user_settings",
        "budget_warning_threshold_percent >= 1 AND budget_warning_threshold_percent <= 100",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_settings_budget_warning_threshold_percent_range",
        "user_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_user_settings_event_reminder_lead_minutes_range", "user_settings", type_="check"
    )
    op.drop_constraint(
        "ck_user_settings_task_reminder_lead_minutes_range", "user_settings", type_="check"
    )
    op.drop_constraint("ck_user_settings_quiet_hours_end_range", "user_settings", type_="check")
    op.drop_constraint("ck_user_settings_quiet_hours_start_range", "user_settings", type_="check")
    op.drop_column("user_settings", "budget_warning_threshold_percent")
    op.drop_column("user_settings", "event_reminder_lead_minutes")
    op.drop_column("user_settings", "task_reminder_lead_minutes")
    op.drop_column("user_settings", "quiet_hours_end")
    op.drop_column("user_settings", "quiet_hours_start")
    op.drop_index(
        "ix_scheduled_notification_user_id_run_at", table_name="scheduled_notification"
    )
    op.drop_index(
        "ix_scheduled_notification_status_run_at", table_name="scheduled_notification"
    )
    op.drop_table("scheduled_notification")
