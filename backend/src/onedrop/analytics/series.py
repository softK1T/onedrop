"""Series helpers for analytics. Pure functions, no I/O."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta

MAX_SERIES_DAYS = 366


def date_range(start: date, end: date) -> list[date]:
    """Inclusive list of days, capped to a year to keep responses small."""
    if end < start:
        return []
    days: list[date] = []
    cursor = start
    while cursor <= end and len(days) < MAX_SERIES_DAYS:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def fill_daily_series(
    start: date, end: date, values: Mapping[date, int]
) -> list[tuple[date, int]]:
    """Return one point per day, filling gaps with zero."""
    return [(day, int(values.get(day, 0))) for day in date_range(start, end)]


def percentage(part: int, total: int) -> int:
    """Integer percentage, zero when there is nothing to divide by."""
    if total <= 0:
        return 0
    return max(0, min(100, int(round(part * 100 / total))))


def average(total: int, days: int) -> int:
    """Rounded daily average."""
    if days <= 0:
        return 0
    return int(round(total / days))
