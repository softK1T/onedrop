"""Telegram Stars invoices.

Stars use `currency = XTR` and an empty provider token, so there is no payment
secret to store. The invoice payload carries the user id and the plan, and is
verified again in `pre_checkout_query`.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from onedrop.db.models.enums import Plan
from onedrop.errors import ForbiddenError, ValidationError

STARS_CURRENCY = "XTR"
PAYLOAD_PREFIX = "onedrop"
MAX_PAYLOAD_LENGTH = 128
NONCE_BYTES = 6


@dataclass(frozen=True, slots=True)
class InvoicePayload:
    """Parsed invoice payload."""

    plan: str
    user_id: UUID
    nonce: str

    def encode(self) -> str:
        return f"{PAYLOAD_PREFIX}:{self.plan}:{self.user_id}:{self.nonce}"[
            :MAX_PAYLOAD_LENGTH
        ]


def build_payload(user_id: UUID, plan: str = Plan.PRO.value) -> str:
    """Fresh payload for one invoice."""
    if plan not in {member.value for member in Plan}:
        raise ValidationError(f"unsupported plan: {plan}")
    nonce = secrets.token_hex(NONCE_BYTES)
    return InvoicePayload(plan=plan, user_id=user_id, nonce=nonce).encode()


def parse_payload(raw: str | None) -> InvoicePayload | None:
    """Parse a payload, returning None when it is not ours."""
    if not raw:
        return None
    parts = raw.split(":")
    if len(parts) != 4 or parts[0] != PAYLOAD_PREFIX:
        return None
    _, plan, raw_user_id, nonce = parts
    if plan not in {member.value for member in Plan}:
        return None
    try:
        user_id = UUID(raw_user_id)
    except ValueError:
        return None
    return InvoicePayload(plan=plan, user_id=user_id, nonce=nonce)


def validate_payload(raw: str | None, *, user_id: UUID) -> InvoicePayload:
    """Ensure the payload belongs to the paying user."""
    parsed = parse_payload(raw)
    if parsed is None:
        raise ValidationError("invoice payload is not recognised")
    if parsed.user_id != user_id:
        raise ForbiddenError("invoice payload belongs to another account")
    return parsed


def build_invoice_arguments(
    *, title: str, description: str, payload: str, amount_stars: int
) -> dict[str, Any]:
    """Arguments for `createInvoiceLink`. Provider token stays empty for Stars."""
    if amount_stars <= 0:
        raise ValidationError("Stars amount must be positive")
    return {
        "title": title[:32],
        "description": description[:255],
        "payload": payload,
        "provider_token": "",
        "currency": STARS_CURRENCY,
        "prices": [{"label": title[:32], "amount": amount_stars}],
    }
