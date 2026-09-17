"""Telegram webhook secret token validation."""

from __future__ import annotations

from onedrop.capture.telegram_intake import (
    TELEGRAM_SECRET_HEADER,
    verify_webhook_secret,
)

EXPECTED = "webhook-secret-value-for-tests"


def test_matching_secret_is_accepted() -> None:
    assert verify_webhook_secret(EXPECTED, EXPECTED) is True


def test_wrong_secret_is_rejected() -> None:
    assert verify_webhook_secret("another-value", EXPECTED) is False


def test_missing_header_is_rejected() -> None:
    assert verify_webhook_secret(None, EXPECTED) is False
    assert verify_webhook_secret("", EXPECTED) is False


def test_unconfigured_secret_rejects_everything() -> None:
    assert verify_webhook_secret(EXPECTED, "") is False
    assert verify_webhook_secret(None, "") is False


def test_header_name_matches_telegram_contract() -> None:
    assert TELEGRAM_SECRET_HEADER == "X-Telegram-Bot-Api-Secret-Token"
