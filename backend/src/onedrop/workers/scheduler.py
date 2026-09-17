"""Reminder scheduler process.

A small loop that survives restarts: every tick it asks the database for due
reminders, and every reminder carries a unique idempotency key, so nothing is
sent twice even if two schedulers overlap.

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
from onedrop.workers.jobs import cleanup_media, dispatch_due_reminders

logger = get_logger(__name__)

TICK_SECONDS = 60
CLEANUP_HOUR_UTC = 3


async def run_scheduler(stop: asyncio.Event) -> None:
    settings = get_settings()
    logger.info("scheduler.startup", tick_seconds=TICK_SECONDS, env=settings.app_env)
    last_cleanup_day: int | None = None

    while not stop.is_set():
        now = datetime.now(tz=UTC)
        try:
            await dispatch_due_reminders({})
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
