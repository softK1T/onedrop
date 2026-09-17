"""Domain enumerations shared by models, schemas and services."""

from __future__ import annotations

from enum import StrEnum


class InputType(StrEnum):
    TEXT = "text"
    VOICE = "voice"
    PHOTO = "photo"


class InboxStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    NEEDS_CONFIRMATION = "needs_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    UNDONE = "undone"


class EntityType(StrEnum):
    TASK = "task"
    EVENT = "event"
    EXPENSE = "expense"
    MEAL = "meal"
    HABIT = "habit"
    HABIT_LOG = "habit_log"
    NOTE = "note"


class AiOperationType(StrEnum):
    PARSE = "parse"
    TRANSCRIBE = "transcribe"
    VISION = "vision"


class AiOperationStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"


class EventStatus(StrEnum):
    PLANNED = "planned"
    DONE = "done"
    CANCELLED = "cancelled"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MeasurementType(StrEnum):
    BOOLEAN = "boolean"
    NUMERIC = "numeric"


class ReminderKind(StrEnum):
    TASK = "task"
    EVENT = "event"
    HABIT = "habit"
    MORNING_DIGEST = "morning_digest"
    BUDGET_WARNING = "budget_warning"


class ReminderStatus(StrEnum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


class UsageScope(StrEnum):
    BONUS = "bonus"
    DAILY = "daily"
    MONTHLY = "monthly"


class ExpenseCategory(StrEnum):
    FOOD = "food"
    TRANSPORT = "transport"
    HOUSING = "housing"
    HEALTH = "health"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    BILLS = "bills"
    EDUCATION = "education"
    TRAVEL = "travel"
    OTHER = "other"


class Currency(StrEnum):
    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"
    UAH = "UAH"


def values(enum_cls: type[StrEnum]) -> tuple[str, ...]:
    """Return enum values, used to build database check constraints."""
    return tuple(member.value for member in enum_cls)
