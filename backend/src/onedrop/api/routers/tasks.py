"""Task endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.db.repositories.tasks import MAX_PAGE_SIZE
from onedrop.tasks.filters import TASK_FILTERS
from onedrop.tasks.schemas import TaskCreate, TaskPage, TaskResponse, TaskUpdate
from onedrop.tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskPage)
async def list_tasks(
    session: DbSession,
    user: CurrentUser,
    filter_name: Annotated[str, Query(alias="filter")] = "today",
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskPage:
    """Filtered task list: today, upcoming, no_date, completed or all."""
    resolved = filter_name if filter_name in TASK_FILTERS else "today"
    items, has_more = await TaskService(session).list(
        user.id, filter_name=resolved, limit=limit, offset=offset
    )
    return TaskPage(
        items=[TaskResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        has_more=has_more,
        filter=resolved,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, session: DbSession, user: CurrentUser
) -> TaskResponse:
    task = await TaskService(session).create(user.id, payload)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> TaskResponse:
    task = await TaskService(session).get(user.id, task_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def patch_task(
    task_id: uuid.UUID, payload: TaskUpdate, session: DbSession, user: CurrentUser
) -> TaskResponse:
    task = await TaskService(session).patch(user.id, task_id, payload)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> TaskResponse:
    """Mark the task done and cancel its pending reminders."""
    task = await TaskService(session).complete(user.id, task_id)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> Response:
    """Soft delete: the row stays for audit but leaves every list."""
    await TaskService(session).delete(user.id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
