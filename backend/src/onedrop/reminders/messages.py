"""Text of every outbound notification.

Templates are resolved by locale with an English fallback, and every template
placeholder is always supplied, so a missing payload field can never leak a raw
``{placeholder}`` into a user's chat. The locale set matches the Mini App:
en, ru, pl, uk.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from onedrop.reminders.models import NotificationKind

DEFAULT_LOCALE = "en"

TEMPLATES: dict[str, dict[str, str]] = {
    "en": {
        NotificationKind.MORNING_DIGEST.value: (
            "Good morning. Plan for {local_date}:\n"
            "Tasks due today: {tasks}\n"
            "Events: {events}\n"
            "Habits left: {habits}\n"
            "Budget left: {budget}"
        ),
        NotificationKind.TASK_REMINDER.value: "Task due at {when}: {title}",
        NotificationKind.EVENT_REMINDER.value: "Event at {when}: {title}",
        NotificationKind.HABIT_REMINDER.value: "Habit not done yet today: {title}",
        NotificationKind.BUDGET_WARNING.value: (
            "Budget warning: {percent}% of your {period} limit is spent "
            "({spent} of {limit})."
        ),
    },
    "ru": {
        NotificationKind.MORNING_DIGEST.value: (
            "Доброе утро. План на {local_date}:\n"
            "Задач на сегодня: {tasks}\n"
            "Событий: {events}\n"
            "Привычек осталось: {habits}\n"
            "Остаток бюджета: {budget}"
        ),
        NotificationKind.TASK_REMINDER.value: "Задача к {when}: {title}",
        NotificationKind.EVENT_REMINDER.value: "Событие в {when}: {title}",
        NotificationKind.HABIT_REMINDER.value: "Привычка ещё не отмечена сегодня: {title}",
        NotificationKind.BUDGET_WARNING.value: (
            "Внимание: израсходовано {percent}% лимита за {period} "
            "({spent} из {limit})."
        ),
    },
    "pl": {
        NotificationKind.MORNING_DIGEST.value: (
            "Dzień dobry. Plan na {local_date}:\n"
            "Zadania na dziś: {tasks}\n"
            "Wydarzenia: {events}\n"
            "Nawyki do zrobienia: {habits}\n"
            "Pozostały budżet: {budget}"
        ),
        NotificationKind.TASK_REMINDER.value: "Zadanie na {when}: {title}",
        NotificationKind.EVENT_REMINDER.value: "Wydarzenie o {when}: {title}",
        NotificationKind.HABIT_REMINDER.value: "Nawyk nie odnotowany dzisiaj: {title}",
        NotificationKind.BUDGET_WARNING.value: (
            "Uwaga: wykorzystano {percent}% limitu za {period} "
            "({spent} z {limit})."
        ),
    },
    "uk": {
        NotificationKind.MORNING_DIGEST.value: (
            "Доброго ранку. План на {local_date}:\n"
            "Завдань на сьогодні: {tasks}\n"
            "Подій: {events}\n"
            "Звичок залишилося: {habits}\n"
            "Залишок бюджету: {budget}"
        ),
        NotificationKind.TASK_REMINDER.value: "Завдання до {when}: {title}",
        NotificationKind.EVENT_REMINDER.value: "Подія о {when}: {title}",
        NotificationKind.HABIT_REMINDER.value: "Звичка ще не відмічена сьогодні: {title}",
        NotificationKind.BUDGET_WARNING.value: (
            "Увага: витрачено {percent}% ліміту за {period} "
            "({spent} з {limit})."
        ),
    },
}

SUPPORTED_LOCALES: tuple[str, ...] = tuple(TEMPLATES)
FALLBACK_TEMPLATE = "OneDrop: {title}"


def format_money(minor: int | None, currency: str) -> str:
    """Render a minor-unit amount as ``12.34 PLN``."""
    if minor is None:
        return "-"
    sign = "-" if minor < 0 else ""
    absolute = abs(int(minor))
    return f"{sign}{absolute // 100}.{absolute % 100:02d} {currency}"


def format_local_time(moment: str | None, timezone: str) -> str:
    """Render an ISO timestamp as local ``HH:MM``, or ``-`` when absent."""
    if not moment:
        return "-"
    try:
        parsed = datetime.fromisoformat(moment)
    except ValueError:
        return "-"
    if parsed.tzinfo is None:
        return "-"
    # An unknown timezone must never break delivery: fall back to the raw offset.
    try:
        zone = ZoneInfo(timezone)
    except (KeyError, ValueError):
        return parsed.strftime("%H:%M")
    return parsed.astimezone(zone).strftime("%H:%M")


def _values(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Complete placeholder set for one notification kind."""
    timezone = str(payload.get("timezone") or "UTC")
    currency = str(payload.get("currency") or "PLN")
    title = str(payload.get("title") or "OneDrop")
    if kind == NotificationKind.MORNING_DIGEST.value:
        return {
            "local_date": str(payload.get("local_date") or "-"),
            "tasks": int(payload.get("tasks") or 0),
            "events": int(payload.get("events") or 0),
            "habits": int(payload.get("habits") or 0),
            "budget": (
                format_money(payload.get("budget_left_minor"), currency)
                if payload.get("budget_left_minor") is not None
                else "-"
            ),
        }
    if kind == NotificationKind.BUDGET_WARNING.value:
        return {
            "percent": int(payload.get("percent") or 0),
            "period": str(payload.get("period") or "-"),
            "spent": format_money(payload.get("spent_minor"), currency),
            "limit": format_money(payload.get("limit_minor"), currency),
        }
    if kind == NotificationKind.HABIT_REMINDER.value:
        return {"title": title}
    return {"title": title, "when": format_local_time(payload.get("moment"), timezone)}


def render_notification(locale: str | None, kind: str, payload: Mapping[str, Any]) -> str:
    """Build the message body for one notification."""
    language = (locale or DEFAULT_LOCALE)[:2].lower()
    table = TEMPLATES.get(language, TEMPLATES[DEFAULT_LOCALE])
    template = table.get(kind) or TEMPLATES[DEFAULT_LOCALE].get(kind) or FALLBACK_TEMPLATE
    values = _values(kind, payload)
    if template is FALLBACK_TEMPLATE:
        values = {"title": str(payload.get("title") or "OneDrop")}
    return template.format(**values)
