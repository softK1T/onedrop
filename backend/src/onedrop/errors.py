"""Application error hierarchy shared by services and the API layer."""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected, user-visible failures."""

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class QuotaExceededError(AppError):
    """AI quota exhausted; the client should show the paywall."""

    status_code = 402
    code = "quota_exceeded"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


class UnsupportedMediaError(AppError):
    status_code = 415
    code = "unsupported_media"


class ProviderError(AppError):
    """An AI or messaging provider failed; the operation may be retried."""

    status_code = 503
    code = "provider_unavailable"
