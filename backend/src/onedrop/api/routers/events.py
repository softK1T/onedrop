"""Event endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.db.repositories.events import MAX_PAGE_SIZE
from onedrop.events.schemas import (
    EventCreate,
    EventPage,
    EventResponse,
    EventUpdate,
    EventWithConflicts,
)
from onedrop.events.service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventPage)
async def list_events(
    session: DbSession,
    user: CurrentUser,
    period: Annotated[str, Query(pattern="^(day|week)$")] = "day",
    anchor_date: Annotated[date | None, Query(alias="date")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventPage:
    """Day or week agenda in the user's local calendar."""
    items, has_more, resolved_date = await EventService(session).list_period(
        user.id, period=period, anchor=anchor_date, limit=limit, offset=offset
    )
    return EventPage(
        items=[EventResponse.model_validate(item) for item in items],
        range="week" if period == "week" else "day",
        anchor_date=resolved_date,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("", response_model=EventWithConflicts, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate, session: DbSession, user: CurrentUser
) -> EventWithConflicts:
    """Create an event. Overlapping events are reported, not blocked."""
    event, conflicts = await EventService(session).create(user.id, payload)
    return EventWithConflicts(
        event=EventResponse.model_validate(event), conflicts=conflicts
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> EventResponse:
    event = await EventService(session).get(user.id, event_id)
    return EventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=EventWithConflicts)
async def patch_event(
    event_id: uuid.UUID, payload: EventUpdate, session: DbSession, user: CurrentUser
) -> EventWithConflicts:
    event, conflicts = await EventService(session).patch(user.id, event_id, payload)
    return EventWithConflicts(
        event=EventResponse.model_validate(event), conflicts=conflicts
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> Response:
    await EventService(session).delete(user.id, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
