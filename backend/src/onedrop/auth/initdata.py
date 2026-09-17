"""Server-side validation of Telegram Mini App init data.

The client value `initDataUnsafe` is never trusted. Only the signed `initData`
string is accepted, and only after the HMAC signature and `auth_date` checks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl

CLOCK_SKEW_TOLERANCE_SECONDS = 300


class InitDataError(ValueError):
    """Init data is missing, malformed, expired or has an invalid signature."""


@dataclass(frozen=True, slots=True)
class TelegramInitData:
    """Verified identity extracted from Telegram init data."""

    telegram_user_id: int
    first_name: str | None
    username: str | None
    language_code: str | None
    auth_date: datetime


def _data_check_string(fields: dict[str, str]) -> str:
    return "\n".join(f"{key}={fields[key]}" for key in sorted(fields))


def compute_signature(fields: dict[str, str], bot_token: str) -> str:
    """Compute the Telegram WebApp signature for already-parsed fields."""
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(
        secret_key, _data_check_string(fields).encode(), hashlib.sha256
    ).hexdigest()


def validate_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age_seconds: int,
    now: datetime | None = None,
) -> TelegramInitData:
    """Validate signature and freshness, then return the verified user."""
    if not bot_token:
        raise InitDataError("bot token is not configured")
    if not init_data:
        raise InitDataError("init data is empty")

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise InitDataError("init data has no hash")

    expected_hash = compute_signature(fields, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("init data signature mismatch")

    raw_auth_date = fields.get("auth_date", "")
    if not raw_auth_date.isdigit():
        raise InitDataError("init data has no valid auth_date")
    auth_date = datetime.fromtimestamp(int(raw_auth_date), tz=UTC)

    reference = now or datetime.now(tz=UTC)
    age_seconds = (reference - auth_date).total_seconds()
    if age_seconds > max_age_seconds:
        raise InitDataError("init data has expired")
    if age_seconds < -CLOCK_SKEW_TOLERANCE_SECONDS:
        raise InitDataError("init data auth_date is in the future")

    raw_user = fields.get("user")
    if not raw_user:
        raise InitDataError("init data has no user")
    try:
        user_payload = json.loads(raw_user)
    except json.JSONDecodeError as exc:
        raise InitDataError("init data user is not valid JSON") from exc
    if not isinstance(user_payload, dict):
        raise InitDataError("init data user is not an object")

    telegram_user_id = user_payload.get("id")
    if not isinstance(telegram_user_id, int):
        raise InitDataError("init data user has no numeric id")

    def _optional_str(key: str) -> str | None:
        value = user_payload.get(key)
        return value if isinstance(value, str) and value else None

    return TelegramInitData(
        telegram_user_id=telegram_user_id,
        first_name=_optional_str("first_name"),
        username=_optional_str("username"),
        language_code=_optional_str("language_code"),
        auth_date=auth_date,
    )
