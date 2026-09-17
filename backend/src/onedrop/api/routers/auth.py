"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from onedrop.api.dependencies import DbSession, UserAgent
from onedrop.auth.schemas import (
    DevLoginRequest,
    LogoutRequest,
    RefreshRequest,
    TelegramLoginRequest,
    TokenPairResponse,
)
from onedrop.auth.service import AuthService
from onedrop.config import get_settings
from onedrop.errors import NotFoundError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=TokenPairResponse)
async def login_with_telegram(
    payload: TelegramLoginRequest, session: DbSession, user_agent: UserAgent
) -> TokenPairResponse:
    """Exchange signed Telegram init data for an access/refresh pair."""
    return await AuthService(session).login_with_init_data(
        payload.init_data, user_agent=user_agent
    )


@router.post("/dev", response_model=TokenPairResponse)
async def dev_login(
    payload: DevLoginRequest, session: DbSession, user_agent: UserAgent
) -> TokenPairResponse:
    """Development-only login. Returns 404 when disabled or in production."""
    if not get_settings().dev_login_allowed:
        raise NotFoundError("Not found")
    return await AuthService(session).dev_login(
        telegram_user_id=payload.telegram_user_id,
        first_name=payload.first_name,
        username=payload.username,
        locale=payload.locale,
        user_agent=user_agent,
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_session(
    payload: RefreshRequest, session: DbSession, user_agent: UserAgent
) -> TokenPairResponse:
    return await AuthService(session).refresh(
        payload.refresh_token, user_agent=user_agent
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, session: DbSession) -> Response:
    await AuthService(session).logout(payload.refresh_token)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
