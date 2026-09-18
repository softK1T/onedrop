"""Task filter windows."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from onedrop.tasks.filters import build_filter_window

TZ = "Europe/Warsaw"
NOW = datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo(TZ))


def test_today_filter_covers_the_local_day_in_utc() -> None:
    window = build_filter_window("today", TZ, now_local=NOW)
    assert window.start == datetime(2026, 9, 16, 22, 0, tzinfo=UTC)
    assert window.end == datetime(2026, 9, 17, 22, 0, tzinfo=UTC)
    assert window.require_due is True
    assert window.only_open is True


def test_upcoming_filter_starts_after_today() -> None:
    window = build_filter_window("upcoming", TZ, now_local=NOW)
    assert window.start == datetime(2026, 9, 17, 22, 0, tzinfo=UTC)
    assert window.end is None
    assert window.only_open is True


def test_no_date_filter_requires_missing_due_date() -> None:
    window = build_filter_window("no_date", TZ, now_local=NOW)
    assert window.require_no_due is True
    assert window.require_due is False
    assert window.only_open is True


def test_completed_filter_only_returns_done_tasks() -> None:
    window = build_filter_window("completed", TZ, now_local=NOW)
    assert window.only_completed is True
    assert window.only_open is False


def test_unknown_filter_falls_back_to_all() -> None:
    window = build_filter_window("whatever", TZ, now_local=NOW)
    assert window.name == "all"
    assert window.start is None
    assert window.only_open is False
