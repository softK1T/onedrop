"""Liveness, readiness and version endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from onedrop import __version__
from onedrop.api.dependencies import DbSession
from onedrop.config import get_settings
from onedrop.logging import get_logger

router = APIRouter(tags=["system"])
logger = get_logger(__name__)


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe including dependencies")
async def ready(session: DbSession) -> JSONResponse:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.warning("health.database_unavailable", exc_info=True)
        checks["database"] = "unavailable"

    client: Redis | None = None
    try:
        client = Redis.from_url(get_settings().redis_url)
        await client.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.warning("health.redis_unavailable", exc_info=True)
        checks["redis"] = "unavailable"
    finally:
        if client is not None:
            await client.aclose()

    healthy = all(value == "ok" for value in checks.values())
    body: dict[str, Any] = {"status": "ready" if healthy else "degraded", "checks": checks}
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@router.get("/version", summary="Build and environment information")
async def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": __version__,
        "environment": settings.app_env,
        "ai_provider_mode": settings.ai_provider_mode,
    }
