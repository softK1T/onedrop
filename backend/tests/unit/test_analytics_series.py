"""Analytics series helpers."""

from __future__ import annotations

from datetime import date

from onedrop.analytics.series import (
    MAX_SERIES_DAYS,
    average,
    date_range,
    fill_daily_series,
    percentage,
)

START = date(2026, 9, 14)
END = date(2026, 9, 18)


def test_date_range_is_inclusive() -> None:
    days = date_range(START, END)
    assert days[0] == START
    assert days[-1] == END
    assert len(days) == 5


def test_reversed_range_is_empty() -> None:
    assert date_range(END, START) == []


def test_range_is_capped_to_a_year() -> None:
    days = date_range(date(2020, 1, 1), date(2030, 1, 1))
    assert len(days) == MAX_SERIES_DAYS


def test_series_fills_gaps_with_zero() -> None:
    series = fill_daily_series(START, END, {date(2026, 9, 16): 4200})
    assert series[0] == (START, 0)
    assert series[2] == (date(2026, 9, 16), 4200)
    assert all(isinstance(value, int) for _, value in series)


def test_percentage_handles_zero_total() -> None:
    assert percentage(5, 0) == 0
    assert percentage(5, 10) == 50
    assert percentage(15, 10) == 100


def test_average_rounds_and_guards_zero_days() -> None:
    assert average(0, 0) == 0
    assert average(700, 7) == 100
    assert average(10, 3) == 3
