"""Subscription and payment persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.billing import Payment, Subscription
from onedrop.db.models.enums import PaymentStatus, SubscriptionStatus


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_subscription(self, user_id: UUID) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
            .order_by(Subscription.started_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def record_payment(
        self,
        *,
        user_id: UUID,
        telegram_payment_charge_id: str,
        invoice_payload: str,
        amount_stars: int,
        plan: str,
        period_days: int,
    ) -> Payment | None:
        """Insert the payment once. Returns None for a redelivered charge id."""
        stmt = (
            pg_insert(Payment)
            .values(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                invoice_payload=invoice_payload,
                amount_stars=amount_stars,
                plan=plan,
                period_days=period_days,
                status=PaymentStatus.PAID.value,
            )
            .on_conflict_do_nothing(
                constraint="uq_payments_telegram_payment_charge_id"
            )
            .returning(Payment.id)
        )
        result = await self._session.execute(stmt)
        payment_id = result.scalar_one_or_none()
        await self._session.flush()
        if payment_id is None:
            return None
        return await self.get_payment(payment_id)

    async def get_payment(self, payment_id: UUID) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def payment_by_charge_id(self, charge_id: str) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.telegram_payment_charge_id == charge_id)
        )
        return result.scalar_one_or_none()

    async def upsert_subscription(
        self,
        *,
        user_id: UUID,
        plan: str,
        expires_at: datetime,
        existing: Subscription | None,
    ) -> Subscription:
        if existing is not None:
            existing.plan = plan
            existing.expires_at = expires_at
            existing.status = SubscriptionStatus.ACTIVE.value
            await self._session.flush()
            return existing
        row = Subscription(
            user_id=user_id,
            plan=plan,
            status=SubscriptionStatus.ACTIVE.value,
            started_at=datetime.now(tz=UTC),
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def expire_due(self, *, now: datetime | None = None) -> int:
        """Mark subscriptions past their expiry as expired."""
        moment = now or datetime.now(tz=UTC)
        stmt = (
            update(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.expires_at.is_not(None),
                Subscription.expires_at < moment,
            )
            .values(status=SubscriptionStatus.EXPIRED.value)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)
