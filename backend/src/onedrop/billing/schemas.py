"""Billing request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanFeatures(BaseModel):
    photo_recognition: bool
    morning_digest: bool
    advanced_analytics: bool
    csv_export: bool
    history_days: int


class PlanResponse(BaseModel):
    """Current plan, its limits and the Pro price in Stars."""

    plan: str
    status: str
    expires_at: datetime | None
    bonus_limit: int
    period_scope: str
    period_limit: int
    features: PlanFeatures
    pro_price_stars: int
    pro_period_days: int


class InvoiceRequest(StrictModel):
    plan: Literal["pro"] = "pro"


class InvoiceResponse(BaseModel):
    """Invoice link plus the payload the client must not modify."""

    invoice_link: str | None
    payload: str
    amount_stars: int
    currency: str
    period_days: int
    test_mode: bool = False


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount_stars: int
    plan: str
    period_days: int
    status: str
    created_at: datetime


class ActivationResponse(BaseModel):
    activated: bool
    duplicate: bool
    plan: str
    expires_at: datetime | None
    extended_days: int = Field(default=0, ge=0)
