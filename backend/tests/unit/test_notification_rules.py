"""Delivery rules: dedup keys, quiet hours, retry backoff, opt-in switches."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

import pytest

from onedrop.reminders.models import (
    DEDUP_KEY_MAX_LENGTH,
    NotificationKind,
    QuietHours,
    ReminderPreferences,
    RetryPolicy,
    dedup_key,
    dedup_prefix,
    period_dedup_key,
    run_at_bucket,
    shift_out_of_quiet_hours,
)

TZ = "Europe/Warsaw"
USER = UUID("11111111-1111-1111-1111-111111111111")
ENTITY = UUID("22222222-2222-2222-2222-222222222222")


def test_dedup_key_is_stable_within_the_same_minute() -> None:
    first = dedup_key(
        NotificationKind.TASK_REMINDER.value, USER, ENTITY, datetime(2026, 9, 18, 7, 30, tzinfo=UTC)
    )
    second = dedup_key(
        NotificationKind.TASK_REMINDER.value,
        USER,
        ENTITY,
        datetime(2026, 9, 18, 7, 30, 59, tzinfo=UTC),
    )
    assert first == second
    assert first == f"task_reminder:{USER}:{ENTITY}:20260918T0730"


def test_dedup_key_changes_with_the_run_at_bucket() -> None:
    early = dedup_key(
        NotificationKind.TASK_REMINDER.value, USER, ENTITY, datetime(2026, 9, 18, 7, 30, tzinfo=UTC)
    )
    late = dedup_key(
        NotificationKind.TASK_REMINDER.value, USER, ENTITY, datetime(2026, 9, 18, 8, 30, tzinfo=UTC)
    )
    assert early != late


def test_dedup_key_uses_a_placeholder_for_user_wide_notifications() -> None:
    key = dedup_key(
        NotificationKind.MORNING_DIGEST.value, USER, None, datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    )
    assert key == f"morning_digest:{USER}:-:20260918T0600"
    assert key.startswith(dedup_prefix(NotificationKind.MORNING_DIGEST.value, USER, None))


def test_dedup_key_never_exceeds_the_column_length() -> None:
    key = dedup_key("x" * 400, USER, ENTITY, datetime(2026, 9, 18, 6, 0, tzinfo=UTC))
    assert len(key) == DEDUP_KEY_MAX_LENGTH


def test_period_dedup_key_allows_one_warning_per_threshold_and_period() -> None:
    eighty = period_dedup_key(
        NotificationKind.BUDGET_WARNING.value, USER, "2026-09", "80"
    )
    hundred = period_dedup_key(
        NotificationKind.BUDGET_WARNING.value, USER, "2026-09", "100"
    )
    next_month = period_dedup_key(
        NotificationKind.BUDGET_WARNING.value, USER, "2026-10", "80"
    )
    assert eighty != hundred
    assert eighty != next_month
    assert eighty == period_dedup_key(
        NotificationKind.BUDGET_WARNING.value, USER, "2026-09", "80"
    )


def test_run_at_bucket_normalises_to_utc() -> None:
    assert run_at_bucket(datetime(2026, 9, 18, 9, 30, tzinfo=UTC)) == "20260918T0930"


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError):
        run_at_bucket(datetime(2026, 9, 18, 9, 30))


def test_quiet_hours_wrapping_midnight_cover_night_times() -> None:
    quiet = QuietHours(start_hour=22, end_hour=7)
    assert quiet.enabled is True
    assert quiet.wraps_midnight is True
    assert quiet.covers(time(23, 30)) is True
    assert quiet.covers(time(3, 0)) is True
    assert quiet.covers(time(7, 0)) is False
    assert quiet.covers(time(12, 0)) is False


def test_quiet_hours_inside_one_day() -> None:
    quiet = QuietHours(start_hour=13, end_hour=15)
    assert quiet.wraps_midnight is False
    assert quiet.covers(time(14, 0)) is True
    assert quiet.covers(time(15, 0)) is False


def test_equal_bounds_disable_quiet_hours() -> None:
    quiet = QuietHours(start_hour=0, end_hour=0)
    assert quiet.enabled is False
    assert quiet.covers(time(2, 0)) is False


def test_out_of_range_quiet_hours_are_rejected() -> None:
    with pytest.raises(ValueError):
        QuietHours(start_hour=24, end_hour=7)


def test_late_night_delivery_moves_to_the_next_morning() -> None:
    quiet = QuietHours(start_hour=22, end_hour=7)
    run_at = datetime(2026, 9, 18, 21, 30, tzinfo=UTC)
    shifted = shift_out_of_quiet_hours(run_at, TZ, quiet)
    assert shifted == datetime(2026, 9, 19, 5, 0, tzinfo=UTC)


def test_early_morning_delivery_moves_to_the_same_morning() -> None:
    quiet = QuietHours(start_hour=22, end_hour=7)
    run_at = datetime(2026, 9, 18, 2, 0, tzinfo=UTC)
    shifted = shift_out_of_quiet_hours(run_at, TZ, quiet)
    assert shifted == datetime(2026, 9, 18, 5, 0, tzinfo=UTC)


def test_delivery_outside_quiet_hours_is_untouched() -> None:
    quiet = QuietHours(start_hour=22, end_hour=7)
    run_at = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    assert shift_out_of_quiet_hours(run_at, TZ, quiet) == run_at


def test_disabled_quiet_hours_never_shift() -> None:
    quiet = QuietHours(start_hour=6, end_hour=6)
    run_at = datetime(2026, 9, 18, 1, 0, tzinfo=UTC)
    assert shift_out_of_quiet_hours(run_at, TZ, quiet) == run_at


def test_backoff_grows_exponentially_and_is_capped() -> None:
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=60, max_delay_seconds=600)
    assert policy.delay_after(1) == timedelta(seconds=60)
    assert policy.delay_after(2) == timedelta(seconds=120)
    assert policy.delay_after(3) == timedelta(seconds=240)
    assert policy.delay_after(4) == timedelta(seconds=480)
    assert policy.delay_after(5) == timedelta(seconds=600)
    assert policy.delay_after(9) == timedelta(seconds=600)


def test_next_run_at_is_relative_to_now() -> None:
    policy = RetryPolicy(base_delay_seconds=30)
    now = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    assert policy.next_run_at(1, now=now) == datetime(2026, 9, 18, 10, 0, 30, tzinfo=UTC)


def test_attempts_are_exhausted_at_the_limit() -> None:
    policy = RetryPolicy(max_attempts=3)
    assert policy.is_exhausted(2) is False
    assert policy.is_exhausted(3) is True


def test_invalid_retry_policies_are_rejected() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        RetryPolicy(base_delay_seconds=0)
    with pytest.raises(ValueError):
        RetryPolicy(base_delay_seconds=600, max_delay_seconds=60)


def _prefs(**overrides: object) -> ReminderPreferences:
    base: dict[str, object] = {
        "timezone": TZ,
        "quiet_hours": QuietHours(start_hour=22, end_hour=7),
        "morning_digest_hour": 8,
        "task_lead_minutes": 30,
        "event_lead_minutes": 60,
        "budget_threshold_percent": 80,
    }
    base.update(overrides)
    return ReminderPreferences(**base)  # type: ignore[arg-type]


def test_master_switch_disables_every_kind() -> None:
    prefs = _prefs(reminders_enabled=False)
    assert prefs.allows(NotificationKind.MORNING_DIGEST.value) is False
    assert prefs.allows(NotificationKind.TASK_REMINDER.value) is False


def test_per_kind_switches_are_respected() -> None:
    prefs = _prefs(habit_reminders=False)
    assert prefs.allows(NotificationKind.HABIT_REMINDER.value) is False
    assert prefs.allows(NotificationKind.EVENT_REMINDER.value) is True


def test_lead_minutes_depend_on_the_kind() -> None:
    prefs = _prefs()
    assert prefs.lead_minutes(NotificationKind.TASK_REMINDER.value) == 30
    assert prefs.lead_minutes(NotificationKind.EVENT_REMINDER.value) == 60
    assert prefs.lead_minutes(NotificationKind.MORNING_DIGEST.value) == 0
