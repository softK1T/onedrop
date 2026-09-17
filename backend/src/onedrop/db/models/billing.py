"""Subscriptions, Telegram Stars payments and AI usage counters."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import (
    PaymentStatus,
    Plan,
    SubscriptionStatus,
    UsageScope,
    values,
)


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(_in_clause("plan", values(Plan)), name="plan_valid"),
        CheckConstraint(_in_clause("status", values(SubscriptionStatus)), name="status_valid"),
        Index("ix_subscriptions_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="telegram_stars", server_default="telegram_stars"
    )


class Payment(UUIDPrimaryKeyMixin, Base):
    """One confirmed Telegram Stars payment. The charge id is unique."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(_in_clause("status", values(PaymentStatus)), name="status_valid"),
        CheckConstraint("amount_stars > 0", name="amount_positive"),
        Index("ix_payments_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    telegram_payment_charge_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    invoice_payload: Mapped[str] = mapped_column(String(128), nullable=False)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    plan: Mapped[str] = mapped_column(String(8), nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default=PaymentStatus.PAID.value, server_default="paid"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UsageCounter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI action counters per scope and period (`bonus`, `daily`, `monthly`)."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        CheckConstraint(_in_clause("scope", values(UsageScope)), name="scope_valid"),
        CheckConstraint("used >= 0", name="used_non_negative"),
        UniqueConstraint("user_id", "scope", "period_key", name="uq_usage_counters_period"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(10), nullable=False)
    period_key: Mapped[str] = mapped_column(String(16), nullable=False)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
