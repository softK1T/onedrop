"""AI contract: discriminated union, strictness and confidence handling."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from onedrop.ai.schemas import (
    CaptureResult,
    ExpenseCreateIntent,
    capture_result_json_schema,
    parse_capture_result,
)

ACCEPTANCE_PAYLOAD: dict[str, Any] = {
    "language": "ru",
    "timezone": "Europe/Warsaw",
    "intents": [
        {
            "type": "event.create",
            "confidence": 0.94,
            "source_fragment": "Завтра в 15:00 встреча с Андреем",
            "fields": {"title": "Встреча с Андреем", "starts_at": "2026-09-18T15:00:00"},
        },
        {
            "type": "expense.create",
            "confidence": 0.97,
            "source_fragment": "потратил 45 злотых на такси",
            "fields": {
                "amount_minor": 4500,
                "currency": "PLN",
                "category": "transport",
                "merchant": None,
                "occurred_at": "2026-09-17T18:00:00",
            },
        },
        {
            "type": "task.create",
            "confidence": 0.9,
            "source_fragment": "нужно оплатить интернет",
            "fields": {"title": "Оплатить интернет", "due_at": "2026-09-17T21:00:00"},
        },
    ],
    "needs_confirmation": False,
    "clarification_question": None,
}


def test_multi_intent_payload_is_parsed() -> None:
    result = parse_capture_result(ACCEPTANCE_PAYLOAD)
    assert [intent.type for intent in result.intents] == [
        "event.create",
        "expense.create",
        "task.create",
    ]
    expense = result.intents[1]
    assert isinstance(expense, ExpenseCreateIntent)
    assert expense.fields.amount_minor == 4500
    assert expense.fields.currency == "PLN"
    assert expense.fields.category == "transport"


def test_unknown_field_is_rejected() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [
            {
                "type": "task.create",
                "confidence": 0.8,
                "source_fragment": "pay rent",
                "fields": {"title": "Pay rent", "sql": "DROP TABLE tasks"},
            }
        ],
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_unknown_intent_type_is_rejected() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [
            {"type": "invoice.create", "confidence": 0.9, "source_fragment": "x", "fields": {}}
        ],
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_unsupported_currency_is_rejected() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [
            {
                "type": "expense.create",
                "confidence": 0.9,
                "source_fragment": "spent 10 CHF",
                "fields": {"amount_minor": 1000, "currency": "CHF"},
            }
        ],
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_negative_amount_is_rejected() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [
            {
                "type": "expense.create",
                "confidence": 0.9,
                "source_fragment": "spent -5",
                "fields": {"amount_minor": -500, "currency": "PLN"},
            }
        ],
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_event_end_before_start_is_rejected() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [
            {
                "type": "event.create",
                "confidence": 0.9,
                "source_fragment": "meeting",
                "fields": {
                    "title": "Meeting",
                    "starts_at": "2026-09-18T15:00:00",
                    "ends_at": "2026-09-18T14:00:00",
                },
            }
        ],
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_needs_confirmation_requires_question() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [],
        "needs_confirmation": True,
        "clarification_question": None,
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_confidence_out_of_range_is_rejected() -> None:
    payload = {
        "language": "en",
        "timezone": "Europe/Warsaw",
        "intents": [
            {
                "type": "note.create",
                "confidence": 1.5,
                "source_fragment": "note",
                "fields": {"content": "remember this"},
            }
        ],
    }
    with pytest.raises(ValidationError):
        parse_capture_result(payload)


def test_actionable_intents_exclude_unknown() -> None:
    result = CaptureResult.model_validate(
        {
            "language": "en",
            "timezone": "Europe/Warsaw",
            "intents": [
                {
                    "type": "unknown",
                    "confidence": 0.2,
                    "source_fragment": "hello",
                    "fields": {"reason": "greeting"},
                }
            ],
        }
    )
    assert result.actionable_intents == []
    assert result.min_confidence() == 0.0


def test_json_schema_is_exposed_for_providers() -> None:
    schema = capture_result_json_schema()
    assert schema["title"] == "CaptureResult"
    assert "intents" in schema["properties"]
