"""Persistence for canonical reminder schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.reminders import Reminder
from onedrop.reminders.models import require_aware

ACTIVE_ENTITY_CONSTRAINT = "uq_reminders_active_entity"


class ReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sync_entity(
        self,
        *,
        user_id: UUID,
        kind: str,
        entity_type: str,
        entity_id: UUID,
        scheduled_at: datetime | None,
        payload: dict[str, Any],
    ) -> Reminder | None:
        await self.cancel_entity(user_id=user_id, kind=kind, entity_id=entity_id)
        if scheduled_at is None:
            return None
        moment = require_aware(scheduled_at, "scheduled_at")
        key = f"{kind}:{user_id}:{entity_id}:{moment.isoformat()}"
        stmt = (
            pg_insert(Reminder)
            .values(
                user_id=user_id,
                kind=kind,
                entity_type=entity_type,
                entity_id=entity_id,
                scheduled_at=moment,
                payload=payload,
                idempotency_key=key,
                status="scheduled",
            )
            .on_conflict_do_nothing(index_elements=[Reminder.idempotency_key])
            .returning(Reminder.id)
        )
        reminder_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if reminder_id is None:
            return await self._session.scalar(
                select(Reminder).where(Reminder.idempotency_key == key)
            )
        return await self._session.get(Reminder, reminder_id)

    async def cancel_entity(self, *, user_id: UUID, kind: str, entity_id: UUID) -> int:
        stmt = (
            update(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.kind == kind,
                Reminder.entity_id == entity_id,
                Reminder.status == "scheduled",
            )
            .values(status="cancelled")
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)

    async def due_for_planning(
        self, *, user_id: UUID, now: datetime, horizon: datetime, limit: int = 200
    ) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.status == "scheduled",
                Reminder.scheduled_at > require_aware(now, "now"),
                Reminder.scheduled_at <= require_aware(horizon, "horizon"),
            )
            .order_by(Reminder.scheduled_at)
            .limit(max(limit, 1))
        )
        return list((await self._session.execute(stmt)).scalars().all())
