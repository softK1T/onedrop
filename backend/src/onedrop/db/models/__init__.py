"""Model package. Importing it registers every table on Base.metadata."""

from onedrop.db.models.billing import Payment, Subscription, UsageCounter
from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, HabitLog, Meal
from onedrop.db.models.inbox import (
    AiOperation,
    AuditEvent,
    InboxEntityLink,
    InboxItem,
    UserFeedback,
)
from onedrop.db.models.notifications import ScheduledNotification
from onedrop.db.models.notes import Note
from onedrop.db.models.planner import Event, Task
from onedrop.db.models.user import AuthSession, TelegramUpdate, User, UserSettings

__all__ = [
    "AiOperation",
    "AuditEvent",
    "AuthSession",
    "Event",
    "Expense",
    "Habit",
    "HabitLog",
    "InboxEntityLink",
    "InboxItem",
    "Meal",
    "Note",
    "Payment",
    "ScheduledNotification",
    "Subscription",
    "Task",
    "TelegramUpdate",
    "UsageCounter",
    "User",
    "UserFeedback",
    "UserSettings",
]
