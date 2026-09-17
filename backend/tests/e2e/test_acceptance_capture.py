"""Mandatory OneDrop acceptance scenario.

The full flow uses real PostgreSQL and the deterministic fake provider:

"Завтра в 15:00 встреча с Андреем, потратил 45 злотых на такси
и нужно оплатить интернет"

must create exactly one event, expense and task, link all records to one inbox
item, ignore repeated delivery and atomically undo all three.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.providers.base import CaptureContext, ParseOutcome, ProviderUsage
from onedrop.ai.providers.fake_rules import parse_text
from onedrop.capture.service import CaptureService
from onedrop.db.models.enums import InboxStatus
from onedrop.db.models.finance import Expense
from onedrop.db.models.inbox import InboxEntityLink
from onedrop.db.models.planner import Event, Task

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

TEXT = (
    "Завтра в 15:00 встреча с Андреем, потратил 45 злотых на такси "
    "и нужно оплатить интернет"
)


class FixedFakeProvider:
    """Deterministic provider with a fixed reference time for acceptance."""

    name = "fake"

    async def parse(self, text: str, context: CaptureContext) -> ParseOutcome:
        fixed = CaptureContext(
            timezone="Europe/Warsaw",
            locale="ru",
            base_currency="PLN",
            now_local=datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        )
        return ParseOutcome(
            result=parse_text(text, fixed),
            usage=ProviderUsage(provider="fake", model="acceptance", duration_ms=1),
        )


async def test_multi_intent_capture_idempotency_and_undo(
    session: AsyncSession, user
) -> None:
    service = CaptureService(session, llm=FixedFakeProvider())
    inbox = await service.create_text_capture(
        user_id=user.id,
        text=TEXT,
        idempotency_key="acceptance-update-9001",
        telegram_update_id=9001,
    )
    outcome = await service.process(inbox.id)
    assert outcome.status == InboxStatus.COMPLETED.value
    assert len(outcome.created) == 3

    events = list((await session.execute(select(Event).where(Event.user_id == user.id))).scalars())
    expenses = list((await session.execute(select(Expense).where(Expense.user_id == user.id))).scalars())
    tasks = list((await session.execute(select(Task).where(Task.user_id == user.id))).scalars())
    links = list((await session.execute(select(InboxEntityLink).where(InboxEntityLink.inbox_item_id == inbox.id))).scalars())
    assert len(events) == 1
    assert len(expenses) == 1
    assert len(tasks) == 1
    assert expenses[0].amount_minor == 4500
    assert expenses[0].currency == "PLN"
    assert len(links) == 3
    assert {link.entity_type for link in links} == {"event", "expense", "task"}

    repeated = await service.create_text_capture(
        user_id=user.id,
        text=TEXT,
        idempotency_key="acceptance-update-9001",
        telegram_update_id=9001,
    )
    assert repeated.id == inbox.id
    second_outcome = await service.process(repeated.id)
    assert len(second_outcome.created) == 3

    for model in (Event, Expense, Task):
        count = int((await session.execute(select(func.count(model.id)).where(model.user_id == user.id))).scalar_one())
        assert count == 1

    reverted = await service.undo(user_id=user.id, inbox_item_id=inbox.id)
    assert reverted == 3
    for model in (Event, Expense, Task):
        active = int((await session.execute(select(func.count(model.id)).where(model.user_id == user.id, model.deleted_at.is_(None)))).scalar_one())
        assert active == 0
