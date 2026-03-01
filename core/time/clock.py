"""
BOS Core Time — Explicit Clock Protocol
=========================================
Doctrine: NO datetime.now() inside engine logic.
Time must be passed explicitly as command payload
or injected via Clock protocol for infrastructure.

Engines receive time in command payloads. This module
provides the Clock protocol for infrastructure layers
(subscriptions, projections) that need wall-clock time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


# ══════════════════════════════════════════════════════════════
# CLOCK PROTOCOL
# ══════════════════════════════════════════════════════════════

class Clock(Protocol):
    """Injectable time source."""

    def now_utc(self) -> datetime:
        """Return current UTC time."""
        ...  # pragma: no cover


# ══════════════════════════════════════════════════════════════
# IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════

class SystemClock:
    """Production clock — real system time."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """
    Test clock — returns a fixed timestamp.

    Usage:
        clock = FixedClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert clock.now_utc().year == 2025
    """

    def __init__(self, fixed_dt: datetime) -> None:
        if fixed_dt.tzinfo is None:
            raise ValueError("FixedClock requires timezone-aware datetime.")
        self._fixed_dt = fixed_dt

    def now_utc(self) -> datetime:
        return self._fixed_dt

    def advance(self, seconds: float) -> None:
        """Advance the fixed time (useful for multi-step test scenarios)."""
        from datetime import timedelta
        object.__setattr__(self, "_fixed_dt", self._fixed_dt + timedelta(seconds=seconds))


# ══════════════════════════════════════════════════════════════
# DEFAULT CLOCK (infrastructure use only)
# ══════════════════════════════════════════════════════════════

_default_clock: Clock = SystemClock()


def set_default_clock(clock: Clock) -> None:
    """Override the default clock (testing only)."""
    global _default_clock
    _default_clock = clock


def get_default_clock() -> Clock:
    """Get the current default clock."""
    return _default_clock


def now_utc() -> datetime:
    """Convenience: get current UTC time from default clock."""
    return _default_clock.now_utc()
