"""Capture handlers: text, voice and photo.

Every handler acknowledges immediately and hands the work to the worker, so a
slow AI call never blocks the chat.
"""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.types import Message

from onedrop.bot.texts import t
from onedrop.capture.media_service import MediaCaptureService
from onedrop.capture.service import CaptureService
from onedrop.capture.telegram_intake import (
    AUDIO_FALLBACK_MIME,
    IMAGE_FALLBACK_MIME,
    TelegramIntakeService,
)
from onedrop.db.models.enums import InputType
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import session_scope
from onedrop.errors import AppError
from onedrop.logging import get_logger
from onedrop.queue import enqueue

router = Router(name="capture")
logger = get_logger(__name__)


async def _user_and_locale(message: Message) -> tuple[uuid.UUID, str]:
    """Return (user_id, locale) for the sender, creating the user if needed."""
    sender = message.from_user
    if sender is None:
        raise ValueError("message has no sender")
    async with session_scope() as session:
        user = await UserRepository(session).upsert_from_telegram(
            telegram_user_id=sender.id,
            first_name=sender.first_name,
            username=sender.username,
            language_code=sender.language_code,
        )
        return user.id, user.locale


def _idempotency_key(message: Message) -> str:
    return f"tg:{message.chat.id}:{message.message_id}"[:128]


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    """Text capture: acknowledge, store, queue."""
    user_id, locale = await _user_and_locale(message)
    ack = await message.answer(t(locale, "ack"))
    try:
        async with session_scope() as session:
            item = await CaptureService(session).create_text_capture(
                user_id=user_id,
                text=message.text or "",
                idempotency_key=_idempotency_key(message),
                telegram_chat_id=message.chat.id,
                telegram_message_id=ack.message_id,
            )
        await enqueue("process_capture", str(item.id), job_id=f"capture:{item.id}")
    except AppError as exc:
        logger.warning("bot.text_capture_failed", code=exc.code)
        await ack.edit_text(t(locale, "error_generic"))


@router.message(F.voice | F.audio)
async def handle_voice(message: Message) -> None:
    """Voice capture: download, store the file, queue transcription."""
    user_id, locale = await _user_and_locale(message)
    ack = await message.answer(t(locale, "ack"))
    source = message.voice or message.audio
    if source is None:
        await ack.edit_text(t(locale, "unsupported"))
        return
    try:
        async with session_scope() as session:
            data = await TelegramIntakeService(session).download_file(source.file_id)
            item = await MediaCaptureService(session).create_media_capture(
                user_id=user_id,
                data=data,
                mime_type=getattr(source, "mime_type", None) or AUDIO_FALLBACK_MIME,
                input_type=InputType.VOICE.value,
                idempotency_key=_idempotency_key(message),
                telegram_chat_id=message.chat.id,
                telegram_message_id=ack.message_id,
            )
        await enqueue("process_voice_capture", str(item.id), job_id=f"voice:{item.id}")
    except AppError as exc:
        logger.warning("bot.voice_capture_failed", code=exc.code)
        await ack.edit_text(t(locale, "error_generic"))


@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    """Food photo capture: download the largest size, queue the estimate."""
    user_id, locale = await _user_and_locale(message)
    ack = await message.answer(t(locale, "ack"))
    photos = message.photo or []
    if not photos:
        await ack.edit_text(t(locale, "unsupported"))
        return
    try:
        async with session_scope() as session:
            data = await TelegramIntakeService(session).download_file(photos[-1].file_id)
            item = await MediaCaptureService(session).create_media_capture(
                user_id=user_id,
                data=data,
                mime_type=IMAGE_FALLBACK_MIME,
                input_type=InputType.PHOTO.value,
                idempotency_key=_idempotency_key(message),
                telegram_chat_id=message.chat.id,
                telegram_message_id=ack.message_id,
            )
        await enqueue("process_image_capture", str(item.id), job_id=f"image:{item.id}")
    except AppError as exc:
        logger.warning("bot.photo_capture_failed", code=exc.code)
        await ack.edit_text(t(locale, "error_generic"))


@router.message(F.document | F.sticker | F.video | F.location)
async def handle_unsupported(message: Message) -> None:
    """Unsupported input types never consume AI quota."""
    _, locale = await _user_and_locale(message)
    await message.answer(t(locale, "unsupported"))
