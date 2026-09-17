"""Structured logging setup with redaction of sensitive values."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from onedrop.config import get_settings

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "bot_token",
        "telegram_bot_token",
        "init_data",
        "initdata",
        "access_token",
        "refresh_token",
        "jwt",
        "password",
        "api_key",
        "openrouter_api_key",
        "stt_api_key",
        "telegram_payment_charge_id",
        "provider_payment_charge_id",
        "audio",
        "image",
        "file_bytes",
    }
)

REDACTED = "[redacted]"


def _redact_sensitive(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Replace values of sensitive keys before anything reaches stdout."""
    for key in list(event_dict.keys()):
        lowered = key.lower()
        if lowered in SENSITIVE_KEYS or lowered.endswith(("_token", "_secret", "_key")):
            event_dict[key] = REDACTED
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
