"""Access token and refresh token behaviour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from onedrop.auth.tokens import (
    ALGORITHM,
    ISSUER,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from onedrop.config import get_settings
from onedrop.errors import AuthError


def test_access_token_round_trip() -> None:
    user_id, session_id = uuid4(), uuid4()
    token, ttl = create_access_token(user_id, session_id)
    payload = decode_access_token(token)
    assert payload.user_id == user_id
    assert payload.session_id == session_id
    assert ttl == get_settings().access_token_ttl_seconds
    assert payload.expires_at > datetime.now(tz=UTC)


def test_expired_access_token_raises() -> None:
    settings = get_settings()
    issued = datetime.now(tz=UTC) - timedelta(hours=2)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "iss": ISSUER,
            "iat": int(issued.timestamp()),
            "exp": int((issued + timedelta(minutes=15)).timestamp()),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(AuthError, match="expired"):
        decode_access_token(token)


def test_token_signed_with_other_key_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "iss": ISSUER,
            "exp": int((datetime.now(tz=UTC) + timedelta(minutes=5)).timestamp()),
        },
        "a-completely-different-signing-key",
        algorithm=ALGORITHM,
    )
    with pytest.raises(AuthError):
        decode_access_token(token)


def test_refresh_token_is_only_stored_as_hash() -> None:
    token = generate_refresh_token()
    digest = hash_refresh_token(token)
    assert len(token) >= 40
    assert len(digest) == 64
    assert digest != token
    assert hash_refresh_token(token) == digest
