"""Meal request and response schemas.

Nutrition numbers are estimates unless the user corrects them. OneDrop makes no
medical claims and gives no dietary advice.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MealTypeCode = Literal["breakfast", "lunch", "dinner", "snack"]
NUTRITION_FIELDS: tuple[str, ...] = ("calories", "protein", "fat", "carbohydrates")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MealCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    meal_type: MealTypeCode = "snack"
    eaten_at: datetime | None = None
    calories: int | None = Field(default=None, ge=0, le=20_000)
    protein: int | None = Field(default=None, ge=0, le=2_000)
    fat: int | None = Field(default=None, ge=0, le=2_000)
    carbohydrates: int | None = Field(default=None, ge=0, le=2_000)
    estimated: bool = True


class MealUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    meal_type: MealTypeCode | None = None
    eaten_at: datetime | None = None
    calories: int | None = Field(default=None, ge=0, le=20_000)
    protein: int | None = Field(default=None, ge=0, le=2_000)
    fat: int | None = Field(default=None, ge=0, le=2_000)
    carbohydrates: int | None = Field(default=None, ge=0, le=2_000)


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    meal_type: str
    eaten_at: datetime
    calories: int | None
    protein: int | None
    fat: int | None
    carbohydrates: int | None
    estimated: bool
    source_inbox_item_id: UUID | None
    created_at: datetime


class MealPage(BaseModel):
    items: list[MealResponse]
    day: date
    limit: int
    offset: int
    has_more: bool


class DailyNutrition(BaseModel):
    """Daily totals computed in SQL, never by the model."""

    day: date
    meals_count: int
    calories: int
    protein: int
    fat: int
    carbohydrates: int
    contains_estimates: bool
    disclaimer: str = "Approximate values. Not medical or dietary advice."
