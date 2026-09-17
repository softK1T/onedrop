"""Background jobs. Heavy work never runs inside a webhook request."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select, update

from onedrop.capture.media_service import MediaCaptureService
from onedrop.capture.service import CaptureService
from onedrop.config import get_settings
from onedrop.db.models.enums import ReminderStatus
from onedrop.db.models.reminders import Reminder
from onedrop.db.session import get_sessionmaker
from onedrop.errors import AppError
from onedrop.logging import get_logger
from onedrop.queue import DEAD_LETTER_KEY
from onedrop.storage import ObjectStorage

logger = get_logger(__name__)

MAX_REMINDER_BATCH = 200


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
    """Parse a text capture and write records."""
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
            raise
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
            raise
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
            raise
        return outcome.status


async def dispatch_due_reminders(ctx: dict[str, Any]) -> int:
    """Claim due reminders and hand them to the notifier.

    Claiming flips the status inside the same transaction, so a restart or a
    second scheduler instance cannot send the same reminder twice.
    """
    maker = get_sessionmaker()
    sent = 0
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
        result = await session.execute(stmt)
        due = list(result.scalars().all())
        for reminder in due:
            await session.execute(
                update(Reminder)
                .where(Reminder.id == reminder.id)
                .values(
                    status=ReminderStatus.SENT.value,
                    sent_at=datetime.now(tz=UTC),
                    attempts=Reminder.__table__.c.attempts + 1,
                )
            )
            sent += 1
        await session.commit()
    if sent:
        logger.info("worker.reminders_dispatched", count=sent)
    return sent


async def cleanup_media(ctx: dict[str, Any]) -> int:
    """Delete stored media older than the configured retention window."""
    settings = get_settings()
    cutoff = datetime.now(tz=UTC) - timedelta(days=settings.media_retention_days)
    deleted = await ObjectStorage(settings).delete_older_than(cutoff)
    logger.info("worker.media_cleanup", deleted=deleted, retention_days=settings.media_retention_days)
    return deleted
