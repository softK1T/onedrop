"""Durable notification scheduler process.

A small loop that survives restarts. On every tick it plans due notifications,
then delivers everything whose ``run_at`` has passed. Planning is idempotent by
dedup key and delivery claims rows with row-level locks, so an overlapping
second scheduler cannot send anything twice.

Run with: `python -m onedrop.workers.scheduler`
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from datetime import UTC, datetime

from onedrop.config import get_settings
from onedrop.db.session import dispose_engine
from onedrop.logging import configure_logging, get_logger
from onedrop.workers.jobs import cleanup_media
from onedrop.workers.notifications import deliver_notifications, plan_notifications

logger = get_logger(__name__)

TICK_SECONDS = 60
PLAN_INTERVAL_SECONDS = 300
CLEANUP_HOUR_UTC = 3


async def run_scheduler(stop: asyncio.Event) -> None:
    settings = get_settings()
    logger.info("scheduler.startup", tick_seconds=TICK_SECONDS, env=settings.app_env)
    last_cleanup_day: int | None = None
    last_plan: datetime | None = None

    while not stop.is_set():
        now = datetime.now(tz=UTC)
        try:
            if (
                last_plan is None
                or (now - last_plan).total_seconds() >= PLAN_INTERVAL_SECONDS
            ):
                await plan_notifications({})
                last_plan = now
            await deliver_notifications({})
            if now.hour == CLEANUP_HOUR_UTC and last_cleanup_day != now.day:
                await cleanup_media({})
                last_cleanup_day = now.day
        except Exception:
            logger.warning("scheduler.tick_failed", exc_info=True)

        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=TICK_SECONDS)

    await dispose_engine()
    logger.info("scheduler.shutdown")


def main() -> None:
    configure_logging()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    try:
        loop.run_until_complete(run_scheduler(stop))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
