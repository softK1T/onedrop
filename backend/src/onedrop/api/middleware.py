"""HTTP middleware: security headers and request logging."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from onedrop.config import get_settings
from onedrop.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative security headers to every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a request id to the log context and record request duration."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "api.request",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        return response
