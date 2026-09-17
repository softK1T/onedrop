"""Telegram update intake.

The webhook only validates, records and enqueues. Anything expensive happens in
the worker, so Telegram always gets a fast 200.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.capture.media_service import MediaCaptureService
from onedrop.capture.service import CaptureService
from onedrop.config import get_settings
from onedrop.db.models.enums import InputType
from onedrop.db.models.user import TelegramUpdate
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import ProviderError
from onedrop.logging import get_logger
from onedrop.queue import enqueue

logger = get_logger(__name__)

TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
AUDIO_FALLBACK_MIME = "audio/ogg"
IMAGE_FALLBACK_MIME = "image/jpeg"


def verify_webhook_secret(provided: str | None, expected: str) -> bool:
    """Constant-time comparison of the Telegram secret token header."""
    if not expected:
        return False
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)


@dataclass(frozen=True, slots=True)
class IngestResult:
    """What the webhook learned about one update."""

    accepted: bool
    duplicate: bool
    kind: str
    inbox_item_id: UUID | None = None
    chat_id: int | None = None
    message_id: int | None = None


class TelegramIntakeService:
    """Turns raw Telegram updates into inbox items and queued jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def register_update(self, update_id: int, payload: dict[str, Any]) -> bool:
        """Insert the update once. Returns False when it was already seen."""
        stmt = (
            pg_insert(TelegramUpdate)
            .values(update_id=update_id, payload=payload)
            .on_conflict_do_nothing(constraint="uq_telegram_updates_update_id")
            .returning(TelegramUpdate.id)
        )
        result = await self._session.execute(stmt)
        inserted = result.scalar_one_or_none() is not None
        await self._session.commit()
        return inserted

    async def ingest(self, update: dict[str, Any]) -> IngestResult:
        """Store the capture and enqueue processing."""
        update_id = int(update.get("update_id", 0))
        is_new = await self.register_update(update_id, update)
        if not is_new:
            logger.info("telegram.duplicate_update", update_id=update_id)
            return IngestResult(accepted=False, duplicate=True, kind="duplicate")

        message = update.get("message") or update.get("edited_message")
        if not isinstance(message, dict):
            return IngestResult(accepted=False, duplicate=False, kind="unsupported")

        sender = message.get("from") or {}
        telegram_user_id = sender.get("id")
        if not isinstance(telegram_user_id, int):
            return IngestResult(accepted=False, duplicate=False, kind="unsupported")

        user = await self._users.upsert_from_telegram(
            telegram_user_id=telegram_user_id,
            first_name=sender.get("first_name"),
            username=sender.get("username"),
            language_code=sender.get("language_code"),
        )
        await self._session.commit()

        chat_id = int((message.get("chat") or {}).get("id", telegram_user_id))
        message_id = int(message.get("message_id", 0))
        idempotency_key = f"tg:{update_id}"

        text = message.get("text")
        if isinstance(text, str) and text.strip() and not text.startswith("/"):
            item = await CaptureService(self._session).create_text_capture(
                user_id=user.id,
                text=text,
                idempotency_key=idempotency_key,
                telegram_update_id=update_id,
                telegram_chat_id=chat_id,
                telegram_message_id=message_id,
            )
            await enqueue("process_capture", str(item.id), job_id=f"capture:{item.id}")
            return IngestResult(
                accepted=True,
                duplicate=False,
                kind="text",
                inbox_item_id=item.id,
                chat_id=chat_id,
                message_id=message_id,
            )

        voice = message.get("voice") or message.get("audio")
        if isinstance(voice, dict) and isinstance(voice.get("file_id"), str):
            data = await self.download_file(str(voice["file_id"]))
            item = await MediaCaptureService(self._session).create_media_capture(
                user_id=user.id,
                data=data,
                mime_type=str(voice.get("mime_type") or AUDIO_FALLBACK_MIME),
                input_type=InputType.VOICE.value,
                idempotency_key=idempotency_key,
                telegram_update_id=update_id,
                telegram_chat_id=chat_id,
                telegram_message_id=message_id,
            )
            await enqueue("process_voice_capture", str(item.id), job_id=f"voice:{item.id}")
            return IngestResult(
                accepted=True,
                duplicate=False,
                kind="voice",
                inbox_item_id=item.id,
                chat_id=chat_id,
                message_id=message_id,
            )

        photos = message.get("photo")
        if isinstance(photos, list) and photos:
            largest = photos[-1]
            data = await self.download_file(str(largest["file_id"]))
            item = await MediaCaptureService(self._session).create_media_capture(
                user_id=user.id,
                data=data,
                mime_type=IMAGE_FALLBACK_MIME,
                input_type=InputType.PHOTO.value,
                idempotency_key=idempotency_key,
                telegram_update_id=update_id,
                telegram_chat_id=chat_id,
                telegram_message_id=message_id,
            )
            await enqueue("process_image_capture", str(item.id), job_id=f"image:{item.id}")
            return IngestResult(
                accepted=True,
                duplicate=False,
                kind="photo",
                inbox_item_id=item.id,
                chat_id=chat_id,
                message_id=message_id,
            )

        return IngestResult(
            accepted=False,
            duplicate=False,
            kind="unsupported",
            chat_id=chat_id,
            message_id=message_id,
        )

    async def download_file(self, file_id: str) -> bytes:
        """Fetch a file through the Bot API. The token never leaves this call."""
        settings = get_settings()
        if not settings.telegram_bot_token:
            raise ProviderError("Telegram bot token is not configured")
        base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                meta = await client.get(f"{base}/getFile", params={"file_id": file_id})
                meta.raise_for_status()
                file_path = meta.json()["result"]["file_path"]
                download = await client.get(
                    f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
                )
                download.raise_for_status()
                return download.content
        except (httpx.HTTPError, KeyError) as exc:
            logger.warning("telegram.file_download_failed", error_type=type(exc).__name__)
            raise ProviderError("could not download the Telegram file") from exc
