"""Seed a demo user with sample records.

Safe to run repeatedly: the demo user is looked up by Telegram id and records are
only created when the account is still empty.

Run with: `python scripts/seed_demo.py`
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from onedrop.db.models.finance import Expense
from onedrop.db.models.health import Habit, Meal
from onedrop.db.models.notes import Note
from onedrop.db.models.planner import Event, Task
from onedrop.db.repositories.users import UserRepository
from onedrop.db.session import dispose_engine, session_scope
from onedrop.logging import configure_logging, get_logger

logger = get_logger(__name__)

DEMO_TELEGRAM_ID = 100_001
DEMO_FIRST_NAME = "Demo"


async def seed() -> None:
    now = datetime.now(tz=UTC)
    async with session_scope() as session:
        repository = UserRepository(session)
        user = await repository.upsert_from_telegram(
            telegram_user_id=DEMO_TELEGRAM_ID,
            first_name=DEMO_FIRST_NAME,
            username="onedrop_demo",
            language_code="en",
        )
        settings_row = await repository.get_settings(user.id)
        if settings_row is None:
            settings_row = await repository.update_settings(user.id, {})
        settings_row.monthly_budget_minor = 2_000_00
        settings_row.consent_at = settings_row.consent_at or now
        settings_row.onboarding_completed = True

        existing = await session.execute(
            select(func.count(Task.id)).where(Task.user_id == user.id)
        )
        if int(existing.scalar_one() or 0) > 0:
            logger.info("seed.skipped", reason="demo user already has records")
            return

        session.add_all(
            [
                Task(
                    user_id=user.id,
                    title="Pay the internet bill",
                    due_at=now.replace(hour=21, minute=0, second=0, microsecond=0),
                    priority="high",
                    category="bills",
                ),
                Task(user_id=user.id, title="Review OneDrop roadmap"),
                Event(
                    user_id=user.id,
                    title="Meeting with Andrew",
                    starts_at=(now + timedelta(days=1)).replace(
                        hour=13, minute=0, second=0, microsecond=0
                    ),
                    location="Cafe",
                ),
                Expense(
                    user_id=user.id,
                    amount_minor=4500,
                    currency="PLN",
                    base_amount_minor=4500,
                    base_currency="PLN",
                    category="transport",
                    occurred_at=now,
                    description="Taxi",
                ),
                Meal(
                    user_id=user.id,
                    title="Oatmeal with banana",
                    meal_type="breakfast",
                    eaten_at=now.replace(hour=8, minute=0, second=0, microsecond=0),
                    calories=380,
                    protein=12,
                    fat=8,
                    carbohydrates=65,
                    estimated=True,
                ),
                Habit(
                    user_id=user.id,
                    name="Morning walk",
                    measurement_type="boolean",
                    schedule={"days": [1, 2, 3, 4, 5]},
                ),
                Note(
                    user_id=user.id,
                    title="Demo note",
                    content="Send a voice message to see transcription in demo mode.",
                    tags=["demo"],
                    pinned=True,
                ),
            ]
        )
        logger.info("seed.completed", telegram_user_id=DEMO_TELEGRAM_ID)


async def main() -> None:
    configure_logging()
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
