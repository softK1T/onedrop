"""Safe administrative aggregate endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from onedrop.api.dependencies import CurrentUser, DbSession
from onedrop.config import get_settings
from onedrop.db.models.billing import Payment, Subscription
from onedrop.db.models.inbox import AiOperation, InboxItem
from onedrop.db.models.notifications import ScheduledNotification
from onedrop.db.models.user import User
from onedrop.errors import ForbiddenError

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminOverview(BaseModel):
    users_count: int
    captures_by_status: dict[str, int]
    failed_captures_count: int
    pending_notifications_count: int
    failed_notifications_count: int
    ai_operations_count: int
    ai_cost_micro: int
    provider_cost_micro: dict[str, int]
    active_subscriptions_count: int
    payments_count: int
    payment_stars_total: int


def require_admin(user: CurrentUser) -> User:
    if user.telegram_user_id not in set(get_settings().admin_telegram_user_id_list):
        raise ForbiddenError("Administrator permission is required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/overview", response_model=AdminOverview)
async def overview(session: DbSession, _admin: AdminUser) -> AdminOverview:
    now = datetime.now(tz=UTC)
    users_count = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    capture_rows = (
        await session.execute(select(InboxItem.status, func.count()).group_by(InboxItem.status))
    ).all()
    captures = {str(status): int(count) for status, count in capture_rows}
    notification_rows = (
        await session.execute(
            select(ScheduledNotification.status, func.count()).group_by(
                ScheduledNotification.status
            )
        )
    ).all()
    notifications = {str(status): int(count) for status, count in notification_rows}
    ai_count, ai_cost = (
        await session.execute(
            select(
                func.count(AiOperation.id),
                func.coalesce(func.sum(AiOperation.cost_micro), 0),
            )
        )
    ).one()
    provider_rows = (
        await session.execute(
            select(
                AiOperation.provider,
                func.coalesce(func.sum(AiOperation.cost_micro), 0),
            ).group_by(AiOperation.provider)
        )
    ).all()
    active_subscriptions = int(
        await session.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.status == "active",
                (Subscription.expires_at.is_(None)) | (Subscription.expires_at > now),
            )
        )
        or 0
    )
    payment_count, payment_total = (
        await session.execute(
            select(
                func.count(Payment.id), func.coalesce(func.sum(Payment.amount_stars), 0)
            ).where(Payment.status == "paid")
        )
    ).one()
    return AdminOverview(
        users_count=users_count,
        captures_by_status=captures,
        failed_captures_count=captures.get("failed", 0),
        pending_notifications_count=notifications.get("pending", 0),
        failed_notifications_count=notifications.get("failed", 0),
        ai_operations_count=int(ai_count),
        ai_cost_micro=int(ai_cost),
        provider_cost_micro={str(provider): int(cost) for provider, cost in provider_rows},
        active_subscriptions_count=active_subscriptions,
        payments_count=int(payment_count),
        payment_stars_total=int(payment_total),
    )
