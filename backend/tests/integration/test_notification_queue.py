"""Durable notification queue against a real PostgreSQL instance.

These tests prove the properties the pure unit tests cannot: uniqueness of the
dedup key at the database level, row-level claiming with ``SKIP LOCKED``,
recovery of locks left behind by a killed worker, retry backoff and the attempt
limit.
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from onedrop.config import get_settings
from onedrop.db.base import Base
from onedrop.db.models.notifications import ScheduledNotification
from onedrop.db.models.user import User, UserSettings
from onedrop.reminders.dispatcher import NotificationDispatcher
from onedrop.reminders.models import (
    DeliveryStatus,
    NotificationKind,
    RetryPolicy,
    dedup_key,
)
from onedrop.reminders.repository import ScheduledNotificationRepository

pytestmark = pytest.mark.integration

TABLES = [
    User.__table__,
    UserSettings.__table__,
    ScheduledNotification.__table__,
]
KIND = NotificationKind.TASK_REMINDER.value
ENTITY = UUID("33333333-3333-3333-3333-333333333333")


class RecordingSender:
    """Transport double that records every delivery attempt."""

    def __init__(self, *, result: bool = True) -> None:
        self.result = result
        self.calls: list[tuple[int, str]] = []

    async def __call__(self, *, telegram_user_id: int, text: str) -> bool:
        self.calls.append((telegram_user_id, text))
        return self.result


class ExplodingSender:
    """Transport double that always raises, to exercise error handling."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, *, telegram_user_id: int, text: str) -> bool:
        self.calls += 1
        raise RuntimeError("telegram is unreachable")


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    created = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with created.begin() as connection:
            await connection.run_sync(Base.metadata.create_all, tables=TABLES)
    except (SQLAlchemyError, OSError) as exc:
        await created.dispose()
        pytest.skip(f"PostgreSQL is not available: {type(exc).__name__}")
    yield created
    await created.dispose()


@pytest.fixture
def maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def user_id(maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[UUID]:
    async with maker() as session:
        user = User(
            telegram_user_id=random.randint(1_000_000_000, 1_999_999_999),
            locale="en",
        )
        session.add(user)
        await session.flush()
        session.add(
            UserSettings(
                user_id=user.id,
                timezone="Europe/Warsaw",
                quiet_hours_start=0,
                quiet_hours_end=0,
            )
        )
        await session.commit()
        created = user.id
    yield created
    async with maker() as session:
        await session.execute(
            delete(ScheduledNotification).where(ScheduledNotification.user_id == created)
        )
        await session.execute(delete(UserSettings).where(UserSettings.user_id == created))
        await session.execute(delete(User).where(User.id == created))
        await session.commit()


def _payload() -> dict[str, str]:
    return {
        "title": "Pay rent",
        "moment": "2026-09-18T15:00:00+00:00",
        "timezone": "Europe/Warsaw",
    }


async def _enqueue(
    maker: async_sessionmaker[AsyncSession],
    user_id: UUID,
    *,
    run_at: datetime,
    entity_id: UUID = ENTITY,
) -> UUID | None:
    async with maker() as session:
        created = await ScheduledNotificationRepository(session).enqueue(
            user_id=user_id,
            kind=KIND,
            run_at=run_at,
            dedup_key=dedup_key(KIND, user_id, entity_id, run_at),
            payload=_payload(),
        )
        await session.commit()
        return created


async def _row(
    maker: async_sessionmaker[AsyncSession], notification_id: UUID
) -> ScheduledNotification:
    async with maker() as session:
        row = await session.get(ScheduledNotification, notification_id)
        assert row is not None
        return row


async def _count(maker: async_sessionmaker[AsyncSession], user_id: UUID) -> int:
    async with maker() as session:
        total = await session.scalar(
            select(func.count())
            .select_from(ScheduledNotification)
            .where(ScheduledNotification.user_id == user_id)
        )
        return int(total or 0)


async def test_enqueue_is_idempotent_by_dedup_key(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    run_at = datetime.now(tz=UTC) + timedelta(hours=1)
    first = await _enqueue(maker, user_id, run_at=run_at)
    second = await _enqueue(maker, user_id, run_at=run_at)
    assert first is not None
    assert second is None
    assert await _count(maker, user_id) == 1


async def test_only_due_rows_are_claimed_and_locked(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    due = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=5))
    await _enqueue(
        maker,
        user_id,
        run_at=now + timedelta(hours=3),
        entity_id=UUID("44444444-4444-4444-4444-444444444444"),
    )
    async with maker() as session:
        claimed = await ScheduledNotificationRepository(session).claim_due(
            worker_id="worker-a", now=now
        )
        ids = [row.id for row in claimed]
        await session.commit()
    assert ids == [due]
    row = await _row(maker, ids[0])
    assert row.locked_by == "worker-a"
    assert row.locked_at is not None


async def test_a_second_worker_skips_locked_rows(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    await _enqueue(maker, user_id, run_at=now - timedelta(minutes=5))
    async with maker() as first_session:
        first = await ScheduledNotificationRepository(first_session).claim_due(
            worker_id="worker-a", now=now
        )
        assert len(first) == 1
        async with maker() as second_session:
            second = await ScheduledNotificationRepository(second_session).claim_due(
                worker_id="worker-b", now=now
            )
            assert second == []
            await second_session.rollback()
        await first_session.commit()


async def test_locks_left_by_a_killed_worker_are_reclaimed(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    notification_id = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=30))
    assert notification_id is not None

    async with maker() as session:
        await ScheduledNotificationRepository(session).claim_due(
            worker_id="worker-crashed", now=now
        )
        await session.commit()

    later = now + timedelta(minutes=10)
    async with maker() as session:
        repository = ScheduledNotificationRepository(session)
        released = await repository.release_stale_locks(
            now=later, lock_timeout=timedelta(minutes=5)
        )
        await session.commit()
    assert released == 1

    sender = RecordingSender()
    report = await NotificationDispatcher(maker, sender=sender).run_once(now=later)
    assert report.claimed == 1
    assert report.sent == 1
    row = await _row(maker, notification_id)
    assert row.status == DeliveryStatus.SENT.value
    assert row.locked_at is None


async def test_dispatcher_delivers_rendered_text_and_marks_sent(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    notification_id = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=1))
    assert notification_id is not None
    sender = RecordingSender()
    report = await NotificationDispatcher(maker, sender=sender).run_once(now=now)
    assert report.sent == 1
    assert len(sender.calls) == 1
    assert "Pay rent" in sender.calls[0][1]
    row = await _row(maker, notification_id)
    assert row.status == DeliveryStatus.SENT.value
    assert row.attempts == 1
    assert row.last_error is None


async def test_a_rejected_delivery_is_retried_with_backoff(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    notification_id = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=1))
    assert notification_id is not None
    dispatcher = NotificationDispatcher(
        maker,
        sender=RecordingSender(result=False),
        policy=RetryPolicy(max_attempts=3, base_delay_seconds=60),
    )
    report = await dispatcher.run_once(now=now)
    assert report.retried == 1
    row = await _row(maker, notification_id)
    assert row.status == DeliveryStatus.PENDING.value
    assert row.attempts == 1
    assert row.run_at > now
    assert row.locked_by is None
    assert row.last_error is not None


async def test_a_raising_transport_is_recorded_and_retried(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    notification_id = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=1))
    assert notification_id is not None
    sender = ExplodingSender()
    dispatcher = NotificationDispatcher(
        maker, sender=sender, policy=RetryPolicy(max_attempts=3)
    )
    report = await dispatcher.run_once(now=now)
    assert sender.calls == 1
    assert report.retried == 1
    row = await _row(maker, notification_id)
    assert row.status == DeliveryStatus.PENDING.value
    assert "RuntimeError" in str(row.last_error)


async def test_delivery_fails_permanently_after_the_attempt_limit(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    notification_id = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=1))
    assert notification_id is not None
    dispatcher = NotificationDispatcher(
        maker,
        sender=RecordingSender(result=False),
        policy=RetryPolicy(max_attempts=1),
    )
    report = await dispatcher.run_once(now=now)
    assert report.failed == 1
    row = await _row(maker, notification_id)
    assert row.status == DeliveryStatus.FAILED.value
    assert row.attempts == 1


async def test_a_disabled_kind_is_cancelled_instead_of_sent(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    notification_id = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=1))
    assert notification_id is not None
    async with maker() as session:
        settings_row = await session.scalar(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        assert settings_row is not None
        settings_row.task_reminders = False
        await session.commit()

    sender = RecordingSender()
    report = await NotificationDispatcher(maker, sender=sender).run_once(now=now)
    assert report.claimed == 0
    assert report.skipped == 1
    assert sender.calls == []
    row = await _row(maker, notification_id)
    assert row.status == DeliveryStatus.CANCELLED.value


async def test_a_restarted_dispatcher_drains_the_remaining_backlog(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    first = await _enqueue(maker, user_id, run_at=now - timedelta(minutes=10))
    second = await _enqueue(
        maker,
        user_id,
        run_at=now - timedelta(minutes=5),
        entity_id=UUID("55555555-5555-5555-5555-555555555555"),
    )
    assert first is not None and second is not None

    sender = RecordingSender()
    first_pass = await NotificationDispatcher(
        maker, sender=sender, claim_limit=1
    ).run_once(now=now)
    assert first_pass.sent == 1

    second_pass = await NotificationDispatcher(maker, sender=sender).run_once(now=now)
    assert second_pass.sent == 1
    assert len(sender.calls) == 2
    assert (await _row(maker, first)).status == DeliveryStatus.SENT.value
    assert (await _row(maker, second)).status == DeliveryStatus.SENT.value


async def test_cancelling_an_entity_clears_only_pending_rows(
    maker: async_sessionmaker[AsyncSession], user_id: UUID
) -> None:
    now = datetime.now(tz=UTC)
    pending = await _enqueue(maker, user_id, run_at=now + timedelta(hours=2))
    assert pending is not None
    async with maker() as session:
        cancelled = await ScheduledNotificationRepository(session).cancel_pending(
            kind=KIND, user_id=user_id, entity_id=ENTITY
        )
        await session.commit()
    assert cancelled == 1
    assert (await _row(maker, pending)).status == DeliveryStatus.CANCELLED.value

    sender = RecordingSender()
    report = await NotificationDispatcher(maker, sender=sender).run_once(
        now=now + timedelta(hours=3)
    )
    assert report.claimed == 0
    assert sender.calls == []
