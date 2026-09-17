"""AI usage counters and the operations ledger."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.providers.base import ProviderUsage
from onedrop.billing.plans import (
    BONUS_PERIOD_KEY,
    PlanLimits,
    QuotaState,
    evaluate_quota,
    period_key_for,
)
from onedrop.db.models.billing import UsageCounter
from onedrop.db.models.enums import AiOperationStatus
from onedrop.db.models.inbox import AiOperation
from onedrop.errors import QuotaExceededError
from onedrop.logging import get_logger

logger = get_logger(__name__)


class UsageService:
    """Counts AI actions. Quota is charged only for real provider calls."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _used(self, user_id: UUID, scope: str, period_key: str) -> int:
        stmt = select(UsageCounter.used).where(
            UsageCounter.user_id == user_id,
            UsageCounter.scope == scope,
            UsageCounter.period_key == period_key,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one_or_none() or 0)

    async def snapshot(
        self, user_id: UUID, *, limits: PlanLimits, now_local: datetime
    ) -> QuotaState:
        """Current quota state without changing anything."""
        bonus_used = await self._used(user_id, "bonus", BONUS_PERIOD_KEY)
        period_used = await self._used(
            user_id, limits.period_scope, period_key_for(limits, now_local)
        )
        return evaluate_quota(limits=limits, bonus_used=bonus_used, period_used=period_used)

    async def already_charged(self, idempotency_key: str) -> bool:
        """True when this idempotency key was already accounted for."""
        stmt = select(AiOperation.id).where(AiOperation.idempotency_key == idempotency_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _increment(self, user_id: UUID, scope: str, period_key: str) -> None:
        stmt = (
            pg_insert(UsageCounter)
            .values(user_id=user_id, scope=scope, period_key=period_key, used=1)
            .on_conflict_do_update(
                constraint="uq_usage_counters_period",
                set_={"used": UsageCounter.__table__.c.used + 1},
            )
        )
        await self._session.execute(stmt)

    async def reserve(
        self,
        user_id: UUID,
        *,
        limits: PlanLimits,
        now_local: datetime,
        idempotency_key: str,
    ) -> QuotaState:
        """Charge one AI action, or raise `QuotaExceededError`.

        A repeated idempotency key never charges twice.
        """
        if await self.already_charged(idempotency_key):
            logger.info("usage.duplicate_idempotency_key")
            return await self.snapshot(user_id, limits=limits, now_local=now_local)

        state = await self.snapshot(user_id, limits=limits, now_local=now_local)
        if not state.allowed:
            raise QuotaExceededError(
                "Daily AI limit reached",
                details={"plan": state.plan, "remaining": 0},
            )
        if state.next_scope == "bonus":
            await self._increment(user_id, "bonus", BONUS_PERIOD_KEY)
        else:
            await self._increment(
                user_id, limits.period_scope, period_key_for(limits, now_local)
            )
        await self._session.flush()
        return await self.snapshot(user_id, limits=limits, now_local=now_local)

    async def record_operation(
        self,
        *,
        user_id: UUID,
        inbox_item_id: UUID | None,
        operation_type: str,
        usage: ProviderUsage,
        status: str = AiOperationStatus.SUCCESS.value,
        charged: bool = True,
        idempotency_key: str,
    ) -> None:
        """Append to the ledger. Duplicate keys are ignored, never duplicated."""
        stmt = (
            pg_insert(AiOperation)
            .values(
                user_id=user_id,
                inbox_item_id=inbox_item_id,
                operation_type=operation_type,
                provider=usage.provider,
                model=usage.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_micro=usage.cost_micro,
                duration_ms=usage.duration_ms,
                status=status,
                charged=charged,
                idempotency_key=idempotency_key,
            )
            .on_conflict_do_nothing(constraint="uq_ai_operations_idempotency_key")
        )
        await self._session.execute(stmt)
        await self._session.flush()
