"""Refresh session persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.user import AuthSession


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> AuthSession:
        row = AuthSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=(user_agent or None) and user_agent[:256],
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_active(self, refresh_token_hash: str) -> AuthSession | None:
        stmt = select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(tz=UTC),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, session_id: UUID) -> AuthSession | None:
        stmt = select(AuthSession).where(AuthSession.id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, session_id: UUID) -> None:
        stmt = (
            update(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(tz=UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(tz=UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()
