"""Capture correction behaviour against PostgreSQL."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.schemas import (
    CaptureResult,
    HabitCreateFields,
    HabitCreateIntent,
    TaskCreateIntent,
    TaskFields,
)
from onedrop.capture.schemas import CaptureCorrectionRequest
from onedrop.capture.service import CaptureService
from onedrop.db.models.enums import InboxStatus
from onedrop.db.models.health import Habit
from onedrop.db.models.planner import Task
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import ConflictError, NotFoundError

pytestmark = pytest.mark.integration


def task_result(title: str, *, confidence: float = 1.0) -> CaptureResult:
    return CaptureResult(
        language="en",
        timezone="Europe/Warsaw",
        intents=[
            TaskCreateIntent(
                type="task.create",
                confidence=confidence,
                source_fragment=title,
                fields=TaskFields(title=title),
            )
        ],
    )


async def create_capture(
    session: AsyncSession,
    user,
    *,
    key: str,
    status: str,
    ai_result: dict | None = None,
):
    service = CaptureService(session)
    item = await service.create_text_capture(
        user_id=user.id,
        text="ambiguous capture",
        idempotency_key=key,
    )
    from onedrop.db.repositories.inbox import InboxRepository

    await InboxRepository(session).set_status(
        item.id,
        status,
        ai_result=ai_result,
        clarification_question=(
            "What did you mean?"
            if status == InboxStatus.NEEDS_CONFIRMATION.value
            else None
        ),
    )
    await session.commit()
    return item


async def test_needs_confirmation_can_be_corrected(
    session: AsyncSession, user
) -> None:
    item = await create_capture(
        session,
        user,
        key="correction-needs-confirmation",
        status=InboxStatus.NEEDS_CONFIRMATION.value,
    )

    outcome = await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=task_result("Buy milk"),
    )

    assert outcome.status == InboxStatus.COMPLETED.value
    assert len(outcome.created) == 1
    task = await session.scalar(
        select(Task).where(
            Task.user_id == user.id,
            Task.source_inbox_item_id == item.id,
            Task.deleted_at.is_(None),
        )
    )
    assert task is not None
    assert task.title == "Buy milk"
    await session.refresh(item)
    assert item.clarification_question is None
    assert item.error is None


async def test_completed_capture_replaces_its_task(
    session: AsyncSession, user
) -> None:
    item = await create_capture(
        session,
        user,
        key="correction-replace-task",
        status=InboxStatus.NEEDS_CONFIRMATION.value,
    )
    first = await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=task_result("Old title"),
    )
    old_task_id = first.created[0][1]

    second = await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=task_result("New title"),
    )

    old_task = await session.get(Task, old_task_id)
    assert old_task is not None
    assert old_task.deleted_at is not None
    new_task = await session.get(Task, second.created[0][1])
    assert new_task is not None
    assert new_task.title == "New title"
    assert new_task.deleted_at is None


async def test_identical_completed_correction_is_idempotent(
    session: AsyncSession, user
) -> None:
    result = task_result("Keep one task")
    item = await create_capture(
        session,
        user,
        key="correction-idempotent",
        status=InboxStatus.NEEDS_CONFIRMATION.value,
    )
    first = await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=result,
    )

    second = await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=result,
    )

    assert second.created == first.created
    tasks = list(
        (
            await session.execute(
                select(Task).where(
                    Task.user_id == user.id,
                    Task.source_inbox_item_id == item.id,
                    Task.deleted_at.is_(None),
                )
            )
        ).scalars()
    )
    assert len(tasks) == 1


async def test_correction_rejects_another_users_capture(
    session: AsyncSession, user
) -> None:
    item = await create_capture(
        session,
        user,
        key="correction-ownership",
        status=InboxStatus.NEEDS_CONFIRMATION.value,
    )
    other = await UserRepository(session).upsert_from_telegram(
        telegram_user_id=777099,
        first_name="Other correction user",
        username=None,
        language_code="en",
    )
    await session.commit()

    with pytest.raises(NotFoundError):
        await CaptureService(session).correct(
            user_id=other.id,
            inbox_item_id=item.id,
            result=task_result("Not allowed"),
        )


async def test_correction_rejects_processing_capture(
    session: AsyncSession, user
) -> None:
    item = await create_capture(
        session,
        user,
        key="correction-processing",
        status=InboxStatus.PROCESSING.value,
    )

    with pytest.raises(ConflictError):
        await CaptureService(session).correct(
            user_id=user.id,
            inbox_item_id=item.id,
            result=task_result("Too early"),
        )


async def test_correction_does_not_delete_preexisting_habit(
    session: AsyncSession, user
) -> None:
    habit = Habit(user_id=user.id, name="Read", measurement_type="boolean")
    session.add(habit)
    await session.commit()
    item = await create_capture(
        session,
        user,
        key="correction-existing-habit",
        status=InboxStatus.NEEDS_CONFIRMATION.value,
    )
    habit_result = CaptureResult(
        language="en",
        timezone="Europe/Warsaw",
        intents=[
            HabitCreateIntent(
                type="habit.create",
                confidence=1.0,
                source_fragment="Read",
                fields=HabitCreateFields(name="Read"),
            )
        ],
    )
    first = await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=habit_result,
    )
    assert first.created[0][1] == habit.id

    await CaptureService(session).correct(
        user_id=user.id,
        inbox_item_id=item.id,
        result=task_result("Read a chapter"),
    )

    await session.refresh(habit)
    assert habit.deleted_at is None
    assert habit.source_inbox_item_id is None


def test_correction_schema_requires_actionable_confirmed_result() -> None:
    with pytest.raises(ValueError):
        CaptureCorrectionRequest(
            result=CaptureResult(
                language="en",
                timezone="Europe/Warsaw",
                needs_confirmation=True,
                clarification_question="Confirm?",
            )
        )

    with pytest.raises(ValueError):
        CaptureCorrectionRequest(
            result=CaptureResult(
                language="en",
                timezone="Europe/Warsaw",
                intents=[],
            )
        )
