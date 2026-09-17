"""ARQ worker configuration.

Run with: `arq onedrop.workers.settings.WorkerSettings`
"""

from __future__ import annotations

from typing import Any

from onedrop.logging import configure_logging, get_logger
from onedrop.queue import redis_settings
from onedrop.workers.jobs import (
    cleanup_media,
    dispatch_due_reminders,
    process_capture,
    process_image_capture,
    process_voice_capture,
)
from onedrop.workers.notifications import deliver_notifications, plan_notifications

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    logger.info("worker.startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    from onedrop.db.session import dispose_engine

    await dispose_engine()
    logger.info("worker.shutdown")


class WorkerSettings:
    """Settings object consumed by the `arq` CLI."""

    functions = [
        process_capture,
        process_voice_capture,
        process_image_capture,
        dispatch_due_reminders,
        plan_notifications,
        deliver_notifications,
        cleanup_media,
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 3
    job_timeout = 180
    keep_result = 3600
    max_jobs = 10
    retry_jobs = True

    @staticmethod
    def redis_settings() -> Any:  # noqa: D401 - arq reads this attribute
        return redis_settings()
