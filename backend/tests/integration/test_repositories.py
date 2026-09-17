"""Repository idempotency, ownership isolation and soft deletion."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.enums import InputType
from onedrop.db.repositories.inbox import InboxRepository
from onedrop.db.repositories.tasks import TaskRepository
from onedrop.db.repositories.users import UserRepository

pytestmark = pytest.mark.integration


async def test_inbox_idempotency_key_is_unique(session: AsyncSession, user) -> None:
    inbox = InboxRepository(session)
    first = await inbox.create(
        user_id=user.id,
        input_type=InputType.TEXT.value,
        raw_text="hello",
        idempotency_key="integration-duplicate-key",
    )
    await session.commit()
    duplicate = await inbox.get_by_idempotency_key("integration-duplicate-key")
    assert duplicate is not None
    assert duplicate.id == first.id


async def test_ownership_isolation_returns_nothing(session: AsyncSession, user) -> None:
    other = await UserRepository(session).upsert_from_telegram(
        telegram_user_id=777002,
        first_name="Other",
        username=None,
        language_code="en",
    )
    task = await TaskRepository(session).create(
        user_id=user.id, values={"title": "private task"}
    )
    await session.commit()
    assert await TaskRepository(session).get(task.id, other.id) is None


async def test_soft_deleted_task_leaves_lists(session: AsyncSession, user) -> None:
    repository = TaskRepository(session)
    task = await repository.create(user_id=user.id, values={"title": "remove me"})
    await repository.soft_delete(task)
    await session.commit()
    assert await repository.get(task.id, user.id) is None


async def test_payment_charge_id_is_unique(session: AsyncSession, user) -> None:
    from onedrop.db.repositories.billing import BillingRepository

    billing = BillingRepository(session)
    first = await billing.record_payment(
        user_id=user.id,
        telegram_payment_charge_id="charge-integration-001",
        invoice_payload="onedrop:pro:" + str(user.id) + ":abc",
        amount_stars=250,
        plan="pro",
        period_days=30,
    )
    await session.commit()
    second = await billing.record_payment(
        user_id=user.id,
        telegram_payment_charge_id="charge-integration-001",
        invoice_payload="onedrop:pro:" + str(user.id) + ":abc",
        amount_stars=250,
        plan="pro",
        period_days=30,
    )
    assert first is not None
    assert second is None


async def test_redis_fixture_is_real(redis_client) -> None:
    await redis_client.set("integration", "ok")
    assert await redis_client.get("integration") == b"ok"
