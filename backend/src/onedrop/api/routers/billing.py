"""Billing endpoints. Payment confirmation arrives through the bot, not here."""

from __future__ import annotations

from fastapi import APIRouter

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.billing.schemas import InvoiceRequest, InvoiceResponse, PlanResponse
from onedrop.billing.service import BillingService
from onedrop.users.schemas import UsageResponse
from onedrop.users.service import UserService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plan", response_model=PlanResponse)
async def get_plan(session: DbSession, user: CurrentUser) -> PlanResponse:
    """Active plan, its limits and the configured Stars price."""
    return await BillingService(session).plan(user.id)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(session: DbSession, user: CurrentUser) -> UsageResponse:
    """Remaining AI allowance for the current period."""
    return await UserService(session).usage(user.id)


@router.post("/invoice", response_model=InvoiceResponse)
async def create_invoice(
    payload: InvoiceRequest, session: DbSession, user: CurrentUser
) -> InvoiceResponse:
    """Create a Telegram Stars invoice link for the Pro plan."""
    _ = payload.plan
    return await BillingService(session).create_invoice(user.id)
