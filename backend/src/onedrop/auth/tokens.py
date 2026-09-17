"""Access token creation/verification and refresh token hashing."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from onedrop.config import get_settings
from onedrop.errors import AuthError

ALGORITHM = "HS256"
ISSUER = "onedrop"


@dataclass(frozen=True, slots=True)
class AccessTokenPayload:
    user_id: UUID
    session_id: UUID
    expires_at: datetime


def create_access_token(user_id: UUID, session_id: UUID) -> tuple[str, int]:
    """Return a signed short-lived access token and its lifetime in seconds."""
    settings = get_settings()
    ttl = settings.access_token_ttl_seconds
    issued_at = datetime.now(tz=UTC)
    claims = {
        "sub": str(user_id),
        "sid": str(session_id),
        "iss": ISSUER,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=ttl)).timestamp()),
    }
    token = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)
    return token, ttl


def decode_access_token(token: str) -> AccessTokenPayload:
    """Decode and verify an access token, raising AuthError when invalid."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "sub", "sid"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Access token is invalid") from exc

    try:
        user_id = UUID(str(claims["sub"]))
        session_id = UUID(str(claims["sid"]))
    except (KeyError, ValueError) as exc:
        raise AuthError("Access token payload is malformed") from exc

    return AccessTokenPayload(
        user_id=user_id,
        session_id=session_id,
        expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=UTC),
    )


def generate_refresh_token() -> str:
    """Opaque refresh token; only its hash is persisted."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
