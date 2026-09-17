"""Pure time-range rules for events. No database, no timezone guessing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

DEFAULT_EVENT_MINUTES = 60


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Half-open range. An event without an end gets a default duration."""

    start: datetime
    end: datetime | None = None

    @property
    def effective_end(self) -> datetime:
        if self.end is not None:
            return self.end
        return self.start + timedelta(minutes=DEFAULT_EVENT_MINUTES)

    @property
    def duration_minutes(self) -> int:
        return int((self.effective_end - self.start).total_seconds() // 60)


def overlaps(first: TimeRange, second: TimeRange) -> bool:
    """True when the two ranges share at least one instant.

    Ranges are half-open, so an event that ends exactly when another starts is
    not a conflict.
    """
    return first.start < second.effective_end and second.start < first.effective_end


def find_overlaps(
    candidate: TimeRange, existing: Sequence[tuple[UUID, TimeRange]]
) -> list[UUID]:
    """Ids of existing events that clash with the candidate."""
    return [event_id for event_id, span in existing if overlaps(candidate, span)]
