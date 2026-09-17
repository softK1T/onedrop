"""Deterministic parser behaviour, including the acceptance sentence."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from onedrop.ai.providers.base import CaptureContext
from onedrop.ai.providers.fake import (
    FakeSpeechToTextProvider,
    FakeStructuredLLMProvider,
    FakeVisionProvider,
)
from onedrop.ai.providers.fake_rules import parse_text
from onedrop.ai.schemas import (
    EventCreateIntent,
    ExpenseCreateIntent,
    TaskCreateIntent,
)
from onedrop.errors import UnsupportedMediaError

TZ = "Europe/Warsaw"
NOW = datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo(TZ))
ACCEPTANCE_TEXT = (
    "\u0417\u0430\u0432\u0442\u0440\u0430 \u0432 15:00 \u0432\u0441\u0442\u0440\u0435\u0447\u0430 \u0441 "
    "\u0410\u043d\u0434\u0440\u0435\u0435\u043c, \u043f\u043e\u0442\u0440\u0430\u0442\u0438\u043b 45 "
    "\u0437\u043b\u043e\u0442\u044b\u0445 \u043d\u0430 \u0442\u0430\u043a\u0441\u0438 \u0438 "
    "\u043d\u0443\u0436\u043d\u043e \u043e\u043f\u043b\u0430\u0442\u0438\u0442\u044c "
    "\u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442"
)


def context(habits: tuple[str, ...] = ()) -> CaptureContext:
    return CaptureContext(
        timezone=TZ, locale="ru", base_currency="PLN", now_local=NOW, habits=habits
    )


def test_acceptance_sentence_yields_three_intents() -> None:
    result = parse_text(ACCEPTANCE_TEXT, context())
    types = [intent.type for intent in result.intents]
    assert types.count("event.create") == 1
    assert types.count("expense.create") == 1
    assert types.count("task.create") == 1
    assert result.needs_confirmation is False
    assert result.language == "ru"


def test_acceptance_expense_is_4500_pln_transport() -> None:
    result = parse_text(ACCEPTANCE_TEXT, context())
    expense = next(i for i in result.intents if isinstance(i, ExpenseCreateIntent))
    assert expense.fields.amount_minor == 4500
    assert expense.fields.currency == "PLN"
    assert expense.fields.category == "transport"
    assert "45" in expense.source_fragment


def test_acceptance_event_is_tomorrow_at_15() -> None:
    result = parse_text(ACCEPTANCE_TEXT, context())
    event = next(i for i in result.intents if isinstance(i, EventCreateIntent))
    assert event.fields.starts_at.date() == NOW.date().replace(day=18)
    assert event.fields.starts_at.hour == 15
    assert "\u0410\u043d\u0434\u0440\u0435" in event.fields.title


def test_acceptance_task_has_a_due_date_today() -> None:
    result = parse_text(ACCEPTANCE_TEXT, context())
    task = next(i for i in result.intents if isinstance(i, TaskCreateIntent))
    assert task.fields.title.lower().startswith("\u043e\u043f\u043b\u0430\u0442")
    assert task.fields.due_at is None or task.fields.due_at.date() == NOW.date()


def test_amount_without_currency_asks_instead_of_guessing() -> None:
    result = parse_text("\u043f\u043e\u0442\u0440\u0430\u0442\u0438\u043b 30 \u043d\u0430 \u043a\u043e\u0444\u0435", context())
    assert result.needs_confirmation is True
    assert result.clarification_question is not None
    assert all(intent.type != "expense.create" for intent in result.intents)


def test_english_expense_is_detected() -> None:
    result = parse_text("Spent 12 euro on lunch", context())
    expense = next(i for i in result.intents if isinstance(i, ExpenseCreateIntent))
    assert expense.fields.amount_minor == 1200
    assert expense.fields.currency == "EUR"
    assert expense.fields.category == "food"


def test_meal_text_is_marked_estimated() -> None:
    result = parse_text("\u0421\u044a\u0435\u043b \u043e\u0432\u0441\u044f\u043d\u043a\u0443 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430\u043a", context())
    meal = next(i for i in result.intents if i.type == "meal.create")
    assert meal.fields.estimated is True
    assert meal.fields.meal_type == "breakfast"


def test_habit_log_uses_known_habit_name() -> None:
    habits = ("\u0431\u0435\u0433",)
    result = parse_text("\u041f\u0440\u043e\u0431\u0435\u0436\u0430\u043b 5 \u043a\u043c", context(habits))
    log = next(i for i in result.intents if i.type == "habit.log")
    assert log.fields.value == 5


def test_note_is_created_for_note_prefix() -> None:
    result = parse_text("\u0417\u0430\u043c\u0435\u0442\u043a\u0430: \u043a\u0443\u043f\u0438\u0442\u044c \u043b\u0430\u043c\u043f\u0443", context())
    note = next(i for i in result.intents if i.type == "note.create")
    assert note.fields.content


def test_unrecognised_message_returns_unknown() -> None:
    result = parse_text("\u043f\u0440\u0438\u0432\u0435\u0442", context())
    assert [intent.type for intent in result.intents] == ["unknown"]


async def test_fake_provider_is_deterministic() -> None:
    provider = FakeStructuredLLMProvider()
    first = await provider.parse(ACCEPTANCE_TEXT, context())
    second = await provider.parse(ACCEPTANCE_TEXT, context())
    assert first.result.model_dump() == second.result.model_dump()
    assert first.usage.provider == "fake"
    assert first.usage.cost_micro == 0


async def test_fake_transcription_rejects_bad_mime() -> None:
    with pytest.raises(UnsupportedMediaError):
        await FakeSpeechToTextProvider().transcribe(b"data", "application/pdf")


async def test_fake_vision_marks_values_estimated() -> None:
    outcome = await FakeVisionProvider().analyze_meal(b"image-bytes", "image/jpeg", context())
    assert outcome.fields.estimated is True
    assert outcome.fields.calories is not None
    assert 0.0 <= outcome.confidence <= 1.0
