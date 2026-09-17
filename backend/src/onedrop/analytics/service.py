"""Analytics use cases. Aggregation happens in SQL, shaping happens here."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_day_bounds, local_now
from onedrop.analytics.schemas import (
    AiUsageSummary,
    DailyPoint,
    ExpenseAnalytics,
    HabitAnalytics,
    HabitAnalyticsItem,
    NutritionAnalytics,
    NutritionPoint,
    ProductivityAnalytics,
    TaskCounters,
    TodayDashboard,
)
from onedrop.analytics.series import average, fill_daily_series, percentage
from onedrop.db.repositories.analytics import AnalyticsRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.events.schemas import EventResponse
from onedrop.events.service import EventService
from onedrop.expenses.service import ExpenseService
from onedrop.habits.completion import build_progress
from onedrop.meals.service import MealService
from onedrop.tasks.schemas import TaskResponse
from onedrop.tasks.service import TaskService
from onedrop.users.service import UserService

DEFAULT_PERIOD_DAYS = 30
TODAY_TASK_LIMIT = 20
TODAY_EVENT_LIMIT = 20


class AnalyticsService:
    """Read-only aggregates for the Analytics and Today screens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AnalyticsRepository(session)
        self._users = UserRepository(session)
        self._user_service = UserService(session)

    async def _timezone(self, user_id: UUID) -> str:
        row = await self._users.get_settings(user_id)
        return row.timezone if row is not None else "UTC"

    def _period(self, timezone: str, days: int) -> tuple[date, date, datetime, datetime]:
        today = local_now(timezone).date()
        start_day = today - timedelta(days=max(1, days) - 1)
        start, _ = local_day_bounds(start_day, timezone)
        _, end = local_day_bounds(today, timezone)
        return start_day, today, start, end

    async def _ai_summary(
        self, user_id: UUID, *, start: datetime, end: datetime
    ) -> AiUsageSummary:
        usage = await self._user_service.usage(user_id)
        operations, cost = await self._repo.ai_operations_summary(
            user_id, start=start, end=end
        )
        return AiUsageSummary(
            plan=usage.plan,
            remaining=usage.remaining,
            operations_total=operations,
            cost_micro_total=cost,
        )

    async def today(self, user_id: UUID) -> TodayDashboard:
        """Single request powering the Today screen."""
        settings_row = await self._user_service.settings_for(user_id)
        timezone = settings_row.timezone
        today = local_now(timezone).date()
        day_start, day_end = local_day_bounds(today, timezone)
        now = datetime.now(tz=UTC)

        counters = await self._repo.task_counters(
            user_id, day_start=day_start, day_end=day_end, now=now
        )
        task_items, _ = await TaskService(self._session).list(
            user_id, filter_name="today", limit=TODAY_TASK_LIMIT, offset=0
        )
        events, _, _ = await EventService(self._session).list_period(
            user_id, period="day", anchor=today, limit=TODAY_EVENT_LIMIT, offset=0
        )
        spent_today = await self._repo.expenses_total(
            user_id, start=day_start, end=day_end
        )
        nutrition = await MealService(self._session).daily_totals(user_id, day=today)
        summary = await ExpenseService(self._session).monthly_summary(user_id)

        return TodayDashboard(
            day=today,
            timezone=timezone,
            tasks=TaskCounters(
                today=counters[0],
                overdue=counters[1],
                completed_today=counters[2],
                open_total=counters[3],
            ),
            task_items=[TaskResponse.model_validate(item) for item in task_items],
            events=[EventResponse.model_validate(item) for item in events],
            expenses_today_minor=spent_today,
            base_currency=settings_row.base_currency,
            nutrition=nutrition,
            budget_warning=summary.budget.warning,
            ai=await self._ai_summary(user_id, start=day_start, end=day_end),
        )

    async def expenses(
        self, user_id: UUID, *, year: int | None = None, month: int | None = None
    ) -> ExpenseAnalytics:
        timezone = await self._timezone(user_id)
        summary = await ExpenseService(self._session).monthly_summary(
            user_id, year=year, month=month
        )
        first_day = date(summary.year, summary.month, 1)
        last_day = (
            date(summary.year + 1, 1, 1) if summary.month == 12 else date(summary.year, summary.month + 1, 1)
        ) - timedelta(days=1)
        start, _ = local_day_bounds(first_day, timezone)
        _, end = local_day_bounds(last_day, timezone)
        by_day = await self._repo.expenses_by_day(
            user_id, start=start, end=end, timezone=timezone
        )
        return ExpenseAnalytics(
            summary=summary,
            daily=[
                DailyPoint(day=day, value=value)
                for day, value in fill_daily_series(first_day, last_day, by_day)
            ],
        )

    async def nutrition(
        self, user_id: UUID, *, days: int = DEFAULT_PERIOD_DAYS
    ) -> NutritionAnalytics:
        timezone = await self._timezone(user_id)
        start_day, today, start, end = self._period(timezone, days)
        series, estimated = await self._repo.nutrition_by_day(
            user_id, start=start, end=end, timezone=timezone
        )
        calories_by_day = {row[0]: row[1] for row in series}
        points = [
            NutritionPoint(
                day=row[0],
                calories=row[1],
                protein=row[2],
                fat=row[3],
                carbohydrates=row[4],
            )
            for row in series
        ]
        total_calories = sum(calories_by_day.values())
        return NutritionAnalytics(
            period_start=start_day,
            period_end=today,
            days=points,
            average_calories=average(total_calories, (today - start_day).days + 1),
            contains_estimates=estimated,
        )

    async def habits(
        self, user_id: UUID, *, days: int = DEFAULT_PERIOD_DAYS
    ) -> HabitAnalytics:
        timezone = await self._timezone(user_id)
        start_day, today, start, end = self._period(timezone, days)
        rows = await self._repo.habit_completion(
            user_id, start=start, end=end, timezone=timezone
        )
        items: list[HabitAnalyticsItem] = []
        for habit_id, name, schedule, completed in rows:
            progress = build_progress(
                schedule=schedule, start=start_day, end=today, completed_days=completed
            )
            items.append(
                HabitAnalyticsItem(
                    habit_id=str(habit_id),
                    name=name,
                    expected=progress.expected,
                    completed=progress.completed,
                    percent=progress.percent,
                )
            )
        return HabitAnalytics(period_start=start_day, period_end=today, items=items)

    async def productivity(
        self, user_id: UUID, *, days: int = DEFAULT_PERIOD_DAYS
    ) -> ProductivityAnalytics:
        timezone = await self._timezone(user_id)
        start_day, today, start, end = self._period(timezone, days)
        day_start, day_end = local_day_bounds(today, timezone)
        counters = await self._repo.task_counters(
            user_id, day_start=day_start, day_end=day_end, now=datetime.now(tz=UTC)
        )
        completed, created = await self._repo.completed_tasks_in_range(
            user_id, start=start, end=end
        )
        captures = await self._repo.captures_by_day(
            user_id, start=start, end=end, timezone=timezone
        )
        total, failed, undone = await self._repo.capture_status_counts(
            user_id, start=start, end=end
        )
        return ProductivityAnalytics(
            period_start=start_day,
            period_end=today,
            tasks=TaskCounters(
                today=counters[0],
                overdue=counters[1],
                completed_today=counters[2],
                open_total=counters[3],
            ),
            completion_percent=percentage(completed, max(created, completed)),
            captures=[
                DailyPoint(day=day, value=value)
                for day, value in fill_daily_series(start_day, today, captures)
            ],
            captures_total=total,
            captures_failed=failed,
            captures_undone=undone,
            ai=await self._ai_summary(user_id, start=start, end=end),
        )
