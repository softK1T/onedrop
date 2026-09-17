"""Queue access. Job ids double as idempotency keys."""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from onedrop.config import get_settings
from onedrop.logging import get_logger

logger = get_logger(__name__)

DEAD_LETTER_KEY = "onedrop:dead-letter"


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def enqueue(function: str, *args: Any, job_id: str | None = None) -> bool:
    """Enqueue a job. Returns False when a job with this id already exists."""
    pool = await create_pool(redis_settings())
    try:
        job = await pool.enqueue_job(function, *args, _job_id=job_id)
    finally:
        await pool.close()
    if job is None:
        logger.info("queue.duplicate_job", function=function)
        return False
    return True
