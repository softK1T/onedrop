"""Event use cases: day and week lists, overlap reporting, reminders."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_day_bounds, local_now
from onedrop.db.models.planner import Event
from onedrop.db.repositories.events import EventRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import NotFoundError
from onedrop.events.overlap import TimeRange, find_overlaps
from onedrop.events.schemas import EventCreate, EventUpdate
from onedrop.reminders.models import NotificationKind
from onedrop.reminders.service import ReminderService

WEEK_DAYS = 7


class EventService:
    """Application service for events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._users = UserRepository(session)
        self._reminders = ReminderService(session)

    async def _timezone(self, user_id: UUID) -> str:
        settings_row = await self._users.get_settings(user_id)
        return settings_row.timezone if settings_row is not None else "UTC"

    async def create(
        self, user_id: UUID, payload: EventCreate
    ) -> tuple[Event, list[UUID]]:
        span = TimeRange(start=payload.starts_at, end=payload.ends_at)
        conflicts = await self._conflicts(user_id, span)
        event = await self._events.create(
            user_id=user_id, values=payload.model_dump(exclude_unset=False)
        )
        await self._session.commit()
        return event, conflicts

    async def get(self, user_id: UUID, event_id: UUID) -> Event:
        event = await self._events.get(event_id, user_id)
        if event is None:
            raise NotFoundError("Event not found")
        return event

    async def list_period(
        self,
        user_id: UUID,
        *,
        period: str,
        anchor: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Event], bool, date]:
        """Day or week list, bounded by the user's local calendar."""
        timezone = await self._timezone(user_id)
        anchor_date = anchor or local_now(timezone).date()
        if period == "week":
            week_start = anchor_date - timedelta(days=anchor_date.weekday())
            start, _ = local_day_bounds(week_start, timezone)
            _, end = local_day_bounds(week_start + timedelta(days=WEEK_DAYS - 1), timezone)
        else:
            start, end = local_day_bounds(anchor_date, timezone)
        rows = await self._events.list_range(
            user_id, start=start, end=end, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit, anchor_date

    async def patch(
        self, user_id: UUID, event_id: UUID, payload: EventUpdate
    ) -> tuple[Event, list[UUID]]:
        event = await self.get(user_id, event_id)
        changes = payload.model_dump(exclude_unset=True)
        starts_at = changes.get("starts_at", event.starts_at)
        ends_at = changes.get("ends_at", event.ends_at)
        conflicts = await self._conflicts(
            user_id, TimeRange(start=starts_at, end=ends_at), exclude_id=event.id
        )
        event = await self._events.apply_changes(event, changes)
        if "starts_at" in changes:
            await self._reminders.cancel_for_entity(
                kind=NotificationKind.EVENT_REMINDER.value,
                user_id=user_id,
                entity_id=event.id,
            )
        await self._session.commit()
        return event, conflicts

    async def delete(self, user_id: UUID, event_id: UUID) -> None:
        event = await self.get(user_id, event_id)
        await self._events.soft_delete(event)
        await self._reminders.cancel_for_entity(
            kind=NotificationKind.EVENT_REMINDER.value,
            user_id=user_id,
            entity_id=event.id,
        )
        await self._session.commit()

    async def _conflicts(
        self, user_id: UUID, span: TimeRange, *, exclude_id: UUID | None = None
    ) -> list[UUID]:
        candidates = await self._events.candidates_for_conflicts(
            user_id, start=span.start, end=span.effective_end, exclude_id=exclude_id
        )
        return find_overlaps(
            span,
            [(row.id, TimeRange(start=row.starts_at, end=row.ends_at)) for row in candidates],
        )
