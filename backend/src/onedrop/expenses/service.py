"""Expense use cases: conversion, monthly views and budget warnings."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_month_bounds, local_now
from onedrop.db.models.finance import Expense
from onedrop.db.models.user import UserSettings
from onedrop.db.repositories.expenses import ExpenseRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import NotFoundError
from onedrop.expenses.budget import delta_percent, evaluate_budget
from onedrop.expenses.schemas import (
    BudgetSummary,
    CategoryTotal,
    ExpenseCreate,
    ExpenseUpdate,
    MonthlySummary,
)
from onedrop.money import convert_minor


class ExpenseService:
    """Application service for expenses."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._expenses = ExpenseRepository(session)
        self._users = UserRepository(session)

    async def _settings(self, user_id: UUID) -> UserSettings:
        row = await self._users.get_settings(user_id)
        if row is None:
            row = await self._users.update_settings(user_id, {})
            await self._session.commit()
        return row

    async def create(self, user_id: UUID, payload: ExpenseCreate) -> Expense:
        """Store the original amount and, when possible, the converted one."""
        settings_row = await self._settings(user_id)
        base_minor, rate = convert_minor(
            payload.amount_minor, payload.currency, settings_row.base_currency
        )
        values = payload.model_dump(exclude_unset=False)
        values["occurred_at"] = payload.occurred_at or datetime.now(tz=UTC)
        values["base_amount_minor"] = base_minor
        values["base_currency"] = settings_row.base_currency if base_minor is not None else None
        values["fx_rate"] = rate
        expense = await self._expenses.create(user_id=user_id, values=values)
        await self._session.commit()
        return expense

    async def get(self, user_id: UUID, expense_id: UUID) -> Expense:
        expense = await self._expenses.get(expense_id, user_id)
        if expense is None:
            raise NotFoundError("Expense not found")
        return expense

    async def list_month(
        self,
        user_id: UUID,
        *,
        year: int | None,
        month: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Expense], bool, int, int]:
        settings_row = await self._settings(user_id)
        reference = local_now(settings_row.timezone)
        target_year = year or reference.year
        target_month = month or reference.month
        start, end = local_month_bounds(target_year, target_month, settings_row.timezone)
        rows = await self._expenses.list_range(
            user_id, start=start, end=end, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit, target_year, target_month

    async def patch(
        self, user_id: UUID, expense_id: UUID, payload: ExpenseUpdate
    ) -> Expense:
        expense = await self.get(user_id, expense_id)
        settings_row = await self._settings(user_id)
        changes = payload.model_dump(exclude_unset=True)
        if "amount_minor" in changes or "currency" in changes:
            amount = changes.get("amount_minor", expense.amount_minor)
            currency = changes.get("currency", expense.currency)
            base_minor, rate = convert_minor(amount, currency, settings_row.base_currency)
            changes["base_amount_minor"] = base_minor
            changes["base_currency"] = (
                settings_row.base_currency if base_minor is not None else None
            )
            changes["fx_rate"] = rate
        expense = await self._expenses.apply_changes(expense, changes)
        await self._session.commit()
        return expense

    async def delete(self, user_id: UUID, expense_id: UUID) -> None:
        expense = await self.get(user_id, expense_id)
        await self._expenses.soft_delete(expense)
        await self._session.commit()

    async def monthly_summary(
        self, user_id: UUID, *, year: int | None = None, month: int | None = None
    ) -> MonthlySummary:
        """Category totals, month-over-month delta and budget state."""
        settings_row = await self._settings(user_id)
        reference = local_now(settings_row.timezone)
        target_year = year or reference.year
        target_month = month or reference.month
        start, end = local_month_bounds(target_year, target_month, settings_row.timezone)
        previous_year, previous_month = (
            (target_year - 1, 12) if target_month == 1 else (target_year, target_month - 1)
        )
        previous_start, previous_end = local_month_bounds(
            previous_year, previous_month, settings_row.timezone
        )

        total = await self._expenses.total_minor(user_id, start=start, end=end)
        previous_total = await self._expenses.total_minor(
            user_id, start=previous_start, end=previous_end
        )
        rows = await self._expenses.totals_by_category(user_id, start=start, end=end)
        categories = [
            CategoryTotal(
                category=category,
                total_minor=amount,
                share_percent=int(round(amount * 100 / total)) if total > 0 else 0,
            )
            for category, amount in rows
        ]
        status = evaluate_budget(
            currency=settings_row.base_currency,
            spent_minor=total,
            budget_minor=settings_row.monthly_budget_minor,
        )
        return MonthlySummary(
            year=target_year,
            month=target_month,
            base_currency=settings_row.base_currency,
            total_minor=total,
            previous_total_minor=previous_total,
            delta_percent=delta_percent(total, previous_total),
            categories=categories,
            budget=BudgetSummary(
                currency=status.currency,
                spent_minor=status.spent_minor,
                budget_minor=status.budget_minor,
                remaining_minor=status.remaining_minor,
                usage_percent=status.usage_percent,
                warning=status.warning,
                exceeded=status.exceeded,
            ),
        )
