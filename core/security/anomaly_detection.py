"""
BOS Core Security — Anomaly Detection
=========================================
Rule-based detection of suspicious patterns.
No ML — deterministic rules with explicit thresholds.

Time is injected via Clock protocol — no datetime.now() calls.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Deque, Dict, List, Optional, Set, Tuple


# ══════════════════════════════════════════════════════════════
# ANOMALY SEVERITY
# ══════════════════════════════════════════════════════════════

class AnomalySeverity(Enum):
    INFO = "INFO"    # Log only
    WARN = "WARN"    # Log + flag for review
    BLOCK = "BLOCK"  # Log + deny command


# ══════════════════════════════════════════════════════════════
# ANOMALY RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AnomalyResult:
    """Result of an anomaly check."""
    detected: bool
    anomaly_type: str = ""
    severity: AnomalySeverity = AnomalySeverity.INFO
    description: str = ""
    actor_id: str = ""
    business_id: Optional[uuid.UUID] = None

    @staticmethod
    def clean() -> AnomalyResult:
        """No anomaly detected."""
        return AnomalyResult(detected=False)


# ══════════════════════════════════════════════════════════════
# ACTIVITY RECORD (for window tracking)
# ══════════════════════════════════════════════════════════════

@dataclass
class ActivityRecord:
    """A single command activity event for tracking."""
    actor_id: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    command_type: str
    occurred_at: datetime
    was_rejected: bool = False


# ══════════════════════════════════════════════════════════════
# ANOMALY DETECTOR
# ══════════════════════════════════════════════════════════════

_ActorKey = Tuple[str, uuid.UUID]  # (actor_id, business_id)


class AnomalyDetector:
    """
    Rule-based anomaly detector.

    Tracks actor activity within sliding windows and applies
    deterministic rules to detect suspicious patterns.
    """

    def __init__(
        self,
        high_velocity_threshold: int = 100,
        rapid_branch_switch_threshold: int = 3,
        rapid_branch_window_seconds: int = 30,
        repeated_rejection_threshold: int = 5,
        window_seconds: int = 60,
    ) -> None:
        self._high_velocity = high_velocity_threshold
        self._branch_switch_threshold = rapid_branch_switch_threshold
        self._branch_switch_window = timedelta(seconds=rapid_branch_window_seconds)
        self._rejection_threshold = repeated_rejection_threshold
        self._window = timedelta(seconds=window_seconds)
        self._activities: Dict[_ActorKey, Deque[ActivityRecord]] = defaultdict(deque)

    def record_activity(self, activity: ActivityRecord) -> None:
        """Record a command activity for anomaly tracking."""
        key: _ActorKey = (activity.actor_id, activity.business_id)
        bucket = self._activities[key]
        bucket.append(activity)

        # Evict old records (keep 2x window for branch switching analysis)
        cutoff = activity.occurred_at - (self._window * 2)
        while bucket and bucket[0].occurred_at < cutoff:
            bucket.popleft()

    def check(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        branch_id: Optional[uuid.UUID],
        command_type: str,
        now: datetime,
    ) -> AnomalyResult:
        """
        Run all anomaly detection rules.

        Returns the highest-severity anomaly found, or clean result.
        """
        key: _ActorKey = (actor_id, business_id)
        bucket = self._activities.get(key, deque())

        # Filter to window
        cutoff = now - self._window
        recent = [a for a in bucket if a.occurred_at >= cutoff]

        results: List[AnomalyResult] = []

        # Rule 1: High velocity
        r = self._check_high_velocity(actor_id, business_id, recent, now)
        if r.detected:
            results.append(r)

        # Rule 2: Rapid branch switching
        if branch_id is not None:
            r = self._check_rapid_branch_switch(
                actor_id, business_id, branch_id, recent, now
            )
            if r.detected:
                results.append(r)

        # Rule 3: Repeated rejections
        r = self._check_repeated_rejections(
            actor_id, business_id, command_type, recent, now
        )
        if r.detected:
            results.append(r)

        if not results:
            return AnomalyResult.clean()

        # Return highest severity
        severity_order = {
            AnomalySeverity.BLOCK: 3,
            AnomalySeverity.WARN: 2,
            AnomalySeverity.INFO: 1,
        }
        results.sort(key=lambda r: severity_order.get(r.severity, 0), reverse=True)
        return results[0]

    def _check_high_velocity(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        recent: List[ActivityRecord],
        now: datetime,
    ) -> AnomalyResult:
        """Detect >N commands/minute from a single actor."""
        if len(recent) >= self._high_velocity:
            return AnomalyResult(
                detected=True,
                anomaly_type="HIGH_VELOCITY",
                severity=AnomalySeverity.WARN,
                description=(
                    f"Actor {actor_id} issued {len(recent)} commands in the last minute "
                    f"(threshold: {self._high_velocity})."
                ),
                actor_id=actor_id,
                business_id=business_id,
            )
        return AnomalyResult.clean()

    def _check_rapid_branch_switch(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        current_branch_id: uuid.UUID,
        recent: List[ActivityRecord],
        now: datetime,
    ) -> AnomalyResult:
        """Detect actor switching branches rapidly (potential abuse)."""
        switch_cutoff = now - self._branch_switch_window
        recent_branches: Set[uuid.UUID] = set()
        for a in recent:
            if a.occurred_at >= switch_cutoff and a.branch_id is not None:
                recent_branches.add(a.branch_id)
        recent_branches.add(current_branch_id)

        if len(recent_branches) > self._branch_switch_threshold:
            return AnomalyResult(
                detected=True,
                anomaly_type="RAPID_BRANCH_SWITCH",
                severity=AnomalySeverity.BLOCK,
                description=(
                    f"Actor {actor_id} accessed {len(recent_branches)} different branches "
                    f"in the last {self._branch_switch_window.seconds}s "
                    f"(threshold: {self._branch_switch_threshold})."
                ),
                actor_id=actor_id,
                business_id=business_id,
            )
        return AnomalyResult.clean()

    def _check_repeated_rejections(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        command_type: str,
        recent: List[ActivityRecord],
        now: datetime,
    ) -> AnomalyResult:
        """Detect repeated rejections of the same command type."""
        rejections = [
            a for a in recent
            if a.was_rejected and a.command_type == command_type
        ]
        if len(rejections) >= self._rejection_threshold:
            return AnomalyResult(
                detected=True,
                anomaly_type="REPEATED_REJECTIONS",
                severity=AnomalySeverity.WARN,
                description=(
                    f"Actor {actor_id} had {len(rejections)} rejections for "
                    f"'{command_type}' in the last minute "
                    f"(threshold: {self._rejection_threshold})."
                ),
                actor_id=actor_id,
                business_id=business_id,
            )
        return AnomalyResult.clean()
