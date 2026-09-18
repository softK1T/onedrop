"""Jobs that plan and deliver durable notifications."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from onedrop.db.session import get_sessionmaker
from onedrop.logging import get_logger
from onedrop.reminders.dispatcher import NotificationDispatcher
from onedrop.reminders.outbox import CanonicalReminderPlanner
from onedrop.reminders.service import ReminderService

logger = get_logger(__name__)


async def plan_notifications(ctx: dict[str, Any]) -> int:
    maker = get_sessionmaker()
    async with maker() as session:
        now = datetime.now(tz=UTC)
        service = ReminderService(session)
        generated = await service.plan_for_all_users(now=now)
        due = await CanonicalReminderPlanner(session).plan_due(now=now)
        await session.commit()
    return generated + due


async def deliver_notifications(ctx: dict[str, Any]) -> int:
    report = await NotificationDispatcher().run_once()
    if report.failed:
        logger.warning("notifications.some_deliveries_failed", failed=report.failed)
    return report.sent
