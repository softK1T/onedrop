"""Budget evaluation. Pure integer arithmetic on minor units."""

from __future__ import annotations

from dataclasses import dataclass

WARNING_THRESHOLD_PERCENT = 80


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    """Month-to-date spending against the configured monthly budget."""

    currency: str
    spent_minor: int
    budget_minor: int | None

    @property
    def has_budget(self) -> bool:
        return self.budget_minor is not None and self.budget_minor > 0

    @property
    def remaining_minor(self) -> int | None:
        if not self.has_budget or self.budget_minor is None:
            return None
        return self.budget_minor - self.spent_minor

    @property
    def usage_percent(self) -> int | None:
        if not self.has_budget or self.budget_minor is None:
            return None
        return int(round(self.spent_minor * 100 / self.budget_minor))

    @property
    def exceeded(self) -> bool:
        remaining = self.remaining_minor
        return remaining is not None and remaining < 0

    @property
    def warning(self) -> bool:
        """True once spending reaches the warning threshold."""
        percent = self.usage_percent
        return percent is not None and percent >= WARNING_THRESHOLD_PERCENT


def evaluate_budget(
    *, currency: str, spent_minor: int, budget_minor: int | None
) -> BudgetStatus:
    return BudgetStatus(
        currency=currency.upper(),
        spent_minor=max(0, spent_minor),
        budget_minor=budget_minor,
    )


def delta_percent(current_minor: int, previous_minor: int) -> int | None:
    """Month-over-month change in percent, or None when there is no baseline."""
    if previous_minor <= 0:
        return None
    return int(round((current_minor - previous_minor) * 100 / previous_minor))
