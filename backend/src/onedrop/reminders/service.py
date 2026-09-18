"""Planning of durable notifications.

The planning pass is idempotent: every notification it produces carries a
deterministic dedup key, so running the pass every minute queues each message
exactly once. Pure planning functions are separated from the database access so
they can be unit-tested without Postgres.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_day_bounds
from onedrop.db.models.enums import EventStatus, TaskStatus
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog
from onedrop.db.models.planner import Event, Task
from onedrop.db.models.user import User, UserSettings
from onedrop.logging import get_logger
from onedrop.reminders.models import (
    NotificationKind,
    QuietHours,
    ReminderPreferences,
    dedup_key,
    period_dedup_key,
    require_aware,
    shift_out_of_quiet_hours,
)
from onedrop.reminders.repository import ScheduledNotificationRepository

logger = get_logger(__name__)

DEFAULT_HORIZON = timedelta(hours=26)
MAX_USERS_PER_PASS = 500
MAX_ENTITIES_PER_USER = 200
FULL_BUDGET_PERCENT = 100


@dataclass(frozen=True, slots=True)
class PlannedNotification:
    """One notification the planner wants to queue."""

    kind: str
    run_at: datetime
    dedup_key: str
    payload: dict[str, Any]


def preferences_from_settings(row: UserSettings) -> ReminderPreferences:
    """Project a settings row onto the reminder preference value object."""
    return ReminderPreferences(
        timezone=row.timezone,
        quiet_hours=QuietHours(
            start_hour=row.quiet_hours_start, end_hour=row.quiet_hours_end
        ),
        morning_digest_hour=row.morning_digest_hour,
        task_lead_minutes=row.task_reminder_lead_minutes,
        event_lead_minutes=row.event_reminder_lead_minutes,
        budget_threshold_percent=row.budget_warning_threshold_percent,
        reminders_enabled=row.reminders_enabled,
        morning_digest=row.morning_digest,
        task_reminders=row.task_reminders,
        event_reminders=row.event_reminders,
        habit_reminders=row.habit_reminders,
        budget_warnings=row.budget_warnings,
    )


def local_month_bounds(now: datetime, timezone: str) -> tuple[str, datetime, datetime]:
    """Period key plus UTC bounds of the user's current local month."""
    zone = ZoneInfo(timezone)
    local = require_aware(now, "now").astimezone(zone)
    start = datetime(local.year, local.month, 1, tzinfo=zone)
    if local.month == 12:
        end = datetime(local.year + 1, 1, 1, tzinfo=zone)
    else:
        end = datetime(local.year, local.month + 1, 1, tzinfo=zone)
    return f"{local.year:04d}-{local.month:02d}", start.astimezone(UTC), end.astimezone(UTC)


def habit_runs_on(schedule: dict[str, Any] | None, local_date: date) -> bool:
    """True when a habit is expected on this weekday.

    ``schedule`` supports ``{"weekdays": [0, 2, 4]}`` with Monday as 0. Any
    other shape means the habit is expected every day.
    """
    if not schedule:
        return True
    weekdays = schedule.get("weekdays")
    if not isinstance(weekdays, list) or not weekdays:
        return True
    allowed: set[int] = set()
    for value in weekdays:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            allowed.add(value % 7)
        elif isinstance(value, str) and value.strip().isdigit():
            allowed.add(int(value.strip()) % 7)
    if not allowed:
        return True
    return local_date.weekday() in allowed


def plan_morning_digest(
    user_id: UUID, prefs: ReminderPreferences, *, now: datetime
) -> PlannedNotification | None:
    """Queue the next morning digest, one per local day."""
    kind = NotificationKind.MORNING_DIGEST.value
    if not prefs.allows(kind):
        return None
    zone = ZoneInfo(prefs.timezone)
    local = require_aware(now, "now").astimezone(zone)
    target_date = local.date()
    candidate = datetime.combine(target_date, time(hour=prefs.morning_digest_hour), tzinfo=zone)
    if candidate <= local:
        target_date = target_date + timedelta(days=1)
        candidate = datetime.combine(
            target_date, time(hour=prefs.morning_digest_hour), tzinfo=zone
        )
    run_at = shift_out_of_quiet_hours(
        candidate.astimezone(UTC), prefs.timezone, prefs.quiet_hours
    )
    local_date = target_date.isoformat()
    return PlannedNotification(
        kind=kind,
        run_at=run_at,
        dedup_key=period_dedup_key(kind, user_id, local_date, "digest"),
        payload={"local_date": local_date, "timezone": prefs.timezone},
    )


def plan_entity_reminder(
    *,
    kind: str,
    user_id: UUID,
    entity_id: UUID,
    title: str,
    moment: datetime,
    prefs: ReminderPreferences,
    now: datetime,
) -> PlannedNotification | None:
    """Queue a task or event reminder, lead time and quiet hours applied."""
    if not prefs.allows(kind):
        return None
    target = require_aware(moment, "moment")
    reference = require_aware(now, "now")
    run_at = target - timedelta(minutes=prefs.lead_minutes(kind))
    if run_at <= reference:
        return None
    run_at = shift_out_of_quiet_hours(run_at, prefs.timezone, prefs.quiet_hours)
    return PlannedNotification(
        kind=kind,
        run_at=run_at,
        dedup_key=dedup_key(kind, user_id, entity_id, run_at),
        payload={
            "title": title,
            "moment": target.isoformat(),
            "timezone": prefs.timezone,
            "entity_id": str(entity_id),
        },
    )


def plan_habit_reminder(
    *,
    user_id: UUID,
    habit_id: UUID,
    title: str,
    reminder_hour: int | None,
    prefs: ReminderPreferences,
    now: datetime,
    already_logged: bool,
) -> PlannedNotification | None:
    """Queue today's habit reminder unless the habit is already done."""
    kind = NotificationKind.HABIT_REMINDER.value
    if not prefs.allows(kind) or already_logged or reminder_hour is None:
        return None
    zone = ZoneInfo(prefs.timezone)
    local = require_aware(now, "now").astimezone(zone)
    candidate = datetime.combine(local.date(), time(hour=reminder_hour), tzinfo=zone)
    if candidate <= local:
        return None
    run_at = shift_out_of_quiet_hours(
        candidate.astimezone(UTC), prefs.timezone, prefs.quiet_hours
    )
    return PlannedNotification(
        kind=kind,
        run_at=run_at,
        dedup_key=dedup_key(kind, user_id, habit_id, run_at),
        payload={
            "title": title,
            "local_date": local.date().isoformat(),
            "timezone": prefs.timezone,
            "entity_id": str(habit_id),
        },
    )


def plan_budget_warning(
    *,
    user_id: UUID,
    prefs: ReminderPreferences,
    spent_minor: int,
    limit_minor: int | None,
    currency: str,
    period_key: str,
    now: datetime,
) -> PlannedNotification | None:
    """Queue at most one warning per crossed threshold per period."""
    kind = NotificationKind.BUDGET_WARNING.value
    if not prefs.allows(kind) or not limit_minor or limit_minor <= 0:
        return None
    percent = spent_minor * 100 // limit_minor
    if percent >= FULL_BUDGET_PERCENT:
        threshold = FULL_BUDGET_PERCENT
    elif percent >= prefs.budget_threshold_percent:
        threshold = prefs.budget_threshold_percent
    else:
        return None
    run_at = shift_out_of_quiet_hours(
        require_aware(now, "now"), prefs.timezone, prefs.quiet_hours
    )
    return PlannedNotification(
        kind=kind,
        run_at=run_at,
        dedup_key=period_dedup_key(kind, user_id, period_key, str(threshold)),
        payload={
            "threshold": threshold,
            "percent": percent,
            "spent_minor": spent_minor,
            "limit_minor": limit_minor,
            "currency": currency,
            "period": period_key,
            "timezone": prefs.timezone,
        },
    )


class ReminderService:
    """Turns domain state into queued notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notifications = ScheduledNotificationRepository(session)

    async def plan_for_all_users(
        self, *, now: datetime, horizon: timedelta = DEFAULT_HORIZON
    ) -> int:
        """Run one planning pass for every active user."""
        reference = require_aware(now, "now")
        stmt = (
            select(User, UserSettings)
            .join(UserSettings, UserSettings.user_id == User.id)
            .where(User.deleted_at.is_(None), User.is_blocked.is_(False))
            .order_by(User.created_at)
            .limit(MAX_USERS_PER_PASS)
        )
        rows = (await self._session.execute(stmt)).all()
        queued = 0
        for user, settings_row in rows:
            queued += await self.plan_for_user(
                user, settings_row, now=reference, horizon=horizon
            )
        if queued:
            logger.info("reminders.planned", queued=queued, users=len(rows))
        return queued

    async def plan_for_user(
        self,
        user: User,
        settings_row: UserSettings,
        *,
        now: datetime,
        horizon: timedelta = DEFAULT_HORIZON,
    ) -> int:
        """Queue every notification this user needs within the horizon."""
        prefs = preferences_from_settings(settings_row)
        if not prefs.reminders_enabled:
            return 0
        reference = require_aware(now, "now")
        plans: list[PlannedNotification] = []

        digest = plan_morning_digest(user.id, prefs, now=reference)
        if digest is not None:
            plans.append(digest)

        plans.extend(
            await self._plan_tasks(user.id, prefs, now=reference, horizon=horizon)
        )
        plans.extend(
            await self._plan_events(user.id, prefs, now=reference, horizon=horizon)
        )
        plans.extend(await self._plan_habits(user.id, prefs, now=reference))
        budget = await self._plan_budget(user.id, settings_row, prefs, now=reference)
        if budget is not None:
            plans.append(budget)

        queued = 0
        for plan in plans:
            created = await self._notifications.enqueue(
                user_id=user.id,
                kind=plan.kind,
                run_at=plan.run_at,
                dedup_key=plan.dedup_key,
                payload=plan.payload,
            )
            if created is not None:
                queued += 1
        return queued

    async def _plan_tasks(
        self, user_id: UUID, prefs: ReminderPreferences, *, now: datetime, horizon: timedelta
    ) -> list[PlannedNotification]:
        kind = NotificationKind.TASK_REMINDER.value
        if not prefs.allows(kind):
            return []
        window_end = now + horizon
        stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.OPEN.value,
                Task.due_at.is_not(None),
            )
            .order_by(Task.due_at)
            .limit(MAX_ENTITIES_PER_USER)
        )
        plans: list[PlannedNotification] = []
        for task in (await self._session.execute(stmt)).scalars().all():
            if task.due_at is None or task.due_at > window_end:
                continue
            plan = plan_entity_reminder(
                kind=kind,
                user_id=user_id,
                entity_id=task.id,
                title=task.title,
                moment=task.due_at,
                prefs=prefs,
                now=now,
            )
            if plan is not None:
                plans.append(plan)
        return plans

    async def _plan_events(
        self, user_id: UUID, prefs: ReminderPreferences, *, now: datetime, horizon: timedelta
    ) -> list[PlannedNotification]:
        kind = NotificationKind.EVENT_REMINDER.value
        if not prefs.allows(kind):
            return []
        window_end = now + horizon
        stmt = (
            select(Event)
            .where(
                Event.user_id == user_id,
                Event.deleted_at.is_(None),
                Event.status == EventStatus.PLANNED.value,
                Event.starts_at <= window_end,
                Event.starts_at >= now - timedelta(days=1),
            )
            .order_by(Event.starts_at)
            .limit(MAX_ENTITIES_PER_USER)
        )
        plans: list[PlannedNotification] = []
        for event in (await self._session.execute(stmt)).scalars().all():
            plan = plan_entity_reminder(
                kind=kind,
                user_id=user_id,
                entity_id=event.id,
                title=event.title,
                moment=event.starts_at,
                prefs=prefs,
                now=now,
            )
            if plan is not None:
                plans.append(plan)
        return plans

    async def _plan_habits(
        self, user_id: UUID, prefs: ReminderPreferences, *, now: datetime
    ) -> list[PlannedNotification]:
        kind = NotificationKind.HABIT_REMINDER.value
        if not prefs.allows(kind):
            return []
        zone = ZoneInfo(prefs.timezone)
        local_date = now.astimezone(zone).date()
        day_start, day_end = local_day_bounds(local_date, prefs.timezone)
        stmt = (
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.deleted_at.is_(None),
                Habit.active.is_(True),
                Habit.reminder_hour.is_not(None),
            )
            .order_by(Habit.name)
            .limit(MAX_ENTITIES_PER_USER)
        )
        plans: list[PlannedNotification] = []
        for habit in (await self._session.execute(stmt)).scalars().all():
            if not habit_runs_on(habit.schedule, local_date):
                continue
            logged = await self._session.scalar(
                select(func.count())
                .select_from(HabitLog)
                .where(
                    HabitLog.habit_id == habit.id,
                    HabitLog.logged_at >= day_start,
                    HabitLog.logged_at < day_end,
                )
            )
            already_logged = bool(logged)
            if already_logged:
                await self._notifications.cancel_pending(
                    kind=kind, user_id=user_id, entity_id=habit.id
                )
                continue
            plan = plan_habit_reminder(
                user_id=user_id,
                habit_id=habit.id,
                title=habit.name,
                reminder_hour=habit.reminder_hour,
                prefs=prefs,
                now=now,
                already_logged=already_logged,
            )
            if plan is not None:
                plans.append(plan)
        return plans

    async def _plan_budget(
        self,
        user_id: UUID,
        settings_row: UserSettings,
        prefs: ReminderPreferences,
        *,
        now: datetime,
    ) -> PlannedNotification | None:
        if not prefs.allows(NotificationKind.BUDGET_WARNING.value):
            return None
        if not settings_row.monthly_budget_minor:
            return None
        period_key, month_start, month_end = local_month_bounds(now, prefs.timezone)
        spent = await self._month_spending(user_id, month_start, month_end)
        return plan_budget_warning(
            user_id=user_id,
            prefs=prefs,
            spent_minor=spent,
            limit_minor=settings_row.monthly_budget_minor,
            currency=settings_row.base_currency,
            period_key=period_key,
            now=now,
        )

    async def _month_spending(self, user_id: UUID, start: datetime, end: datetime) -> int:
        total = await self._session.scalar(
            select(
                func.coalesce(
                    func.sum(
                        func.coalesce(Expense.base_amount_minor, Expense.amount_minor)
                    ),
                    0,
                )
            ).where(
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
                Expense.occurred_at >= start,
                Expense.occurred_at < end,
            )
        )
        return int(total or 0)

    async def build_digest(
        self, user_id: UUID, prefs: ReminderPreferences, *, now: datetime
    ) -> dict[str, Any]:
        """Counts for the morning digest, computed at delivery time."""
        reference = require_aware(now, "now")
        zone = ZoneInfo(prefs.timezone)
        local_date = reference.astimezone(zone).date()
        day_start, day_end = local_day_bounds(local_date, prefs.timezone)

        tasks = await self._session.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.OPEN.value,
                Task.due_at >= day_start,
                Task.due_at < day_end,
            )
        )
        events = await self._session.scalar(
            select(func.count())
            .select_from(Event)
            .where(
                Event.user_id == user_id,
                Event.deleted_at.is_(None),
                Event.status == EventStatus.PLANNED.value,
                Event.starts_at >= day_start,
                Event.starts_at < day_end,
            )
        )
        habit_rows = (
            await self._session.execute(
                select(Habit).where(
                    Habit.user_id == user_id,
                    Habit.deleted_at.is_(None),
                    Habit.active.is_(True),
                )
            )
        ).scalars().all()
        expected = [habit for habit in habit_rows if habit_runs_on(habit.schedule, local_date)]
        done = await self._session.scalar(
            select(func.count(func.distinct(HabitLog.habit_id))).where(
                HabitLog.user_id == user_id,
                HabitLog.logged_at >= day_start,
                HabitLog.logged_at < day_end,
            )
        )
        settings_row = await self._session.scalar(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        budget_left: int | None = None
        currency = settings_row.base_currency if settings_row is not None else "PLN"
        if settings_row is not None and settings_row.monthly_budget_minor:
            _, month_start, month_end = local_month_bounds(reference, prefs.timezone)
            spent = await self._month_spending(user_id, month_start, month_end)
            budget_left = int(settings_row.monthly_budget_minor) - spent

        return {
            "local_date": local_date.isoformat(),
            "timezone": prefs.timezone,
            "tasks": int(tasks or 0),
            "events": int(events or 0),
            "habits": max(len(expected) - int(done or 0), 0),
            "budget_left_minor": budget_left,
            "currency": currency,
        }

    async def cancel_for_entity(self, *, kind: str, user_id: UUID, entity_id: UUID) -> int:
        """Drop queued notifications for an entity that no longer needs them."""
        return await self._notifications.cancel_pending(
            kind=kind, user_id=user_id, entity_id=entity_id
        )
