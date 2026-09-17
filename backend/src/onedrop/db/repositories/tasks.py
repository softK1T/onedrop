"""Task persistence. Every query is scoped by user and skips soft-deleted rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.enums import TaskStatus
from onedrop.db.models.planner import Task
from onedrop.tasks.filters import FilterWindow

MAX_PAGE_SIZE = 100


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, values: dict[str, Any]) -> Task:
        row = Task(user_id=user_id, **values)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, task_id: UUID, user_id: UUID) -> Task | None:
        stmt = select(Task).where(
            Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, user_id: UUID, *, window: FilterWindow, limit: int = 20, offset: int = 0
    ) -> list[Task]:
        conditions: list[ColumnElement[bool]] = [
            Task.user_id == user_id,
            Task.deleted_at.is_(None),
        ]
        if window.only_open:
            conditions.append(Task.status == TaskStatus.OPEN.value)
        if window.only_completed:
            conditions.append(Task.status == TaskStatus.DONE.value)
        if window.require_due:
            conditions.append(Task.due_at.is_not(None))
        if window.require_no_due:
            conditions.append(Task.due_at.is_(None))
        if window.start is not None:
            conditions.append(Task.due_at >= window.start)
        if window.end is not None:
            conditions.append(Task.due_at < window.end)

        order = Task.completed_at.desc() if window.only_completed else Task.due_at.asc()
        stmt = (
            select(Task)
            .where(*conditions)
            .order_by(order.nullslast(), Task.created_at.desc())
            .limit(min(max(limit, 1), MAX_PAGE_SIZE + 1))
            .offset(max(offset, 0))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def apply_changes(self, task: Task, changes: dict[str, Any]) -> Task:
        for field, value in changes.items():
            setattr(task, field, value)
        await self._session.flush()
        return task

    async def complete(self, task: Task) -> Task:
        task.status = TaskStatus.DONE.value
        task.completed_at = datetime.now(tz=UTC)
        await self._session.flush()
        return task

    async def soft_delete(self, task: Task) -> None:
        task.deleted_at = datetime.now(tz=UTC)
        await self._session.flush()
