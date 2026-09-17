"""Deterministic evaluation corpus for the fake provider.

The CI corpus never calls a real AI API. It protects the extraction contract
against regressions in rule parsing and covers every supported intent family.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from onedrop.ai.providers.base import CaptureContext
from onedrop.ai.providers.fake_rules import parse_text

FIXTURES = Path(__file__).parents[1] / "fixtures" / "ai_eval" / "cases.json"
CONTEXT = CaptureContext(
    timezone="Europe/Warsaw",
    locale="ru",
    base_currency="PLN",
    now_local=datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
)
CASES: list[dict[str, object]] = json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[str(case["id"]) for case in CASES])
def test_fake_provider_matches_eval_fixture(case: dict[str, object]) -> None:
    result = parse_text(str(case["text"]), CONTEXT)
    actual = [intent.type for intent in result.intents]
    expected = list(case["types"])
    for intent_type in expected:
        assert intent_type in actual
    assert result.needs_confirmation is bool(case.get("needs_confirmation", False))


def test_corpus_has_at_least_fifty_cases() -> None:
    assert len(CASES) >= 50


def test_corpus_covers_every_supported_intent() -> None:
    types = {item for case in CASES for item in case["types"]}
    assert {"task.create", "event.create", "expense.create", "meal.create", "note.create", "habit.create", "habit.log", "unknown"}.issubset(types)
