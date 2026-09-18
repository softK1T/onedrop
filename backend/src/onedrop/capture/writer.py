"""Turns validated intents into domain rows inside one transaction."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.schemas import (
    CaptureResult,
    EventCreateIntent,
    ExpenseCreateIntent,
    HabitCreateIntent,
    HabitLogIntent,
    Intent,
    MealCreateIntent,
    NoteCreateIntent,
    TaskCreateIntent,
)
from onedrop.db.models.enums import EntityType
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog, Meal
from onedrop.db.models.notes import Note
from onedrop.db.models.planner import Event, Task
from onedrop.db.models.user import UserSettings
from onedrop.money import convert_minor

CreatedEntity = tuple[str, UUID]


class CaptureWriter:
    """Creates entities for a capture. Raises on invalid data so the caller can
    roll the whole capture back."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def apply(
        self,
        *,
        user_id: UUID,
        settings: UserSettings,
        inbox_item_id: UUID,
        result: CaptureResult,
    ) -> list[CreatedEntity]:
        created: list[CreatedEntity] = []
        for intent in result.actionable_intents:
            created.append(
                await self._apply_intent(
                    intent,
                    user_id=user_id,
                    settings=settings,
                    inbox_item_id=inbox_item_id,
                )
            )
        return created

    async def _apply_intent(
        self,
        intent: Intent,
        *,
        user_id: UUID,
        settings: UserSettings,
        inbox_item_id: UUID,
    ) -> CreatedEntity:
        if isinstance(intent, TaskCreateIntent):
            return await self._task(intent, user_id, inbox_item_id)
        if isinstance(intent, EventCreateIntent):
            return await self._event(intent, user_id, inbox_item_id)
        if isinstance(intent, ExpenseCreateIntent):
            return await self._expense(intent, user_id, settings, inbox_item_id)
        if isinstance(intent, MealCreateIntent):
            return await self._meal(intent, user_id, inbox_item_id)
        if isinstance(intent, NoteCreateIntent):
            return await self._note(intent, user_id, inbox_item_id)
        if isinstance(intent, HabitCreateIntent):
            return await self._habit(intent, user_id, inbox_item_id)
        if isinstance(intent, HabitLogIntent):
            return await self._habit_log(intent, user_id, inbox_item_id)
        raise ValueError(f"unsupported intent type: {intent.type}")

    async def _task(
        self, intent: TaskCreateIntent, user_id: UUID, inbox_item_id: UUID
    ) -> CreatedEntity:
        row = Task(
            user_id=user_id,
            title=intent.fields.title,
            description=intent.fields.description,
            due_at=intent.fields.due_at,
            priority=intent.fields.priority,
            category=intent.fields.category,
            reminder_at=intent.fields.reminder_at,
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.TASK.value, row.id

    async def _event(
        self, intent: EventCreateIntent, user_id: UUID, inbox_item_id: UUID
    ) -> CreatedEntity:
        row = Event(
            user_id=user_id,
            title=intent.fields.title,
            starts_at=intent.fields.starts_at,
            ends_at=intent.fields.ends_at,
            location=intent.fields.location,
            description=intent.fields.description,
            reminder_at=intent.fields.reminder_at,
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.EVENT.value, row.id

    async def _expense(
        self,
        intent: ExpenseCreateIntent,
        user_id: UUID,
        settings: UserSettings,
        inbox_item_id: UUID,
    ) -> CreatedEntity:
        base_currency = settings.base_currency
        base_minor, rate = convert_minor(
            intent.fields.amount_minor, intent.fields.currency, base_currency
        )
        row = Expense(
            user_id=user_id,
            amount_minor=intent.fields.amount_minor,
            currency=intent.fields.currency,
            base_amount_minor=base_minor,
            base_currency=base_currency if base_minor is not None else None,
            fx_rate=rate,
            category=intent.fields.category,
            merchant=intent.fields.merchant,
            occurred_at=intent.fields.occurred_at or datetime.now(tz=UTC),
            description=intent.fields.description,
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.EXPENSE.value, row.id

    async def _meal(
        self, intent: MealCreateIntent, user_id: UUID, inbox_item_id: UUID
    ) -> CreatedEntity:
        row = Meal(
            user_id=user_id,
            meal_type=intent.fields.meal_type,
            eaten_at=intent.fields.eaten_at or datetime.now(tz=UTC),
            title=intent.fields.title,
            calories=intent.fields.calories,
            protein=intent.fields.protein,
            fat=intent.fields.fat,
            carbohydrates=intent.fields.carbohydrates,
            estimated=intent.fields.estimated,
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.MEAL.value, row.id

    async def _note(
        self, intent: NoteCreateIntent, user_id: UUID, inbox_item_id: UUID
    ) -> CreatedEntity:
        row = Note(
            user_id=user_id,
            title=intent.fields.title,
            content=intent.fields.content,
            tags=list(intent.fields.tags),
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.NOTE.value, row.id

    async def _habit(
        self, intent: HabitCreateIntent, user_id: UUID, inbox_item_id: UUID
    ) -> CreatedEntity:
        existing = await self._find_habit(user_id, intent.fields.name)
        if existing is not None:
            if existing.source_inbox_item_id == inbox_item_id:
                existing.measurement_type = intent.fields.measurement_type
                existing.target_value = intent.fields.target_value
                existing.unit = intent.fields.unit
                existing.schedule = (
                    {"days": intent.fields.schedule_days}
                    if intent.fields.schedule_days
                    else None
                )
                await self._session.flush()
            return EntityType.HABIT.value, existing.id
        row = Habit(
            user_id=user_id,
            name=intent.fields.name,
            measurement_type=intent.fields.measurement_type,
            target_value=intent.fields.target_value,
            unit=intent.fields.unit,
            schedule=(
                {"days": intent.fields.schedule_days}
                if intent.fields.schedule_days
                else None
            ),
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.HABIT.value, row.id

    async def _habit_log(
        self, intent: HabitLogIntent, user_id: UUID, inbox_item_id: UUID
    ) -> CreatedEntity:
        habit = await self._find_habit(user_id, intent.fields.habit_name)
        if habit is None:
            habit = Habit(
                user_id=user_id,
                name=intent.fields.habit_name,
                measurement_type="numeric" if intent.fields.value > 1 else "boolean",
                source_inbox_item_id=inbox_item_id,
            )
            self._session.add(habit)
            await self._session.flush()
        row = HabitLog(
            user_id=user_id,
            habit_id=habit.id,
            value=intent.fields.value,
            logged_at=intent.fields.logged_at or datetime.now(tz=UTC),
            source_inbox_item_id=inbox_item_id,
        )
        self._session.add(row)
        await self._session.flush()
        return EntityType.HABIT_LOG.value, row.id

    async def _find_habit(self, user_id: UUID, name: str) -> Habit | None:
        stmt = select(Habit).where(
            Habit.user_id == user_id,
            Habit.name == name,
            Habit.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
