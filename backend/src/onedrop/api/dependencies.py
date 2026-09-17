"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.auth.tokens import decode_access_token
from onedrop.db.models.user import User, UserSettings
from onedrop.db.repositories.sessions import SessionRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import get_session
from onedrop.errors import AuthError, ForbiddenError

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve the caller from the bearer access token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Authorization header with a bearer token is required")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)

    auth_session = await SessionRepository(session).get_by_id(payload.session_id)
    if auth_session is None or auth_session.revoked_at is not None:
        raise AuthError("Session is no longer active")

    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise AuthError("User no longer exists")
    if user.is_blocked:
        raise ForbiddenError("This account is blocked")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_settings(session: DbSession, user: CurrentUser) -> UserSettings:
    """Settings row for the caller, created lazily if it is missing."""
    repo = UserRepository(session)
    row = await repo.get_settings(user.id)
    if row is None:
        row = await repo.update_settings(user.id, {})
        await session.commit()
    return row


CurrentSettings = Annotated[UserSettings, Depends(get_current_settings)]


async def get_user_agent(
    user_agent: Annotated[str | None, Header()] = None,
) -> str | None:
    return user_agent


UserAgent = Annotated[str | None, Depends(get_user_agent)]
