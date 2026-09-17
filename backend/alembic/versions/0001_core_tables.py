"""Core tables: users, settings, sessions, telegram updates, inbox, AI usage, audit.

Revision ID: 0001_core
Revises: None
Create Date: 2026-09-17

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("locale", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Europe/Warsaw", nullable=False),
        sa.Column("base_currency", sa.String(length=3), server_default="PLN", nullable=False),
        sa.Column("monthly_budget_minor", sa.BigInteger(), nullable=True),
        sa.Column("reminders_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("task_reminders", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("event_reminders", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("habit_reminders", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("morning_digest", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("budget_warnings", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("morning_digest_hour", sa.Integer(), server_default="8", nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_training", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_settings"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_settings_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user_id"),
        sa.CheckConstraint(
            "base_currency IN ('PLN', 'EUR', 'USD', 'UAH')",
            name="ck_user_settings_base_currency_supported",
        ),
        sa.CheckConstraint(
            "morning_digest_hour >= 0 AND morning_digest_hour <= 23",
            name="ck_user_settings_morning_digest_hour_range",
        ),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("refresh_token_hash", name="uq_sessions_refresh_token_hash"),
    )

    op.create_table(
        "telegram_updates",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="received", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_telegram_updates"),
        sa.UniqueConstraint("update_id", name="uq_telegram_updates_update_id"),
    )

    op.create_table(
        "inbox_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("input_type", sa.String(length=16), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("media_key", sa.String(length=256), nullable=True),
        sa.Column("media_mime", sa.String(length=64), nullable=True),
        sa.Column("telegram_update_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="received", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("ai_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("processing_ms", sa.Integer(), nullable=True),
        sa.Column("ai_cost_micro", sa.BigInteger(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_inbox_items"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_inbox_items_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_inbox_items_idempotency_key"),
        sa.CheckConstraint(
            "input_type IN ('text', 'voice', 'photo')", name="ck_inbox_items_input_type_valid"
        ),
        sa.CheckConstraint(
            "status IN ('received', 'queued', 'processing', 'needs_confirmation', 'completed', 'failed', 'undone')",
            name="ck_inbox_items_status_valid",
        ),
    )
    op.create_index("ix_inbox_items_user_id_created_at", "inbox_items", ["user_id", "created_at"])

    op.create_table(
        "inbox_entity_links",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("inbox_item_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_inbox_entity_links"),
        sa.ForeignKeyConstraint(
            ["inbox_item_id"],
            ["inbox_items.id"],
            name="fk_inbox_entity_links_inbox_item_id_inbox_items",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "inbox_item_id", "entity_type", "entity_id", name="uq_inbox_entity_links_entity"
        ),
        sa.CheckConstraint(
            "entity_type IN ('task', 'event', 'expense', 'meal', 'habit', 'habit_log', 'note')",
            name="ck_inbox_entity_links_entity_type_valid",
        ),
    )

    op.create_table(
        "ai_operations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("operation_type", sa.String(length=24), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_micro", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("charged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ai_operations"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ai_operations_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inbox_item_id"],
            ["inbox_items.id"],
            name="fk_ai_operations_inbox_item_id_inbox_items",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_ai_operations_idempotency_key"),
        sa.CheckConstraint(
            "operation_type IN ('parse', 'transcribe', 'vision')",
            name="ck_ai_operations_operation_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('success', 'failed', 'skipped')", name="ck_ai_operations_status_valid"
        ),
    )
    op.create_index("ix_ai_operations_user_id_created_at", "ai_operations", ["user_id", "created_at"])

    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("inbox_item_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_feedback"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_feedback_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inbox_item_id"],
            ["inbox_items.id"],
            name="fk_user_feedback_inbox_item_id_inbox_items",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("rating IN (-1, 1)", name="ck_user_feedback_rating_valid"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_audit_events_user_id_users", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_audit_events_user_id_created_at", "audit_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_user_id_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("user_feedback")
    op.drop_index("ix_ai_operations_user_id_created_at", table_name="ai_operations")
    op.drop_table("ai_operations")
    op.drop_table("inbox_entity_links")
    op.drop_index("ix_inbox_items_user_id_created_at", table_name="inbox_items")
    op.drop_table("inbox_items")
    op.drop_table("telegram_updates")
    op.drop_table("sessions")
    op.drop_table("user_settings")
    op.drop_table("users")
