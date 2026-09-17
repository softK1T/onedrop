"""Planning rules and message rendering for the five notification kinds."""

from __future__ import annotations

from datetime import UTC, datetime, date, timedelta
from uuid import UUID

from onedrop.reminders.messages import format_money, render_notification
from onedrop.reminders.models import NotificationKind, QuietHours, ReminderPreferences
from onedrop.reminders.service import (
    habit_runs_on,
    local_month_bounds,
    plan_budget_warning,
    plan_entity_reminder,
    plan_habit_reminder,
    plan_morning_digest,
)

TZ = "Europe/Warsaw"
USER = UUID("11111111-1111-1111-1111-111111111111")
ENTITY = UUID("22222222-2222-2222-2222-222222222222")


def prefs(**overrides: object) -> ReminderPreferences:
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


def test_digest_is_planned_for_today_when_the_hour_is_ahead() -> None:
    now = datetime(2026, 9, 18, 4, 0, tzinfo=UTC)
    plan = plan_morning_digest(USER, prefs(), now=now)
    assert plan is not None
    assert plan.run_at == datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    assert plan.payload["local_date"] == "2026-09-18"


def test_digest_moves_to_tomorrow_when_the_hour_has_passed() -> None:
    now = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    plan = plan_morning_digest(USER, prefs(), now=now)
    assert plan is not None
    assert plan.run_at == datetime(2026, 9, 19, 6, 0, tzinfo=UTC)
    assert plan.payload["local_date"] == "2026-09-19"


def test_digest_key_is_identical_on_repeated_planning_passes() -> None:
    first = plan_morning_digest(USER, prefs(), now=datetime(2026, 9, 18, 4, 0, tzinfo=UTC))
    second = plan_morning_digest(USER, prefs(), now=datetime(2026, 9, 18, 5, 30, tzinfo=UTC))
    assert first is not None and second is not None
    assert first.dedup_key == second.dedup_key


def test_digest_inside_quiet_hours_is_pushed_to_the_end_of_the_window() -> None:
    plan = plan_morning_digest(
        USER, prefs(morning_digest_hour=5), now=datetime(2026, 9, 18, 0, 30, tzinfo=UTC)
    )
    assert plan is not None
    assert plan.run_at == datetime(2026, 9, 18, 5, 0, tzinfo=UTC)


def test_digest_is_skipped_when_the_user_disabled_it() -> None:
    plan = plan_morning_digest(
        USER, prefs(morning_digest=False), now=datetime(2026, 9, 18, 4, 0, tzinfo=UTC)
    )
    assert plan is None


def test_task_reminder_applies_the_lead_time() -> None:
    plan = plan_entity_reminder(
        kind=NotificationKind.TASK_REMINDER.value,
        user_id=USER,
        entity_id=ENTITY,
        title="Pay rent",
        moment=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        prefs=prefs(),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
    )
    assert plan is not None
    assert plan.run_at == datetime(2026, 9, 18, 14, 30, tzinfo=UTC)
    assert plan.payload["title"] == "Pay rent"


def test_event_reminder_uses_its_own_lead_time() -> None:
    plan = plan_entity_reminder(
        kind=NotificationKind.EVENT_REMINDER.value,
        user_id=USER,
        entity_id=ENTITY,
        title="Dentist",
        moment=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        prefs=prefs(),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
    )
    assert plan is not None
    assert plan.run_at == datetime(2026, 9, 18, 14, 0, tzinfo=UTC)


def test_reminder_in_the_past_is_not_planned() -> None:
    plan = plan_entity_reminder(
        kind=NotificationKind.TASK_REMINDER.value,
        user_id=USER,
        entity_id=ENTITY,
        title="Too late",
        moment=datetime(2026, 9, 18, 9, 10, tzinfo=UTC),
        prefs=prefs(),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
    )
    assert plan is None


def test_reminder_key_is_stable_across_planning_passes() -> None:
    kwargs = {
        "kind": NotificationKind.TASK_REMINDER.value,
        "user_id": USER,
        "entity_id": ENTITY,
        "title": "Pay rent",
        "moment": datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        "prefs": prefs(),
    }
    first = plan_entity_reminder(now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC), **kwargs)  # type: ignore[arg-type]
    second = plan_entity_reminder(now=datetime(2026, 9, 18, 13, 0, tzinfo=UTC), **kwargs)  # type: ignore[arg-type]
    assert first is not None and second is not None
    assert first.dedup_key == second.dedup_key


def test_disabled_task_reminders_produce_nothing() -> None:
    plan = plan_entity_reminder(
        kind=NotificationKind.TASK_REMINDER.value,
        user_id=USER,
        entity_id=ENTITY,
        title="Pay rent",
        moment=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        prefs=prefs(task_reminders=False),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
    )
    assert plan is None


def test_habit_reminder_is_planned_for_its_local_hour() -> None:
    plan = plan_habit_reminder(
        user_id=USER,
        habit_id=ENTITY,
        title="Gym",
        reminder_hour=19,
        prefs=prefs(),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        already_logged=False,
    )
    assert plan is not None
    assert plan.run_at == datetime(2026, 9, 18, 17, 0, tzinfo=UTC)


def test_completed_habit_gets_no_reminder() -> None:
    plan = plan_habit_reminder(
        user_id=USER,
        habit_id=ENTITY,
        title="Gym",
        reminder_hour=19,
        prefs=prefs(),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        already_logged=True,
    )
    assert plan is None


def test_habit_hour_already_passed_today_is_skipped() -> None:
    plan = plan_habit_reminder(
        user_id=USER,
        habit_id=ENTITY,
        title="Gym",
        reminder_hour=8,
        prefs=prefs(),
        now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        already_logged=False,
    )
    assert plan is None


def test_habit_schedule_limits_weekdays() -> None:
    friday = date(2026, 9, 18)
    assert habit_runs_on(None, friday) is True
    assert habit_runs_on({}, friday) is True
    assert habit_runs_on({"weekdays": [4]}, friday) is True
    assert habit_runs_on({"weekdays": [0, 2]}, friday) is False
    assert habit_runs_on({"weekdays": ["4"]}, friday) is True
    assert habit_runs_on({"weekdays": "friday"}, friday) is True


def test_budget_warning_at_the_user_threshold() -> None:
    plan = plan_budget_warning(
        user_id=USER,
        prefs=prefs(),
        spent_minor=82_000,
        limit_minor=100_000,
        currency="PLN",
        period_key="2026-09",
        now=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )
    assert plan is not None
    assert plan.payload["threshold"] == 80
    assert plan.dedup_key.endswith("2026-09:80")


def test_budget_warning_at_full_limit_uses_its_own_key() -> None:
    plan = plan_budget_warning(
        user_id=USER,
        prefs=prefs(),
        spent_minor=101_000,
        limit_minor=100_000,
        currency="PLN",
        period_key="2026-09",
        now=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )
    assert plan is not None
    assert plan.payload["threshold"] == 100
    assert plan.dedup_key.endswith("2026-09:100")


def test_budget_below_threshold_is_silent() -> None:
    plan = plan_budget_warning(
        user_id=USER,
        prefs=prefs(),
        spent_minor=50_000,
        limit_minor=100_000,
        currency="PLN",
        period_key="2026-09",
        now=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )
    assert plan is None


def test_budget_without_a_limit_is_silent() -> None:
    plan = plan_budget_warning(
        user_id=USER,
        prefs=prefs(),
        spent_minor=50_000,
        limit_minor=None,
        currency="PLN",
        period_key="2026-09",
        now=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )
    assert plan is None


def test_local_month_bounds_cover_the_users_month() -> None:
    period, start, end = local_month_bounds(datetime(2026, 9, 18, 12, 0, tzinfo=UTC), TZ)
    assert period == "2026-09"
    assert start == datetime(2026, 8, 31, 22, 0, tzinfo=UTC)
    assert end == datetime(2026, 9, 30, 22, 0, tzinfo=UTC)
    assert end - start > timedelta(days=29)


def test_december_rolls_into_the_next_year() -> None:
    period, _, end = local_month_bounds(datetime(2026, 12, 15, 12, 0, tzinfo=UTC), TZ)
    assert period == "2026-12"
    assert end == datetime(2026, 12, 31, 23, 0, tzinfo=UTC)


def test_rendering_uses_the_user_locale_and_never_leaks_placeholders() -> None:
    payload = {
        "title": "Pay rent",
        "moment": "2026-09-18T15:00:00+00:00",
        "timezone": TZ,
    }
    english = render_notification("en", NotificationKind.TASK_REMINDER.value, payload)
    russian = render_notification("ru", NotificationKind.TASK_REMINDER.value, payload)
    assert english == "Task due at 17:00: Pay rent"
    assert russian == "Задача к 17:00: Pay rent"
    assert "{" not in english and "{" not in russian


def test_unknown_locale_falls_back_to_english() -> None:
    text = render_notification(
        "de", NotificationKind.HABIT_REMINDER.value, {"title": "Gym"}
    )
    assert text == "Habit not done yet today: Gym"


def test_digest_rendering_includes_every_counter() -> None:
    text = render_notification(
        "en",
        NotificationKind.MORNING_DIGEST.value,
        {
            "local_date": "2026-09-18",
            "tasks": 3,
            "events": 1,
            "habits": 2,
            "budget_left_minor": 45_000,
            "currency": "PLN",
        },
    )
    assert "Tasks due today: 3" in text
    assert "Events: 1" in text
    assert "Habits left: 2" in text
    assert "450.00 PLN" in text


def test_missing_digest_payload_renders_neutral_values() -> None:
    text = render_notification("en", NotificationKind.MORNING_DIGEST.value, {})
    assert "Tasks due today: 0" in text
    assert "Budget left: -" in text


def test_budget_rendering_shows_amounts_and_percent() -> None:
    text = render_notification(
        "en",
        NotificationKind.BUDGET_WARNING.value,
        {
            "percent": 82,
            "period": "2026-09",
            "spent_minor": 82_000,
            "limit_minor": 100_000,
            "currency": "PLN",
        },
    )
    assert "82%" in text
    assert "820.00 PLN of 1000.00 PLN" in text


def test_money_formatting_handles_zero_and_negative_values() -> None:
    assert format_money(0, "PLN") == "0.00 PLN"
    assert format_money(-1250, "EUR") == "-12.50 EUR"
    assert format_money(None, "PLN") == "-"
