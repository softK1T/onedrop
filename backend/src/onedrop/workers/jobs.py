"""Background jobs. Heavy work never runs inside a webhook request."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select, update

from onedrop.bot.notifier import notify_capture_result, notify_reminder
from onedrop.capture.media_service import MediaCaptureService
from onedrop.capture.service import CaptureService
from onedrop.config import get_settings
from onedrop.db.models.enums import EntityType, ReminderStatus
from onedrop.db.models.health import Habit
from onedrop.db.models.planner import Event, Task
from onedrop.db.models.reminders import Reminder
from onedrop.db.models.user import User, UserSettings
from onedrop.db.session import get_sessionmaker
from onedrop.errors import AppError
from onedrop.logging import get_logger
from onedrop.queue import DEAD_LETTER_KEY
from onedrop.storage import ObjectStorage

logger = get_logger(__name__)

MAX_REMINDER_BATCH = 200
TITLE_BY_ENTITY = {
    EntityType.TASK.value: Task,
    EntityType.EVENT.value: Event,
    EntityType.HABIT.value: Habit,
}


async def _dead_letter(function: str, payload: dict[str, Any], reason: str) -> None:
    """Park a permanently failed job so it is visible instead of lost."""
    client = Redis.from_url(get_settings().redis_url)
    try:
        await client.rpush(
            DEAD_LETTER_KEY,
            json.dumps(
                {
                    "function": function,
                    "payload": payload,
                    "reason": reason,
                    "at": datetime.now(tz=UTC).isoformat(),
                }
            ),
        )
    finally:
        await client.aclose()


async def process_capture(ctx: dict[str, Any], inbox_item_id: str) -> str:
    """Parse a text capture, write records, then update the chat message."""
    maker = get_sessionmaker()
    async with maker() as session:
        service = CaptureService(session)
        try:
            outcome = await service.process(UUID(inbox_item_id))
        except AppError as exc:
            if ctx.get("job_try", 1) >= int(ctx.get("max_tries", 3)):
                await _dead_letter(
                    "process_capture", {"inbox_item_id": inbox_item_id}, exc.code
                )
                await notify_capture_result(UUID(inbox_item_id))
            raise
    await notify_capture_result(UUID(inbox_item_id))
    logger.info(
        "worker.capture_processed",
        inbox_item_id=inbox_item_id,
        status=outcome.status,
        created=len(outcome.created),
    )
    return outcome.status


async def process_voice_capture(ctx: dict[str, Any], inbox_item_id: str) -> str:
    """Transcribe a voice capture, then parse the transcript."""
    maker = get_sessionmaker()
    async with maker() as session:
        service = MediaCaptureService(session)
        try:
            outcome = await service.process_voice(UUID(inbox_item_id))
        except AppError as exc:
            if ctx.get("job_try", 1) >= int(ctx.get("max_tries", 3)):
                await _dead_letter(
                    "process_voice_capture", {"inbox_item_id": inbox_item_id}, exc.code
                )
                await notify_capture_result(UUID(inbox_item_id))
            raise
    await notify_capture_result(UUID(inbox_item_id))
    return outcome.status


async def process_image_capture(ctx: dict[str, Any], inbox_item_id: str) -> str:
    """Estimate a meal from a photo and store it as an approximate record."""
    maker = get_sessionmaker()
    async with maker() as session:
        service = MediaCaptureService(session)
        try:
            outcome = await service.process_image(UUID(inbox_item_id))
        except AppError as exc:
            if ctx.get("job_try", 1) >= int(ctx.get("max_tries", 3)):
                await _dead_letter(
                    "process_image_capture", {"inbox_item_id": inbox_item_id}, exc.code
                )
            await notify_capture_result(UUID(inbox_item_id))
            raise
    await notify_capture_result(UUID(inbox_item_id))
    return outcome.status


async def _entity_title(session: Any, reminder: Reminder) -> str:
    """Human title for the reminded entity, or a neutral fallback."""
    model = TITLE_BY_ENTITY.get(reminder.entity_type or "")
    if model is None or reminder.entity_id is None:
        return str((reminder.payload or {}).get("title", "OneDrop"))
    column = model.name if model is Habit else model.title
    stmt = select(column).where(model.id == reminder.entity_id)
    result = await session.execute(stmt)
    title = result.scalar_one_or_none()
    return str(title) if title else "OneDrop"


async def dispatch_due_reminders(ctx: dict[str, Any]) -> int:
    """Claim due reminders and send them.

    Claiming flips the status inside the same transaction before anything is
    sent, so a restart or a second scheduler cannot deliver the same reminder
    twice. A failed send is logged and left as `sent`: at-most-once delivery is
    the deliberate trade-off.
    """
    maker = get_sessionmaker()
    claimed: list[tuple[int, str, str, str, datetime, str]] = []

    async with maker() as session:
        stmt = (
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.SCHEDULED.value,
                Reminder.scheduled_at <= datetime.now(tz=UTC),
            )
            .order_by(Reminder.scheduled_at)
            .limit(MAX_REMINDER_BATCH)
            .with_for_update(skip_locked=True)
        )
        due = list((await session.execute(stmt)).scalars().all())
        for reminder in due:
            user = (
                await session.execute(select(User).where(User.id == reminder.user_id))
            ).scalar_one_or_none()
            settings_row = (
                await session.execute(
                    select(UserSettings).where(UserSettings.user_id == reminder.user_id)
                )
            ).scalar_one_or_none()
            if user is None or settings_row is None or not settings_row.reminders_enabled:
                await session.execute(
                    update(Reminder)
                    .where(Reminder.id == reminder.id)
                    .values(status=ReminderStatus.CANCELLED.value)
                )
                continue
            title = await _entity_title(session, reminder)
            claimed.append(
                (
                    user.telegram_user_id,
                    user.locale,
                    reminder.kind,
                    title,
                    reminder.scheduled_at,
                    settings_row.timezone,
                )
            )
            await session.execute(
                update(Reminder)
                .where(Reminder.id == reminder.id)
                .values(
                    status=ReminderStatus.SENT.value,
                    sent_at=datetime.now(tz=UTC),
                    attempts=Reminder.__table__.c.attempts + 1,
                )
            )
        await session.commit()

    sent = 0
    for telegram_user_id, locale, kind, title, scheduled_at, timezone in claimed:
        delivered = await notify_reminder(
            telegram_user_id=telegram_user_id,
            locale=locale,
            kind=kind,
            title=title,
            scheduled_at=scheduled_at,
            timezone=timezone,
        )
        sent += 1 if delivered else 0
    if claimed:
        logger.info("worker.reminders_dispatched", claimed=len(claimed), sent=sent)
    return sent


async def cleanup_media(ctx: dict[str, Any]) -> int:
    """Delete stored media older than the configured retention window."""
    settings = get_settings()
    cutoff = datetime.now(tz=UTC) - timedelta(days=settings.media_retention_days)
    deleted = await ObjectStorage(settings).delete_older_than(cutoff)
    logger.info(
        "worker.media_cleanup", deleted=deleted, retention_days=settings.media_retention_days
    )
    return deleted
