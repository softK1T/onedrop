"""Task use cases. Routers stay thin; this is where the rules live."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.planner import Task
from onedrop.db.repositories.tasks import TaskRepository
from onedrop.db.repositories.users import UserRepository
from onedrop.errors import NotFoundError
from onedrop.reminders.models import NotificationKind
from onedrop.reminders.service import ReminderService
from onedrop.tasks.filters import build_filter_window
from onedrop.tasks.schemas import TaskCreate, TaskUpdate


class TaskService:
    """Application service for tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._users = UserRepository(session)
        self._reminders = ReminderService(session)

    async def create(self, user_id: UUID, payload: TaskCreate) -> Task:
        task = await self._tasks.create(
            user_id=user_id, values=payload.model_dump(exclude_unset=False)
        )
        await self._session.commit()
        return task

    async def list(
        self,
        user_id: UUID,
        *,
        filter_name: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], bool]:
        settings_row = await self._users.get_settings(user_id)
        timezone = settings_row.timezone if settings_row is not None else "UTC"
        window = build_filter_window(filter_name, timezone)
        rows = await self._tasks.list(
            user_id, window=window, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit

    async def get(self, user_id: UUID, task_id: UUID) -> Task:
        task = await self._tasks.get(task_id, user_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    async def patch(self, user_id: UUID, task_id: UUID, payload: TaskUpdate) -> Task:
        task = await self.get(user_id, task_id)
        changes = payload.model_dump(exclude_unset=True)
        task = await self._tasks.apply_changes(task, changes)
        if "due_at" in changes:
            await self._reminders.cancel_for_entity(
                kind=NotificationKind.TASK_REMINDER.value,
                user_id=user_id,
                entity_id=task.id,
            )
        await self._session.commit()
        return task

    async def complete(self, user_id: UUID, task_id: UUID) -> Task:
        task = await self.get(user_id, task_id)
        task = await self._tasks.complete(task)
        await self._reminders.cancel_for_entity(
            kind=NotificationKind.TASK_REMINDER.value,
            user_id=user_id,
            entity_id=task.id,
        )
        await self._session.commit()
        return task

    async def delete(self, user_id: UUID, task_id: UUID) -> None:
        task = await self.get(user_id, task_id)
        await self._tasks.soft_delete(task)
        await self._reminders.cancel_for_entity(
            kind=NotificationKind.TASK_REMINDER.value,
            user_id=user_id,
            entity_id=task.id,
        )
        await self._session.commit()
