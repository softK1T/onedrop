"""Habit endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.db.repositories.habits import MAX_PAGE_SIZE
from onedrop.habits.schemas import (
    HabitCreate,
    HabitLogPage,
    HabitLogRequest,
    HabitLogResponse,
    HabitPage,
    HabitProgressResponse,
    HabitResponse,
    HabitUpdate,
)
from onedrop.habits.service import HabitService

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=HabitPage)
async def list_habits(
    session: DbSession,
    user: CurrentUser,
    include_inactive: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HabitPage:
    items, has_more = await HabitService(session).list(
        user.id, active_only=not include_inactive, limit=limit, offset=offset
    )
    return HabitPage(
        items=[HabitResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_habit(
    payload: HabitCreate, session: DbSession, user: CurrentUser
) -> HabitResponse:
    habit = await HabitService(session).create(user.id, payload)
    return HabitResponse.model_validate(habit)


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> HabitResponse:
    habit = await HabitService(session).get(user.id, habit_id)
    return HabitResponse.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitResponse)
async def patch_habit(
    habit_id: uuid.UUID, payload: HabitUpdate, session: DbSession, user: CurrentUser
) -> HabitResponse:
    habit = await HabitService(session).patch(user.id, habit_id, payload)
    return HabitResponse.model_validate(habit)


@router.post("/{habit_id}/disable", response_model=HabitResponse)
async def disable_habit(
    habit_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> HabitResponse:
    """Stop tracking a habit but keep its history."""
    habit = await HabitService(session).deactivate(user.id, habit_id)
    return HabitResponse.model_validate(habit)


@router.post(
    "/{habit_id}/log", response_model=HabitLogResponse, status_code=status.HTTP_201_CREATED
)
async def log_habit(
    habit_id: uuid.UUID,
    payload: HabitLogRequest,
    session: DbSession,
    user: CurrentUser,
) -> HabitLogResponse:
    """Log a completion, from the Mini App or from a voice capture."""
    entry = await HabitService(session).log(
        user.id, habit_id, value=payload.value, logged_at=payload.logged_at
    )
    return HabitLogResponse.model_validate(entry)


@router.get("/{habit_id}/logs", response_model=HabitLogPage)
async def habit_history(
    habit_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HabitLogPage:
    items, has_more = await HabitService(session).history(
        user.id, habit_id, limit=limit, offset=offset
    )
    return HabitLogPage(
        items=[HabitLogResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/{habit_id}/progress", response_model=HabitProgressResponse)
async def habit_progress(
    habit_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> HabitProgressResponse:
    """Completion percentage against the habit schedule."""
    return await HabitService(session).progress(user.id, habit_id, days=days)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> Response:
    await HabitService(session).delete(user.id, habit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
