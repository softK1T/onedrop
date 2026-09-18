"""Planning of canonical reminders into the internal delivery outbox."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.reminders import Reminder
from onedrop.reminders.models import require_aware
from onedrop.reminders.repository import ScheduledNotificationRepository

MAX_DUE_PER_PASS = 500


class CanonicalReminderPlanner:
    """The only bridge from user schedules to delivery attempts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = ScheduledNotificationRepository(session)

    async def plan_due(self, *, now: datetime) -> int:
        moment = require_aware(now, "now")
        rows = list((await self._session.execute(select(Reminder).where(Reminder.status == "scheduled", Reminder.scheduled_at <= moment).order_by(Reminder.scheduled_at).limit(MAX_DUE_PER_PASS).with_for_update(skip_locked=True))).scalars().all())
        queued = 0
        for reminder in rows:
            delivery_id = await self._outbox.enqueue(
                user_id=reminder.user_id,
                reminder_id=reminder.id,
                kind=reminder.kind,
                run_at=reminder.scheduled_at,
                dedup_key=reminder.idempotency_key,
                payload={**reminder.payload, "reminder_id": str(reminder.id)},
            )
            if delivery_id is not None:
                queued += 1
        return queued

    async def mark_sent(self, reminder_id: UUID, *, sent_at: datetime) -> None:
        reminder = await self._session.get(Reminder, reminder_id)
        if reminder is not None:
            reminder.status = "sent"
            reminder.sent_at = require_aware(sent_at, "sent_at")
            await self._session.flush()

    async def mark_failed(self, reminder_id: UUID) -> None:
        reminder = await self._session.get(Reminder, reminder_id)
        if reminder is not None:
            reminder.status = "failed"
            await self._session.flush()
