"""Task filter windows and reminder idempotency keys."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from onedrop.reminders.scheduling import digest_key, reminder_key
from onedrop.tasks.filters import build_filter_window

TZ = "Europe/Warsaw"
NOW = datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo(TZ))
ENTITY = UUID("11111111-2222-3333-4444-555555555555")


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


def test_reminder_key_is_stable_per_minute() -> None:
    first = reminder_key("task", ENTITY, datetime(2026, 9, 18, 8, 30, tzinfo=UTC))
    second = reminder_key("task", ENTITY, datetime(2026, 9, 18, 8, 30, 45, tzinfo=UTC))
    assert first == second
    assert first.startswith("task:")


def test_reminder_key_differs_for_another_moment() -> None:
    first = reminder_key("task", ENTITY, datetime(2026, 9, 18, 8, 30, tzinfo=UTC))
    later = reminder_key("task", ENTITY, datetime(2026, 9, 18, 9, 30, tzinfo=UTC))
    assert first != later


def test_reminder_key_normalises_timezone() -> None:
    local = datetime(2026, 9, 18, 10, 30, tzinfo=ZoneInfo(TZ))
    assert reminder_key("task", ENTITY, local).endswith("20260918T0830")


def test_digest_key_is_per_user_and_day() -> None:
    key = digest_key("morning_digest", ENTITY, "2026-09-18")
    assert key == f"morning_digest:{ENTITY}:2026-09-18"
