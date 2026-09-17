"""Read-only SQL aggregates for analytics."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.enums import InboxStatus, TaskStatus
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog, Meal
from onedrop.db.models.inbox import AiOperation, InboxItem
from onedrop.db.models.planner import Task


class AnalyticsRepository:
    """Aggregate queries. All of them are scoped by `user_id`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _local_day(self, column: Any, timezone: str) -> Any:
        return func.date(func.timezone(timezone, column))

    async def task_counters(
        self, user_id: UUID, *, day_start: datetime, day_end: datetime, now: datetime
    ) -> tuple[int, int, int, int]:
        """Return (today, overdue, completed_today, open_total)."""
        base = [Task.user_id == user_id, Task.deleted_at.is_(None)]
        today_stmt = select(func.count(Task.id)).where(
            *base,
            Task.status == TaskStatus.OPEN.value,
            Task.due_at >= day_start,
            Task.due_at < day_end,
        )
        overdue_stmt = select(func.count(Task.id)).where(
            *base, Task.status == TaskStatus.OPEN.value, Task.due_at < now
        )
        completed_stmt = select(func.count(Task.id)).where(
            *base,
            Task.status == TaskStatus.DONE.value,
            Task.completed_at >= day_start,
            Task.completed_at < day_end,
        )
        open_stmt = select(func.count(Task.id)).where(
            *base, Task.status == TaskStatus.OPEN.value
        )
        today = int((await self._session.execute(today_stmt)).scalar_one() or 0)
        overdue = int((await self._session.execute(overdue_stmt)).scalar_one() or 0)
        completed = int((await self._session.execute(completed_stmt)).scalar_one() or 0)
        open_total = int((await self._session.execute(open_stmt)).scalar_one() or 0)
        return today, overdue, completed, open_total

    async def completed_tasks_in_range(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> tuple[int, int]:
        """Return (completed, created) inside the range."""
        completed_stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.deleted_at.is_(None),
            Task.completed_at >= start,
            Task.completed_at < end,
        )
        created_stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.deleted_at.is_(None),
            Task.created_at >= start,
            Task.created_at < end,
        )
        completed = int((await self._session.execute(completed_stmt)).scalar_one() or 0)
        created = int((await self._session.execute(created_stmt)).scalar_one() or 0)
        return completed, created

    async def expenses_total(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> int:
        amount = func.coalesce(Expense.base_amount_minor, Expense.amount_minor)
        stmt = select(func.coalesce(func.sum(amount), 0)).where(
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
            Expense.occurred_at >= start,
            Expense.occurred_at < end,
        )
        return int((await self._session.execute(stmt)).scalar_one() or 0)

    async def expenses_by_day(
        self, user_id: UUID, *, start: datetime, end: datetime, timezone: str
    ) -> dict[date, int]:
        amount = func.coalesce(Expense.base_amount_minor, Expense.amount_minor)
        day = self._local_day(Expense.occurred_at, timezone)
        stmt = (
            select(day.label("day"), func.coalesce(func.sum(amount), 0))
            .where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.occurred_at >= start,
                Expense.occurred_at < end,
            )
            .group_by(day)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: int(row[1] or 0) for row in rows}

    async def nutrition_by_day(
        self, user_id: UUID, *, start: datetime, end: datetime, timezone: str
    ) -> tuple[list[tuple[date, int, int, int, int]], bool]:
        day = self._local_day(Meal.eaten_at, timezone)
        stmt = (
            select(
                day.label("day"),
                func.coalesce(func.sum(Meal.calories), 0),
                func.coalesce(func.sum(Meal.protein), 0),
                func.coalesce(func.sum(Meal.fat), 0),
                func.coalesce(func.sum(Meal.carbohydrates), 0),
                func.coalesce(func.bool_or(Meal.estimated), False),
            )
            .where(
                Meal.user_id == user_id,
                Meal.deleted_at.is_(None),
                Meal.eaten_at >= start,
                Meal.eaten_at < end,
            )
            .group_by(day)
            .order_by(day)
        )
        rows = (await self._session.execute(stmt)).all()
        series = [
            (row[0], int(row[1] or 0), int(row[2] or 0), int(row[3] or 0), int(row[4] or 0))
            for row in rows
        ]
        estimated = any(bool(row[5]) for row in rows)
        return series, estimated

    async def habit_completion(
        self, user_id: UUID, *, start: datetime, end: datetime, timezone: str
    ) -> list[tuple[UUID, str, dict[str, Any] | None, int]]:
        """Per habit: id, name, schedule and distinct local days with a log."""
        day = self._local_day(HabitLog.logged_at, timezone)
        stmt = (
            select(
                Habit.id,
                Habit.name,
                Habit.schedule,
                func.count(func.distinct(day)),
            )
            .join(
                HabitLog,
                (HabitLog.habit_id == Habit.id)
                & (HabitLog.logged_at >= start)
                & (HabitLog.logged_at < end),
                isouter=True,
            )
            .where(
                Habit.user_id == user_id,
                Habit.deleted_at.is_(None),
                Habit.active.is_(True),
            )
            .group_by(Habit.id, Habit.name, Habit.schedule)
            .order_by(Habit.name)
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], str(row[1]), row[2], int(row[3] or 0)) for row in rows]

    async def captures_by_day(
        self, user_id: UUID, *, start: datetime, end: datetime, timezone: str
    ) -> dict[date, int]:
        day = self._local_day(InboxItem.created_at, timezone)
        stmt = (
            select(day.label("day"), func.count(InboxItem.id))
            .where(
                InboxItem.user_id == user_id,
                InboxItem.deleted_at.is_(None),
                InboxItem.created_at >= start,
                InboxItem.created_at < end,
            )
            .group_by(day)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: int(row[1] or 0) for row in rows}

    async def capture_status_counts(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> tuple[int, int, int]:
        """Return (total, failed, undone) captures in the range."""
        base = [
            InboxItem.user_id == user_id,
            InboxItem.deleted_at.is_(None),
            InboxItem.created_at >= start,
            InboxItem.created_at < end,
        ]
        total_stmt = select(func.count(InboxItem.id)).where(*base)
        failed_stmt = select(func.count(InboxItem.id)).where(
            *base, InboxItem.status == InboxStatus.FAILED.value
        )
        undone_stmt = select(func.count(InboxItem.id)).where(
            *base, InboxItem.status == InboxStatus.UNDONE.value
        )
        total = int((await self._session.execute(total_stmt)).scalar_one() or 0)
        failed = int((await self._session.execute(failed_stmt)).scalar_one() or 0)
        undone = int((await self._session.execute(undone_stmt)).scalar_one() or 0)
        return total, failed, undone

    async def ai_operations_summary(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> tuple[int, int]:
        """Return (operations, cost_micro) in the range."""
        stmt = select(
            func.count(AiOperation.id), func.coalesce(func.sum(AiOperation.cost_micro), 0)
        ).where(
            AiOperation.user_id == user_id,
            AiOperation.created_at >= start,
            AiOperation.created_at < end,
        )
        row = (await self._session.execute(stmt)).one()
        return int(row[0] or 0), int(row[1] or 0)
