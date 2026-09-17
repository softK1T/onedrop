"""Expense endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.db.repositories.expenses import MAX_PAGE_SIZE
from onedrop.expenses.schemas import (
    ExpenseCreate,
    ExpensePage,
    ExpenseResponse,
    ExpenseUpdate,
    MonthlySummary,
)
from onedrop.expenses.service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=ExpensePage)
async def list_expenses(
    session: DbSession,
    user: CurrentUser,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExpensePage:
    """Expenses of one local calendar month, newest first."""
    items, has_more, resolved_year, resolved_month = await ExpenseService(session).list_month(
        user.id, year=year, month=month, limit=limit, offset=offset
    )
    return ExpensePage(
        items=[ExpenseResponse.model_validate(item) for item in items],
        year=resolved_year,
        month=resolved_month,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/summary", response_model=MonthlySummary)
async def expense_summary(
    session: DbSession,
    user: CurrentUser,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> MonthlySummary:
    """Category totals, month-over-month delta and budget state, computed in SQL."""
    return await ExpenseService(session).monthly_summary(user.id, year=year, month=month)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate, session: DbSession, user: CurrentUser
) -> ExpenseResponse:
    """Create an expense. The applied FX rate is stored with the row."""
    expense = await ExpenseService(session).create(user.id, payload)
    return ExpenseResponse.model_validate(expense)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> ExpenseResponse:
    expense = await ExpenseService(session).get(user.id, expense_id)
    return ExpenseResponse.model_validate(expense)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def patch_expense(
    expense_id: uuid.UUID,
    payload: ExpenseUpdate,
    session: DbSession,
    user: CurrentUser,
) -> ExpenseResponse:
    expense = await ExpenseService(session).patch(user.id, expense_id, payload)
    return ExpenseResponse.model_validate(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> Response:
    await ExpenseService(session).delete(user.id, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
