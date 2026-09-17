"""Telegram init data validation: signature, tampering and expiry."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import pytest

from onedrop.auth.initdata import InitDataError, compute_signature, validate_init_data
from tests.conftest import TEST_BOT_TOKEN

MAX_AGE = 86_400


def build_init_data(
    *,
    bot_token: str = TEST_BOT_TOKEN,
    auth_date: datetime | None = None,
    telegram_user_id: int = 555_001,
    language_code: str = "ru",
) -> str:
    moment = auth_date or datetime.now(tz=UTC)
    fields = {
        "auth_date": str(int(moment.timestamp())),
        "query_id": "AAF_test_query",
        "user": json.dumps(
            {
                "id": telegram_user_id,
                "first_name": "Nazar",
                "username": "demo_user",
                "language_code": language_code,
            },
            separators=(",", ":"),
        ),
    }
    signed = dict(fields)
    signed["hash"] = compute_signature(fields, bot_token)
    return urlencode(signed)


def test_valid_init_data_is_accepted() -> None:
    verified = validate_init_data(
        build_init_data(), bot_token=TEST_BOT_TOKEN, max_age_seconds=MAX_AGE
    )
    assert verified.telegram_user_id == 555_001
    assert verified.first_name == "Nazar"
    assert verified.username == "demo_user"
    assert verified.language_code == "ru"


def test_tampered_payload_is_rejected() -> None:
    init_data = build_init_data().replace("555001", "999999")
    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token=TEST_BOT_TOKEN, max_age_seconds=MAX_AGE)


def test_wrong_bot_token_is_rejected() -> None:
    init_data = build_init_data(bot_token="999:another-token")
    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token=TEST_BOT_TOKEN, max_age_seconds=MAX_AGE)


def test_expired_init_data_is_rejected() -> None:
    stale = datetime.now(tz=UTC) - timedelta(seconds=MAX_AGE + 60)
    with pytest.raises(InitDataError, match="expired"):
        validate_init_data(
            build_init_data(auth_date=stale),
            bot_token=TEST_BOT_TOKEN,
            max_age_seconds=MAX_AGE,
        )


def test_future_auth_date_is_rejected() -> None:
    future = datetime.now(tz=UTC) + timedelta(hours=1)
    with pytest.raises(InitDataError):
        validate_init_data(
            build_init_data(auth_date=future),
            bot_token=TEST_BOT_TOKEN,
            max_age_seconds=MAX_AGE,
        )


def test_missing_hash_is_rejected() -> None:
    with pytest.raises(InitDataError, match="hash"):
        validate_init_data(
            "auth_date=1758000000&user=%7B%22id%22%3A1%7D",
            bot_token=TEST_BOT_TOKEN,
            max_age_seconds=MAX_AGE,
        )


def test_empty_bot_token_is_rejected() -> None:
    with pytest.raises(InitDataError, match="bot token"):
        validate_init_data(build_init_data(), bot_token="", max_age_seconds=MAX_AGE)
