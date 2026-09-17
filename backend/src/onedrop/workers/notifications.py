"""Jobs that plan and deliver durable notifications.

Both jobs are safe to run on every tick and from several worker replicas: the
planner deduplicates by key, the dispatcher claims rows with row-level locks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from onedrop.db.session import get_sessionmaker
from onedrop.logging import get_logger
from onedrop.reminders.dispatcher import NotificationDispatcher
from onedrop.reminders.service import ReminderService

logger = get_logger(__name__)


async def plan_notifications(ctx: dict[str, Any]) -> int:
    """Queue every notification due within the planning horizon."""
    maker = get_sessionmaker()
    async with maker() as session:
        queued = await ReminderService(session).plan_for_all_users(
            now=datetime.now(tz=UTC)
        )
        await session.commit()
    return queued


async def deliver_notifications(ctx: dict[str, Any]) -> int:
    """Deliver claimed notifications, retrying failures with backoff."""
    report = await NotificationDispatcher().run_once()
    if report.failed:
        logger.warning("notifications.some_deliveries_failed", failed=report.failed)
    return report.sent
