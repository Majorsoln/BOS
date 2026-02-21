"""
BOS Projections — Guard Read Model
======================================
Staleness tracking for read models.

Reports whether a projection is fresh enough
for a given SLA requirement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass(frozen=True)
class StalenessPolicy:
    """Defines acceptable staleness for a projection."""

    projection_name: str
    max_staleness_seconds: int  # e.g. 60 = must be updated within last 60s
    description: str = ""


@dataclass(frozen=True)
class FreshnessCheck:
    """Result of checking projection freshness."""

    projection_name: str
    is_fresh: bool
    last_updated_at: Optional[datetime]
    staleness_seconds: float = 0.0
    policy_max_seconds: int = 0


class FreshnessGuard:
    """
    Tracks projection freshness and enforces SLA policies.

    Used by API handlers to warn consumers when data may be stale.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, StalenessPolicy] = {}
        self._last_updated: Dict[str, datetime] = {}

    def set_policy(self, policy: StalenessPolicy) -> None:
        self._policies[policy.projection_name] = policy

    def record_update(self, projection_name: str, updated_at: datetime) -> None:
        """Record that a projection was updated."""
        self._last_updated[projection_name] = updated_at

    def check(self, projection_name: str, now: datetime) -> FreshnessCheck:
        """Check if a projection meets its freshness SLA."""
        policy = self._policies.get(projection_name)
        last = self._last_updated.get(projection_name)

        if policy is None:
            # No policy = always fresh
            return FreshnessCheck(
                projection_name=projection_name,
                is_fresh=True,
                last_updated_at=last,
            )

        if last is None:
            # Never updated = stale
            return FreshnessCheck(
                projection_name=projection_name,
                is_fresh=False,
                last_updated_at=None,
                policy_max_seconds=policy.max_staleness_seconds,
            )

        staleness = (now - last).total_seconds()
        return FreshnessCheck(
            projection_name=projection_name,
            is_fresh=staleness <= policy.max_staleness_seconds,
            last_updated_at=last,
            staleness_seconds=staleness,
            policy_max_seconds=policy.max_staleness_seconds,
        )

    def check_all(self, now: datetime) -> Dict[str, FreshnessCheck]:
        """Check freshness for all projections with policies."""
        return {
            name: self.check(name, now)
            for name in self._policies
        }
