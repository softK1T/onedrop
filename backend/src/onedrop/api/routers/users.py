"""Profile, settings, usage, export and account deletion endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.users.schemas import (
    DeleteAccountResponse,
    ExportResponse,
    UsageResponse,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from onedrop.users.service import UserService

router = APIRouter(prefix="/me", tags=["user"])


@router.get("", response_model=UserResponse)
async def get_me(session: DbSession, user: CurrentUser) -> UserResponse:
    """Current profile with settings."""
    settings_row = await UserService(session).settings_for(user.id)
    return UserResponse(
        id=user.id,
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        username=user.username,
        locale=user.locale,
        created_at=user.created_at,
        settings=UserSettingsResponse.model_validate(settings_row),
    )


@router.patch("/settings", response_model=UserSettingsResponse)
async def patch_settings(
    payload: UserSettingsUpdate, session: DbSession, user: CurrentUser
) -> UserSettingsResponse:
    """Update timezone, currency, budget, reminder toggles and consent."""
    settings_row = await UserService(session).update_settings(user.id, payload)
    return UserSettingsResponse.model_validate(settings_row)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(session: DbSession, user: CurrentUser) -> UsageResponse:
    """Remaining AI allowance and plan features."""
    return await UserService(session).usage(user.id)


@router.post("/export", response_model=ExportResponse)
async def export_data(session: DbSession, user: CurrentUser) -> ExportResponse:
    """Export every record OneDrop stores about the caller."""
    return await UserService(session).export(user.id)


@router.delete("", response_model=DeleteAccountResponse)
async def delete_account(session: DbSession, user: CurrentUser) -> DeleteAccountResponse:
    """Delete the account, all records and all uploaded media. Irreversible."""
    return await UserService(session).delete_account(user.id)
