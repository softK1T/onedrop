"""User profile use cases: settings, usage, export, deletion."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import TimezoneError, local_now, resolve_zone
from onedrop.billing.plans import limits_for
from onedrop.billing.usage import UsageService
from onedrop.config import get_settings
from onedrop.db.models.billing import Subscription
from onedrop.db.models.enums import Plan
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog, Meal
from onedrop.db.models.inbox import InboxItem
from onedrop.db.models.notes import Note
from onedrop.db.models.planner import Event, Task
from onedrop.db.models.user import User, UserSettings
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import NotFoundError, ValidationError
from onedrop.logging import get_logger
from onedrop.storage import ObjectStorage
from onedrop.users.schemas import (
    DeleteAccountResponse,
    ExportResponse,
    UsageResponse,
    UserSettingsUpdate,
)

logger = get_logger(__name__)
EXPORT_ROW_LIMIT = 5000


def _as_dict(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: getattr(row, field) for field in fields}


class UserService:
    """Profile, settings, privacy operations."""

    def __init__(self, session: AsyncSession, *, storage: ObjectStorage | None = None) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._usage = UsageService(session)
        self._storage = storage or ObjectStorage()

    async def settings_for(self, user_id: UUID) -> UserSettings:
        row = await self._users.get_settings(user_id)
        if row is None:
            row = await self._users.update_settings(user_id, {})
            await self._session.commit()
        return row

    async def update_settings(
        self, user_id: UUID, payload: UserSettingsUpdate
    ) -> UserSettings:
        changes = payload.model_dump(exclude_unset=True)
        if "timezone" in changes and changes["timezone"]:
            try:
                resolve_zone(str(changes["timezone"]))
            except TimezoneError as exc:
                raise ValidationError("timezone must be a valid IANA identifier") from exc
        if changes.pop("accept_consent", False):
            changes["consent_at"] = datetime.now(tz=UTC)
        locale = changes.pop("locale", None)
        row = await self._users.update_settings(user_id, changes)
        if locale is not None:
            user = await self._users.get_by_id(user_id)
            if user is not None:
                user.locale = str(locale)
        await self._session.commit()
        return row

    async def usage(self, user_id: UUID) -> UsageResponse:
        settings = get_settings()
        settings_row = await self.settings_for(user_id)
        plan = await self._plan(user_id)
        limits = limits_for(plan, settings)
        state = await self._usage.snapshot(
            user_id, limits=limits, now_local=local_now(settings_row.timezone)
        )
        return UsageResponse(
            plan=state.plan,
            bonus_used=state.bonus_used,
            bonus_limit=state.bonus_limit,
            period_scope=state.period_scope,
            period_used=state.period_used,
            period_limit=state.period_limit,
            remaining=state.remaining,
            photo_recognition=limits.photo_recognition,
            morning_digest=limits.morning_digest,
            csv_export=limits.csv_export,
        )

    async def export(self, user_id: UUID) -> ExportResponse:
        """Collect everything stored about the user (GDPR-style export)."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        settings_row = await self.settings_for(user_id)

        tasks = await self._rows(Task, user_id)
        events = await self._rows(Event, user_id)
        expenses = await self._rows(Expense, user_id)
        meals = await self._rows(Meal, user_id)
        habits = await self._rows(Habit, user_id)
        habit_logs = await self._rows(HabitLog, user_id)
        notes = await self._rows(Note, user_id)
        inbox_items = await self._rows(InboxItem, user_id)

        return ExportResponse(
            generated_at=datetime.now(tz=UTC),
            user=_as_dict(
                user, ("id", "telegram_user_id", "first_name", "username", "locale", "created_at")
            ),
            settings=_as_dict(
                settings_row,
                (
                    "timezone",
                    "base_currency",
                    "monthly_budget_minor",
                    "allow_training",
                    "consent_at",
                ),
            ),
            counts={
                "tasks": len(tasks),
                "events": len(events),
                "expenses": len(expenses),
                "meals": len(meals),
                "habits": len(habits),
                "habit_logs": len(habit_logs),
                "notes": len(notes),
                "inbox_items": len(inbox_items),
            },
            tasks=tasks,
            events=events,
            expenses=expenses,
            meals=meals,
            habits=habits,
            habit_logs=habit_logs,
            notes=notes,
            inbox_items=inbox_items,
        )

    async def delete_account(self, user_id: UUID) -> DeleteAccountResponse:
        """Irreversible: rows are removed by cascade and media is deleted."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        removed = await self._storage.delete_prefix(f"{user_id}/")
        await self._session.execute(delete(User).where(User.id == user_id))
        await self._session.commit()
        logger.info("user.account_deleted", user_id=str(user_id), media_removed=removed)
        return DeleteAccountResponse(deleted=True, media_objects_removed=removed)

    async def _plan(self, user_id: UUID) -> str:
        stmt = select(Subscription).where(
            Subscription.user_id == user_id, Subscription.status == "active"
        )
        result = await self._session.execute(stmt)
        subscription = result.scalars().first()
        if subscription is None:
            return Plan.FREE.value
        if subscription.expires_at is not None and subscription.expires_at < datetime.now(tz=UTC):
            return Plan.FREE.value
        return subscription.plan

    async def _rows(self, model: Any, user_id: UUID) -> list[dict[str, Any]]:
        stmt = select(model).where(model.user_id == user_id).limit(EXPORT_ROW_LIMIT)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        columns = tuple(column.name for column in model.__table__.columns)
        return [_as_dict(row, columns) for row in rows]
