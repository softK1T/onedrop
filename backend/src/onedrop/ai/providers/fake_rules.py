"""Deterministic rule parser behind the fake provider.

No randomness and no network: the same input always yields the same intents.
It covers the documented acceptance example and the evaluation fixtures, which
is what makes demo mode usable without any AI credentials.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from onedrop.ai.providers.base import CaptureContext
from onedrop.ai.schemas import (
    CaptureResult,
    EventCreateIntent,
    EventFields,
    ExpenseCreateIntent,
    ExpenseFields,
    HabitCreateFields,
    HabitCreateIntent,
    HabitLogFields,
    HabitLogIntent,
    Intent,
    MealCreateIntent,
    MealFields,
    NoteCreateIntent,
    NoteFields,
    TaskCreateIntent,
    TaskFields,
    UnknownFields,
    UnknownIntent,
)
from onedrop.money import to_minor_units

AMOUNT_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)")
TIME_RE = re.compile(r"\b(\d{1,2})[:.](\d{2})\b")
CLAUSE_SPLIT_RE = re.compile(r"[,;\n]|\s\u0438\s|\s\u0430\s|\sand\s|\soraz\s|\s\u0442\u0430\s", re.IGNORECASE)

CURRENCY_TOKENS: tuple[tuple[str, str], ...] = (
    ("\u0437\u043b\u043e\u0442", "PLN"),
    ("z\u0142", "PLN"),
    ("pln", "PLN"),
    ("\u0435\u0432\u0440\u043e", "EUR"),
    ("euro", "EUR"),
    ("eur", "EUR"),
    ("\u20ac", "EUR"),
    ("\u0434\u043e\u043b\u043b\u0430\u0440", "USD"),
    ("dolar", "USD"),
    ("usd", "USD"),
    ("$", "USD"),
    ("\u0433\u0440\u0438\u0432", "UAH"),
    ("\u0433\u0440\u043d", "UAH"),
    ("uah", "UAH"),
    ("\u20b4", "UAH"),
)

SPEND_WORDS = (
    "\u043f\u043e\u0442\u0440\u0430\u0442\u0438\u043b",
    "\u0437\u0430\u043f\u043b\u0430\u0442\u0438\u043b",
    "\u043a\u0443\u043f\u0438\u043b",
    "spent",
    "paid",
    "bought",
    "wyda\u0142em",
    "zap\u0142aci\u0142em",
    "\u0432\u0438\u0442\u0440\u0430\u0442\u0438\u0432",
)

CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "transport",
        (
            "\u0442\u0430\u043a\u0441\u0438",
            "taxi",
            "uber",
            "bolt",
            "\u0431\u0435\u043d\u0437\u0438\u043d",
            "paliwo",
            "\u043c\u0435\u0442\u0440\u043e",
            "bilet",
            "\u043f\u0440\u043e\u0435\u0437\u0434",
            "fuel",
        ),
    ),
    (
        "food",
        (
            "\u043a\u0430\u0444\u0435",
            "\u0440\u0435\u0441\u0442\u043e\u0440\u0430\u043d",
            "\u043f\u0440\u043e\u0434\u0443\u043a\u0442",
            "groceries",
            "lunch",
            "coffee",
            "\u043a\u043e\u0444\u0435",
            "\u043f\u0438\u0446\u0446",
            "biedronka",
            "\u0436\u0430\u0431\u043a\u0430",
        ),
    ),
    (
        "bills",
        (
            "\u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442",
            "internet",
            "\u0442\u0435\u043b\u0435\u0444\u043e\u043d",
            "rachunek",
            "\u043a\u043e\u043c\u043c\u0443\u043d\u0430\u043b",
            "bill",
            "\u043f\u043e\u0434\u043f\u0438\u0441\u043a",
            "subscription",
        ),
    ),
    (
        "housing",
        ("\u0430\u0440\u0435\u043d\u0434", "rent", "czynsz", "\u043a\u0432\u0430\u0440\u0442\u0438\u0440"),
    ),
    (
        "health",
        (
            "\u0430\u043f\u0442\u0435\u043a",
            "pharmacy",
            "apteka",
            "\u0432\u0440\u0430\u0447",
            "doctor",
            "dentist",
            "\u0441\u0442\u043e\u043c\u0430\u0442\u043e\u043b\u043e\u0433",
        ),
    ),
    (
        "entertainment",
        ("\u043a\u0438\u043d\u043e", "cinema", "kino", "\u0438\u0433\u0440", "game", "concert", "\u043a\u043e\u043d\u0446\u0435\u0440\u0442"),
    ),
    (
        "shopping",
        ("\u043e\u0434\u0435\u0436\u0434", "clothes", "ubrania", "zalando", "\u043c\u0430\u0433\u0430\u0437\u0438\u043d"),
    ),
    (
        "education",
        ("\u043a\u0443\u0440\u0441", "course", "kurs", "\u043a\u043d\u0438\u0433", "book", "udemy"),
    ),
    (
        "travel",
        ("\u043e\u0442\u0435\u043b", "hotel", "flight", "\u0431\u0438\u043b\u0435\u0442 \u043d\u0430 \u0441\u0430\u043c\u043e\u043b", "airbnb"),
    ),
)

EVENT_WORDS = (
    "\u0432\u0441\u0442\u0440\u0435\u0447",
    "meeting",
    "spotkanie",
    "\u0437\u0443\u0441\u0442\u0440\u0456\u0447",
    "\u0441\u043e\u0437\u0432\u043e\u043d",
    "call",
    "appointment",
    "\u0432\u0438\u0437\u0438\u0442",
    "interview",
    "\u0441\u043e\u0431\u0435\u0441\u0435\u0434\u043e\u0432\u0430\u043d",
    "\u0442\u0440\u0435\u043d\u0438\u0440\u043e\u0432\u043a",
)
TASK_WORDS = (
    "\u043d\u0443\u0436\u043d\u043e",
    "\u043d\u0430\u0434\u043e",
    "need to",
    "must",
    "trzeba",
    "musz\u0119",
    "\u043f\u043e\u0442\u0440\u0456\u0431\u043d\u043e",
    "\u0442\u0440\u0435\u0431\u0430",
    "remind me",
    "\u043d\u0435 \u0437\u0430\u0431\u044b\u0442\u044c",
    "todo",
)
MEAL_WORDS = (
    "\u0441\u044a\u0435\u043b",
    "\u043f\u043e\u0435\u043b",
    "\u0437\u0430\u0432\u0442\u0440\u0430\u043a",
    "\u043e\u0431\u0435\u0434",
    "\u0443\u0436\u0438\u043d",
    "\u043f\u0435\u0440\u0435\u043a\u0443\u0441",
    "ate",
    "breakfast",
    "dinner",
    "snack",
    "jad\u0142em",
    "\u015bniadanie",
    "\u043e\u0431\u0456\u0434",
    "\u0432\u0435\u0447\u0435\u0440\u044f",
)
NOTE_WORDS = (
    "\u0437\u0430\u043c\u0435\u0442\u043a",
    "note",
    "notatka",
    "\u043d\u043e\u0442\u0430\u0442\u043a",
    "\u0438\u0434\u0435\u044f",
    "idea",
)
HABIT_LOG_WORDS = (
    "\u0432\u044b\u043f\u0438\u043b",
    "\u043f\u0440\u043e\u0431\u0435\u0436\u0430\u043b",
    "\u043f\u0440\u043e\u0448\u0451\u043b",
    "\u043f\u0440\u043e\u0448\u0435\u043b",
    "drank",
    "walked",
    "ran",
    "wypi\u0142em",
    "\u0432\u0438\u043f\u0438\u0432",
    "\u0441\u0434\u0435\u043b\u0430\u043b \u0437\u0430\u0440\u044f\u0434\u043a",
    "\u043c\u0435\u0434\u0438\u0442\u0438\u0440\u043e\u0432\u0430\u043b",
    "meditated",
)
HABIT_CREATE_WORDS = (
    "\u043d\u043e\u0432\u0430\u044f \u043f\u0440\u0438\u0432\u044b\u0447\u043a",
    "new habit",
    "nowy nawyk",
    "\u0445\u043e\u0447\u0443 \u043f\u0440\u0438\u0432\u044b\u0447\u043a",
    "\u0431\u0443\u0434\u0443 \u043a\u0430\u0436\u0434\u044b\u0439 \u0434\u0435\u043d\u044c",
)

TOMORROW_WORDS = ("\u0437\u0430\u0432\u0442\u0440\u0430", "tomorrow", "jutro")
DAY_AFTER_WORDS = ("\u043f\u043e\u0441\u043b\u0435\u0437\u0430\u0432\u0442\u0440\u0430", "pojutrze")
TODAY_WORDS = ("\u0441\u0435\u0433\u043e\u0434\u043d\u044f", "today", "dzi\u015b", "dzisiaj", "\u0441\u044c\u043e\u0433\u043e\u0434\u043d\u0456")
EVENING_WORDS = ("\u0432\u0435\u0447\u0435\u0440\u043e\u043c", "evening", "wieczorem", "\u0432\u0432\u0435\u0447\u0435\u0440\u0456")
MORNING_WORDS = ("\u0443\u0442\u0440\u043e\u043c", "morning", "rano", "\u0432\u0440\u0430\u043d\u0446\u0456")

EVENING_HOUR = 21
MORNING_HOUR = 9
DEFAULT_EVENT_HOUR = 12

CLARIFY_CURRENCY = {
    "ru": "\u0412 \u043a\u0430\u043a\u043e\u0439 \u0432\u0430\u043b\u044e\u0442\u0435 \u044d\u0442\u0430 \u0441\u0443\u043c\u043c\u0430?",
    "en": "Which currency was this amount in?",
    "pl": "W jakiej walucie by\u0142a ta kwota?",
    "uk": "\u0423 \u044f\u043a\u0456\u0439 \u0432\u0430\u043b\u044e\u0442\u0456 \u0446\u044f \u0441\u0443\u043c\u0430?",
}


def detect_language(text: str) -> str:
    lowered = text.lower()
    if any(char in lowered for char in "\u0457\u0454\u0491"):
        return "uk"
    if any(char in lowered for char in "\u0105\u0107\u0119\u0142\u0144\u015b\u017a\u017c"):
        return "pl"
    if any("\u0430" <= char <= "\u044f" for char in lowered):
        return "ru"
    return "en"


def split_clauses(text: str) -> list[str]:
    parts = [part.strip() for part in CLAUSE_SPLIT_RE.split(text)]
    return [part for part in parts if part]


def _contains(clause: str, words: tuple[str, ...]) -> bool:
    lowered = clause.lower()
    return any(word in lowered for word in words)


def _resolve_day(clause: str, today: date) -> date:
    if _contains(clause, DAY_AFTER_WORDS):
        return today + timedelta(days=2)
    if _contains(clause, TOMORROW_WORDS):
        return today + timedelta(days=1)
    return today


def _resolve_time(clause: str) -> time | None:
    match = TIME_RE.search(clause)
    if match is not None:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour=hour, minute=minute)
    if _contains(clause, EVENING_WORDS):
        return time(hour=EVENING_HOUR)
    if _contains(clause, MORNING_WORDS):
        return time(hour=MORNING_HOUR)
    return None


def _resolve_datetime(clause: str, context: CaptureContext, default_hour: int) -> datetime | None:
    moment = _resolve_time(clause)
    day = _resolve_day(clause, context.now_local.date())
    explicit_day = _contains(clause, TOMORROW_WORDS + DAY_AFTER_WORDS + TODAY_WORDS)
    if moment is None and not explicit_day:
        return None
    return datetime.combine(day, moment or time(hour=default_hour))


def _find_currency(clause: str) -> str | None:
    lowered = clause.lower()
    for token, code in CURRENCY_TOKENS:
        if token in lowered:
            return code
    return None


def _find_amount(clause: str) -> str | None:
    match = AMOUNT_RE.search(clause)
    return match.group(1).replace(",", ".") if match else None


def _category_for(clause: str) -> str:
    for category, words in CATEGORY_KEYWORDS:
        if _contains(clause, words):
            return category
    return "other"


def _strip_markers(clause: str, extra: tuple[str, ...] = ()) -> str:
    cleaned = TIME_RE.sub(" ", clause)
    for word in (
        *TOMORROW_WORDS,
        *DAY_AFTER_WORDS,
        *TODAY_WORDS,
        *EVENING_WORDS,
        *MORNING_WORDS,
        *extra,
    ):
        cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .,:;-—")


def _titleise(value: str, fallback: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return fallback
    return cleaned[:1].upper() + cleaned[1:]


def _meal_type(clause: str, context: CaptureContext) -> str:
    lowered = clause.lower()
    if any(word in lowered for word in ("\u0437\u0430\u0432\u0442\u0440\u0430\u043a", "breakfast", "\u015bniadanie")):
        return "breakfast"
    if any(word in lowered for word in ("\u043e\u0431\u0435\u0434", "lunch", "obiad", "\u043e\u0431\u0456\u0434")):
        return "lunch"
    if any(word in lowered for word in ("\u0443\u0436\u0438\u043d", "dinner", "kolacja", "\u0432\u0435\u0447\u0435\u0440\u044f")):
        return "dinner"
    hour = context.now_local.hour
    if hour < 11:
        return "breakfast"
    if hour < 16:
        return "lunch"
    if hour < 22:
        return "dinner"
    return "snack"


def _expense_intent(clause: str, context: CaptureContext) -> Intent | None:
    amount = _find_amount(clause)
    if amount is None:
        return None
    currency = _find_currency(clause)
    if currency is None:
        return None
    occurred = _resolve_datetime(clause, context, context.now_local.hour) or context.now_local.replace(
        tzinfo=None
    )
    return ExpenseCreateIntent(
        type="expense.create",
        confidence=0.96,
        source_fragment=clause,
        fields=ExpenseFields(
            amount_minor=to_minor_units(amount, currency),
            currency=currency,  # type: ignore[arg-type]
            category=_category_for(clause),  # type: ignore[arg-type]
            merchant=None,
            occurred_at=occurred,
            description=clause[:500],
        ),
    )


def _event_intent(clause: str, context: CaptureContext) -> Intent:
    starts_at = _resolve_datetime(clause, context, DEFAULT_EVENT_HOUR) or datetime.combine(
        context.now_local.date(), time(hour=DEFAULT_EVENT_HOUR)
    )
    title = _titleise(_strip_markers(clause), "Event")
    return EventCreateIntent(
        type="event.create",
        confidence=0.94,
        source_fragment=clause,
        fields=EventFields(title=title[:200], starts_at=starts_at),
    )


def _task_intent(clause: str, context: CaptureContext) -> Intent:
    due_at = _resolve_datetime(clause, context, EVENING_HOUR)
    title = _titleise(_strip_markers(clause, TASK_WORDS), "Task")
    return TaskCreateIntent(
        type="task.create",
        confidence=0.9,
        source_fragment=clause,
        fields=TaskFields(title=title[:200], due_at=due_at),
    )


def _meal_intent(clause: str, context: CaptureContext) -> Intent:
    calories: int | None = None
    lowered = clause.lower()
    if "\u043a\u043a\u0430\u043b" in lowered or "kcal" in lowered or "cal" in lowered:
        amount = _find_amount(clause)
        if amount is not None:
            calories = int(float(amount))
    title = _titleise(_strip_markers(clause, MEAL_WORDS), "Meal")
    return MealCreateIntent(
        type="meal.create",
        confidence=0.85,
        source_fragment=clause,
        fields=MealFields(
            title=title[:200],
            meal_type=_meal_type(clause, context),  # type: ignore[arg-type]
            eaten_at=_resolve_datetime(clause, context, context.now_local.hour),
            calories=calories,
            estimated=True,
        ),
    )


def _habit_log_intent(clause: str, context: CaptureContext) -> Intent:
    amount = _find_amount(clause)
    value = int(float(amount)) if amount is not None else 1
    known = next(
        (habit for habit in context.habits if habit.lower() in clause.lower()),
        None,
    )
    name = known or _titleise(_strip_markers(clause, HABIT_LOG_WORDS), "Habit")
    return HabitLogIntent(
        type="habit.log",
        confidence=0.88,
        source_fragment=clause,
        fields=HabitLogFields(
            habit_name=name[:100],
            value=value,
            logged_at=_resolve_datetime(clause, context, context.now_local.hour),
        ),
    )


def _habit_create_intent(clause: str) -> Intent:
    name = _titleise(_strip_markers(clause, HABIT_CREATE_WORDS), "Habit")
    return HabitCreateIntent(
        type="habit.create",
        confidence=0.86,
        source_fragment=clause,
        fields=HabitCreateFields(name=name[:100], measurement_type="boolean"),
    )


def _note_intent(clause: str) -> Intent:
    content = _strip_markers(clause, NOTE_WORDS) or clause
    return NoteCreateIntent(
        type="note.create",
        confidence=0.8,
        source_fragment=clause,
        fields=NoteFields(title=None, content=content[:10_000], tags=[]),
    )


def _classify(clause: str, context: CaptureContext) -> tuple[Intent | None, bool]:
    """Return `(intent, currency_missing)` for one clause."""
    if _contains(clause, SPEND_WORDS) or _find_currency(clause) is not None:
        expense = _expense_intent(clause, context)
        if expense is not None:
            return expense, False
        if _find_amount(clause) is not None:
            return None, True
    if _contains(clause, NOTE_WORDS):
        return _note_intent(clause), False
    if _contains(clause, HABIT_CREATE_WORDS):
        return _habit_create_intent(clause), False
    if _contains(clause, MEAL_WORDS):
        return _meal_intent(clause, context), False
    if _contains(clause, HABIT_LOG_WORDS):
        return _habit_log_intent(clause, context), False
    if _contains(clause, EVENT_WORDS):
        return _event_intent(clause, context), False
    if _contains(clause, TASK_WORDS):
        return _task_intent(clause, context), False
    if TIME_RE.search(clause) is not None:
        return _event_intent(clause, context), False
    return None, False


def parse_text(text: str, context: CaptureContext) -> CaptureResult:
    """Deterministically map free text to intents."""
    language = detect_language(text)
    intents: list[Intent] = []
    currency_missing = False

    for clause in split_clauses(text):
        intent, missing_currency = _classify(clause, context)
        if intent is not None:
            intents.append(intent)
        currency_missing = currency_missing or missing_currency

    if not intents and not currency_missing:
        intents.append(
            UnknownIntent(
                type="unknown",
                confidence=0.3,
                source_fragment=text[:500],
                fields=UnknownFields(reason="no_actionable_content"),
            )
        )

    question = CLARIFY_CURRENCY.get(language) if currency_missing else None
    return CaptureResult(
        language=language,
        timezone=context.timezone,
        intents=intents,
        needs_confirmation=currency_missing,
        clarification_question=question,
    )
