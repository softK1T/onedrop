"""Domain tables: tasks, events, expenses, meals, habits, notes, reminders, billing.

Revision ID: 0002_domain
Revises: 0001_core
Create Date: 2026-09-17

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_domain"
down_revision: str | None = "0001_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENCIES = "'PLN', 'EUR', 'USD', 'UAH'"
CATEGORIES = (
    "'food', 'transport', 'housing', 'health', 'entertainment', "
    "'shopping', 'bills', 'education', 'travel', 'other'"
)


def _user_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["user_id"], ["users.id"], name=f"fk_{table}_user_id_users", ondelete="CASCADE"
    )


def _inbox_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["source_inbox_item_id"],
        ["inbox_items.id"],
        name=f"fk_{table}_source_inbox_item_id_inbox_items",
        ondelete="SET NULL",
    )


def _timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.String(length=8), server_default="normal", nullable=False),
        sa.Column("status", sa.String(length=12), server_default="open", nullable=False),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
        _user_fk("tasks"),
        _inbox_fk("tasks"),
        sa.CheckConstraint("status IN ('open', 'done', 'cancelled')", name="ck_tasks_status_valid"),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high')", name="ck_tasks_priority_valid"
        ),
    )
    op.create_index("ix_tasks_user_id_due_at", "tasks", ["user_id", "due_at"])
    op.create_index("ix_tasks_user_id_status", "tasks", ["user_id", "status"])

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="planned", nullable=False),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
        _user_fk("events"),
        _inbox_fk("events"),
        sa.CheckConstraint(
            "status IN ('planned', 'done', 'cancelled')", name="ck_events_status_valid"
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at >= starts_at", name="ck_events_time_range_valid"
        ),
    )
    op.create_index("ix_events_user_id_starts_at", "events", ["user_id", "starts_at"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("base_amount_minor", sa.BigInteger(), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=True),
        sa.Column("fx_rate", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("category", sa.String(length=20), server_default="other", nullable=False),
        sa.Column("merchant", sa.String(length=120), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
        _user_fk("expenses"),
        _inbox_fk("expenses"),
        sa.CheckConstraint("amount_minor >= 0", name="ck_expenses_amount_non_negative"),
        sa.CheckConstraint(f"currency IN ({CURRENCIES})", name="ck_expenses_currency_supported"),
        sa.CheckConstraint(f"category IN ({CATEGORIES})", name="ck_expenses_category_valid"),
    )
    op.create_index("ix_expenses_user_id_occurred_at", "expenses", ["user_id", "occurred_at"])
    op.create_index("ix_expenses_user_id_category", "expenses", ["user_id", "category"])

    op.create_table(
        "meals",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("meal_type", sa.String(length=12), server_default="snack", nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("protein", sa.Integer(), nullable=True),
        sa.Column("fat", sa.Integer(), nullable=True),
        sa.Column("carbohydrates", sa.Integer(), nullable=True),
        sa.Column("estimated", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_meals"),
        _user_fk("meals"),
        _inbox_fk("meals"),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_meals_meal_type_valid",
        ),
        sa.CheckConstraint(
            "calories IS NULL OR calories >= 0", name="ck_meals_calories_non_negative"
        ),
    )
    op.create_index("ix_meals_user_id_eaten_at", "meals", ["user_id", "eaten_at"])

    op.create_table(
        "habits",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "measurement_type", sa.String(length=8), server_default="boolean", nullable=False
        ),
        sa.Column("target_value", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("schedule", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("reminder_hour", sa.Integer(), nullable=True),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_habits"),
        _user_fk("habits"),
        _inbox_fk("habits"),
        sa.UniqueConstraint("user_id", "name", name="uq_habits_user_id_name"),
        sa.CheckConstraint(
            "measurement_type IN ('boolean', 'numeric')",
            name="ck_habits_measurement_type_valid",
        ),
    )

    op.create_table(
        "habit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("habit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("value", sa.Integer(), server_default="1", nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_habit_logs"),
        _user_fk("habit_logs"),
        _inbox_fk("habit_logs"),
        sa.ForeignKeyConstraint(
            ["habit_id"], ["habits.id"], name="fk_habit_logs_habit_id_habits", ondelete="CASCADE"
        ),
        sa.CheckConstraint("value >= 0", name="ck_habit_logs_value_non_negative"),
    )
    op.create_index("ix_habit_logs_habit_id_logged_at", "habit_logs", ["habit_id", "logged_at"])

    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=32)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("source_inbox_item_id", sa.Uuid(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_notes"),
        _user_fk("notes"),
        _inbox_fk("notes"),
    )
    op.create_index("ix_notes_user_id_created_at", "notes", ["user_id", "created_at"])
    op.create_index("ix_notes_user_id_pinned", "notes", ["user_id", "pinned"])

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
        _user_fk("reminders"),
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
    op.create_index("ix_reminders_status_scheduled_at", "reminders", ["status", "scheduled_at"])
    op.create_index("ix_reminders_user_id_scheduled_at", "reminders", ["user_id", "scheduled_at"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source", sa.String(length=20), server_default="telegram_stars", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        _user_fk("subscriptions"),
        sa.CheckConstraint("plan IN ('free', 'pro')", name="ck_subscriptions_plan_valid"),
        sa.CheckConstraint(
            "status IN ('active', 'expired', 'cancelled')", name="ck_subscriptions_status_valid"
        ),
    )
    op.create_index("ix_subscriptions_user_id_status", "subscriptions", ["user_id", "status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("telegram_payment_charge_id", sa.String(length=128), nullable=False),
        sa.Column("invoice_payload", sa.String(length=128), nullable=False),
        sa.Column("amount_stars", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=8), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="paid", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        _user_fk("payments"),
        sa.UniqueConstraint(
            "telegram_payment_charge_id", name="uq_payments_telegram_payment_charge_id"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'paid', 'refunded')", name="ck_payments_status_valid"
        ),
        sa.CheckConstraint("amount_stars > 0", name="ck_payments_amount_positive"),
    )
    op.create_index("ix_payments_user_id_created_at", "payments", ["user_id", "created_at"])

    op.create_table(
        "usage_counters",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=10), nullable=False),
        sa.Column("period_key", sa.String(length=16), nullable=False),
        sa.Column("used", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usage_counters"),
        _user_fk("usage_counters"),
        sa.UniqueConstraint("user_id", "scope", "period_key", name="uq_usage_counters_period"),
        sa.CheckConstraint(
            "scope IN ('bonus', 'daily', 'monthly')", name="ck_usage_counters_scope_valid"
        ),
        sa.CheckConstraint("used >= 0", name="ck_usage_counters_used_non_negative"),
    )


def downgrade() -> None:
    op.drop_table("usage_counters")
    op.drop_index("ix_payments_user_id_created_at", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_reminders_user_id_scheduled_at", table_name="reminders")
    op.drop_index("ix_reminders_status_scheduled_at", table_name="reminders")
    op.drop_table("reminders")
    op.drop_index("ix_notes_user_id_pinned", table_name="notes")
    op.drop_index("ix_notes_user_id_created_at", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_habit_logs_habit_id_logged_at", table_name="habit_logs")
    op.drop_table("habit_logs")
    op.drop_table("habits")
    op.drop_index("ix_meals_user_id_eaten_at", table_name="meals")
    op.drop_table("meals")
    op.drop_index("ix_expenses_user_id_category", table_name="expenses")
    op.drop_index("ix_expenses_user_id_occurred_at", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_events_user_id_starts_at", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_tasks_user_id_status", table_name="tasks")
    op.drop_index("ix_tasks_user_id_due_at", table_name="tasks")
    op.drop_table("tasks")
