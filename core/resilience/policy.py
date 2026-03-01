"""
BOS Core Resilience — Enforcement Policy
===========================================
Pre-execution check: reject write commands if system is degraded.
"""

from __future__ import annotations

from typing import Optional

from core.commands.rejection import RejectionReason
from core.resilience.modes import SystemHealth


def check_resilience(
    health: SystemHealth, is_write: bool
) -> Optional[RejectionReason]:
    """
    Return a RejectionReason if the operation should be blocked.

    - Write operations require NORMAL mode.
    - Read operations are always allowed.
    """
    if is_write and not health.can_write():
        return RejectionReason(
            code="SYSTEM_DEGRADED",
            message=(
                f"System is in {health.mode.value} mode"
                f"{': ' + health.reason if health.reason else ''}. "
                f"Write operations are not accepted."
            ),
            policy_name="check_resilience",
        )
    return None
