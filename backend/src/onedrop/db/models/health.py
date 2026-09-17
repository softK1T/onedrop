"""Meals, habits and habit logs. Nutrition values may be approximate."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from onedrop.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from onedrop.db.models.enums import MealType, MeasurementType, values


def _in_clause(column: str, allowed: tuple[str, ...]) -> str:
    return column + " IN ('" + "', '".join(allowed) + "')"


class Meal(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "meals"
    __table_args__ = (
        CheckConstraint(_in_clause("meal_type", values(MealType)), name="meal_type_valid"),
        CheckConstraint("calories IS NULL OR calories >= 0", name="calories_non_negative"),
        Index("ix_meals_user_id_eaten_at", "user_id", "eaten_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    meal_type: Mapped[str] = mapped_column(
        String(12), nullable=False, default=MealType.SNACK.value, server_default="snack"
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carbohydrates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )


class Habit(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(
            _in_clause("measurement_type", values(MeasurementType)), name="measurement_type_valid"
        ),
        UniqueConstraint("user_id", "name", name="uq_habits_user_id_name"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    measurement_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default=MeasurementType.BOOLEAN.value,
        server_default="boolean",
    )
    target_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    schedule: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    reminder_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )


class HabitLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "habit_logs"
    __table_args__ = (
        CheckConstraint("value >= 0", name="value_non_negative"),
        Index("ix_habit_logs_habit_id_logged_at", "habit_id", "logged_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    habit_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_inbox_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
