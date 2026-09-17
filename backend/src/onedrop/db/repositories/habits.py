"""Habit and habit-log persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.health import Habit, HabitLog

MAX_PAGE_SIZE = 100


class HabitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, values: dict[str, Any]) -> Habit:
        row = Habit(user_id=user_id, **values)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, habit_id: UUID, user_id: UUID) -> Habit | None:
        stmt = select(Habit).where(
            Habit.id == habit_id, Habit.user_id == user_id, Habit.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, user_id: UUID, name: str) -> Habit | None:
        stmt = select(Habit).where(
            Habit.user_id == user_id, Habit.name == name, Habit.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: UUID,
        *,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Habit]:
        conditions: list[ColumnElement[bool]] = [
            Habit.user_id == user_id,
            Habit.deleted_at.is_(None),
        ]
        if active_only:
            conditions.append(Habit.active.is_(True))
        stmt = (
            select(Habit)
            .where(*conditions)
            .order_by(Habit.created_at.asc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def apply_changes(self, habit: Habit, changes: dict[str, Any]) -> Habit:
        for field, value in changes.items():
            setattr(habit, field, value)
        await self._session.flush()
        return habit

    async def soft_delete(self, habit: Habit) -> None:
        habit.deleted_at = datetime.now(tz=UTC)
        habit.active = False
        await self._session.flush()

    async def add_log(
        self,
        *,
        user_id: UUID,
        habit_id: UUID,
        value: int,
        logged_at: datetime,
    ) -> HabitLog:
        row = HabitLog(
            user_id=user_id, habit_id=habit_id, value=value, logged_at=logged_at
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_logs(
        self,
        *,
        habit_id: UUID,
        user_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HabitLog]:
        conditions: list[ColumnElement[bool]] = [
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == user_id,
        ]
        if start is not None:
            conditions.append(HabitLog.logged_at >= start)
        if end is not None:
            conditions.append(HabitLog.logged_at < end)
        stmt = (
            select(HabitLog)
            .where(*conditions)
            .order_by(HabitLog.logged_at.desc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_logged_days(
        self, *, habit_id: UUID, user_id: UUID, start: datetime, end: datetime, timezone: str
    ) -> int:
        """Distinct local days with at least one log entry."""
        local_day = func.date(func.timezone(timezone, HabitLog.logged_at))
        stmt = select(func.count(func.distinct(local_day))).where(
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == user_id,
            HabitLog.logged_at >= start,
            HabitLog.logged_at < end,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)
