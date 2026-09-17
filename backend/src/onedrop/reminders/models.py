"""Delivery rules for durable notifications.

Pure logic only: no I/O, no ORM. Everything here is deterministic so the
scheduler and the worker can be reasoned about and unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

DEDUP_KEY_MAX_LENGTH = 200
GLOBAL_ENTITY = "-"


class NotificationKind(StrEnum):
    """Every notification type the worker can deliver."""

    MORNING_DIGEST = "morning_digest"
    TASK_REMINDER = "task_reminder"
    EVENT_REMINDER = "event_reminder"
    HABIT_REMINDER = "habit_reminder"
    BUDGET_WARNING = "budget_warning"


class DeliveryStatus(StrEnum):
    """Lifecycle of a single planned delivery."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


def kinds() -> tuple[str, ...]:
    """Notification kind values, used to build database check constraints."""
    return tuple(member.value for member in NotificationKind)


def statuses() -> tuple[str, ...]:
    """Delivery status values, used to build database check constraints."""
    return tuple(member.value for member in DeliveryStatus)


def require_aware(moment: datetime, field: str) -> datetime:
    """Return the moment in UTC, rejecting naive datetimes."""
    if moment.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return moment.astimezone(UTC)


def run_at_bucket(run_at: datetime) -> str:
    """Minute-precision UTC bucket: two schedules in the same minute collapse."""
    return require_aware(run_at, "run_at").strftime("%Y%m%dT%H%M")


def dedup_key(
    kind: str,
    user_id: UUID | str,
    entity_id: UUID | str | None,
    run_at: datetime,
) -> str:
    """Deterministic key for one delivery.

    Re-running the scheduler for the same entity and the same minute rebuilds
    the identical key, and the unique index turns the second insert into a
    no-op instead of a duplicate message.
    """
    entity = GLOBAL_ENTITY if entity_id is None else str(entity_id)
    key = f"{kind}:{user_id}:{entity}:{run_at_bucket(run_at)}"
    return key[:DEDUP_KEY_MAX_LENGTH]


def dedup_prefix(kind: str, user_id: UUID | str, entity_id: UUID | str | None) -> str:
    """Prefix shared by every delivery of one entity, used to cancel them."""
    entity = GLOBAL_ENTITY if entity_id is None else str(entity_id)
    return f"{kind}:{user_id}:{entity}:"


def period_dedup_key(kind: str, user_id: UUID | str, period_key: str, marker: str) -> str:
    """Key for at-most-once-per-period notifications such as budget warnings."""
    key = f"{kind}:{user_id}:{period_key}:{marker}"
    return key[:DEDUP_KEY_MAX_LENGTH]


@dataclass(frozen=True, slots=True)
class QuietHours:
    """Local window in which the user must not be disturbed.

    ``start_hour == end_hour`` disables the window. A window whose start is
    later than its end wraps around midnight, e.g. 22:00-07:00.
    """

    start_hour: int
    end_hour: int

    def __post_init__(self) -> None:
        for value in (self.start_hour, self.end_hour):
            if not 0 <= value <= 23:
                raise ValueError("quiet hours must be within 0..23")

    @property
    def enabled(self) -> bool:
        return self.start_hour != self.end_hour

    @property
    def wraps_midnight(self) -> bool:
        return self.start_hour > self.end_hour

    def covers(self, moment: time) -> bool:
        """True when a local wall-clock time falls inside the quiet window."""
        if not self.enabled:
            return False
        start = time(hour=self.start_hour)
        end = time(hour=self.end_hour)
        if self.wraps_midnight:
            return moment >= start or moment < end
        return start <= moment < end


def shift_out_of_quiet_hours(run_at: datetime, timezone: str, quiet: QuietHours) -> datetime:
    """Move a delivery to the first allowed moment after the quiet window.

    The returned value is always in UTC and never earlier than ``run_at``.
    """
    moment = require_aware(run_at, "run_at")
    if not quiet.enabled:
        return moment
    tz = ZoneInfo(timezone)
    local = moment.astimezone(tz)
    if not quiet.covers(local.timetz().replace(tzinfo=None)):
        return moment
    resume_date = local.date()
    if quiet.wraps_midnight and local.hour >= quiet.start_hour:
        resume_date = resume_date + timedelta(days=1)
    resumed = datetime.combine(resume_date, time(hour=quiet.end_hour), tzinfo=tz)
    return max(resumed.astimezone(UTC), moment)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Exponential backoff with a ceiling and a hard attempt limit."""

    max_attempts: int = 5
    base_delay_seconds: int = 60
    max_delay_seconds: int = 3600

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds < 1:
            raise ValueError("base_delay_seconds must be at least 1")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must not be below base_delay_seconds")

    def is_exhausted(self, attempts: int) -> bool:
        """True when the delivery must be marked failed instead of retried."""
        return attempts >= self.max_attempts

    def delay_after(self, attempts: int) -> timedelta:
        """Delay before the next attempt, given the number of attempts so far."""
        exponent = max(attempts - 1, 0)
        seconds = self.base_delay_seconds * (2**exponent)
        return timedelta(seconds=min(seconds, self.max_delay_seconds))

    def next_run_at(self, attempts: int, *, now: datetime) -> datetime:
        """Absolute UTC moment of the next attempt."""
        return require_aware(now, "now") + self.delay_after(attempts)


@dataclass(frozen=True, slots=True)
class ReminderPreferences:
    """Reminder-relevant slice of a user profile."""

    timezone: str
    quiet_hours: QuietHours
    morning_digest_hour: int
    task_lead_minutes: int
    event_lead_minutes: int
    budget_threshold_percent: int
    reminders_enabled: bool = True
    morning_digest: bool = True
    task_reminders: bool = True
    event_reminders: bool = True
    habit_reminders: bool = True
    budget_warnings: bool = True

    def allows(self, kind: str) -> bool:
        """True when the user opted in to this notification kind."""
        if not self.reminders_enabled:
            return False
        switches = {
            NotificationKind.MORNING_DIGEST.value: self.morning_digest,
            NotificationKind.TASK_REMINDER.value: self.task_reminders,
            NotificationKind.EVENT_REMINDER.value: self.event_reminders,
            NotificationKind.HABIT_REMINDER.value: self.habit_reminders,
            NotificationKind.BUDGET_WARNING.value: self.budget_warnings,
        }
        return switches.get(kind, False)

    def lead_minutes(self, kind: str) -> int:
        """Lead time applied before the moment a reminder refers to."""
        if kind == NotificationKind.TASK_REMINDER.value:
            return self.task_lead_minutes
        if kind == NotificationKind.EVENT_REMINDER.value:
            return self.event_lead_minutes
        return 0
