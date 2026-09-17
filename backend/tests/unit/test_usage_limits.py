"""Free bonus, daily limit and Pro monthly limit arithmetic."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from onedrop.billing.plans import (
    daily_period_key,
    evaluate_quota,
    limits_for,
    monthly_period_key,
    period_key_for,
)
from onedrop.config import get_settings

SETTINGS = get_settings()
NOW = datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo("Europe/Warsaw"))


def test_free_plan_starts_with_onboarding_bonus() -> None:
    limits = limits_for("free", SETTINGS)
    state = evaluate_quota(limits=limits, bonus_used=0, period_used=0)
    assert state.bonus_limit == SETTINGS.free_onboarding_bonus
    assert state.bonus_remaining == SETTINGS.free_onboarding_bonus
    assert state.next_scope == "bonus"
    assert state.allowed is True


def test_free_plan_falls_back_to_daily_limit() -> None:
    limits = limits_for("free", SETTINGS)
    state = evaluate_quota(
        limits=limits, bonus_used=SETTINGS.free_onboarding_bonus, period_used=0
    )
    assert state.bonus_remaining == 0
    assert state.period_remaining == SETTINGS.free_daily_ai_limit
    assert state.next_scope == "daily"


def test_free_plan_blocks_when_bonus_and_day_are_exhausted() -> None:
    limits = limits_for("free", SETTINGS)
    state = evaluate_quota(
        limits=limits,
        bonus_used=SETTINGS.free_onboarding_bonus,
        period_used=SETTINGS.free_daily_ai_limit,
    )
    assert state.remaining == 0
    assert state.allowed is False


def test_pro_plan_uses_monthly_limit_and_no_bonus() -> None:
    limits = limits_for("pro", SETTINGS)
    state = evaluate_quota(limits=limits, bonus_used=0, period_used=10)
    assert limits.period_scope == "monthly"
    assert state.bonus_limit == 0
    assert state.period_remaining == SETTINGS.pro_monthly_ai_limit - 10
    assert state.next_scope == "monthly"


def test_pro_plan_unlocks_paid_features() -> None:
    free = limits_for("free", SETTINGS)
    pro = limits_for("pro", SETTINGS)
    assert free.photo_recognition is False
    assert free.morning_digest is False
    assert free.csv_export is False
    assert pro.photo_recognition is True
    assert pro.morning_digest is True
    assert pro.csv_export is True
    assert pro.history_days > free.history_days


def test_period_keys_follow_local_time() -> None:
    assert daily_period_key(NOW) == "2026-09-17"
    assert monthly_period_key(NOW) == "2026-09"
    assert period_key_for(limits_for("free", SETTINGS), NOW) == "2026-09-17"
    assert period_key_for(limits_for("pro", SETTINGS), NOW) == "2026-09"


def test_negative_counters_never_produce_negative_remaining() -> None:
    limits = limits_for("free", SETTINGS)
    state = evaluate_quota(limits=limits, bonus_used=999, period_used=999)
    assert state.bonus_remaining == 0
    assert state.period_remaining == 0
    assert state.remaining == 0
