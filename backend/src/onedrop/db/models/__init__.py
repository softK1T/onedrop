"""Model package. Importing it registers every table on Base.metadata."""

from onedrop.db.models.inbox import (
    AiOperation,
    AuditEvent,
    InboxEntityLink,
    InboxItem,
    UserFeedback,
)
from onedrop.db.models.user import AuthSession, TelegramUpdate, User, UserSettings

__all__ = [
    "AiOperation",
    "AuditEvent",
    "AuthSession",
    "InboxEntityLink",
    "InboxItem",
    "TelegramUpdate",
    "User",
    "UserFeedback",
    "UserSettings",
]
