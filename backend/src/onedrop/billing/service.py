"""Billing use cases for the API and the bot."""

from __future__ import annotations

from uuid import UUID

from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.billing.plans import limits_for
from onedrop.billing.schemas import (
    InvoiceResponse,
    PlanFeatures,
    PlanResponse,
)
from onedrop.billing.stars import (
    STARS_CURRENCY,
    build_invoice_arguments,
    build_payload,
)
from onedrop.billing.subscriptions import SubscriptionService
from onedrop.bot.app import create_bot
from onedrop.config import get_settings
from onedrop.db.models.enums import Plan
from onedrop.logging import get_logger

logger = get_logger(__name__)

INVOICE_TITLE = "OneDrop Pro"
INVOICE_DESCRIPTION = (
    "Food photo recognition, morning digest, advanced analytics, CSV export "
    "and a monthly AI allowance."
)


class BillingService:
    """Plan information and Stars invoice creation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._subscriptions = SubscriptionService(session)

    async def plan(self, user_id: UUID) -> PlanResponse:
        settings = get_settings()
        state = await self._subscriptions.current_state(user_id)
        limits = limits_for(state.plan, settings)
        return PlanResponse(
            plan=state.plan,
            status=state.status,
            expires_at=state.expires_at,
            bonus_limit=limits.bonus_limit,
            period_scope=limits.period_scope,
            period_limit=limits.period_limit,
            features=PlanFeatures(
                photo_recognition=limits.photo_recognition,
                morning_digest=limits.morning_digest,
                advanced_analytics=limits.advanced_analytics,
                csv_export=limits.csv_export,
                history_days=limits.history_days,
            ),
            pro_price_stars=settings.pro_price_stars,
            pro_period_days=settings.pro_period_days,
        )

    async def create_invoice(self, user_id: UUID) -> InvoiceResponse:
        """Create a Stars invoice link.

        The subscription is not touched here: only a confirmed
        `successful_payment` activates Pro.
        """
        settings = get_settings()
        payload = build_payload(user_id, Plan.PRO.value)
        arguments = build_invoice_arguments(
            title=INVOICE_TITLE,
            description=INVOICE_DESCRIPTION,
            payload=payload,
            amount_stars=settings.pro_price_stars,
        )

        link: str | None = None
        bot = create_bot(settings)
        if bot is not None:
            try:
                link = await bot.create_invoice_link(**arguments)
            except TelegramAPIError as exc:
                logger.warning(
                    "billing.invoice_link_failed", error_type=type(exc).__name__
                )
            finally:
                await bot.session.close()
        else:
            logger.warning("billing.invoice_without_bot")

        return InvoiceResponse(
            invoice_link=link,
            payload=payload,
            amount_stars=settings.pro_price_stars,
            currency=STARS_CURRENCY,
            period_days=settings.pro_period_days,
            test_mode=settings.billing_test_mode and not settings.is_production,
        )
