"""Request and response schemas for the auth endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TelegramLoginRequest(StrictModel):
    init_data: str = Field(min_length=1, max_length=4096)


class DevLoginRequest(StrictModel):
    telegram_user_id: int = Field(gt=0)
    first_name: str | None = Field(default=None, max_length=128)
    username: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=8)


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=16, max_length=256)


class LogoutRequest(StrictModel):
    refresh_token: str = Field(min_length=16, max_length=256)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"
