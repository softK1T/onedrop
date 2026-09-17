"""Timezone and datetime normalisation.

The model is not trusted with timezone maths. It returns local wall-clock values;
the backend attaches the user's IANA zone and converts everything to UTC.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from onedrop.ai.schemas import CaptureResult, Intent

MORNING_HOUR = 9
EVENING_HOUR = 19
END_OF_DAY_HOUR = 22


class TimezoneError(ValueError):
    """Raised when a timezone string is not a valid IANA identifier."""


def resolve_zone(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TimezoneError(f"unknown timezone: {timezone}") from exc


def local_now(timezone: str) -> datetime:
    return datetime.now(tz=resolve_zone(timezone))


def ensure_aware(value: datetime, timezone: str) -> datetime:
    """Attach the user's zone to a naive value; keep an explicit offset as is."""
    if value.tzinfo is None:
        return value.replace(tzinfo=resolve_zone(timezone))
    return value


def to_utc(value: datetime, timezone: str) -> datetime:
    return ensure_aware(value, timezone).astimezone(UTC)


def to_local(value: datetime, timezone: str) -> datetime:
    return ensure_aware(value, timezone).astimezone(resolve_zone(timezone))


def at_local_time(day: date, hour: int, timezone: str, minute: int = 0) -> datetime:
    """UTC instant for a local wall-clock time on a given day."""
    zone = resolve_zone(timezone)
    local = datetime.combine(day, time(hour=hour, minute=minute), tzinfo=zone)
    return local.astimezone(UTC)


def local_day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    """UTC half-open range [start, end) covering one local calendar day."""
    zone = resolve_zone(timezone)
    start_local = datetime.combine(day, time.min, tzinfo=zone)
    end_local = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def local_month_bounds(year: int, month: int, timezone: str) -> tuple[datetime, datetime]:
    """UTC half-open range covering one local calendar month."""
    zone = resolve_zone(timezone)
    start_local = datetime(year, month, 1, tzinfo=zone)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    end_local = datetime(next_year, next_month, 1, tzinfo=zone)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _convert_value(value: Any, timezone: str) -> Any:
    if isinstance(value, datetime):
        return to_utc(value, timezone)
    return value


def normalise_intent(intent: Intent, timezone: str) -> Intent:
    """Return a copy of the intent with every datetime field in UTC."""
    raw = intent.fields.model_dump()
    converted = {key: _convert_value(value, timezone) for key, value in raw.items()}
    fields_cls = type(intent.fields)
    return intent.model_copy(update={"fields": fields_cls.model_validate(converted)})


def normalise_capture_result(result: CaptureResult, *, timezone: str) -> CaptureResult:
    """Normalise every intent against the user's timezone, not the model's guess."""
    zone_name = timezone or result.timezone
    resolve_zone(zone_name)
    intents = [normalise_intent(intent, zone_name) for intent in result.intents]
    return result.model_copy(update={"timezone": zone_name, "intents": intents})
