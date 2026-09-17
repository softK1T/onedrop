"""Shared test configuration.

Environment defaults are set before the application settings are imported so unit
tests never touch real credentials or external services.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-0123456789abcdef")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:test-bot-token")
os.environ.setdefault("AI_PROVIDER_MODE", "fake")
os.environ.setdefault("DEV_LOGIN_ENABLED", "true")
os.environ.setdefault("DEFAULT_TIMEZONE", "Europe/Warsaw")
os.environ.setdefault("DEFAULT_BASE_CURRENCY", "PLN")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://onedrop:onedrop@localhost:5432/onedrop_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

TEST_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
