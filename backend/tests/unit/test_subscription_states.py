"""Subscription state resolution and period extension."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from onedrop.billing.subscriptions import next_expiry, resolve_state

NOW = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)


def test_no_subscription_means_free() -> None:
    state = resolve_state(plan=None, status=None, expires_at=None, now=NOW)
    assert state.plan == "free"


def test_active_pro_is_reported_as_pro() -> None:
    state = resolve_state(
        plan="pro",
        status="active",
        expires_at=NOW + timedelta(days=10),
        now=NOW,
    )
    assert state.plan == "pro"
    assert state.status == "active"


def test_expired_row_is_free_before_the_sweep_runs() -> None:
    state = resolve_state(
        plan="pro",
        status="active",
        expires_at=NOW - timedelta(minutes=1),
        now=NOW,
    )
    assert state.plan == "free"
    assert state.status == "expired"


def test_cancelled_subscription_is_free() -> None:
    state = resolve_state(
        plan="pro", status="cancelled", expires_at=NOW + timedelta(days=5), now=NOW
    )
    assert state.plan == "free"


def test_new_period_starts_from_now() -> None:
    assert next_expiry(current=None, now=NOW, period_days=30) == NOW + timedelta(days=30)


def test_active_period_is_extended_not_replaced() -> None:
    current = NOW + timedelta(days=5)
    assert next_expiry(current=current, now=NOW, period_days=30) == current + timedelta(
        days=30
    )


def test_expired_period_restarts_from_now() -> None:
    current = NOW - timedelta(days=5)
    assert next_expiry(current=current, now=NOW, period_days=30) == NOW + timedelta(
        days=30
    )


def test_period_is_at_least_one_day() -> None:
    assert next_expiry(current=None, now=NOW, period_days=0) == NOW + timedelta(days=1)
