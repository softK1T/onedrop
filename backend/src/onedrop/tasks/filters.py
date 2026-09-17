"""Pure list filters for tasks. No I/O, fully unit-testable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from onedrop.ai.normalize import local_day_bounds, local_now

TaskFilter = Literal["today", "upcoming", "no_date", "completed", "all"]
TASK_FILTERS: tuple[str, ...] = ("today", "upcoming", "no_date", "completed", "all")


@dataclass(frozen=True, slots=True)
class FilterWindow:
    """Resolved UTC window plus the flags a repository needs."""

    name: str
    start: datetime | None = None
    end: datetime | None = None
    require_due: bool = False
    require_no_due: bool = False
    only_open: bool = False
    only_completed: bool = False


def build_filter_window(
    name: str, timezone: str, *, now_local: datetime | None = None
) -> FilterWindow:
    """Translate a UI filter into a UTC window for the query layer."""
    if name not in TASK_FILTERS:
        name = "all"
    reference = now_local or local_now(timezone)
    start_of_day, end_of_day = local_day_bounds(reference.date(), timezone)

    if name == "today":
        return FilterWindow(
            name=name,
            start=start_of_day,
            end=end_of_day,
            require_due=True,
            only_open=True,
        )
    if name == "upcoming":
        return FilterWindow(name=name, start=end_of_day, require_due=True, only_open=True)
    if name == "no_date":
        return FilterWindow(name=name, require_no_due=True, only_open=True)
    if name == "completed":
        return FilterWindow(name=name, only_completed=True)
    return FilterWindow(name="all")
