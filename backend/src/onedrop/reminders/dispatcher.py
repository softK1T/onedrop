"""Delivery of queued notifications.

The dispatcher is restart-safe: it reclaims locks left behind by a crashed
process, claims rows with ``FOR UPDATE SKIP LOCKED``, and only marks a row sent
after the transport confirmed the message. Failures are retried with
exponential backoff until the attempt limit turns them into ``failed``.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from onedrop.bot.notifier import notify_text
from onedrop.db.models.notifications import ScheduledNotification
from onedrop.db.models.user import User, UserSettings
from onedrop.db.session import get_sessionmaker
from onedrop.logging import get_logger
from onedrop.reminders.messages import render_notification
from onedrop.reminders.models import (
    DeliveryStatus,
    NotificationKind,
    RetryPolicy,
    require_aware,
)
from onedrop.reminders.repository import (
    DEFAULT_CLAIM_LIMIT,
    DEFAULT_LOCK_TIMEOUT,
    ScheduledNotificationRepository,
)
from onedrop.reminders.service import ReminderService, preferences_from_settings

logger = get_logger(__name__)


class Sender(Protocol):
    """Transport used to deliver a rendered notification."""

    async def __call__(self, *, telegram_user_id: int, text: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class DispatchReport:
    """Outcome of one dispatcher pass."""

    claimed: int = 0
    sent: int = 0
    retried: int = 0
    failed: int = 0
    skipped: int = 0
    released: int = 0


@dataclass(frozen=True, slots=True)
class _Claim:
    notification_id: UUID
    kind: str
    telegram_user_id: int
    locale: str
    payload: dict[str, Any]


def default_worker_id() -> str:
    """Identifier written into ``locked_by`` for observability."""
    return f"{socket.gethostname()}:{os.getpid()}"[:64]


class NotificationDispatcher:
    """Claims due notifications and delivers them."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
        *,
        sender: Sender | None = None,
        policy: RetryPolicy | None = None,
        worker_id: str | None = None,
        claim_limit: int = DEFAULT_CLAIM_LIMIT,
        lock_timeout: timedelta = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        self._sessionmaker = sessionmaker or get_sessionmaker()
        self._sender: Sender = sender or notify_text
        self._policy = policy or RetryPolicy()
        self._worker_id = worker_id or default_worker_id()
        self._claim_limit = claim_limit
        self._lock_timeout = lock_timeout

    async def run_once(self, *, now: datetime | None = None) -> DispatchReport:
        """Reclaim stale locks, claim due rows and deliver them."""
        moment = require_aware(now or datetime.now(tz=UTC), "now")
        claims, released, skipped = await self._claim(moment)
        sent = retried = failed = 0

        for claim in claims:
            delivered, error = await self._deliver(claim)
            outcome = await self._record(claim, delivered=delivered, error=error)
            if outcome == DeliveryStatus.SENT.value:
                sent += 1
            elif outcome == DeliveryStatus.FAILED.value:
                failed += 1
            else:
                retried += 1

        if claims or released:
            logger.info(
                "notifications.dispatched",
                claimed=len(claims),
                sent=sent,
                retried=retried,
                failed=failed,
                skipped=skipped,
                released=released,
            )
        return DispatchReport(
            claimed=len(claims),
            sent=sent,
            retried=retried,
            failed=failed,
            skipped=skipped,
            released=released,
        )

    async def _claim(self, moment: datetime) -> tuple[list[_Claim], int, int]:
        claims: list[_Claim] = []
        skipped = 0
        async with self._sessionmaker() as session:
            repository = ScheduledNotificationRepository(session)
            released = await repository.release_stale_locks(
                now=moment, lock_timeout=self._lock_timeout
            )
            rows = await repository.claim_due(
                worker_id=self._worker_id,
                now=moment,
                limit=self._claim_limit,
                lock_timeout=self._lock_timeout,
            )
            service = ReminderService(session)
            for row in rows:
                user = await session.get(User, row.user_id)
                settings_row = await session.scalar(
                    select(UserSettings).where(UserSettings.user_id == row.user_id)
                )
                if user is None or user.is_blocked or settings_row is None:
                    self._cancel(row)
                    skipped += 1
                    continue
                prefs = preferences_from_settings(settings_row)
                if not prefs.allows(row.kind):
                    self._cancel(row)
                    skipped += 1
                    continue
                payload = dict(row.payload or {})
                payload.setdefault("timezone", prefs.timezone)
                if row.kind == NotificationKind.MORNING_DIGEST.value:
                    payload.update(
                        await service.build_digest(row.user_id, prefs, now=moment)
                    )
                claims.append(
                    _Claim(
                        notification_id=row.id,
                        kind=row.kind,
                        telegram_user_id=user.telegram_user_id,
                        locale=user.locale,
                        payload=payload,
                    )
                )
            await session.commit()
        return claims, released, skipped

    @staticmethod
    def _cancel(row: ScheduledNotification) -> None:
        row.status = DeliveryStatus.CANCELLED.value
        row.locked_at = None
        row.locked_by = None

    async def _deliver(self, claim: _Claim) -> tuple[bool, str | None]:
        text = render_notification(claim.locale, claim.kind, claim.payload)
        try:
            delivered = await self._sender(
                telegram_user_id=claim.telegram_user_id, text=text
            )
        except Exception as exc:  # noqa: BLE001 - transport errors must be retried
            return False, f"{type(exc).__name__}: {exc}"
        return delivered, None if delivered else "transport rejected the message"

    async def _record(
        self, claim: _Claim, *, delivered: bool, error: str | None
    ) -> str:
        async with self._sessionmaker() as session:
            repository = ScheduledNotificationRepository(session)
            row = await session.get(ScheduledNotification, claim.notification_id)
            if row is None:
                await session.commit()
                return DeliveryStatus.CANCELLED.value
            now = datetime.now(tz=UTC)
            if delivered:
                await repository.mark_sent(row, now=now)
                outcome = DeliveryStatus.SENT.value
            elif self._policy.is_exhausted(row.attempts + 1):
                await repository.mark_failed(row, error=error or "delivery failed")
                outcome = DeliveryStatus.FAILED.value
            else:
                await repository.mark_retry(
                    row,
                    error=error or "delivery failed",
                    retry_at=self._policy.next_run_at(row.attempts + 1, now=now),
                )
                outcome = DeliveryStatus.PENDING.value
            await session.commit()
            return outcome
