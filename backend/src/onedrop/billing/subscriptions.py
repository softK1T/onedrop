"""Subscription state machine and activation from confirmed payments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.billing.schemas import ActivationResponse
from onedrop.db.models.enums import Plan, SubscriptionStatus
from onedrop.db.repositories.billing import BillingRepository
from onedrop.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SubscriptionState:
    """Effective plan for a user at a point in time."""

    plan: str
    status: str
    expires_at: datetime | None


def resolve_state(
    *, plan: str | None, status: str | None, expires_at: datetime | None, now: datetime
) -> SubscriptionState:
    """Pure resolution: an expired row is treated as free immediately.

    The scheduler also sweeps expired rows, but the resolver never waits for it.
    """
    if plan is None or status != SubscriptionStatus.ACTIVE.value:
        return SubscriptionState(
            plan=Plan.FREE.value, status=SubscriptionStatus.EXPIRED.value, expires_at=expires_at
        )
    if expires_at is not None and expires_at <= now:
        return SubscriptionState(
            plan=Plan.FREE.value,
            status=SubscriptionStatus.EXPIRED.value,
            expires_at=expires_at,
        )
    return SubscriptionState(
        plan=plan, status=SubscriptionStatus.ACTIVE.value, expires_at=expires_at
    )


def next_expiry(
    *, current: datetime | None, now: datetime, period_days: int
) -> datetime:
    """Extend an active period, or start a new one from now."""
    base = current if current is not None and current > now else now
    return base + timedelta(days=max(1, period_days))


class SubscriptionService:
    """Owns plan resolution and activation. Pro is granted only after payment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._billing = BillingRepository(session)

    async def current_state(self, user_id: UUID) -> SubscriptionState:
        subscription = await self._billing.active_subscription(user_id)
        return resolve_state(
            plan=subscription.plan if subscription else None,
            status=subscription.status if subscription else None,
            expires_at=subscription.expires_at if subscription else None,
            now=datetime.now(tz=UTC),
        )

    async def activate_from_payment(
        self,
        *,
        user_id: UUID,
        telegram_payment_charge_id: str,
        invoice_payload: str,
        amount_stars: int,
        plan: str,
        period_days: int,
    ) -> ActivationResponse:
        """Activate Pro after a confirmed payment. Redelivery is a no-op."""
        payment = await self._billing.record_payment(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            invoice_payload=invoice_payload,
            amount_stars=amount_stars,
            plan=plan,
            period_days=period_days,
        )
        if payment is None:
            logger.info("billing.duplicate_payment")
            state = await self.current_state(user_id)
            await self._session.commit()
            return ActivationResponse(
                activated=False,
                duplicate=True,
                plan=state.plan,
                expires_at=state.expires_at,
            )

        now = datetime.now(tz=UTC)
        existing = await self._billing.active_subscription(user_id)
        expires_at = next_expiry(
            current=existing.expires_at if existing else None,
            now=now,
            period_days=period_days,
        )
        await self._billing.upsert_subscription(
            user_id=user_id, plan=plan, expires_at=expires_at, existing=existing
        )
        await self._session.commit()
        logger.info("billing.subscription_activated", plan=plan)
        return ActivationResponse(
            activated=True,
            duplicate=False,
            plan=plan,
            expires_at=expires_at,
            extended_days=period_days,
        )

    async def expire_due(self) -> int:
        """Scheduler sweep for subscriptions past their expiry."""
        count = await self._billing.expire_due()
        await self._session.commit()
        return count
