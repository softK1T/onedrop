"""FastAPI application factory. Kept intentionally small."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from onedrop import __version__
from onedrop.api.errors import register_exception_handlers
from onedrop.api.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from onedrop.api.routers import auth as auth_router
from onedrop.api.routers import system as system_router
from onedrop.config import get_settings
from onedrop.db.session import dispose_engine
from onedrop.logging import configure_logging, get_logger

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    get_logger(__name__).info(
        "api.startup",
        environment=settings.app_env,
        ai_provider_mode=settings.ai_provider_mode,
        telegram_enabled=settings.telegram_enabled,
    )
    yield
    await dispose_engine()


def build_api_router() -> APIRouter:
    """Compose the versioned API router from module routers."""
    api = APIRouter(prefix=API_PREFIX)
    api.include_router(system_router.router)
    api.include_router(auth_router.router)
    return api


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        summary="AI-powered Telegram life planner",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(build_api_router())
    return app


app = create_app()
