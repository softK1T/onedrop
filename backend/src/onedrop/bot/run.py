"""Bot entry point.

Modes:
- `polling`  - long polling, the default for local development
- `webhook`  - Telegram posts to the API; this process only registers the hook
- `disabled` - or a missing token: the process idles instead of crash-looping

Run with: `python -m onedrop.bot.run`
"""

from __future__ import annotations

import asyncio
import contextlib
import signal

from onedrop.bot.app import create_bot, create_dispatcher
from onedrop.config import get_settings
from onedrop.db.session import dispose_engine
from onedrop.logging import configure_logging, get_logger

logger = get_logger(__name__)
IDLE_TICK_SECONDS = 60
ALLOWED_UPDATES = ["message", "callback_query", "pre_checkout_query"]


async def idle(stop: asyncio.Event, reason: str) -> None:
    """Stay alive without doing anything, so the container does not restart."""
    logger.warning("bot.idle", reason=reason)
    while not stop.is_set():
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=IDLE_TICK_SECONDS)


async def run(stop: asyncio.Event) -> None:
    settings = get_settings()
    bot = create_bot(settings)
    if bot is None or settings.bot_mode == "disabled":
        await idle(stop, "no_token_or_disabled")
        return

    try:
        if settings.bot_mode == "webhook":
            if not settings.telegram_webhook_url or not settings.telegram_webhook_secret:
                logger.warning("bot.webhook_not_configured")
                await idle(stop, "webhook_not_configured")
                return
            await bot.set_webhook(
                url=settings.telegram_webhook_url,
                secret_token=settings.telegram_webhook_secret,
                allowed_updates=ALLOWED_UPDATES,
                drop_pending_updates=False,
            )
            logger.info("bot.webhook_registered")
            await idle(stop, "webhook_mode")
            return

        dispatcher = create_dispatcher()
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("bot.polling_started")
        await dispatcher.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    finally:
        await bot.session.close()
        await dispose_engine()
        logger.info("bot.stopped")


def main() -> None:
    configure_logging()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    try:
        loop.run_until_complete(run(stop))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
