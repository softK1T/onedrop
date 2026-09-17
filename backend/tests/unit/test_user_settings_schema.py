"""Validation of the settings payload, including reminder preferences."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from onedrop.users.schemas import UserSettingsUpdate


def test_reminder_preferences_are_accepted() -> None:
    payload = UserSettingsUpdate(
        quiet_hours_start=22,
        quiet_hours_end=7,
        task_reminder_lead_minutes=45,
        event_reminder_lead_minutes=90,
        budget_warning_threshold_percent=75,
    )

    assert payload.model_dump(exclude_unset=True) == {
        "quiet_hours_start": 22,
        "quiet_hours_end": 7,
        "task_reminder_lead_minutes": 45,
        "event_reminder_lead_minutes": 90,
        "budget_warning_threshold_percent": 75,
    }


def test_untouched_fields_stay_out_of_the_update() -> None:
    payload = UserSettingsUpdate(quiet_hours_start=23)

    assert payload.model_dump(exclude_unset=True) == {"quiet_hours_start": 23}


def test_equal_quiet_hours_are_allowed_and_mean_disabled() -> None:
    payload = UserSettingsUpdate(quiet_hours_start=0, quiet_hours_end=0)

    assert payload.quiet_hours_start == 0
    assert payload.quiet_hours_end == 0


@pytest.mark.parametrize(
    "field, value",
    [
        ("quiet_hours_start", 24),
        ("quiet_hours_start", -1),
        ("quiet_hours_end", 24),
        ("task_reminder_lead_minutes", 1441),
        ("task_reminder_lead_minutes", -5),
        ("event_reminder_lead_minutes", 1441),
        ("budget_warning_threshold_percent", 0),
        ("budget_warning_threshold_percent", 101),
        ("morning_digest_hour", 24),
    ],
)
def test_out_of_range_values_are_rejected(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        UserSettingsUpdate(**{field: value})


def test_unknown_fields_are_still_forbidden() -> None:
    with pytest.raises(ValidationError):
        UserSettingsUpdate(**{"quiet_hours": 22})


def test_currency_and_locale_stay_restricted() -> None:
    with pytest.raises(ValidationError):
        UserSettingsUpdate(base_currency="GBP")
    with pytest.raises(ValidationError):
        UserSettingsUpdate(locale="de")
