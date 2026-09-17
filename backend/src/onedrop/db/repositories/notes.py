"""Note persistence with search and pinning."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.notes import Note

MAX_PAGE_SIZE = 100
MAX_SEARCH_LENGTH = 100


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, values: dict[str, Any]) -> Note:
        row = Note(user_id=user_id, **values)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, note_id: UUID, user_id: UUID) -> Note | None:
        stmt = select(Note).where(
            Note.id == note_id, Note.user_id == user_id, Note.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: UUID,
        *,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Note]:
        """Pinned notes first, then newest. Search is a parameterised ILIKE."""
        conditions: list[ColumnElement[bool]] = [
            Note.user_id == user_id,
            Note.deleted_at.is_(None),
        ]
        if search:
            pattern = f"%{search[:MAX_SEARCH_LENGTH]}%"
            conditions.append(
                or_(Note.title.ilike(pattern), Note.content.ilike(pattern))
            )
        stmt = (
            select(Note)
            .where(*conditions)
            .order_by(Note.pinned.desc(), Note.created_at.desc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def apply_changes(self, note: Note, changes: dict[str, Any]) -> Note:
        for field, value in changes.items():
            setattr(note, field, value)
        await self._session.flush()
        return note

    async def soft_delete(self, note: Note) -> None:
        note.deleted_at = datetime.now(tz=UTC)
        await self._session.flush()
