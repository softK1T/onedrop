"""Planning and synchronization of durable user reminders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.ai.normalize import local_day_bounds
from onedrop.db.models.enums import TaskStatus
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog
from onedrop.db.models.planner import Event, Task
from onedrop.db.models.user import User, UserSettings
from onedrop.logging import get_logger
from onedrop.reminders.models import NotificationKind, QuietHours, ReminderPreferences, period_dedup_key, require_aware, shift_out_of_quiet_hours
from onedrop.reminders.repository import ScheduledNotificationRepository
from onedrop.reminders.schedule_repository import ReminderRepository

logger = get_logger(__name__)
DEFAULT_HORIZON = timedelta(hours=26)
MAX_USERS_PER_PASS = 500
MAX_ENTITIES_PER_USER = 200

@dataclass(frozen=True, slots=True)
class PlannedNotification:
    kind: str
    run_at: datetime
    dedup_key: str
    payload: dict[str, Any]
    reminder_id: UUID | None = None

def preferences_from_settings(row: UserSettings) -> ReminderPreferences:
    return ReminderPreferences(timezone=row.timezone, quiet_hours=QuietHours(start_hour=row.quiet_hours_start, end_hour=row.quiet_hours_end), morning_digest_hour=row.morning_digest_hour, task_lead_minutes=row.task_reminder_lead_minutes, event_lead_minutes=row.event_reminder_lead_minutes, budget_threshold_percent=row.budget_warning_threshold_percent, reminders_enabled=row.reminders_enabled, morning_digest=row.morning_digest, task_reminders=row.task_reminders, event_reminders=row.event_reminders, habit_reminders=row.habit_reminders, budget_warnings=row.budget_warnings)

def local_month_bounds(now: datetime, timezone: str) -> tuple[str, datetime, datetime]:
    zone=ZoneInfo(timezone); local=require_aware(now,"now").astimezone(zone); start=datetime(local.year,local.month,1,tzinfo=zone)
    end=datetime(local.year+1,1,1,tzinfo=zone) if local.month==12 else datetime(local.year,local.month+1,1,tzinfo=zone)
    return f"{local.year:04d}-{local.month:02d}",start.astimezone(UTC),end.astimezone(UTC)

def habit_runs_on(schedule: dict[str, Any] | None, local_date: date) -> bool:
    if not schedule:return True
    weekdays=schedule.get("weekdays")
    if not isinstance(weekdays,list) or not weekdays:return True
    allowed={int(value)%7 for value in weekdays if not isinstance(value,bool) and (isinstance(value,int) or isinstance(value,str) and value.strip().isdigit())}
    return not allowed or local_date.weekday() in allowed

def plan_morning_digest(user_id: UUID,prefs: ReminderPreferences,*,now: datetime)->PlannedNotification|None:
    kind=NotificationKind.MORNING_DIGEST.value
    if not prefs.allows(kind):return None
    zone=ZoneInfo(prefs.timezone); local=require_aware(now,"now").astimezone(zone); target=local.date(); candidate=datetime.combine(target,time(hour=prefs.morning_digest_hour),tzinfo=zone)
    if candidate<=local:target+=timedelta(days=1);candidate=datetime.combine(target,time(hour=prefs.morning_digest_hour),tzinfo=zone)
    run_at=shift_out_of_quiet_hours(candidate.astimezone(UTC),prefs.timezone,prefs.quiet_hours)
    return PlannedNotification(kind,run_at,period_dedup_key(kind,user_id,target.isoformat(),"digest"),{"local_date":target.isoformat(),"timezone":prefs.timezone})

def plan_habit_reminder(*,user_id:UUID,habit_id:UUID,title:str,reminder_hour:int|None,prefs:ReminderPreferences,now:datetime,already_logged:bool)->PlannedNotification|None:
    kind=NotificationKind.HABIT_REMINDER.value
    if not prefs.allows(kind) or already_logged or reminder_hour is None:return None
    zone=ZoneInfo(prefs.timezone); local=require_aware(now,"now").astimezone(zone); candidate=datetime.combine(local.date(),time(hour=reminder_hour),tzinfo=zone)
    if candidate<=local:return None
    run_at=shift_out_of_quiet_hours(candidate.astimezone(UTC),prefs.timezone,prefs.quiet_hours)
    return PlannedNotification(kind,run_at,period_dedup_key(kind,user_id,local.date().isoformat(),str(habit_id)),{"title":title,"local_date":local.date().isoformat(),"timezone":prefs.timezone,"entity_id":str(habit_id)})

def plan_budget_warning(*,user_id:UUID,prefs:ReminderPreferences,spent_minor:int,limit_minor:int|None,currency:str,period_key:str,now:datetime)->PlannedNotification|None:
    kind=NotificationKind.BUDGET_WARNING.value
    if not prefs.allows(kind) or not limit_minor or limit_minor<=0:return None
    percent=spent_minor*100//limit_minor; threshold=100 if percent>=100 else prefs.budget_threshold_percent if percent>=prefs.budget_threshold_percent else 0
    if not threshold:return None
    run_at=shift_out_of_quiet_hours(require_aware(now,"now"),prefs.timezone,prefs.quiet_hours)
    return PlannedNotification(kind,run_at,period_dedup_key(kind,user_id,period_key,str(threshold)),{"threshold":threshold,"percent":percent,"spent_minor":spent_minor,"limit_minor":limit_minor,"currency":currency,"period":period_key,"timezone":prefs.timezone})

class ReminderService:
    """Canonical schedules are the only source for task/event delivery."""
    def __init__(self,session:AsyncSession)->None:
        self._session=session;self._notifications=ScheduledNotificationRepository(session);self._schedules=ReminderRepository(session)

    async def sync_entity(self,*,user_id:UUID,kind:str,entity_type:str,entity_id:UUID,scheduled_at:datetime|None,payload:dict[str,Any]):
        await self._notifications.cancel_pending(kind=kind,user_id=user_id,entity_id=entity_id)
        return await self._schedules.sync_entity(user_id=user_id,kind=kind,entity_type=entity_type,entity_id=entity_id,scheduled_at=scheduled_at,payload=payload)

    async def cancel_for_entity(self,*,kind:str,user_id:UUID,entity_id:UUID)->int:
        scheduled=await self._schedules.cancel_entity(user_id=user_id,kind=kind,entity_id=entity_id)
        queued=await self._notifications.cancel_pending(kind=kind,user_id=user_id,entity_id=entity_id)
        return scheduled+queued

    async def plan_for_all_users(self,*,now:datetime,horizon:timedelta=DEFAULT_HORIZON)->int:
        reference=require_aware(now,"now")
        rows=(await self._session.execute(select(User,UserSettings).join(UserSettings,UserSettings.user_id==User.id).where(User.deleted_at.is_(None),User.is_blocked.is_(False)).order_by(User.created_at).limit(MAX_USERS_PER_PASS))).all();queued=0
        for user,settings in rows:queued+=await self.plan_for_user(user,settings,now=reference,horizon=horizon)
        if queued:logger.info("reminders.planned",queued=queued,users=len(rows))
        return queued

    async def plan_for_user(self,user:User,settings:UserSettings,*,now:datetime,horizon:timedelta=DEFAULT_HORIZON)->int:
        prefs=preferences_from_settings(settings)
        if not prefs.reminders_enabled:return 0
        reference=require_aware(now,"now");plans=[]
        digest=plan_morning_digest(user.id,prefs,now=reference)
        if digest:plans.append(digest)
        plans.extend(await self._plan_canonical(user.id,prefs,now=reference,horizon=horizon))
        plans.extend(await self._plan_habits(user.id,prefs,now=reference))
        budget=await self._plan_budget(user.id,settings,prefs,now=reference)
        if budget:plans.append(budget)
        queued=0
        for plan in plans:
            if await self._notifications.enqueue(user_id=user.id,kind=plan.kind,run_at=plan.run_at,dedup_key=plan.dedup_key,payload=plan.payload,reminder_id=plan.reminder_id):queued+=1
        return queued

    async def _plan_canonical(self,user_id:UUID,prefs:ReminderPreferences,*,now:datetime,horizon:timedelta)->list[PlannedNotification]:
        schedules=await self._schedules.due_for_planning(user_id=user_id,now=now-timedelta(microseconds=1),horizon=now+horizon,limit=MAX_ENTITIES_PER_USER)
        plans=[]
        for row in schedules:
            if not prefs.allows(row.kind) or row.scheduled_at<=now:continue
            run_at=shift_out_of_quiet_hours(row.scheduled_at,prefs.timezone,prefs.quiet_hours)
            payload={**row.payload,"timezone":prefs.timezone,"entity_id":str(row.entity_id) if row.entity_id else None}
            plans.append(PlannedNotification(row.kind,run_at,f"reminder:{row.id}",payload,row.id))
        return plans

    async def _plan_habits(self,user_id:UUID,prefs:ReminderPreferences,*,now:datetime)->list[PlannedNotification]:
        if not prefs.allows(NotificationKind.HABIT_REMINDER.value):return []
        local_date=now.astimezone(ZoneInfo(prefs.timezone)).date();start,end=local_day_bounds(local_date,prefs.timezone);plans=[]
        habits=(await self._session.execute(select(Habit).where(Habit.user_id==user_id,Habit.deleted_at.is_(None),Habit.active.is_(True),Habit.reminder_hour.is_not(None)).limit(MAX_ENTITIES_PER_USER))).scalars().all()
        for habit in habits:
            if not habit_runs_on(habit.schedule,local_date):continue
            logged=bool(await self._session.scalar(select(func.count()).select_from(HabitLog).where(HabitLog.habit_id==habit.id,HabitLog.logged_at>=start,HabitLog.logged_at<end)))
            plan=plan_habit_reminder(user_id=user_id,habit_id=habit.id,title=habit.name,reminder_hour=habit.reminder_hour,prefs=prefs,now=now,already_logged=logged)
            if plan:plans.append(plan)
        return plans

    async def _plan_budget(self,user_id:UUID,settings:UserSettings,prefs:ReminderPreferences,*,now:datetime)->PlannedNotification|None:
        period,start,end=local_month_bounds(now,prefs.timezone);spent=await self._month_spending(user_id,start,end)
        return plan_budget_warning(user_id=user_id,prefs=prefs,spent_minor=spent,limit_minor=settings.monthly_budget_minor,currency=settings.base_currency,period_key=period,now=now)

    async def _month_spending(self,user_id:UUID,start:datetime,end:datetime)->int:
        value=await self._session.scalar(select(func.coalesce(func.sum(func.coalesce(Expense.base_amount_minor,Expense.amount_minor)),0)).where(Expense.user_id==user_id,Expense.deleted_at.is_(None),Expense.occurred_at>=start,Expense.occurred_at<end));return int(value or 0)

    async def build_digest(self,user_id:UUID,prefs:ReminderPreferences,*,now:datetime)->dict[str,Any]:
        local_date=now.astimezone(ZoneInfo(prefs.timezone)).date();start,end=local_day_bounds(local_date,prefs.timezone)
        tasks=int(await self._session.scalar(select(func.count()).select_from(Task).where(Task.user_id==user_id,Task.deleted_at.is_(None),Task.status==TaskStatus.OPEN.value,Task.due_at>=start,Task.due_at<end)) or 0)
        events=int(await self._session.scalar(select(func.count()).select_from(Event).where(Event.user_id==user_id,Event.deleted_at.is_(None),Event.starts_at>=start,Event.starts_at<end)) or 0)
        return {"local_date":local_date.isoformat(),"timezone":prefs.timezone,"tasks":tasks,"events":events,"habits":0,"budget_left_minor":None,"currency":"PLN"}
