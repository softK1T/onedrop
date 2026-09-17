"""Dashboard and analytics endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from onedrop.analytics.schemas import (
    ExpenseAnalytics,
    HabitAnalytics,
    NutritionAnalytics,
    ProductivityAnalytics,
    TodayDashboard,
)
from onedrop.analytics.service import AnalyticsService
from onedrop.api.dependencies import CurrentUser, DbSession

router = APIRouter(tags=["analytics"])


@router.get("/dashboard/today", response_model=TodayDashboard)
async def today_dashboard(session: DbSession, user: CurrentUser) -> TodayDashboard:
    """Tasks, events, spending, nutrition and remaining AI for today."""
    return await AnalyticsService(session).today(user.id)


@router.get("/analytics/expenses", response_model=ExpenseAnalytics)
async def expense_analytics(
    session: DbSession,
    user: CurrentUser,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> ExpenseAnalytics:
    """Category totals, month comparison, budget state and a daily series."""
    return await AnalyticsService(session).expenses(user.id, year=year, month=month)


@router.get("/analytics/nutrition", response_model=NutritionAnalytics)
async def nutrition_analytics(
    session: DbSession,
    user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=366)] = 30,
) -> NutritionAnalytics:
    """Daily calories and macronutrients over a period."""
    return await AnalyticsService(session).nutrition(user.id, days=days)


@router.get("/analytics/habits", response_model=HabitAnalytics)
async def habit_analytics(
    session: DbSession,
    user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=366)] = 30,
) -> HabitAnalytics:
    """Completion percentage per active habit."""
    return await AnalyticsService(session).habits(user.id, days=days)


@router.get("/analytics/productivity", response_model=ProductivityAnalytics)
async def productivity_analytics(
    session: DbSession,
    user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=366)] = 30,
) -> ProductivityAnalytics:
    """Task counters, capture volume and AI usage over a period."""
    return await AnalyticsService(session).productivity(user.id, days=days)
