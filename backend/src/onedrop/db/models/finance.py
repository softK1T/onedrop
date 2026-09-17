"""Expenses. Amounts are integer minor units; the applied rate is stored."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import Currency, ExpenseCategory, values


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="amount_non_negative"),
        CheckConstraint(_in_clause("currency", values(Currency)), name="currency_supported"),
        CheckConstraint(_in_clause("category", values(ExpenseCategory)), name="category_valid"),
        Index("ix_expenses_user_id_occurred_at", "user_id", "occurred_at"),
        Index("ix_expenses_user_id_category", "user_id", "category"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    base_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ExpenseCategory.OTHER.value, server_default="other"
    )
    merchant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )
