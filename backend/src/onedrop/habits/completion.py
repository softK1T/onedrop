"""Habit completion arithmetic. Pure date maths, no I/O."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

EVERY_DAY: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)


def scheduled_days(schedule: dict[str, Any] | None) -> tuple[int, ...]:
    """ISO weekdays a habit is planned for. Missing schedule means every day."""
    if not schedule:
        return EVERY_DAY
    raw = schedule.get("days")
    if not isinstance(raw, list) or not raw:
        return EVERY_DAY
    days = sorted({int(day) for day in raw if isinstance(day, int) and 1 <= day <= 7})
    return tuple(days) or EVERY_DAY


def expected_occurrences(days: Sequence[int], start: date, end: date) -> int:
    """How many times the habit was due in the inclusive date range."""
    if end < start:
        return 0
    allowed = set(days)
    total = 0
    cursor = start
    while cursor <= end:
        if cursor.isoweekday() in allowed:
            total += 1
        cursor += timedelta(days=1)
    return total


def completion_percent(expected: int, completed: int) -> int | None:
    """Completion rate in percent, or None when nothing was due."""
    if expected <= 0:
        return None
    return max(0, min(100, int(round(completed * 100 / expected))))


@dataclass(frozen=True, slots=True)
class HabitProgress:
    """Progress of one habit over a period."""

    expected: int
    completed: int
    days: tuple[int, ...]

    @property
    def percent(self) -> int | None:
        return completion_percent(self.expected, self.completed)

    @property
    def missed(self) -> int:
        return max(0, self.expected - self.completed)


def build_progress(
    *, schedule: dict[str, Any] | None, start: date, end: date, completed_days: int
) -> HabitProgress:
    days = scheduled_days(schedule)
    return HabitProgress(
        expected=expected_occurrences(days, start, end),
        completed=completed_days,
        days=days,
    )
