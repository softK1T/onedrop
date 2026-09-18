"""Inbox item persistence: captures, entity links and feedback."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.enums import InboxStatus
from onedrop.db.models.inbox import InboxEntityLink, InboxItem, UserFeedback

MAX_PAGE_SIZE = 100


class InboxRepository:
    """All inbox queries are scoped by `user_id`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        input_type: str,
        idempotency_key: str,
        raw_text: str | None = None,
        media_key: str | None = None,
        media_mime: str | None = None,
        telegram_update_id: int | None = None,
        telegram_chat_id: int | None = None,
        telegram_message_id: int | None = None,
    ) -> InboxItem:
        item = InboxItem(
            user_id=user_id,
            input_type=input_type,
            idempotency_key=idempotency_key,
            raw_text=raw_text,
            media_key=media_key,
            media_mime=media_mime,
            telegram_update_id=telegram_update_id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            status=InboxStatus.RECEIVED.value,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_idempotency_key(self, idempotency_key: str) -> InboxItem | None:
        stmt = select(InboxItem).where(InboxItem.idempotency_key == idempotency_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, item_id: UUID, *, user_id: UUID | None = None) -> InboxItem | None:
        conditions = [InboxItem.id == item_id, InboxItem.deleted_at.is_(None)]
        if user_id is not None:
            conditions.append(InboxItem.user_id == user_id)
        result = await self._session.execute(select(InboxItem).where(*conditions))
        return result.scalar_one_or_none()

    async def get_for_update(self, item_id: UUID, *, user_id: UUID) -> InboxItem | None:
        """Lock one owned capture while its linked records are being replaced."""
        stmt = (
            select(InboxItem)
            .where(
                InboxItem.id == item_id,
                InboxItem.user_id == user_id,
                InboxItem.deleted_at.is_(None),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> list[InboxItem]:
        capped = min(max(limit, 1), MAX_PAGE_SIZE)
        conditions = [InboxItem.user_id == user_id, InboxItem.deleted_at.is_(None)]
        if status is not None:
            conditions.append(InboxItem.status == status)
        stmt = (
            select(InboxItem)
            .where(*conditions)
            .order_by(InboxItem.created_at.desc())
            .limit(capped)
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_status(
        self,
        item_id: UUID,
        status: str,
        *,
        error: str | None = None,
        ai_result: dict[str, Any] | None = None,
        clarification_question: str | None = None,
        transcript: str | None = None,
        processing_ms: int | None = None,
        ai_cost_micro: int | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status, "error": error}
        if ai_result is not None:
            values["ai_result"] = ai_result
        if clarification_question is not None:
            values["clarification_question"] = clarification_question
        if transcript is not None:
            values["transcript"] = transcript
        if processing_ms is not None:
            values["processing_ms"] = processing_ms
        if ai_cost_micro is not None:
            values["ai_cost_micro"] = ai_cost_micro
        if provider is not None:
            values["provider"] = provider
        if model is not None:
            values["model"] = model
        await self._session.execute(
            update(InboxItem).where(InboxItem.id == item_id).values(**values)
        )
        await self._session.flush()

    async def complete_correction(
        self, item_id: UUID, *, ai_result: dict[str, Any]
    ) -> None:
        """Store a user-confirmed result and explicitly clear stale errors/questions."""
        await self._session.execute(
            update(InboxItem)
            .where(InboxItem.id == item_id)
            .values(
                status=InboxStatus.COMPLETED.value,
                ai_result=ai_result,
                clarification_question=None,
                error=None,
                updated_at=datetime.now(tz=UTC),
            )
        )
        await self._session.flush()

    async def increment_attempts(self, item_id: UUID) -> None:
        await self._session.execute(
            update(InboxItem)
            .where(InboxItem.id == item_id)
            .values(attempts=InboxItem.__table__.c.attempts + 1)
        )
        await self._session.flush()

    async def add_link(self, *, inbox_item_id: UUID, entity_type: str, entity_id: UUID) -> None:
        """Idempotent: re-applying the same AI result cannot duplicate links."""
        stmt = (
            pg_insert(InboxEntityLink)
            .values(inbox_item_id=inbox_item_id, entity_type=entity_type, entity_id=entity_id)
            .on_conflict_do_nothing(constraint="uq_inbox_entity_links_entity")
        )
        await self._session.execute(stmt)

    async def replace_links(
        self, inbox_item_id: UUID, links: list[tuple[str, UUID]]
    ) -> None:
        """Replace every entity link inside the caller's transaction."""
        await self._session.execute(
            delete(InboxEntityLink).where(InboxEntityLink.inbox_item_id == inbox_item_id)
        )
        for entity_type, entity_id in links:
            await self.add_link(
                inbox_item_id=inbox_item_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        await self._session.flush()

    async def links(self, inbox_item_id: UUID) -> list[InboxEntityLink]:
        stmt = select(InboxEntityLink).where(
            InboxEntityLink.inbox_item_id == inbox_item_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_feedback(
        self, *, user_id: UUID, inbox_item_id: UUID, rating: int, comment: str | None
    ) -> None:
        self._session.add(
            UserFeedback(
                user_id=user_id,
                inbox_item_id=inbox_item_id,
                rating=rating,
                comment=comment,
            )
        )
        await self._session.flush()

    async def mark_undone(self, item_id: UUID) -> None:
        await self._session.execute(
            update(InboxItem)
            .where(InboxItem.id == item_id)
            .values(status=InboxStatus.UNDONE.value, updated_at=datetime.now(tz=UTC))
        )
        await self._session.flush()
