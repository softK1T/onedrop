"""Expense request and response schemas. Amounts are integer minor units."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CurrencyCode = Literal["PLN", "EUR", "USD", "UAH"]
CategoryCode = Literal[
    "food",
    "transport",
    "housing",
    "health",
    "entertainment",
    "shopping",
    "bills",
    "education",
    "travel",
    "other",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpenseCreate(StrictModel):
    amount_minor: int = Field(ge=0, le=1_000_000_000_000)
    currency: CurrencyCode
    category: CategoryCode = "other"
    merchant: str | None = Field(default=None, max_length=120)
    occurred_at: datetime | None = None
    description: str | None = Field(default=None, max_length=500)


class ExpenseUpdate(StrictModel):
    amount_minor: int | None = Field(default=None, ge=0, le=1_000_000_000_000)
    currency: CurrencyCode | None = None
    category: CategoryCode | None = None
    merchant: str | None = Field(default=None, max_length=120)
    occurred_at: datetime | None = None
    description: str | None = Field(default=None, max_length=500)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount_minor: int
    currency: str
    base_amount_minor: int | None
    base_currency: str | None
    fx_rate: Decimal | None
    category: str
    merchant: str | None
    occurred_at: datetime
    description: str | None
    source_inbox_item_id: UUID | None
    created_at: datetime


class ExpensePage(BaseModel):
    items: list[ExpenseResponse]
    year: int
    month: int
    limit: int
    offset: int
    has_more: bool


class CategoryTotal(BaseModel):
    category: str
    total_minor: int
    share_percent: int


class BudgetSummary(BaseModel):
    currency: str
    spent_minor: int
    budget_minor: int | None
    remaining_minor: int | None
    usage_percent: int | None
    warning: bool
    exceeded: bool


class MonthlySummary(BaseModel):
    """Everything the Expenses screen needs in one response."""

    year: int
    month: int
    base_currency: str
    total_minor: int
    previous_total_minor: int
    delta_percent: int | None
    categories: list[CategoryTotal]
    budget: BudgetSummary
