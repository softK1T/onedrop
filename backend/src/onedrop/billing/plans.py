"""Plan definitions and quota arithmetic. Pure functions, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from onedrop.config import Settings
from onedrop.db.models.enums import Plan

BONUS_PERIOD_KEY = "onboarding"


@dataclass(frozen=True, slots=True)
class PlanLimits:
    """What a plan allows. `period_limit` is daily for free, monthly for pro."""

    plan: str
    bonus_limit: int
    period_limit: int
    period_scope: str
    photo_recognition: bool
    morning_digest: bool
    advanced_analytics: bool
    csv_export: bool
    history_days: int


def limits_for(plan: str, settings: Settings) -> PlanLimits:
    if plan == Plan.PRO.value:
        return PlanLimits(
            plan=Plan.PRO.value,
            bonus_limit=0,
            period_limit=settings.pro_monthly_ai_limit,
            period_scope="monthly",
            photo_recognition=True,
            morning_digest=True,
            advanced_analytics=True,
            csv_export=True,
            history_days=3650,
        )
    return PlanLimits(
        plan=Plan.FREE.value,
        bonus_limit=settings.free_onboarding_bonus,
        period_limit=settings.free_daily_ai_limit,
        period_scope="daily",
        photo_recognition=False,
        morning_digest=False,
        advanced_analytics=False,
        csv_export=False,
        history_days=90,
    )


def daily_period_key(moment_local: datetime) -> str:
    return moment_local.strftime("%Y-%m-%d")


def monthly_period_key(moment_local: datetime) -> str:
    return moment_local.strftime("%Y-%m")


def period_key_for(limits: PlanLimits, moment_local: datetime) -> str:
    if limits.period_scope == "monthly":
        return monthly_period_key(moment_local)
    return daily_period_key(moment_local)


@dataclass(frozen=True, slots=True)
class QuotaState:
    """Remaining AI allowance for one user at one point in time."""

    plan: str
    bonus_used: int
    bonus_limit: int
    period_used: int
    period_limit: int
    period_scope: str

    @property
    def bonus_remaining(self) -> int:
        return max(0, self.bonus_limit - self.bonus_used)

    @property
    def period_remaining(self) -> int:
        return max(0, self.period_limit - self.period_used)

    @property
    def remaining(self) -> int:
        return self.bonus_remaining + self.period_remaining

    @property
    def allowed(self) -> bool:
        return self.remaining > 0

    @property
    def next_scope(self) -> str:
        """Which counter the next AI action should charge."""
        return "bonus" if self.bonus_remaining > 0 else self.period_scope


def evaluate_quota(
    *, limits: PlanLimits, bonus_used: int, period_used: int
) -> QuotaState:
    return QuotaState(
        plan=limits.plan,
        bonus_used=bonus_used,
        bonus_limit=limits.bonus_limit,
        period_used=period_used,
        period_limit=limits.period_limit,
        period_scope=limits.period_scope,
    )
