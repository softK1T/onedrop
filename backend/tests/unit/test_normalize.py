"""Timezone normalisation of model output."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from onedrop.ai.normalize import (
    EVENING_HOUR,
    TimezoneError,
    at_local_time,
    local_day_bounds,
    local_month_bounds,
    normalise_capture_result,
    to_utc,
)
from onedrop.ai.schemas import EventCreateIntent, parse_capture_result


def test_naive_local_time_becomes_utc() -> None:
    value = datetime(2026, 9, 18, 15, 0)
    converted = to_utc(value, "Europe/Warsaw")
    assert converted.tzinfo == UTC
    assert converted.hour == 13


def test_explicit_offset_is_preserved() -> None:
    value = datetime.fromisoformat("2026-09-18T15:00:00+02:00")
    assert to_utc(value, "Europe/Kyiv").hour == 13


def test_unknown_timezone_raises() -> None:
    with pytest.raises(TimezoneError):
        to_utc(datetime(2026, 9, 18, 15, 0), "Mars/Olympus_Mons")


def test_local_day_bounds_are_utc_half_open() -> None:
    start, end = local_day_bounds(date(2026, 9, 18), "Europe/Warsaw")
    assert start == datetime(2026, 9, 17, 22, 0, tzinfo=UTC)
    assert end == datetime(2026, 9, 18, 22, 0, tzinfo=UTC)


def test_local_month_bounds_cross_year() -> None:
    start, end = local_month_bounds(2026, 12, "Europe/Warsaw")
    assert start == datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 12, 31, 23, 0, tzinfo=UTC)


def test_at_local_time_uses_wall_clock() -> None:
    moment = at_local_time(date(2026, 9, 17), EVENING_HOUR, "Europe/Warsaw")
    assert moment == datetime(2026, 9, 17, 17, 0, tzinfo=UTC)


def test_capture_result_intents_are_normalised() -> None:
    result = parse_capture_result(
        {
            "language": "ru",
            "timezone": "UTC",
            "intents": [
                {
                    "type": "event.create",
                    "confidence": 0.95,
                    "source_fragment": "завтра в 15:00",
                    "fields": {"title": "Встреча", "starts_at": "2026-09-18T15:00:00"},
                }
            ],
        }
    )
    normalised = normalise_capture_result(result, timezone="Europe/Warsaw")
    intent = normalised.intents[0]
    assert isinstance(intent, EventCreateIntent)
    assert normalised.timezone == "Europe/Warsaw"
    assert intent.fields.starts_at == datetime(2026, 9, 18, 13, 0, tzinfo=UTC)
