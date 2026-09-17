"""Analytics response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from onedrop.events.schemas import EventResponse
from onedrop.expenses.schemas import MonthlySummary
from onedrop.meals.schemas import DailyNutrition
from onedrop.tasks.schemas import TaskResponse


class DailyPoint(BaseModel):
    day: date
    value: int


class NutritionPoint(BaseModel):
    day: date
    calories: int
    protein: int
    fat: int
    carbohydrates: int


class TaskCounters(BaseModel):
    today: int
    overdue: int
    completed_today: int
    open_total: int


class AiUsageSummary(BaseModel):
    plan: str
    remaining: int
    operations_total: int
    cost_micro_total: int


class TodayDashboard(BaseModel):
    """Everything the Today screen needs in a single request."""

    day: date
    timezone: str
    tasks: TaskCounters
    task_items: list[TaskResponse]
    events: list[EventResponse]
    expenses_today_minor: int
    base_currency: str
    nutrition: DailyNutrition
    budget_warning: bool
    ai: AiUsageSummary


class NutritionAnalytics(BaseModel):
    period_start: date
    period_end: date
    days: list[NutritionPoint]
    average_calories: int
    contains_estimates: bool
    disclaimer: str = "Approximate values. Not medical or dietary advice."


class HabitAnalyticsItem(BaseModel):
    habit_id: str
    name: str
    expected: int
    completed: int
    percent: int | None


class HabitAnalytics(BaseModel):
    period_start: date
    period_end: date
    items: list[HabitAnalyticsItem]


class ProductivityAnalytics(BaseModel):
    period_start: date
    period_end: date
    tasks: TaskCounters
    completion_percent: int
    captures: list[DailyPoint]
    captures_total: int
    captures_failed: int
    captures_undone: int
    ai: AiUsageSummary


class ExpenseAnalytics(BaseModel):
    summary: MonthlySummary
    daily: list[DailyPoint]
