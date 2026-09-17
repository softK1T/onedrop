"""Event persistence, scoped by user and free of soft-deleted rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.enums import EventStatus
from onedrop.db.models.planner import Event

MAX_PAGE_SIZE = 100
CONFLICT_SCAN_LIMIT = 200


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, values: dict[str, Any]) -> Event:
        row = Event(user_id=user_id, **values)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, event_id: UUID, user_id: UUID) -> Event | None:
        stmt = select(Event).where(
            Event.id == event_id, Event.user_id == user_id, Event.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_range(
        self,
        user_id: UUID,
        *,
        start: datetime,
        end: datetime,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(
                Event.user_id == user_id,
                Event.deleted_at.is_(None),
                Event.status != EventStatus.CANCELLED.value,
                Event.starts_at >= start,
                Event.starts_at < end,
            )
            .order_by(Event.starts_at.asc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def candidates_for_conflicts(
        self, user_id: UUID, *, start: datetime, end: datetime, exclude_id: UUID | None = None
    ) -> list[Event]:
        """Events that could overlap the given window."""
        conditions = [
            Event.user_id == user_id,
            Event.deleted_at.is_(None),
            Event.status != EventStatus.CANCELLED.value,
            Event.starts_at < end,
        ]
        if exclude_id is not None:
            conditions.append(Event.id != exclude_id)
        stmt = (
            select(Event)
            .where(*conditions)
            .order_by(Event.starts_at.desc())
            .limit(CONFLICT_SCAN_LIMIT)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        return [row for row in rows if (row.ends_at or row.starts_at) >= start]

    async def apply_changes(self, event: Event, changes: dict[str, Any]) -> Event:
        for field, value in changes.items():
            setattr(event, field, value)
        await self._session.flush()
        return event

    async def soft_delete(self, event: Event) -> None:
        event.deleted_at = datetime.now(tz=UTC)
        event.status = EventStatus.CANCELLED.value
        await self._session.flush()
