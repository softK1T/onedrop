"""Expense persistence and SQL aggregates. The LLM never computes these."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.finance import Expense

MAX_PAGE_SIZE = 100


class ExpenseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, values: dict[str, Any]) -> Expense:
        row = Expense(user_id=user_id, **values)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, expense_id: UUID, user_id: UUID) -> Expense | None:
        stmt = select(Expense).where(
            Expense.id == expense_id,
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_range(
        self,
        user_id: UUID,
        *,
        start: datetime,
        end: datetime,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Expense]:
        stmt = (
            select(Expense)
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.occurred_at >= start,
                Expense.occurred_at < end,
            )
            .order_by(Expense.occurred_at.desc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def total_minor(self, user_id: UUID, *, start: datetime, end: datetime) -> int:
        """Sum in the user's base currency, falling back to the original amount."""
        amount = func.coalesce(Expense.base_amount_minor, Expense.amount_minor)
        stmt = select(func.coalesce(func.sum(amount), 0)).where(
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
            Expense.occurred_at >= start,
            Expense.occurred_at < end,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def totals_by_category(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> list[tuple[str, int]]:
        amount = func.coalesce(Expense.base_amount_minor, Expense.amount_minor)
        stmt = (
            select(Expense.category, func.coalesce(func.sum(amount), 0).label("total"))
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.occurred_at >= start,
                Expense.occurred_at < end,
            )
            .group_by(Expense.category)
            .order_by(func.sum(amount).desc())
        )
        result = await self._session.execute(stmt)
        return [(str(row[0]), int(row[1] or 0)) for row in result.all()]

    async def apply_changes(self, expense: Expense, changes: dict[str, Any]) -> Expense:
        for field, value in changes.items():
            setattr(expense, field, value)
        await self._session.flush()
        return expense

    async def soft_delete(self, expense: Expense) -> None:
        expense.deleted_at = datetime.now(tz=UTC)
        await self._session.flush()
