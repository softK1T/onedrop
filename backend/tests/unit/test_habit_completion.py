"""Habit schedules and completion percentages."""

from __future__ import annotations

from datetime import date

from onedrop.habits.completion import (
    EVERY_DAY,
    build_progress,
    completion_percent,
    expected_occurrences,
    scheduled_days,
)

MONDAY = date(2026, 9, 14)
SUNDAY = date(2026, 9, 20)


def test_missing_schedule_means_every_day() -> None:
    assert scheduled_days(None) == EVERY_DAY
    assert scheduled_days({}) == EVERY_DAY
    assert scheduled_days({"days": []}) == EVERY_DAY


def test_schedule_days_are_sorted_and_deduplicated() -> None:
    assert scheduled_days({"days": [3, 1, 3, 5]}) == (1, 3, 5)


def test_invalid_days_are_dropped() -> None:
    assert scheduled_days({"days": [0, 9, "x", 2]}) == (2,)


def test_daily_habit_expects_seven_occurrences_per_week() -> None:
    assert expected_occurrences(EVERY_DAY, MONDAY, SUNDAY) == 7


def test_weekday_habit_expects_five_occurrences_per_week() -> None:
    assert expected_occurrences((1, 2, 3, 4, 5), MONDAY, SUNDAY) == 5


def test_reversed_range_expects_nothing() -> None:
    assert expected_occurrences(EVERY_DAY, SUNDAY, MONDAY) == 0


def test_completion_percent_is_clamped() -> None:
    assert completion_percent(10, 5) == 50
    assert completion_percent(10, 20) == 100
    assert completion_percent(10, -1) == 0
    assert completion_percent(0, 3) is None


def test_progress_reports_missed_days() -> None:
    progress = build_progress(
        schedule={"days": [1, 2, 3, 4, 5]}, start=MONDAY, end=SUNDAY, completed_days=3
    )
    assert progress.expected == 5
    assert progress.completed == 3
    assert progress.missed == 2
    assert progress.percent == 60


def test_progress_without_expectations_has_no_percent() -> None:
    progress = build_progress(
        schedule={"days": [6, 7]}, start=MONDAY, end=date(2026, 9, 18), completed_days=0
    )
    assert progress.expected == 0
    assert progress.percent is None
