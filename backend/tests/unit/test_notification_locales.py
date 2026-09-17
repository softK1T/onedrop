"""Every locale covers every notification kind with usable text."""

from __future__ import annotations

from typing import Any

from onedrop.reminders.messages import (
    SUPPORTED_LOCALES,
    TEMPLATES,
    render_notification,
)
from onedrop.reminders.models import NotificationKind, kinds

TZ = "Europe/Warsaw"

PAYLOADS: dict[str, dict[str, Any]] = {
    NotificationKind.MORNING_DIGEST.value: {
        "local_date": "2026-09-18",
        "tasks": 2,
        "events": 1,
        "habits": 3,
        "budget_left_minor": 12_345,
        "currency": "PLN",
    },
    NotificationKind.TASK_REMINDER.value: {
        "title": "Pay rent",
        "moment": "2026-09-18T15:00:00+00:00",
        "timezone": TZ,
    },
    NotificationKind.EVENT_REMINDER.value: {
        "title": "Dentist",
        "moment": "2026-09-18T15:00:00+00:00",
        "timezone": TZ,
    },
    NotificationKind.HABIT_REMINDER.value: {"title": "Gym"},
    NotificationKind.BUDGET_WARNING.value: {
        "percent": 95,
        "period": "2026-09",
        "spent_minor": 95_000,
        "limit_minor": 100_000,
        "currency": "PLN",
    },
}


def test_locale_set_matches_the_mini_app() -> None:
    assert SUPPORTED_LOCALES == ("en", "ru", "pl", "uk")


def test_every_locale_defines_every_kind() -> None:
    for locale in SUPPORTED_LOCALES:
        assert set(TEMPLATES[locale]) == set(kinds()), locale


def test_every_locale_renders_without_raw_keys() -> None:
    for locale in SUPPORTED_LOCALES:
        for kind, payload in PAYLOADS.items():
            text = render_notification(locale, kind, payload)
            assert text.strip()
            assert "{" not in text
            assert "}" not in text


def test_ukrainian_reminders_use_ukrainian_wording() -> None:
    text = render_notification(
        "uk",
        NotificationKind.TASK_REMINDER.value,
        PAYLOADS[NotificationKind.TASK_REMINDER.value],
    )
    assert text == "Завдання до 17:00: Pay rent"


def test_locale_with_region_suffix_is_accepted() -> None:
    text = render_notification(
        "uk-UA",
        NotificationKind.HABIT_REMINDER.value,
        PAYLOADS[NotificationKind.HABIT_REMINDER.value],
    )
    assert text == "Звичка ще не відмічена сьогодні: Gym"
