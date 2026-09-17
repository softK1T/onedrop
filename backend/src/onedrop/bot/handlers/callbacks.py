"""Callback handlers: fix and undo."""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery

from onedrop.bot.keyboards.common import CALLBACK_FIX, CALLBACK_UNDO, open_app_keyboard
from onedrop.bot.render import render_error, render_undo
from onedrop.bot.texts import t
from onedrop.capture.service import CaptureService
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import session_scope
from onedrop.errors import AppError
from onedrop.logging import get_logger

router = Router(name="callbacks")
logger = get_logger(__name__)


def _parse_uuid(data: str | None, prefix: str) -> UUID | None:
    if not data or not data.startswith(f"{prefix}:"):
        return None
    try:
        return UUID(data.split(":", 1)[1])
    except ValueError:
        return None


@router.callback_query(F.data.startswith(f"{CALLBACK_UNDO}:"))
async def handle_undo(callback: CallbackQuery) -> None:
    """Undo every record created by one capture, atomically."""
    item_id = _parse_uuid(callback.data, CALLBACK_UNDO)
    sender = callback.from_user
    if item_id is None:
        await callback.answer()
        return

    async with session_scope() as session:
        user = await UserRepository(session).get_by_telegram_id(sender.id)
        locale = user.locale if user is not None else None
        if user is None:
            await callback.answer()
            return
        try:
            reverted = await CaptureService(session).undo(
                user_id=user.id, inbox_item_id=item_id
            )
        except AppError as exc:
            logger.warning("bot.undo_failed", code=exc.code)
            await callback.answer()
            if callback.message is not None:
                await callback.message.answer(render_error(locale))
            return

    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(render_undo(locale, reverted))


@router.callback_query(F.data.startswith(f"{CALLBACK_FIX}:"))
async def handle_fix(callback: CallbackQuery) -> None:
    """Send the user into the Mini App to correct the capture."""
    item_id = _parse_uuid(callback.data, CALLBACK_FIX)
    sender = callback.from_user
    async with session_scope() as session:
        user = await UserRepository(session).get_by_telegram_id(sender.id)
        locale = user.locale if user is not None else None

    await callback.answer()
    if callback.message is not None and item_id is not None:
        await callback.message.answer(
            t(locale, "button_fix"),
            reply_markup=open_app_keyboard(locale, f"inbox/{item_id}"),
        )
