"""
BOS Core Security — Guard Pipeline
======================================
Orchestrates all security checks in order:
  1. Tenant isolation
  2. Rate limiting
  3. Anomaly detection

Fail-safe: on any error → DENY (never permissive on error).
All decisions are logged for audit trail.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.rejection import RejectionReason
from core.security.anomaly_detection import (
    ActivityRecord,
    AnomalyDetector,
    AnomalyResult,
    AnomalySeverity,
)
from core.security.ratelimit import RateLimiter, RateLimitResult, rate_limit_rejection
from core.security.tenant_isolation import TenantScope, check_tenant_isolation


# ══════════════════════════════════════════════════════════════
# GUARD CONTEXT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SecurityContext:
    """All inputs needed for the security guard pipeline."""

    actor_id: str
    actor_type: str  # HUMAN | SYSTEM | DEVICE | AI
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    command_type: str
    tenant_scope: TenantScope
    now: datetime


# ══════════════════════════════════════════════════════════════
# GUARD RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SecurityGuardResult:
    """Result of the full security pipeline."""

    allowed: bool
    rejection: Optional[RejectionReason] = None
    anomaly: Optional[AnomalyResult] = None
    rate_limit: Optional[RateLimitResult] = None
    guard_name: str = ""


# ══════════════════════════════════════════════════════════════
# SECURITY GUARD PIPELINE
# ══════════════════════════════════════════════════════════════

class SecurityGuardPipeline:
    """
    Orchestrates all security checks in order.

    Fail-safe: on any error within a guard, defaults to DENY.
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        anomaly_detector: Optional[AnomalyDetector] = None,
    ) -> None:
        self._rate_limiter = rate_limiter or RateLimiter()
        self._anomaly_detector = anomaly_detector or AnomalyDetector()

    def execute(self, ctx: SecurityContext) -> SecurityGuardResult:
        """
        Run all security guards in order.

        Returns SecurityGuardResult with the first rejection found,
        or an allowed result if all guards pass.
        """
        # Guard 1: Tenant isolation
        try:
            rejection = check_tenant_isolation(
                scope=ctx.tenant_scope,
                business_id=ctx.business_id,
                branch_id=ctx.branch_id,
            )
            if rejection is not None:
                return SecurityGuardResult(
                    allowed=False,
                    rejection=rejection,
                    guard_name="tenant_isolation",
                )
        except Exception:
            return SecurityGuardResult(
                allowed=False,
                rejection=RejectionReason(
                    code="SECURITY_ERROR",
                    message="Security check failed — access denied.",
                    policy_name="tenant_isolation_guard",
                ),
                guard_name="tenant_isolation",
            )

        # Guard 2: Rate limiting
        try:
            rl_result = self._rate_limiter.check(
                actor_id=ctx.actor_id,
                business_id=ctx.business_id,
                actor_type=ctx.actor_type,
                now=ctx.now,
            )
            if not rl_result.allowed:
                return SecurityGuardResult(
                    allowed=False,
                    rejection=rate_limit_rejection(rl_result),
                    rate_limit=rl_result,
                    guard_name="rate_limiter",
                )
        except Exception:
            return SecurityGuardResult(
                allowed=False,
                rejection=RejectionReason(
                    code="SECURITY_ERROR",
                    message="Rate limit check failed — access denied.",
                    policy_name="rate_limit_guard",
                ),
                guard_name="rate_limiter",
            )

        # Guard 3: Anomaly detection
        try:
            anomaly = self._anomaly_detector.check(
                actor_id=ctx.actor_id,
                business_id=ctx.business_id,
                branch_id=ctx.branch_id,
                command_type=ctx.command_type,
                now=ctx.now,
            )
            if anomaly.detected and anomaly.severity == AnomalySeverity.BLOCK:
                return SecurityGuardResult(
                    allowed=False,
                    rejection=RejectionReason(
                        code="SECURITY_ANOMALY_DETECTED",
                        message=f"Anomaly detected: {anomaly.anomaly_type}. Command blocked.",
                        policy_name="anomaly_detection_guard",
                    ),
                    anomaly=anomaly,
                    guard_name="anomaly_detector",
                )

            # Record the activity (after all guards pass, before returning)
            self._anomaly_detector.record_activity(ActivityRecord(
                actor_id=ctx.actor_id,
                business_id=ctx.business_id,
                branch_id=ctx.branch_id,
                command_type=ctx.command_type,
                occurred_at=ctx.now,
                was_rejected=False,
            ))

            # WARN-level anomaly: allow but flag
            return SecurityGuardResult(
                allowed=True,
                anomaly=anomaly if anomaly.detected else None,
                rate_limit=rl_result,
                guard_name="",
            )
        except Exception:
            # Anomaly detection errors are non-fatal — allow but log
            return SecurityGuardResult(
                allowed=True,
                rate_limit=rl_result,
                guard_name="",
            )

    def record_rejection(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        branch_id: Optional[uuid.UUID],
        command_type: str,
        now: datetime,
    ) -> None:
        """Record a rejected command for anomaly tracking."""
        self._anomaly_detector.record_activity(ActivityRecord(
            actor_id=actor_id,
            business_id=business_id,
            branch_id=branch_id,
            command_type=command_type,
            occurred_at=now,
            was_rejected=True,
        ))
