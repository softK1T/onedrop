"""Runtime settings used by the durable notification dispatcher."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from onedrop.config import Settings
from onedrop.reminders.dispatcher import runtime_options


def test_runtime_options_use_reminder_settings() -> None:
    settings = Settings(
        reminder_max_attempts=3,
        reminder_base_delay_seconds=15,
        reminder_max_delay_seconds=120,
        reminder_lock_timeout_seconds=45,
        reminder_claim_limit=7,
    )

    options = runtime_options(settings)

    assert options.policy.max_attempts == 3
    assert options.policy.base_delay_seconds == 15
    assert options.policy.max_delay_seconds == 120
    assert options.claim_limit == 7
    assert options.lock_timeout == timedelta(seconds=45)


def test_default_reminder_settings_are_valid() -> None:
    settings = Settings()

    assert settings.reminder_max_attempts >= 1
    assert settings.reminder_base_delay_seconds >= 1
    assert settings.reminder_max_delay_seconds >= settings.reminder_base_delay_seconds
    assert settings.reminder_lock_timeout_seconds >= 1
    assert settings.reminder_claim_limit >= 1


def test_max_retry_delay_cannot_be_below_the_base_delay() -> None:
    with pytest.raises(ValidationError):
        Settings(reminder_base_delay_seconds=120, reminder_max_delay_seconds=60)
