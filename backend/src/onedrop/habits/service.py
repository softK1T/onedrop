"""Habit use cases: create, disable, log, history, completion rate."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_day_bounds, local_now
from onedrop.db.models.health import Habit, HabitLog
from onedrop.db.repositories.habits import HabitRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import ConflictError, NotFoundError
from onedrop.habits.completion import build_progress
from onedrop.habits.schemas import HabitCreate, HabitProgressResponse, HabitUpdate

DEFAULT_PROGRESS_DAYS = 30


class HabitService:
    """Application service for habits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._habits = HabitRepository(session)
        self._users = UserRepository(session)

    async def _timezone(self, user_id: UUID) -> str:
        row = await self._users.get_settings(user_id)
        return row.timezone if row is not None else "UTC"

    async def create(self, user_id: UUID, payload: HabitCreate) -> Habit:
        existing = await self._habits.get_by_name(user_id, payload.name)
        if existing is not None:
            raise ConflictError("A habit with this name already exists")
        values = payload.model_dump(exclude={"schedule_days"})
        values["schedule"] = {"days": payload.schedule_days} if payload.schedule_days else None
        habit = await self._habits.create(user_id=user_id, values=values)
        await self._session.commit()
        return habit

    async def get(self, user_id: UUID, habit_id: UUID) -> Habit:
        habit = await self._habits.get(habit_id, user_id)
        if habit is None:
            raise NotFoundError("Habit not found")
        return habit

    async def list(
        self, user_id: UUID, *, active_only: bool, limit: int, offset: int
    ) -> tuple[list[Habit], bool]:
        rows = await self._habits.list(
            user_id, active_only=active_only, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit

    async def patch(self, user_id: UUID, habit_id: UUID, payload: HabitUpdate) -> Habit:
        habit = await self.get(user_id, habit_id)
        changes = payload.model_dump(exclude_unset=True)
        if "schedule_days" in changes:
            days = changes.pop("schedule_days")
            changes["schedule"] = {"days": days} if days else None
        habit = await self._habits.apply_changes(habit, changes)
        await self._session.commit()
        return habit

    async def deactivate(self, user_id: UUID, habit_id: UUID) -> Habit:
        """Disable a habit without losing its history."""
        habit = await self.get(user_id, habit_id)
        habit = await self._habits.apply_changes(habit, {"active": False})
        await self._session.commit()
        return habit

    async def delete(self, user_id: UUID, habit_id: UUID) -> None:
        habit = await self.get(user_id, habit_id)
        await self._habits.soft_delete(habit)
        await self._session.commit()

    async def log(
        self,
        user_id: UUID,
        habit_id: UUID,
        *,
        value: int,
        logged_at: datetime | None,
    ) -> HabitLog:
        habit = await self.get(user_id, habit_id)
        entry = await self._habits.add_log(
            user_id=user_id,
            habit_id=habit.id,
            value=value,
            logged_at=logged_at or datetime.now(tz=UTC),
        )
        await self._session.commit()
        return entry

    async def history(
        self, user_id: UUID, habit_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[HabitLog], bool]:
        habit = await self.get(user_id, habit_id)
        rows = await self._habits.list_logs(
            habit_id=habit.id, user_id=user_id, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit

    async def progress(
        self, user_id: UUID, habit_id: UUID, *, days: int = DEFAULT_PROGRESS_DAYS
    ) -> HabitProgressResponse:
        """Completion rate over the last N local days."""
        habit = await self.get(user_id, habit_id)
        timezone = await self._timezone(user_id)
        today: date = local_now(timezone).date()
        period_start = today - timedelta(days=max(1, days) - 1)
        start, _ = local_day_bounds(period_start, timezone)
        _, end = local_day_bounds(today, timezone)
        completed = await self._habits.count_logged_days(
            habit_id=habit.id, user_id=user_id, start=start, end=end, timezone=timezone
        )
        progress = build_progress(
            schedule=habit.schedule,
            start=period_start,
            end=today,
            completed_days=completed,
        )
        return HabitProgressResponse(
            habit_id=habit.id,
            name=habit.name,
            period_start=period_start,
            period_end=today,
            scheduled_days=list(progress.days),
            expected=progress.expected,
            completed=progress.completed,
            missed=progress.missed,
            percent=progress.percent,
        )
