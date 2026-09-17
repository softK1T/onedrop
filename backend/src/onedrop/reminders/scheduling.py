"""Reminder scheduling helpers.

Every reminder carries a deterministic idempotency key, so rescheduling the same
moment for the same entity can never produce a second message.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.enums import ReminderKind, ReminderStatus
from onedrop.db.models.reminders import Reminder
from onedrop.logging import get_logger

logger = get_logger(__name__)


def reminder_key(kind: str, entity_id: UUID | str, moment: datetime) -> str:
    """Deterministic key: same entity + same minute = same reminder."""
    stamp = moment.astimezone(UTC).strftime("%Y%m%dT%H%M")
    return f"{kind}:{entity_id}:{stamp}"[:128]


def digest_key(kind: str, user_id: UUID, local_day: str) -> str:
    """Key for per-user daily notifications such as the morning digest."""
    return f"{kind}:{user_id}:{local_day}"[:128]


async def schedule_entity_reminder(
    session: AsyncSession,
    *,
    user_id: UUID,
    kind: str,
    entity_type: str,
    entity_id: UUID,
    scheduled_at: datetime,
    payload: dict[str, str] | None = None,
) -> bool:
    """Insert a reminder unless an identical one already exists."""
    if scheduled_at.tzinfo is None:
        raise ValueError("scheduled_at must be timezone-aware")
    stmt = (
        pg_insert(Reminder)
        .values(
            user_id=user_id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            scheduled_at=scheduled_at.astimezone(UTC),
            status=ReminderStatus.SCHEDULED.value,
            payload=payload,
            idempotency_key=reminder_key(kind, entity_id, scheduled_at),
        )
        .on_conflict_do_nothing(constraint="uq_reminders_idempotency_key")
        .returning(Reminder.id)
    )
    result = await session.execute(stmt)
    created = result.scalar_one_or_none() is not None
    await session.flush()
    return created


async def cancel_entity_reminders(
    session: AsyncSession, *, user_id: UUID, entity_type: str, entity_id: UUID
) -> int:
    """Cancel pending reminders for an entity that was completed or deleted."""
    stmt = (
        update(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
            Reminder.status == ReminderStatus.SCHEDULED.value,
        )
        .values(status=ReminderStatus.CANCELLED.value)
    )
    result = await session.execute(stmt)
    await session.flush()
    return int(result.rowcount or 0)


async def reschedule_entity_reminder(
    session: AsyncSession,
    *,
    user_id: UUID,
    kind: str,
    entity_type: str,
    entity_id: UUID,
    scheduled_at: datetime | None,
) -> None:
    """Replace pending reminders for an entity with a single new one."""
    await cancel_entity_reminders(
        session, user_id=user_id, entity_type=entity_type, entity_id=entity_id
    )
    if scheduled_at is not None and scheduled_at.astimezone(UTC) > datetime.now(tz=UTC):
        await schedule_entity_reminder(
            session,
            user_id=user_id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            scheduled_at=scheduled_at,
        )


KIND_BY_ENTITY: dict[str, str] = {
    "task": ReminderKind.TASK.value,
    "event": ReminderKind.EVENT.value,
    "habit": ReminderKind.HABIT.value,
}
