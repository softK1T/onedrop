"""Canonical reminder lifecycle integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from onedrop.db.models.notifications import ScheduledNotification
from onedrop.db.models.reminders import Reminder
from onedrop.events.schemas import EventCreate, EventUpdate
from onedrop.events.service import EventService
from onedrop.reminders.service import ReminderService
from onedrop.tasks.schemas import TaskCreate, TaskUpdate
from onedrop.tasks.service import TaskService

pytestmark = pytest.mark.asyncio

async def test_task_reminder_create_update_cancel(session, user):
    service=TaskService(session);first=datetime.now(tz=UTC)+timedelta(hours=2)
    task=await service.create(user.id,TaskCreate(title="Pay internet",due_at=first+timedelta(hours=1),reminder_at=first,priority="normal"))
    row=await session.scalar(select(Reminder).where(Reminder.entity_id==task.id,Reminder.status=="scheduled"));assert row and row.scheduled_at==first
    second=first+timedelta(hours=1);await service.patch(user.id,task.id,TaskUpdate(reminder_at=second))
    active=int(await session.scalar(select(func.count()).select_from(Reminder).where(Reminder.entity_id==task.id,Reminder.status=="scheduled")) or 0);assert active==1
    row=await session.scalar(select(Reminder).where(Reminder.entity_id==task.id,Reminder.status=="scheduled"));assert row and row.scheduled_at==second
    await service.delete(user.id,task.id);await session.refresh(row);assert row.status=="cancelled"

async def test_event_reminder_create_update_cancel(session,user):
    service=EventService(session);start=datetime.now(tz=UTC)+timedelta(hours=4);first=start-timedelta(hours=1)
    event,_=await service.create(user.id,EventCreate(title="Meeting",starts_at=start,ends_at=None,reminder_at=first,location=None))
    row=await session.scalar(select(Reminder).where(Reminder.entity_id==event.id,Reminder.status=="scheduled"));assert row
    await service.patch(user.id,event.id,EventUpdate(reminder_at=None));await session.refresh(row);assert row.status=="cancelled"

async def test_duplicate_planning_links_one_outbox_delivery(session,user):
    settings=user.settings;assert settings is not None
    service=TaskService(session);now=datetime.now(tz=UTC);task=await service.create(user.id,TaskCreate(title="Unique",due_at=now+timedelta(hours=2),reminder_at=now+timedelta(hours=1),priority="normal"))
    planner=ReminderService(session);await planner.plan_for_user(user,settings,now=now);await planner.plan_for_user(user,settings,now=now);await session.commit()
    reminder=await session.scalar(select(Reminder).where(Reminder.entity_id==task.id,Reminder.status=="scheduled"));assert reminder
    count=int(await session.scalar(select(func.count()).select_from(ScheduledNotification).where(ScheduledNotification.reminder_id==reminder.id)) or 0);assert count==1
