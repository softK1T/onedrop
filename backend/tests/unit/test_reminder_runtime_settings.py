"""Runtime settings used by the durable notification dispatcher."""

from __future__ import annotations

from datetime import timedelta

from pytest import MonkeyPatch

from onedrop import config
from onedrop.config import get_settings
from onedrop.reminders.dispatcher import NotificationDispatcher


def test_dispatcher_uses_reminder_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("REMINDER_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("REMINDER_BASE_DELAY_SECONDS", "15")
    monkeypatch.setenv("REMINDER_MAX_DELAY_SECONDS", "120")
    monkeypatch.setenv("REMINDER_LOCK_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("REMINDER_CLAIM_LIMIT", "7")
    config.get_settings.cache_clear()
    try:
        dispatcher = NotificationDispatcher(sessionmaker=object())  # type: ignore[arg-type]
        assert dispatcher._policy.max_attempts == 3  # type: ignore[attr-defined]
        assert dispatcher._policy.base_delay_seconds == 15  # type: ignore[attr-defined]
        assert dispatcher._policy.max_delay_seconds == 120  # type: ignore[attr-defined]
        assert dispatcher._claim_limit == 7  # type: ignore[attr-defined]
        assert dispatcher._lock_timeout == timedelta(seconds=45)  # type: ignore[attr-defined]
    finally:
        config.get_settings.cache_clear()


def test_default_reminder_settings_are_valid() -> None:
    settings = get_settings()
    assert settings.reminder_max_attempts >= 1
    assert settings.reminder_base_delay_seconds >= 1
    assert settings.reminder_max_delay_seconds >= settings.reminder_base_delay_seconds
    assert settings.reminder_lock_timeout_seconds >= 1
    assert settings.reminder_claim_limit >= 1
