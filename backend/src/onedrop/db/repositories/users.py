"""User and settings persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.config import SUPPORTED_LOCALES, get_settings
from onedrop.db.models.user import User, UserSettings


class UserRepository:
    """Persistence for users and their settings row."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        stmt = select(User).where(
            User.telegram_user_id == telegram_user_id, User.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_settings(self, user_id: UUID) -> UserSettings | None:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        telegram_user_id: int,
        first_name: str | None = None,
        username: str | None = None,
        locale: str | None = None,
    ) -> User:
        settings = get_settings()
        user = User(
            telegram_user_id=telegram_user_id,
            first_name=first_name,
            username=username,
            locale=self._normalise_locale(locale),
        )
        self._session.add(user)
        await self._session.flush()
        self._session.add(
            UserSettings(
                user_id=user.id,
                timezone=settings.default_timezone,
                base_currency=settings.default_base_currency,
            )
        )
        await self._session.flush()
        return user

    async def upsert_from_telegram(
        self,
        *,
        telegram_user_id: int,
        first_name: str | None,
        username: str | None,
        language_code: str | None,
    ) -> User:
        """Create the user on first login, otherwise refresh profile fields."""
        existing = await self.get_by_telegram_id(telegram_user_id)
        if existing is None:
            return await self.create(
                telegram_user_id=telegram_user_id,
                first_name=first_name,
                username=username,
                locale=language_code,
            )
        if first_name and existing.first_name != first_name:
            existing.first_name = first_name
        if username and existing.username != username:
            existing.username = username
        if language_code:
            normalised = self._normalise_locale(language_code)
            if existing.locale != normalised:
                existing.locale = normalised
        await self._session.flush()
        return existing

    async def update_settings(self, user_id: UUID, changes: dict[str, object]) -> UserSettings:
        row = await self.get_settings(user_id)
        if row is None:
            row = UserSettings(user_id=user_id)
            self._session.add(row)
        for field, value in changes.items():
            if value is not None and hasattr(row, field):
                setattr(row, field, value)
        await self._session.flush()
        return row

    async def soft_delete(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)
        if user is not None:
            user.deleted_at = datetime.now(tz=UTC)
            await self._session.flush()

    @staticmethod
    def _normalise_locale(locale: str | None) -> str:
        settings = get_settings()
        if not locale:
            return settings.default_locale
        short = locale.split("-")[0].lower()
        return short if short in SUPPORTED_LOCALES else settings.default_locale
