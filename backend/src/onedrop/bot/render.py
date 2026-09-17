"""Rendering of bot messages. Pure string building, no I/O."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from onedrop.bot.texts import normalise_locale, t

ENTITY_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "task": "Task",
        "event": "Event",
        "expense": "Expense",
        "meal": "Meal",
        "habit": "Habit",
        "habit_log": "Habit check-in",
        "note": "Note",
    },
    "ru": {
        "task": "\u0417\u0430\u0434\u0430\u0447\u0430",
        "event": "\u0421\u043e\u0431\u044b\u0442\u0438\u0435",
        "expense": "\u0420\u0430\u0441\u0445\u043e\u0434",
        "meal": "\u041f\u0440\u0438\u0451\u043c \u043f\u0438\u0449\u0438",
        "habit": "\u041f\u0440\u0438\u0432\u044b\u0447\u043a\u0430",
        "habit_log": "\u041e\u0442\u043c\u0435\u0442\u043a\u0430 \u043f\u0440\u0438\u0432\u044b\u0447\u043a\u0438",
        "note": "\u0417\u0430\u043c\u0435\u0442\u043a\u0430",
    },
    "pl": {
        "task": "Zadanie",
        "event": "Wydarzenie",
        "expense": "Wydatek",
        "meal": "Posi\u0142ek",
        "habit": "Nawyk",
        "habit_log": "Wpis nawyku",
        "note": "Notatka",
    },
    "uk": {
        "task": "\u0417\u0430\u0432\u0434\u0430\u043d\u043d\u044f",
        "event": "\u041f\u043e\u0434\u0456\u044f",
        "expense": "\u0412\u0438\u0442\u0440\u0430\u0442\u0430",
        "meal": "\u041f\u0440\u0438\u0439\u043e\u043c \u0457\u0436\u0456",
        "habit": "\u0417\u0432\u0438\u0447\u043a\u0430",
        "habit_log": "\u0412\u0456\u0434\u043c\u0456\u0442\u043a\u0430 \u0437\u0432\u0438\u0447\u043a\u0438",
        "note": "\u041d\u043e\u0442\u0430\u0442\u043a\u0430",
    },
}


def entity_label(locale: str | None, entity_type: str) -> str:
    resolved = normalise_locale(locale)
    table = ENTITY_LABELS.get(resolved, ENTITY_LABELS["en"])
    return table.get(entity_type, entity_type)


def render_result(
    locale: str | None,
    created: Sequence[tuple[str, UUID]],
    *,
    remaining: int | None = None,
) -> str:
    """One short confirmation listing every created record as its own line."""
    if not created:
        return t(locale, "result_empty")
    lines = [t(locale, "result_header")]
    counts: dict[str, int] = {}
    for entity_type, _ in created:
        counts[entity_type] = counts.get(entity_type, 0) + 1
    for entity_type, count in counts.items():
        suffix = f" x{count}" if count > 1 else ""
        lines.append(f"\u2022 {entity_label(locale, entity_type)}{suffix}")
    if remaining is not None:
        lines.append(t(locale, "limit_left", remaining=remaining))
    return "\n".join(lines)


def render_clarification(locale: str | None, question: str | None) -> str:
    return t(locale, "needs_confirmation", question=question or "")


def render_error(locale: str | None) -> str:
    return t(locale, "error_generic")


def render_limit_reached(locale: str | None) -> str:
    return t(locale, "limit_reached")


def render_undo(locale: str | None, count: int) -> str:
    return t(locale, "undo_done", count=count)


def render_reminder(
    locale: str | None, *, kind: str, title: str, when_local: datetime | None = None
) -> str:
    """Reminder body. The scheduler passes an already localized moment."""
    label = entity_label(locale, kind if kind in ("task", "event", "habit") else "note")
    when = f" {when_local.strftime('%H:%M')}" if when_local is not None else ""
    return f"{label}{when}: {title}"


def render_digest(
    locale: str | None, *, tasks: Sequence[str], events: Sequence[str]
) -> str:
    """Morning digest: what is due today."""
    lines = [t(locale, "today_header")]
    for event in events:
        lines.append(f"\u25e6 {event}")
    for task in tasks:
        lines.append(f"\u2022 {task}")
    if len(lines) == 1:
        lines.append(t(locale, "today_empty"))
    return "\n".join(lines)
