"""Budget evaluation and month-over-month deltas."""

from __future__ import annotations

from onedrop.expenses.budget import (
    WARNING_THRESHOLD_PERCENT,
    delta_percent,
    evaluate_budget,
)


def test_no_budget_means_no_warning() -> None:
    status = evaluate_budget(currency="PLN", spent_minor=250_00, budget_minor=None)
    assert status.has_budget is False
    assert status.remaining_minor is None
    assert status.usage_percent is None
    assert status.warning is False
    assert status.exceeded is False


def test_spending_below_threshold_is_quiet() -> None:
    status = evaluate_budget(currency="PLN", spent_minor=100_00, budget_minor=1000_00)
    assert status.usage_percent == 10
    assert status.remaining_minor == 900_00
    assert status.warning is False


def test_warning_triggers_at_the_threshold() -> None:
    status = evaluate_budget(
        currency="PLN", spent_minor=800_00, budget_minor=1000_00
    )
    assert status.usage_percent == WARNING_THRESHOLD_PERCENT
    assert status.warning is True
    assert status.exceeded is False


def test_exceeded_budget_reports_negative_remaining() -> None:
    status = evaluate_budget(currency="pln", spent_minor=1200_00, budget_minor=1000_00)
    assert status.currency == "PLN"
    assert status.remaining_minor == -200_00
    assert status.usage_percent == 120
    assert status.exceeded is True
    assert status.warning is True


def test_negative_spending_is_clamped() -> None:
    status = evaluate_budget(currency="EUR", spent_minor=-500, budget_minor=100_00)
    assert status.spent_minor == 0
    assert status.usage_percent == 0


def test_zero_budget_is_treated_as_unset() -> None:
    status = evaluate_budget(currency="PLN", spent_minor=10_00, budget_minor=0)
    assert status.has_budget is False
    assert status.warning is False


def test_delta_percent_needs_a_baseline() -> None:
    assert delta_percent(500_00, 0) is None
    assert delta_percent(500_00, 400_00) == 25
    assert delta_percent(300_00, 400_00) == -25
