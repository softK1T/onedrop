"""Meal endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.db.repositories.meals import MAX_PAGE_SIZE
from onedrop.meals.schemas import (
    DailyNutrition,
    MealCreate,
    MealPage,
    MealResponse,
    MealUpdate,
)
from onedrop.meals.service import MealService

router = APIRouter(prefix="/meals", tags=["meals"])


@router.get("", response_model=MealPage)
async def list_meals(
    session: DbSession,
    user: CurrentUser,
    day: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MealPage:
    """Meals of one local day, in the order they were eaten."""
    items, has_more, resolved_day = await MealService(session).list_day(
        user.id, day=day, limit=limit, offset=offset
    )
    return MealPage(
        items=[MealResponse.model_validate(item) for item in items],
        day=resolved_day,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/daily", response_model=DailyNutrition)
async def daily_nutrition(
    session: DbSession, user: CurrentUser, day: Annotated[date | None, Query()] = None
) -> DailyNutrition:
    """Daily calories and macronutrients. Values may be approximate."""
    return await MealService(session).daily_totals(user.id, day=day)


@router.post("", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
async def create_meal(
    payload: MealCreate, session: DbSession, user: CurrentUser
) -> MealResponse:
    meal = await MealService(session).create(user.id, payload)
    return MealResponse.model_validate(meal)


@router.get("/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> MealResponse:
    meal = await MealService(session).get(user.id, meal_id)
    return MealResponse.model_validate(meal)


@router.patch("/{meal_id}", response_model=MealResponse)
async def patch_meal(
    meal_id: uuid.UUID, payload: MealUpdate, session: DbSession, user: CurrentUser
) -> MealResponse:
    """Correct a meal by hand. Corrected nutrition is no longer estimated."""
    meal = await MealService(session).patch(user.id, meal_id, payload)
    return MealResponse.model_validate(meal)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> Response:
    await MealService(session).delete(user.id, meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
