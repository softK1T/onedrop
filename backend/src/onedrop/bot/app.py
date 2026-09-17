"""Bot and dispatcher factories.

Without a token the bot is not constructed at all, which is what keeps demo mode
runnable without Telegram credentials.
"""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from onedrop.config import Settings, get_settings
from onedrop.logging import get_logger

logger = get_logger(__name__)


def create_bot(settings: Settings | None = None) -> Bot | None:
    """Return a configured bot, or None when no token is configured."""
    active = settings or get_settings()
    if not active.telegram_bot_token:
        logger.warning("bot.disabled_no_token", mode=active.bot_mode)
        return None
    return Bot(
        token=active.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Dispatcher with every router attached, commands before free-form input."""
    from onedrop.bot.handlers import callbacks, capture, commands

    dispatcher = Dispatcher()
    dispatcher.include_router(commands.router)
    dispatcher.include_router(callbacks.router)
    dispatcher.include_router(capture.router)
    return dispatcher
