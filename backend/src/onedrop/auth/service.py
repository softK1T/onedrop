"""Authentication use cases: Telegram login, dev login, refresh, logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.auth.initdata import InitDataError, validate_init_data
from onedrop.auth.schemas import TokenPairResponse
from onedrop.auth.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from onedrop.config import get_settings
from onedrop.db.models.user import User
from onedrop.db.repositories.sessions import SessionRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import AuthError, ForbiddenError
from onedrop.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Application service owning the authentication transaction boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)

    async def login_with_init_data(
        self, init_data: str, *, user_agent: str | None = None
    ) -> TokenPairResponse:
        settings = get_settings()
        try:
            verified = validate_init_data(
                init_data,
                bot_token=settings.telegram_bot_token,
                max_age_seconds=settings.init_data_max_age_seconds,
            )
        except InitDataError as exc:
            logger.warning("auth.init_data_rejected", reason=str(exc))
            raise AuthError("Telegram init data is not valid") from exc

        user = await self._users.upsert_from_telegram(
            telegram_user_id=verified.telegram_user_id,
            first_name=verified.first_name,
            username=verified.username,
            language_code=verified.language_code,
        )
        return await self._issue_pair(user, user_agent=user_agent)

    async def dev_login(
        self,
        *,
        telegram_user_id: int,
        first_name: str | None = None,
        username: str | None = None,
        locale: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        """Development-only login. Callers must check `settings.dev_login_allowed`."""
        settings = get_settings()
        if not settings.dev_login_allowed:
            raise ForbiddenError("Dev login is disabled")
        user = await self._users.upsert_from_telegram(
            telegram_user_id=telegram_user_id,
            first_name=first_name or "Demo",
            username=username,
            language_code=locale,
        )
        logger.info("auth.dev_login", user_id=str(user.id))
        return await self._issue_pair(user, user_agent=user_agent)

    async def refresh(
        self, refresh_token: str, *, user_agent: str | None = None
    ) -> TokenPairResponse:
        """Rotate the session: the presented token is revoked, a new one issued."""
        existing = await self._sessions.get_active(hash_refresh_token(refresh_token))
        if existing is None:
            raise AuthError("Refresh token is invalid or expired")
        user = await self._users.get_by_id(existing.user_id)
        if user is None:
            raise AuthError("Session user no longer exists")
        await self._sessions.revoke(existing.id)
        return await self._issue_pair(user, user_agent=user_agent)

    async def logout(self, refresh_token: str) -> None:
        existing = await self._sessions.get_active(hash_refresh_token(refresh_token))
        if existing is not None:
            await self._sessions.revoke(existing.id)

    async def _issue_pair(
        self, user: User, *, user_agent: str | None
    ) -> TokenPairResponse:
        if user.is_blocked:
            raise ForbiddenError("This account is blocked")
        settings = get_settings()
        refresh_token = generate_refresh_token()
        expires_at = datetime.now(tz=UTC) + timedelta(
            seconds=settings.refresh_token_ttl_seconds
        )
        session_row = await self._sessions.create(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            user_agent=user_agent,
        )
        access_token, ttl = create_access_token(user.id, session_row.id)
        await self._session.commit()
        return TokenPairResponse(
            access_token=access_token, refresh_token=refresh_token, expires_in=ttl
        )
