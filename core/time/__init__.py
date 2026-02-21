"""
BOS Core Time — Public API
============================
Explicit clock protocol and temporal helpers.
Doctrine: NO datetime.now() in engine logic.
"""

from core.time.clock import (
    Clock,
    FixedClock,
    SystemClock,
    get_default_clock,
    now_utc,
    set_default_clock,
)
from core.time.temporal import (
    TimeWindow,
    clamp_to_window,
    is_expired,
    seconds_until_expiry,
)

__all__ = [
    "Clock",
    "FixedClock",
    "SystemClock",
    "get_default_clock",
    "set_default_clock",
    "now_utc",
    "TimeWindow",
    "is_expired",
    "seconds_until_expiry",
    "clamp_to_window",
]
