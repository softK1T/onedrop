"""Commands: /start, /help, /today, /plan, /settings."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from onedrop.analytics.service import AnalyticsService
from onedrop.bot.keyboards.common import (
    CALLBACK_CONSENT,
    consent_keyboard,
    open_app_keyboard,
    paywall_keyboard,
)
from onedrop.bot.texts import t
from onedrop.config import get_settings
from onedrop.db.models.user import User
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import session_scope
from onedrop.logging import get_logger
from onedrop.money import format_amount
from onedrop.users.schemas import UserSettingsUpdate
from onedrop.users.service import UserService

router = Router(name="commands")
logger = get_logger(__name__)

MAX_TODAY_ITEMS = 8


async def _resolve_user(message: Message) -> tuple[User, str]:
    """Upsert the Telegram user and return it with its locale."""
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
        return user, user.locale


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Welcome plus onboarding consent when it has not been given yet."""
    user, locale = await _resolve_user(message)
    async with session_scope() as session:
        settings_row = await UserService(session).settings_for(user.id)
        consented = settings_row.consent_at is not None

    await message.answer(t(locale, "start_welcome"))
    if consented:
        await message.answer(
            t(locale, "onboarding_done"), reply_markup=open_app_keyboard(locale)
        )
        return
    await message.answer(
        t(locale, "onboarding_consent"), reply_markup=consent_keyboard(locale)
    )


@router.callback_query(F.data == CALLBACK_CONSENT)
async def handle_consent(callback: CallbackQuery) -> None:
    """Record consent and finish onboarding."""
    sender = callback.from_user
    async with session_scope() as session:
        repository = UserRepository(session)
        user = await repository.upsert_from_telegram(
            telegram_user_id=sender.id,
            first_name=sender.first_name,
            username=sender.username,
            language_code=sender.language_code,
        )
        await UserService(session).update_settings(
            user.id, UserSettingsUpdate(accept_consent=True, onboarding_completed=True)
        )
        locale = user.locale

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            t(locale, "onboarding_done"), reply_markup=open_app_keyboard(locale)
        )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    _, locale = await _resolve_user(message)
    await message.answer(t(locale, "help"))


@router.message(Command("today"))
async def handle_today(message: Message) -> None:
    """Compact overview of the day plus the remaining AI allowance."""
    user, locale = await _resolve_user(message)
    async with session_scope() as session:
        dashboard = await AnalyticsService(session).today(user.id)

    lines: list[str] = [f"<b>{t(locale, 'today_header')}</b>"]
    if dashboard.task_items:
        for task in dashboard.task_items[:MAX_TODAY_ITEMS]:
            lines.append(f"• {task.title}")
    if dashboard.events:
        for event in dashboard.events[:MAX_TODAY_ITEMS]:
            lines.append(f"◦ {event.starts_at.strftime('%H:%M')} {event.title}")
    if dashboard.expenses_today_minor:
        lines.append(
            format_amount(dashboard.expenses_today_minor, dashboard.base_currency)
        )
    if dashboard.nutrition.calories:
        lines.append(f"{dashboard.nutrition.calories} kcal")
    if len(lines) == 1:
        lines.append(t(locale, "today_empty"))
    lines.append(t(locale, "limit_left", remaining=dashboard.ai.remaining))

    await message.answer(
        "\n".join(lines), reply_markup=open_app_keyboard(locale, "today")
    )


@router.message(Command("plan"))
async def handle_plan(message: Message) -> None:
    _, locale = await _resolve_user(message)
    await message.answer(t(locale, "plan_prompt"))


@router.message(Command("settings"))
async def handle_settings(message: Message) -> None:
    """Show current settings and the active plan."""
    user, locale = await _resolve_user(message)
    async with session_scope() as session:
        service = UserService(session)
        settings_row = await service.settings_for(user.id)
        usage = await service.usage(user.id)

    body = t(
        locale,
        "settings_body",
        timezone=settings_row.timezone,
        currency=settings_row.base_currency,
        reminders="on" if settings_row.reminders_enabled else "off",
        plan=usage.plan,
    )
    await message.answer(
        f"<b>{t(locale, 'settings_header')}</b>\n{body}\n"
        f"{t(locale, 'limit_left', remaining=usage.remaining)}",
        reply_markup=open_app_keyboard(locale, "settings"),
    )


@router.message(Command("pro"))
async def handle_pro(message: Message) -> None:
    """Paywall copy with the configured Stars price."""
    _, locale = await _resolve_user(message)
    settings = get_settings()
    await message.answer(
        t(
            locale,
            "paywall",
            price=settings.pro_price_stars,
            days=settings.pro_period_days,
        ),
        reply_markup=paywall_keyboard(locale),
    )
