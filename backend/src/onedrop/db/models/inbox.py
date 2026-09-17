"""Inbox items, entity links, AI usage ledger, feedback and audit log."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import (
    AiOperationStatus,
    AiOperationType,
    EntityType,
    InboxStatus,
    InputType,
    values,
)


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class InboxItem(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """One capture: text, voice or photo, plus its processing state."""

    __tablename__ = "inbox_items"
    __table_args__ = (
        CheckConstraint(_in_clause("input_type", values(InputType)), name="input_type_valid"),
        CheckConstraint(_in_clause("status", values(InboxStatus)), name="status_valid"),
        Index("ix_inbox_items_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    input_type: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    media_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_update_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=InboxStatus.RECEIVED.value, server_default="received"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    clarification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_cost_micro: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class InboxEntityLink(UUIDPrimaryKeyMixin, Base):
    """Link between a capture and every entity it created (used by undo)."""

    __tablename__ = "inbox_entity_links"
    __table_args__ = (
        CheckConstraint(_in_clause("entity_type", values(EntityType)), name="entity_type_valid"),
        UniqueConstraint(
            "inbox_item_id", "entity_type", "entity_id", name="uq_inbox_entity_links_entity"
        ),
    )

    inbox_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AiOperation(UUIDPrimaryKeyMixin, Base):
    """Ledger of AI provider calls: tokens, cost, duration, quota impact."""

    __tablename__ = "ai_operations"
    __table_args__ = (
        CheckConstraint(
            _in_clause("operation_type", values(AiOperationType)), name="operation_type_valid"
        ),
        CheckConstraint(_in_clause("status", values(AiOperationStatus)), name="status_valid"),
        Index("ix_ai_operations_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )
    operation_type: Mapped[str] = mapped_column(String(24), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cost_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    charged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserFeedback(UUIDPrimaryKeyMixin, Base):
    """Thumbs up/down on a capture result, used to improve prompts and fixtures."""

    __tablename__ = "user_feedback"
    __table_args__ = (CheckConstraint("rating IN (-1, 1)", name="rating_valid"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    inbox_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only trace of privacy-relevant and billing-relevant actions."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
