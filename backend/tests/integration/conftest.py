"""Real PostgreSQL/Redis fixtures for integration and acceptance tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://onedrop:onedrop@localhost:5432/onedrop_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from onedrop.config import get_settings
from onedrop.db import models  # noqa: F401
from onedrop.db.base import Base


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    return get_settings().database_url


@pytest.fixture(scope="session")
def integration_engine(integration_database_url: str):
    return create_async_engine(integration_database_url, pool_pre_ping=True)


@pytest.fixture(scope="session", autouse=True)
async def schema(integration_engine) -> AsyncIterator[None]:
    async with integration_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with integration_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await integration_engine.dispose()


@pytest.fixture
async def session(integration_engine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(integration_engine, expire_on_commit=False)
    async with maker() as database_session:
        try:
            yield database_session
        finally:
            await database_session.rollback()
            await database_session.close()


@pytest.fixture
async def redis_client() -> AsyncIterator[Redis]:
    client = Redis.from_url(get_settings().redis_url)
    await client.ping()
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
async def user(session: AsyncSession):
    from onedrop.db.repositories.users import UserRepository

    row = await UserRepository(session).upsert_from_telegram(
        telegram_user_id=777001,
        first_name="Integration",
        username="integration_user",
        language_code="en",
    )
    await session.commit()
    return row
