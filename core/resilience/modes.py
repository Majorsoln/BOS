"""
BOS Core Resilience — System Health Modes
============================================
Models system degradation states:
  NORMAL → DEGRADED → READ_ONLY

Commands check resilience mode before execution.
Write commands are rejected in non-NORMAL modes.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════
# RESILIENCE MODE ENUM
# ══════════════════════════════════════════════════════════════

class ResilienceMode(Enum):
    """System operational modes."""
    NORMAL = "NORMAL"       # All operations allowed
    DEGRADED = "DEGRADED"   # Writes queued, reads OK
    READ_ONLY = "READ_ONLY" # No writes, reads only


# ══════════════════════════════════════════════════════════════
# SYSTEM HEALTH STATE
# ══════════════════════════════════════════════════════════════

class SystemHealth:
    """
    Current system health state.

    Tracks the operational mode and the reason for any degradation.
    """

    def __init__(self, mode: ResilienceMode = ResilienceMode.NORMAL) -> None:
        self._mode = mode
        self._reason: Optional[str] = None

    @property
    def mode(self) -> ResilienceMode:
        return self._mode

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    def can_write(self) -> bool:
        """Check if write operations are allowed."""
        return self._mode == ResilienceMode.NORMAL

    def can_read(self) -> bool:
        """Check if read operations are allowed (always True for now)."""
        return True

    def set_degraded(self, reason: str) -> None:
        """Transition to DEGRADED mode."""
        self._mode = ResilienceMode.DEGRADED
        self._reason = reason

    def set_read_only(self, reason: str) -> None:
        """Transition to READ_ONLY mode."""
        self._mode = ResilienceMode.READ_ONLY
        self._reason = reason

    def recover(self) -> None:
        """Recover to NORMAL mode."""
        self._mode = ResilienceMode.NORMAL
        self._reason = None
