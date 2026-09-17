"""Stars invoice payloads and invoice arguments."""

from __future__ import annotations

from uuid import uuid4

import pytest

from onedrop.billing.stars import (
    MAX_PAYLOAD_LENGTH,
    STARS_CURRENCY,
    build_invoice_arguments,
    build_payload,
    parse_payload,
    validate_payload,
)
from onedrop.errors import ForbiddenError, ValidationError

USER_ID = uuid4()
OTHER_USER_ID = uuid4()


def test_payload_round_trip() -> None:
    raw = build_payload(USER_ID)
    parsed = parse_payload(raw)
    assert parsed is not None
    assert parsed.user_id == USER_ID
    assert parsed.plan == "pro"
    assert len(raw) <= MAX_PAYLOAD_LENGTH


def test_payloads_are_unique_per_invoice() -> None:
    assert build_payload(USER_ID) != build_payload(USER_ID)


def test_foreign_payload_is_rejected() -> None:
    assert parse_payload("someoneelse:pro:1:2") is None
    assert parse_payload(None) is None
    assert parse_payload("onedrop:pro:not-a-uuid:abc") is None
    assert parse_payload("onedrop:enterprise:" + str(USER_ID) + ":abc") is None


def test_validate_payload_requires_the_same_user() -> None:
    raw = build_payload(USER_ID)
    assert validate_payload(raw, user_id=USER_ID).user_id == USER_ID
    with pytest.raises(ForbiddenError):
        validate_payload(raw, user_id=OTHER_USER_ID)


def test_validate_payload_rejects_garbage() -> None:
    with pytest.raises(ValidationError):
        validate_payload("garbage", user_id=USER_ID)


def test_invoice_arguments_use_xtr_and_no_provider_token() -> None:
    arguments = build_invoice_arguments(
        title="OneDrop Pro", description="Pro plan", payload="p", amount_stars=250
    )
    assert arguments["currency"] == STARS_CURRENCY
    assert arguments["provider_token"] == ""
    assert arguments["prices"][0]["amount"] == 250


def test_invoice_requires_a_positive_amount() -> None:
    with pytest.raises(ValidationError):
        build_invoice_arguments(title="x", description="y", payload="p", amount_stars=0)


def test_unsupported_plan_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_payload(USER_ID, "lifetime")
