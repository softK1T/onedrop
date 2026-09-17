"""Event overlap detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from onedrop.events.overlap import (
    DEFAULT_EVENT_MINUTES,
    TimeRange,
    find_overlaps,
    overlaps,
)

FIRST = UUID("aaaaaaaa-0000-0000-0000-000000000001")
SECOND = UUID("aaaaaaaa-0000-0000-0000-000000000002")
BASE = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)


def test_event_without_end_gets_a_default_duration() -> None:
    span = TimeRange(start=BASE)
    assert span.effective_end == BASE + timedelta(minutes=DEFAULT_EVENT_MINUTES)
    assert span.duration_minutes == DEFAULT_EVENT_MINUTES


def test_partially_overlapping_events_conflict() -> None:
    first = TimeRange(start=BASE, end=BASE + timedelta(hours=2))
    second = TimeRange(start=BASE + timedelta(hours=1), end=BASE + timedelta(hours=3))
    assert overlaps(first, second) is True
    assert overlaps(second, first) is True


def test_touching_events_do_not_conflict() -> None:
    first = TimeRange(start=BASE, end=BASE + timedelta(hours=1))
    second = TimeRange(start=BASE + timedelta(hours=1), end=BASE + timedelta(hours=2))
    assert overlaps(first, second) is False


def test_contained_event_conflicts() -> None:
    outer = TimeRange(start=BASE, end=BASE + timedelta(hours=4))
    inner = TimeRange(start=BASE + timedelta(hours=1), end=BASE + timedelta(hours=2))
    assert overlaps(outer, inner) is True


def test_separate_events_do_not_conflict() -> None:
    morning = TimeRange(start=BASE - timedelta(hours=5), end=BASE - timedelta(hours=4))
    evening = TimeRange(start=BASE, end=BASE + timedelta(hours=1))
    assert overlaps(morning, evening) is False


def test_find_overlaps_returns_only_clashing_ids() -> None:
    candidate = TimeRange(start=BASE, end=BASE + timedelta(minutes=30))
    existing = [
        (FIRST, TimeRange(start=BASE + timedelta(minutes=15))),
        (SECOND, TimeRange(start=BASE + timedelta(hours=3))),
    ]
    assert find_overlaps(candidate, existing) == [FIRST]


def test_find_overlaps_handles_empty_calendar() -> None:
    assert find_overlaps(TimeRange(start=BASE), []) == []
