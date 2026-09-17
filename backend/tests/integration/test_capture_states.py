"""Low-confidence behaviour against PostgreSQL."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.providers.base import CaptureContext, ParseOutcome, ProviderUsage
from onedrop.ai.schemas import CaptureResult, TaskCreateIntent, TaskFields
from onedrop.capture.service import CaptureService
from onedrop.db.models.enums import InboxStatus
from onedrop.db.models.planner import Task

pytestmark = pytest.mark.integration


class LowConfidenceProvider:
    name = "fake"

    async def parse(self, text: str, context: CaptureContext) -> ParseOutcome:
        return ParseOutcome(
            result=CaptureResult(
                language="en",
                timezone=context.timezone,
                intents=[TaskCreateIntent(type="task.create", confidence=0.1, source_fragment=text, fields=TaskFields(title="Ambiguous"))],
                needs_confirmation=True,
                clarification_question="Which date should I use?",
            ),
            usage=ProviderUsage(provider="fake", model="low", duration_ms=1),
        )


async def test_low_confidence_creates_no_domain_rows(session: AsyncSession, user) -> None:
    service = CaptureService(session, llm=LowConfidenceProvider())
    inbox = await service.create_text_capture(user_id=user.id, text="some day", idempotency_key="low-confidence-1")
    outcome = await service.process(inbox.id)
    assert outcome.status == InboxStatus.NEEDS_CONFIRMATION.value
    count = int((await session.execute(select(func.count(Task.id)).where(Task.user_id == user.id))).scalar_one())
    assert count == 0
