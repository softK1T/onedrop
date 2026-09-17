"""Telegram webhook endpoint. Thin: validate, record, enqueue, return 200."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Header, Response, status

from onedrop.api.dependencies import DbSession
from onedrop.capture.telegram_intake import (
    TELEGRAM_SECRET_HEADER,
    TelegramIntakeService,
    verify_webhook_secret,
)
from onedrop.config import get_settings
from onedrop.errors import ForbiddenError
from onedrop.logging import get_logger

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = get_logger(__name__)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook(
    session: DbSession,
    payload: Annotated[dict[str, Any], Body()],
    secret_token: Annotated[str | None, Header(alias=TELEGRAM_SECRET_HEADER)] = None,
) -> Response:
    """Accept one Telegram update.

    The secret token header is mandatory, duplicates are ignored by
    `update_id`, and heavy work is handed to the worker.
    """
    settings = get_settings()
    if not verify_webhook_secret(secret_token, settings.telegram_webhook_secret):
        logger.warning("telegram.webhook_secret_mismatch")
        raise ForbiddenError("Invalid webhook secret token")

    result = await TelegramIntakeService(session).ingest(payload)
    logger.info(
        "telegram.update_ingested",
        kind=result.kind,
        accepted=result.accepted,
        duplicate=result.duplicate,
    )
    return Response(status_code=status.HTTP_200_OK)
