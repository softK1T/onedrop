"""Capture use cases: create, process, correct, undo and retry."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.factory import build_structured_provider
from onedrop.ai.normalize import local_now, normalise_capture_result
from onedrop.ai.providers.base import CaptureContext, StructuredLLMProvider
from onedrop.ai.schemas import CaptureResult
from onedrop.billing.plans import limits_for
from onedrop.billing.usage import UsageService
from onedrop.capture.writer import CaptureWriter, CreatedEntity
from onedrop.config import get_settings
from onedrop.db.models.enums import (
    AiOperationStatus,
    AiOperationType,
    EntityType,
    InboxStatus,
    InputType,
    Plan,
)
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog, Meal
from onedrop.db.models.inbox import InboxItem
from onedrop.db.models.notes import Note
from onedrop.db.models.planner import Event, Task
from onedrop.db.repositories.inbox import InboxRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import ConflictError, NotFoundError, ProviderError, QuotaExceededError
from onedrop.logging import get_logger
from onedrop.reminders.models import NotificationKind
from onedrop.reminders.service import ReminderService

logger = get_logger(__name__)

SOFT_DELETABLE = {
    EntityType.TASK.value: Task,
    EntityType.EVENT.value: Event,
    EntityType.EXPENSE.value: Expense,
    EntityType.MEAL.value: Meal,
    EntityType.NOTE.value: Note,
    EntityType.HABIT.value: Habit,
}

NOTIFICATION_KIND_BY_ENTITY = {
    EntityType.TASK.value: NotificationKind.TASK_REMINDER.value,
    EntityType.EVENT.value: NotificationKind.EVENT_REMINDER.value,
    EntityType.HABIT.value: NotificationKind.HABIT_REMINDER.value,
}

CORRECTABLE_STATUSES = {
    InboxStatus.NEEDS_CONFIRMATION.value,
    InboxStatus.COMPLETED.value,
}


@dataclass(frozen=True, slots=True)
class CaptureOutcome:
    inbox_item_id: UUID
    status: str
    created: tuple[CreatedEntity, ...]
    clarification_question: str | None
    remaining_ai: int


class CaptureService:
    """Application service for the universal capture flow."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        llm: StructuredLLMProvider | None = None,
    ) -> None:
        self._session = session
        self._inbox = InboxRepository(session)
        self._users = UserRepository(session)
        self._usage = UsageService(session)
        self._writer = CaptureWriter(session)
        self._llm = llm or build_structured_provider()

    async def create_text_capture(
        self,
        *,
        user_id: UUID,
        text: str,
        idempotency_key: str,
        telegram_update_id: int | None = None,
        telegram_chat_id: int | None = None,
        telegram_message_id: int | None = None,
    ) -> InboxItem:
        """Store the capture. Returns the existing item for a repeated key."""
        existing = await self._inbox.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        item = await self._inbox.create(
            user_id=user_id,
            input_type=InputType.TEXT.value,
            idempotency_key=idempotency_key,
            raw_text=text,
            telegram_update_id=telegram_update_id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
        )
        await self._session.commit()
        return item

    async def process(self, inbox_item_id: UUID) -> CaptureOutcome:
        """Run the AI step and write records atomically."""
        item = await self._inbox.get(inbox_item_id)
        if item is None:
            raise NotFoundError("Capture not found")
        if item.status in {InboxStatus.COMPLETED.value, InboxStatus.UNDONE.value}:
            return await self._outcome(item)

        settings = get_settings()
        user_settings = await self._users.get_settings(item.user_id)
        if user_settings is None:
            user_settings = await self._users.update_settings(item.user_id, {})
        plan = await self._current_plan(item.user_id)
        limits = limits_for(plan, settings)
        now_local = local_now(user_settings.timezone)

        await self._inbox.set_status(item.id, InboxStatus.PROCESSING.value)
        await self._inbox.increment_attempts(item.id)

        text = item.transcript or item.raw_text or ""
        if not text.strip():
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error="empty_capture"
            )
            await self._session.commit()
            return await self._outcome(item)

        try:
            quota = await self._usage.reserve(
                item.user_id,
                limits=limits,
                now_local=now_local,
                idempotency_key=f"parse:{item.idempotency_key}",
            )
        except QuotaExceededError:
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error="quota_exceeded"
            )
            await self._session.commit()
            raise

        started = time.perf_counter()
        try:
            outcome = await self._llm.parse(
                text,
                CaptureContext(
                    timezone=user_settings.timezone,
                    locale=settings.default_locale,
                    base_currency=user_settings.base_currency,
                    now_local=now_local,
                    habits=await self._habit_names(item.user_id),
                ),
            )
        except ProviderError as exc:
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error=str(exc.message)
            )
            await self._session.commit()
            raise

        result = normalise_capture_result(outcome.result, timezone=user_settings.timezone)
        processing_ms = int((time.perf_counter() - started) * 1000)
        await self._usage.record_operation(
            user_id=item.user_id,
            inbox_item_id=item.id,
            operation_type=AiOperationType.PARSE.value,
            usage=outcome.usage,
            status=AiOperationStatus.SUCCESS.value,
            charged=True,
            idempotency_key=f"parse:{item.idempotency_key}",
        )

        needs_confirmation = (
            result.needs_confirmation
            or (
                result.actionable_intents
                and result.min_confidence() < settings.ai_min_confidence
            )
        )
        if needs_confirmation:
            await self._inbox.set_status(
                item.id,
                InboxStatus.NEEDS_CONFIRMATION.value,
                ai_result=result.model_dump(mode="json"),
                clarification_question=result.clarification_question
                or "Please confirm the details of this capture.",
                processing_ms=processing_ms,
                ai_cost_micro=outcome.usage.cost_micro,
                provider=outcome.usage.provider,
                model=outcome.usage.model,
            )
            await self._session.commit()
            return CaptureOutcome(
                inbox_item_id=item.id,
                status=InboxStatus.NEEDS_CONFIRMATION.value,
                created=(),
                clarification_question=result.clarification_question,
                remaining_ai=quota.remaining,
            )

        try:
            created = await self._writer.apply(
                user_id=item.user_id,
                settings=user_settings,
                inbox_item_id=item.id,
                result=result,
            )
            for entity_type, entity_id in created:
                await self._inbox.add_link(
                    inbox_item_id=item.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            await self._inbox.set_status(
                item.id,
                InboxStatus.COMPLETED.value,
                ai_result=result.model_dump(mode="json"),
                processing_ms=processing_ms,
                ai_cost_micro=outcome.usage.cost_micro,
                provider=outcome.usage.provider,
                model=outcome.usage.model,
            )
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            logger.warning(
                "capture.apply_failed",
                inbox_item_id=str(item.id),
                error_type=type(exc).__name__,
            )
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error="apply_failed"
            )
            await self._session.commit()
            raise

        return CaptureOutcome(
            inbox_item_id=item.id,
            status=InboxStatus.COMPLETED.value,
            created=tuple(created),
            clarification_question=None,
            remaining_ai=quota.remaining,
        )

    async def correct(
        self, *, user_id: UUID, inbox_item_id: UUID, result: CaptureResult
    ) -> CaptureOutcome:
        """Atomically replace records with a user-confirmed structured result."""
        item = await self._inbox.get_for_update(inbox_item_id, user_id=user_id)
        if item is None:
            raise NotFoundError("Capture not found")
        if item.status not in CORRECTABLE_STATUSES:
            raise ConflictError("Capture cannot be corrected in its current state")

        user_settings = await self._users.get_settings(user_id)
        if user_settings is None:
            user_settings = await self._users.update_settings(user_id, {})
        corrected = normalise_capture_result(result, timezone=user_settings.timezone)
        result_json = corrected.model_dump(mode="json")

        if item.status == InboxStatus.COMPLETED.value and item.ai_result == result_json:
            return await self._outcome(item)

        old_links = await self._inbox.links(item.id)
        try:
            created = await self._writer.apply(
                user_id=user_id,
                settings=user_settings,
                inbox_item_id=item.id,
                result=corrected,
            )
            retained = set(created)
            for link in old_links:
                if (link.entity_type, link.entity_id) not in retained:
                    await self._remove_owned_entity(
                        item=item,
                        entity_type=link.entity_type,
                        entity_id=link.entity_id,
                    )
            await self._inbox.replace_links(item.id, created)
            await self._inbox.complete_correction(item.id, ai_result=result_json)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        return CaptureOutcome(
            inbox_item_id=item.id,
            status=InboxStatus.COMPLETED.value,
            created=tuple(created),
            clarification_question=None,
            remaining_ai=0,
        )

    async def _remove_owned_entity(
        self, *, item: InboxItem, entity_type: str, entity_id: UUID
    ) -> None:
        if entity_type == EntityType.HABIT_LOG.value:
            await self._session.execute(
                HabitLog.__table__.delete().where(
                    HabitLog.__table__.c.id == entity_id,
                    HabitLog.__table__.c.user_id == item.user_id,
                    HabitLog.__table__.c.source_inbox_item_id == item.id,
                )
            )
            return

        model = SOFT_DELETABLE.get(entity_type)
        if model is None:
            return
        removal = await self._session.execute(
            update(model)
            .where(
                model.id == entity_id,
                model.user_id == item.user_id,
                model.source_inbox_item_id == item.id,
                model.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(tz=UTC))
        )
        if not removal.rowcount:
            return
        kind = NOTIFICATION_KIND_BY_ENTITY.get(entity_type)
        if kind is not None:
            await ReminderService(self._session).cancel_for_entity(
                kind=kind,
                user_id=item.user_id,
                entity_id=entity_id,
            )

    async def undo(self, *, user_id: UUID, inbox_item_id: UUID) -> int:
        """Atomically revert every record created by one capture."""
        item = await self._inbox.get(inbox_item_id, user_id=user_id)
        if item is None:
            raise NotFoundError("Capture not found")
        links = await self._inbox.links(item.id)
        moment = datetime.now(tz=UTC)
        reverted = 0
        try:
            for link in links:
                if link.entity_type == EntityType.HABIT_LOG.value:
                    removal = await self._session.execute(
                        HabitLog.__table__.delete().where(
                            HabitLog.__table__.c.id == link.entity_id,
                            HabitLog.__table__.c.user_id == user_id,
                            HabitLog.__table__.c.source_inbox_item_id == item.id,
                        )
                    )
                    reverted += int(removal.rowcount or 0)
                    continue
                model = SOFT_DELETABLE.get(link.entity_type)
                if model is None:
                    continue
                removal = await self._session.execute(
                    update(model)
                    .where(
                        model.id == link.entity_id,
                        model.user_id == user_id,
                        model.source_inbox_item_id == item.id,
                        model.deleted_at.is_(None),
                    )
                    .values(deleted_at=moment)
                )
                reverted += int(removal.rowcount or 0)
            await self._inbox.mark_undone(item.id)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        return reverted

    async def retry(self, *, user_id: UUID, inbox_item_id: UUID) -> CaptureOutcome:
        item = await self._inbox.get(inbox_item_id, user_id=user_id)
        if item is None:
            raise NotFoundError("Capture not found")
        await self._inbox.set_status(item.id, InboxStatus.QUEUED.value, error=None)
        await self._session.commit()
        return await self.process(item.id)

    async def _current_plan(self, user_id: UUID) -> str:
        from onedrop.db.models.billing import Subscription

        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
        result = await self._session.execute(stmt)
        subscription = result.scalars().first()
        if subscription is None:
            return Plan.FREE.value
        if (
            subscription.expires_at is not None
            and subscription.expires_at < datetime.now(tz=UTC)
        ):
            return Plan.FREE.value
        return subscription.plan

    async def _habit_names(self, user_id: UUID) -> tuple[str, ...]:
        stmt = select(Habit.name).where(
            Habit.user_id == user_id,
            Habit.active.is_(True),
            Habit.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return tuple(result.scalars().all())

    async def _outcome(self, item: InboxItem) -> CaptureOutcome:
        links = await self._inbox.links(item.id)
        return CaptureOutcome(
            inbox_item_id=item.id,
            status=item.status,
            created=tuple((link.entity_type, link.entity_id) for link in links),
            clarification_question=item.clarification_question,
            remaining_ai=0,
        )
