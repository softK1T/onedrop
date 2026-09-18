"""Persistence for durable notification deliveries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.notifications import ScheduledNotification
from onedrop.reminders.models import DeliveryStatus, dedup_prefix, require_aware

DEDUP_CONSTRAINT = "uq_scheduled_notification_dedup_key"
DEFAULT_CLAIM_LIMIT = 25
DEFAULT_LOCK_TIMEOUT = timedelta(minutes=5)
MAX_ERROR_LENGTH = 2000


class ScheduledNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, *, user_id: UUID, kind: str, run_at: datetime, dedup_key: str, payload: dict[str, Any] | None = None, reminder_id: UUID | None = None) -> UUID | None:
        stmt = (
            pg_insert(ScheduledNotification)
            .values(user_id=user_id, reminder_id=reminder_id, kind=kind, run_at=require_aware(run_at, "run_at"), payload=payload or {}, status=DeliveryStatus.PENDING.value, dedup_key=dedup_key)
            .on_conflict_do_nothing(constraint=DEDUP_CONSTRAINT)
            .returning(ScheduledNotification.id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def get_by_dedup_key(self, dedup_key: str) -> ScheduledNotification | None:
        return await self._session.scalar(select(ScheduledNotification).where(ScheduledNotification.dedup_key == dedup_key))

    async def release_stale_locks(self, *, now: datetime, lock_timeout: timedelta = DEFAULT_LOCK_TIMEOUT) -> int:
        stmt = update(ScheduledNotification).where(ScheduledNotification.status == DeliveryStatus.PENDING.value, ScheduledNotification.locked_at.is_not(None), ScheduledNotification.locked_at < require_aware(now, "now") - lock_timeout).values(locked_at=None, locked_by=None)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)

    async def claim_due(self, *, worker_id: str, now: datetime, limit: int = DEFAULT_CLAIM_LIMIT, lock_timeout: timedelta = DEFAULT_LOCK_TIMEOUT) -> list[ScheduledNotification]:
        moment = require_aware(now, "now")
        ids = list((await self._session.execute(select(ScheduledNotification.id).where(ScheduledNotification.status == DeliveryStatus.PENDING.value, ScheduledNotification.run_at <= moment, or_(ScheduledNotification.locked_at.is_(None), ScheduledNotification.locked_at < moment - lock_timeout)).order_by(ScheduledNotification.run_at, ScheduledNotification.created_at).limit(max(limit, 1)).with_for_update(skip_locked=True))).scalars().all())
        if not ids:
            return []
        await self._session.execute(update(ScheduledNotification).where(ScheduledNotification.id.in_(ids)).values(locked_at=moment, locked_by=worker_id[:64]).execution_options(synchronize_session=False))
        await self._session.flush()
        return list((await self._session.execute(select(ScheduledNotification).where(ScheduledNotification.id.in_(ids)).order_by(ScheduledNotification.run_at, ScheduledNotification.created_at))).scalars().all())

    async def mark_sent(self, row: ScheduledNotification, *, now: datetime) -> None:
        require_aware(now, "now")
        row.status = DeliveryStatus.SENT.value
        row.attempts += 1
        row.last_error = None
        row.locked_at = None
        row.locked_by = None
        await self._session.flush()

    async def mark_retry(self, row: ScheduledNotification, *, error: str, retry_at: datetime) -> None:
        row.attempts += 1
        row.last_error = error[:MAX_ERROR_LENGTH]
        row.run_at = require_aware(retry_at, "retry_at")
        row.locked_at = None
        row.locked_by = None
        await self._session.flush()

    async def mark_failed(self, row: ScheduledNotification, *, error: str) -> None:
        row.status = DeliveryStatus.FAILED.value
        row.attempts += 1
        row.last_error = error[:MAX_ERROR_LENGTH]
        row.locked_at = None
        row.locked_by = None
        await self._session.flush()

    async def cancel_pending(self, *, kind: str, user_id: UUID, entity_id: UUID | str | None) -> int:
        prefix = dedup_prefix(kind, user_id, entity_id)
        stmt = update(ScheduledNotification).where(ScheduledNotification.user_id == user_id, ScheduledNotification.status == DeliveryStatus.PENDING.value, ScheduledNotification.dedup_key.startswith(prefix)).values(status=DeliveryStatus.CANCELLED.value, locked_at=None, locked_by=None)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)

    async def count_by_status(self, status: str, *, user_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(ScheduledNotification).where(ScheduledNotification.status == status)
        if user_id is not None:
            stmt = stmt.where(ScheduledNotification.user_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_for_user(self, user_id: UUID, *, status: str | None = None, limit: int = 50) -> list[ScheduledNotification]:
        stmt = select(ScheduledNotification).where(ScheduledNotification.user_id == user_id)
        if status is not None:
            stmt = stmt.where(ScheduledNotification.status == status)
        return list((await self._session.execute(stmt.order_by(ScheduledNotification.run_at.desc()).limit(max(limit, 1)))).scalars().all())
