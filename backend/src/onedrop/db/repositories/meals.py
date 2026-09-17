"""Meal persistence and nutrition aggregates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.health import Meal

MAX_PAGE_SIZE = 100


class MealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, values: dict[str, Any]) -> Meal:
        row = Meal(user_id=user_id, **values)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, meal_id: UUID, user_id: UUID) -> Meal | None:
        stmt = select(Meal).where(
            Meal.id == meal_id, Meal.user_id == user_id, Meal.deleted_at.is_(None)
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
    ) -> list[Meal]:
        stmt = (
            select(Meal)
            .where(
                Meal.user_id == user_id,
                Meal.deleted_at.is_(None),
                Meal.eaten_at >= start,
                Meal.eaten_at < end,
            )
            .order_by(Meal.eaten_at.asc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def totals(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> tuple[int, int, int, int, int, bool]:
        """Return (count, calories, protein, fat, carbs, contains_estimates)."""
        stmt = select(
            func.count(Meal.id),
            func.coalesce(func.sum(Meal.calories), 0),
            func.coalesce(func.sum(Meal.protein), 0),
            func.coalesce(func.sum(Meal.fat), 0),
            func.coalesce(func.sum(Meal.carbohydrates), 0),
            func.coalesce(func.bool_or(Meal.estimated), False),
        ).where(
            Meal.user_id == user_id,
            Meal.deleted_at.is_(None),
            Meal.eaten_at >= start,
            Meal.eaten_at < end,
        )
        row = (await self._session.execute(stmt)).one()
        return (
            int(row[0] or 0),
            int(row[1] or 0),
            int(row[2] or 0),
            int(row[3] or 0),
            int(row[4] or 0),
            bool(row[5]),
        )

    async def apply_changes(self, meal: Meal, changes: dict[str, Any]) -> Meal:
        for field, value in changes.items():
            setattr(meal, field, value)
        await self._session.flush()
        return meal

    async def soft_delete(self, meal: Meal) -> None:
        meal.deleted_at = datetime.now(tz=UTC)
        await self._session.flush()
