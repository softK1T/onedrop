"""Voice and photo capture: transcription and meal estimation."""

from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.factory import build_stt_provider, build_vision_provider
from onedrop.ai.normalize import local_now
from onedrop.ai.providers.base import (
    CaptureContext,
    SpeechToTextProvider,
    VisionProvider,
)
from onedrop.ai.schemas import CaptureResult, MealCreateIntent
from onedrop.billing.plans import limits_for
from onedrop.billing.usage import UsageService
from onedrop.capture.service import CaptureOutcome, CaptureService
from onedrop.capture.writer import CaptureWriter
from onedrop.config import get_settings
from onedrop.db.models.enums import (
    AiOperationStatus,
    AiOperationType,
    InboxStatus,
    InputType,
    Plan,
)
from onedrop.db.models.inbox import InboxItem
from onedrop.db.repositories.inbox import InboxRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import ForbiddenError, NotFoundError, ProviderError, ValidationError
from onedrop.logging import get_logger
from onedrop.storage import ObjectStorage, build_object_key, validate_media

logger = get_logger(__name__)


class MediaCaptureService:
    """Handles captures that arrive as audio or an image."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        stt: SpeechToTextProvider | None = None,
        vision: VisionProvider | None = None,
        storage: ObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._inbox = InboxRepository(session)
        self._users = UserRepository(session)
        self._usage = UsageService(session)
        self._writer = CaptureWriter(session)
        self._storage = storage or ObjectStorage()
        self._stt = stt or build_stt_provider()
        self._vision = vision or build_vision_provider()

    async def create_media_capture(
        self,
        *,
        user_id: UUID,
        data: bytes,
        mime_type: str,
        input_type: str,
        idempotency_key: str,
        telegram_update_id: int | None = None,
        telegram_chat_id: int | None = None,
        telegram_message_id: int | None = None,
    ) -> InboxItem:
        """Validate, store the file and register the capture."""
        existing = await self._inbox.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        kind = "audio" if input_type == InputType.VOICE.value else "image"
        validate_media(mime_type=mime_type, size_bytes=len(data), kind=kind)
        key = build_object_key(user_id, mime_type)
        await self._storage.put(key, data, mime_type)
        item = await self._inbox.create(
            user_id=user_id,
            input_type=input_type,
            idempotency_key=idempotency_key,
            media_key=key,
            media_mime=mime_type,
            telegram_update_id=telegram_update_id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
        )
        await self._session.commit()
        return item

    async def process_voice(self, inbox_item_id: UUID) -> CaptureOutcome:
        """Transcribe, store the transcript, then run the normal text pipeline."""
        item = await self._require_item(inbox_item_id)
        if item.transcript:
            return await CaptureService(self._session).process(item.id)

        settings = get_settings()
        user_settings = await self._users.get_settings(item.user_id)
        if user_settings is None:
            user_settings = await self._users.update_settings(item.user_id, {})
        limits = limits_for(await self._plan(item.user_id), settings)
        now_local = local_now(user_settings.timezone)

        await self._inbox.set_status(item.id, InboxStatus.PROCESSING.value)
        audio = await self._storage.get(str(item.media_key))
        started = time.perf_counter()
        try:
            transcript = await self._stt.transcribe(
                audio, str(item.media_mime), language=user_settings.timezone and None
            )
        except ProviderError as exc:
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error=exc.message
            )
            await self._session.commit()
            raise

        await self._usage.record_operation(
            user_id=item.user_id,
            inbox_item_id=item.id,
            operation_type=AiOperationType.TRANSCRIBE.value,
            usage=transcript.usage,
            status=AiOperationStatus.SUCCESS.value,
            charged=False,
            idempotency_key=f"transcribe:{item.idempotency_key}",
        )
        await self._inbox.set_status(
            item.id,
            InboxStatus.QUEUED.value,
            transcript=transcript.text,
            processing_ms=int((time.perf_counter() - started) * 1000),
            provider=transcript.usage.provider,
            model=transcript.usage.model,
        )
        await self._session.commit()
        _ = limits, now_local
        return await CaptureService(self._session).process(item.id)

    async def process_image(self, inbox_item_id: UUID) -> CaptureOutcome:
        """Estimate meal nutrition from a photo. Pro plan only."""
        item = await self._require_item(inbox_item_id)
        settings = get_settings()
        user_settings = await self._users.get_settings(item.user_id)
        if user_settings is None:
            user_settings = await self._users.update_settings(item.user_id, {})
        plan = await self._plan(item.user_id)
        limits = limits_for(plan, settings)
        if not limits.photo_recognition:
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error="photo_requires_pro"
            )
            await self._session.commit()
            raise ForbiddenError(
                "Food photo recognition is part of the Pro plan",
                details={"plan": plan, "feature": "photo_recognition"},
            )

        now_local = local_now(user_settings.timezone)
        quota = await self._usage.reserve(
            item.user_id,
            limits=limits,
            now_local=now_local,
            idempotency_key=f"vision:{item.idempotency_key}",
        )

        await self._inbox.set_status(item.id, InboxStatus.PROCESSING.value)
        image = await self._storage.get(str(item.media_key))
        started = time.perf_counter()
        try:
            vision = await self._vision.analyze_meal(
                image,
                str(item.media_mime),
                CaptureContext(
                    timezone=user_settings.timezone,
                    locale=settings.default_locale,
                    base_currency=user_settings.base_currency,
                    now_local=now_local,
                ),
            )
        except ProviderError as exc:
            await self._inbox.set_status(
                item.id, InboxStatus.FAILED.value, error=exc.message
            )
            await self._session.commit()
            raise

        await self._usage.record_operation(
            user_id=item.user_id,
            inbox_item_id=item.id,
            operation_type=AiOperationType.VISION.value,
            usage=vision.usage,
            status=AiOperationStatus.SUCCESS.value,
            charged=True,
            idempotency_key=f"vision:{item.idempotency_key}",
        )

        if vision.fields.calories is None or vision.confidence < settings.ai_min_confidence:
            await self._inbox.set_status(
                item.id,
                InboxStatus.NEEDS_CONFIRMATION.value,
                clarification_question="What was on the plate? The photo estimate is unclear.",
            )
            await self._session.commit()
            return CaptureOutcome(
                inbox_item_id=item.id,
                status=InboxStatus.NEEDS_CONFIRMATION.value,
                created=(),
                clarification_question="What was on the plate?",
                remaining_ai=quota.remaining,
            )

        result = CaptureResult(
            language=settings.default_locale,
            timezone=user_settings.timezone,
            intents=[
                MealCreateIntent(
                    type="meal.create",
                    confidence=vision.confidence,
                    source_fragment="photo",
                    fields=vision.fields,
                )
            ],
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
                    inbox_item_id=item.id, entity_type=entity_type, entity_id=entity_id
                )
            await self._inbox.set_status(
                item.id,
                InboxStatus.COMPLETED.value,
                ai_result=result.model_dump(mode="json"),
                processing_ms=int((time.perf_counter() - started) * 1000),
                ai_cost_micro=vision.usage.cost_micro,
                provider=vision.usage.provider,
                model=vision.usage.model,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
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

    async def _require_item(self, inbox_item_id: UUID) -> InboxItem:
        item = await self._inbox.get(inbox_item_id)
        if item is None:
            raise NotFoundError("Capture not found")
        if not item.media_key:
            raise ValidationError("capture has no stored media")
        return item

    async def _plan(self, user_id: UUID) -> str:
        from sqlalchemy import select

        from onedrop.db.models.billing import Subscription

        stmt = select(Subscription).where(
            Subscription.user_id == user_id, Subscription.status == "active"
        )
        result = await self._session.execute(stmt)
        subscription = result.scalars().first()
        return subscription.plan if subscription is not None else Plan.FREE.value
