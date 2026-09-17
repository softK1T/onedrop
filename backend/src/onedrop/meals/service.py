"""Meal use cases: manual entry, correction and daily totals."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_day_bounds, local_now
from onedrop.db.models.health import Meal
from onedrop.db.repositories.meals import MealRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import NotFoundError
from onedrop.meals.schemas import (
    NUTRITION_FIELDS,
    DailyNutrition,
    MealCreate,
    MealUpdate,
)


class MealService:
    """Application service for meals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._meals = MealRepository(session)
        self._users = UserRepository(session)

    async def _timezone(self, user_id: UUID) -> str:
        row = await self._users.get_settings(user_id)
        return row.timezone if row is not None else "UTC"

    async def create(self, user_id: UUID, payload: MealCreate) -> Meal:
        values = payload.model_dump(exclude_unset=False)
        values["eaten_at"] = payload.eaten_at or datetime.now(tz=UTC)
        meal = await self._meals.create(user_id=user_id, values=values)
        await self._session.commit()
        return meal

    async def get(self, user_id: UUID, meal_id: UUID) -> Meal:
        meal = await self._meals.get(meal_id, user_id)
        if meal is None:
            raise NotFoundError("Meal not found")
        return meal

    async def list_day(
        self,
        user_id: UUID,
        *,
        day: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Meal], bool, date]:
        timezone = await self._timezone(user_id)
        target = day or local_now(timezone).date()
        start, end = local_day_bounds(target, timezone)
        rows = await self._meals.list_range(
            user_id, start=start, end=end, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit, target

    async def patch(self, user_id: UUID, meal_id: UUID, payload: MealUpdate) -> Meal:
        """Manual correction clears the `estimated` flag."""
        meal = await self.get(user_id, meal_id)
        changes = payload.model_dump(exclude_unset=True)
        if any(field in changes for field in NUTRITION_FIELDS):
            changes["estimated"] = False
        meal = await self._meals.apply_changes(meal, changes)
        await self._session.commit()
        return meal

    async def delete(self, user_id: UUID, meal_id: UUID) -> None:
        meal = await self.get(user_id, meal_id)
        await self._meals.soft_delete(meal)
        await self._session.commit()

    async def daily_totals(self, user_id: UUID, *, day: date | None = None) -> DailyNutrition:
        timezone = await self._timezone(user_id)
        target = day or local_now(timezone).date()
        start, end = local_day_bounds(target, timezone)
        count, calories, protein, fat, carbs, estimated = await self._meals.totals(
            user_id, start=start, end=end
        )
        return DailyNutrition(
            day=target,
            meals_count=count,
            calories=calories,
            protein=protein,
            fat=fat,
            carbohydrates=carbs,
            contains_estimates=estimated,
        )
