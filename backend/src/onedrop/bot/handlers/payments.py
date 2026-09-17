"""Stars payment flow: invoice, pre-checkout, successful payment."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from onedrop.billing.service import BillingService
from onedrop.billing.stars import STARS_CURRENCY, parse_payload
from onedrop.billing.subscriptions import SubscriptionService
from onedrop.bot.keyboards.common import CALLBACK_BUY_PRO, open_app_keyboard
from onedrop.bot.texts import t
from onedrop.config import get_settings
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import session_scope
from onedrop.errors import AppError
from onedrop.logging import get_logger

router = Router(name="payments")
logger = get_logger(__name__)


@router.callback_query(F.data == CALLBACK_BUY_PRO)
async def handle_buy_pro(callback: CallbackQuery) -> None:
    """Send a Stars invoice link for the Pro plan."""
    sender = callback.from_user
    async with session_scope() as session:
        user = await UserRepository(session).upsert_from_telegram(
            telegram_user_id=sender.id,
            first_name=sender.first_name,
            username=sender.username,
            language_code=sender.language_code,
        )
        locale = user.locale
        try:
            invoice = await BillingService(session).create_invoice(user.id)
        except AppError as exc:
            logger.warning("bot.invoice_failed", code=exc.code)
            invoice = None

    await callback.answer()
    if callback.message is None:
        return
    if invoice is None or invoice.invoice_link is None:
        await callback.message.answer(t(locale, "error_generic"))
        return
    await callback.message.answer(invoice.invoice_link)


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery) -> None:
    """Approve the charge only when the payload matches the paying user."""
    settings = get_settings()
    parsed = parse_payload(query.invoice_payload)
    if parsed is None or query.currency != STARS_CURRENCY:
        await query.answer(ok=False, error_message="This invoice is no longer valid.")
        return

    async with session_scope() as session:
        user = await UserRepository(session).get_by_telegram_id(query.from_user.id)

    if user is None or user.id != parsed.user_id:
        logger.warning("bot.pre_checkout_payload_mismatch")
        await query.answer(ok=False, error_message="This invoice belongs to another account.")
        return
    if query.total_amount != settings.pro_price_stars:
        logger.warning("bot.pre_checkout_amount_mismatch")
        await query.answer(ok=False, error_message="The price has changed. Please try again.")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message) -> None:
    """Store the charge id and activate the subscription exactly once."""
    payment = message.successful_payment
    sender = message.from_user
    if payment is None or sender is None:
        return
    parsed = parse_payload(payment.invoice_payload)
    if parsed is None:
        logger.warning("bot.successful_payment_unknown_payload")
        return

    settings = get_settings()
    async with session_scope() as session:
        user = await UserRepository(session).get_by_telegram_id(sender.id)
        if user is None or user.id != parsed.user_id:
            logger.warning("bot.successful_payment_user_mismatch")
            return
        locale = user.locale
        result = await SubscriptionService(session).activate_from_payment(
            user_id=user.id,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
            invoice_payload=payment.invoice_payload,
            amount_stars=payment.total_amount,
            plan=parsed.plan,
            period_days=settings.pro_period_days,
        )

    if result.duplicate:
        return
    await message.answer(
        t(locale, "limit_left", remaining=settings.pro_monthly_ai_limit),
        reply_markup=open_app_keyboard(locale, "subscription"),
    )
