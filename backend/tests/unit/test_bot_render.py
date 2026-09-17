"""Bot rendering: result cards, clarification, undo and reminders."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from onedrop.bot.render import (
    ENTITY_LABELS,
    entity_label,
    render_clarification,
    render_digest,
    render_reminder,
    render_result,
    render_undo,
)

TASK_ID = uuid4()
EVENT_ID = uuid4()
EXPENSE_ID = uuid4()


def test_all_locales_label_every_entity_type() -> None:
    reference = set(ENTITY_LABELS["en"])
    for locale, table in ENTITY_LABELS.items():
        assert set(table) == reference, locale


def test_result_lists_each_created_type() -> None:
    text = render_result(
        "ru",
        [("event", EVENT_ID), ("expense", EXPENSE_ID), ("task", TASK_ID)],
    )
    assert entity_label("ru", "event") in text
    assert entity_label("ru", "expense") in text
    assert entity_label("ru", "task") in text


def test_result_collapses_duplicates_with_a_count() -> None:
    text = render_result("en", [("task", uuid4()), ("task", uuid4())])
    assert "x2" in text


def test_result_can_show_remaining_quota() -> None:
    text = render_result("en", [("note", uuid4())], remaining=4)
    assert "4" in text


def test_empty_result_explains_that_nothing_was_saved() -> None:
    text = render_result("en", [])
    assert "could not find" in text.lower()


def test_clarification_includes_the_question() -> None:
    text = render_clarification("en", "Which currency?")
    assert "Which currency?" in text


def test_undo_includes_the_count() -> None:
    assert "3" in render_undo("ru", 3)


def test_reminder_shows_local_time_and_title() -> None:
    text = render_reminder(
        "en",
        kind="event",
        title="Dentist",
        when_local=datetime(2026, 9, 18, 9, 30, tzinfo=UTC),
    )
    assert "09:30" in text
    assert "Dentist" in text


def test_digest_falls_back_to_empty_copy() -> None:
    assert render_digest("en", tasks=[], events=[]).count("\n") == 1


def test_digest_lists_events_before_tasks() -> None:
    text = render_digest("en", tasks=["Pay internet"], events=["10:00 Standup"])
    assert text.index("Standup") < text.index("Pay internet")
