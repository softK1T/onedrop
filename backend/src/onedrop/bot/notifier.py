"""Outbound Telegram messages sent from background jobs.

The worker never holds a long-lived bot instance: each notification creates a
client, sends the message and closes the session.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from aiogram.exceptions import TelegramAPIError

from onedrop.ai.normalize import to_local
from onedrop.bot.app import create_bot
from onedrop.bot.keyboards.common import result_keyboard
from onedrop.bot.render import (
    render_clarification,
    render_error,
    render_limit_reached,
    render_reminder,
    render_result,
)
from onedrop.db.models.enums import InboxStatus
from onedrop.db.repositories.inbox import InboxRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import get_sessionmaker
from onedrop.logging import get_logger

logger = get_logger(__name__)


async def notify_capture_result(inbox_item_id: UUID) -> bool:
    """Edit the acknowledgement message with the capture outcome.

    Returns False when there is nothing to send (no bot, no chat, no item).
    """
    bot = create_bot()
    if bot is None:
        return False

    maker = get_sessionmaker()
    try:
        async with maker() as session:
            repository = InboxRepository(session)
            item = await repository.get(inbox_item_id)
            if item is None or item.telegram_chat_id is None:
                return False
            user = await UserRepository(session).get_by_id(item.user_id)
            locale = user.locale if user is not None else None
            links = await repository.links(item.id)
            created = [(link.entity_type, link.entity_id) for link in links]
            status = item.status
            question = item.clarification_question
            chat_id = item.telegram_chat_id
            message_id = item.telegram_message_id
            error = item.error

        if status == InboxStatus.COMPLETED.value:
            text = render_result(locale, created)
            markup = result_keyboard(locale, inbox_item_id)
        elif status == InboxStatus.NEEDS_CONFIRMATION.value:
            text = render_clarification(locale, question)
            markup = None
        elif error == "quota_exceeded":
            text = render_limit_reached(locale)
            markup = None
        else:
            text = render_error(locale)
            markup = None

        try:
            if message_id is not None:
                await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=markup,
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        except TelegramAPIError as exc:
            logger.warning(
                "notifier.capture_result_failed", error_type=type(exc).__name__
            )
            return False
        return True
    finally:
        await bot.session.close()


async def notify_reminder(
    *,
    telegram_user_id: int,
    locale: str | None,
    kind: str,
    title: str,
    scheduled_at: datetime,
    timezone: str,
) -> bool:
    """Send one reminder. Called after the row was claimed in the database."""
    bot = create_bot()
    if bot is None:
        return False
    try:
        await bot.send_message(
            chat_id=telegram_user_id,
            text=render_reminder(
                locale,
                kind=kind,
                title=title,
                when_local=to_local(scheduled_at, timezone),
            ),
        )
        return True
    except TelegramAPIError as exc:
        logger.warning("notifier.reminder_failed", error_type=type(exc).__name__)
        return False
    finally:
        await bot.session.close()


async def notify_text(*, telegram_user_id: int, text: str) -> bool:
    """Send a plain message, used by the morning digest."""
    bot = create_bot()
    if bot is None:
        return False
    try:
        await bot.send_message(chat_id=telegram_user_id, text=text)
        return True
    except TelegramAPIError as exc:
        logger.warning("notifier.text_failed", error_type=type(exc).__name__)
        return False
    finally:
        await bot.session.close()
