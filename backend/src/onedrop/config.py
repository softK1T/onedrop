"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "staging", "production"]
BotMode = Literal["polling", "webhook", "disabled"]
AiMode = Literal["fake", "real"]

SUPPORTED_CURRENCIES: tuple[str, ...] = ("PLN", "EUR", "USD", "UAH")
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "ru", "pl", "uk")


class Settings(BaseSettings):
    """Runtime configuration. Never hardcode secrets: everything comes from env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = "development"
    app_name: str = "OneDrop"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    public_api_url: str = "http://localhost:8000"
    public_webapp_url: str = "http://localhost:5173"
    secret_key: str = "dev-only-change-me-32-chars-minimum"
    cors_allow_origins: str = "http://localhost:5173"
    trusted_hosts: str = "localhost,127.0.0.1"
    rate_limit_per_minute: int = 60

    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000
    init_data_max_age_seconds: int = 86_400
    dev_login_enabled: bool = True

    database_url: str = "postgresql+asyncpg://onedrop:onedrop@localhost:5432/onedrop"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "onedrop"
    s3_secret_key: str = "onedrop-dev-secret"
    s3_bucket: str = "onedrop-media"
    s3_region: str = "us-east-1"
    media_retention_days: int = 30
    max_upload_bytes: int = 10_485_760

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_url: str = ""
    bot_mode: BotMode = "polling"

    ai_provider_mode: AiMode = "fake"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"
    stt_api_key: str = ""
    stt_base_url: str = "https://api.openai.com/v1"
    stt_model: str = "whisper-1"
    vision_model: str = "openai/gpt-4o-mini"
    ai_request_timeout_seconds: int = 60
    ai_min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)

    free_onboarding_bonus: int = 15
    free_daily_ai_limit: int = 3
    pro_monthly_ai_limit: int = 1000
    pro_price_stars: int = 250
    pro_period_days: int = 30
    billing_test_mode: bool = False

    default_timezone: str = "Europe/Warsaw"
    default_locale: str = "en"
    default_base_currency: str = "PLN"

    reminder_max_attempts: int = Field(default=5, ge=1, le=20)
    reminder_base_delay_seconds: int = Field(default=60, ge=1, le=86_400)
    reminder_max_delay_seconds: int = Field(default=3600, ge=1, le=86_400)
    reminder_lock_timeout_seconds: int = Field(default=300, ge=1, le=86_400)
    reminder_claim_limit: int = Field(default=25, ge=1, le=500)

    @model_validator(mode="after")
    def _check_reminder_delays(self) -> Settings:
        if self.reminder_max_delay_seconds < self.reminder_base_delay_seconds:
            raise ValueError(
                "reminder_max_delay_seconds must not be below reminder_base_delay_seconds"
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def dev_login_allowed(self) -> bool:
        """Dev login is never available in production, regardless of the flag."""
        return self.dev_login_enabled and not self.is_production

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        hosts = [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]
        return hosts or ["*"]

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token) and self.bot_mode != "disabled"

    @property
    def ai_real_mode(self) -> bool:
        return self.ai_provider_mode == "real"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used across the application."""
    return Settings()
