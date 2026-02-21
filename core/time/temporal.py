"""
BOS Core Time — Temporal Helpers
==================================
Pure functions for time interval logic.
All functions take explicit datetime arguments — no hidden clock access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


# ══════════════════════════════════════════════════════════════
# TIME WINDOW — Closed interval [start, end]
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TimeWindow:
    """
    A closed time interval [start, end].

    Invariant: start <= end (enforced at construction).
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(
                f"TimeWindow start ({self.start}) must be <= end ({self.end})."
            )

    def contains(self, dt: datetime) -> bool:
        """Check if datetime falls within window (inclusive)."""
        return self.start <= dt <= self.end

    def overlaps(self, other: TimeWindow) -> bool:
        """Check if two windows overlap."""
        return self.start <= other.end and other.start <= self.end

    def duration(self) -> timedelta:
        """Return the duration of the window."""
        return self.end - self.start


# ══════════════════════════════════════════════════════════════
# PURE TEMPORAL FUNCTIONS
# ══════════════════════════════════════════════════════════════

def is_expired(issued_at: datetime, ttl_seconds: int, now: datetime) -> bool:
    """
    Check if something issued at `issued_at` has expired given a TTL.

    All arguments are explicit — no hidden clock.
    """
    return (now - issued_at).total_seconds() > ttl_seconds


def seconds_until_expiry(
    issued_at: datetime, ttl_seconds: int, now: datetime
) -> Optional[float]:
    """
    Return seconds remaining before expiry, or None if already expired.
    """
    remaining = ttl_seconds - (now - issued_at).total_seconds()
    return remaining if remaining > 0 else None


def clamp_to_window(dt: datetime, window: TimeWindow) -> datetime:
    """Clamp a datetime to within the given window."""
    if dt < window.start:
        return window.start
    if dt > window.end:
        return window.end
    return dt
