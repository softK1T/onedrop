"""Exception handlers translating application errors into JSON responses."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from onedrop.errors import AppError
from onedrop.logging import get_logger

logger = get_logger(__name__)


def error_body(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Uniform error envelope used by every endpoint."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = jsonable_encoder(details)
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers so no stack trace or internal detail ever leaks."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, AppError)
        logger.info(
            "api.app_error",
            code=exc.code,
            status=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        logger.info("api.validation_error", path=request.url.path)
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_error",
                "Request payload is invalid",
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, StarletteHTTPException)
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(f"http_{exc.status_code}", detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "api.unhandled_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Internal server error"),
        )
