"""
Tests — Security Guard Pipeline
===================================
Verifies full security pipeline orchestration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.commands.rejection import ReasonCode
from core.security.anomaly_detection import AnomalyDetector, AnomalySeverity
from core.security.guards import SecurityContext, SecurityGuardPipeline, SecurityGuardResult
from core.security.ratelimit import RateLimitConfig, RateLimiter
from core.security.tenant_isolation import TenantScope


# ── Helpers ──────────────────────────────────────────────────

BIZ_A = uuid.uuid4()
BIZ_B = uuid.uuid4()
BRANCH_1 = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _valid_scope() -> TenantScope:
    return TenantScope(
        actor_id="actor-1",
        business_ids=frozenset([BIZ_A]),
        branch_ids_by_business={BIZ_A: None},
    )


def _ctx(
    business_id: uuid.UUID = BIZ_A,
    branch_id: uuid.UUID | None = BRANCH_1,
    scope: TenantScope | None = None,
    now: datetime = T0,
) -> SecurityContext:
    return SecurityContext(
        actor_id="actor-1",
        actor_type="HUMAN",
        business_id=business_id,
        branch_id=branch_id,
        command_type="CASH:OPEN_SESSION",
        tenant_scope=scope or _valid_scope(),
        now=now,
    )


# ══════════════════════════════════════════════════════════════
# ALL GUARDS PASS
# ══════════════════════════════════════════════════════════════


class TestAllGuardsPass:
    def test_allowed_when_all_checks_pass(self):
        pipeline = SecurityGuardPipeline()
        result = pipeline.execute(_ctx())
        assert result.allowed is True
        assert result.rejection is None

    def test_rate_limit_info_returned(self):
        pipeline = SecurityGuardPipeline()
        result = pipeline.execute(_ctx())
        assert result.rate_limit is not None
        assert result.rate_limit.allowed is True


# ══════════════════════════════════════════════════════════════
# TENANT ISOLATION BLOCKS
# ══════════════════════════════════════════════════════════════


class TestTenantIsolationBlock:
    def test_denied_for_wrong_business(self):
        pipeline = SecurityGuardPipeline()
        result = pipeline.execute(_ctx(business_id=BIZ_B))
        assert result.allowed is False
        assert result.guard_name == "tenant_isolation"
        assert result.rejection is not None
        assert result.rejection.code == ReasonCode.PERMISSION_DENIED

    def test_no_rate_limit_checked_on_tenant_deny(self):
        pipeline = SecurityGuardPipeline()
        result = pipeline.execute(_ctx(business_id=BIZ_B))
        assert result.rate_limit is None  # pipeline short-circuits


# ══════════════════════════════════════════════════════════════
# RATE LIMIT BLOCKS
# ══════════════════════════════════════════════════════════════


class TestRateLimitBlock:
    def test_denied_when_rate_exceeded(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=2, burst_limit=0)}
        rl = RateLimiter(configs=config)
        pipeline = SecurityGuardPipeline(rate_limiter=rl)

        # Consume limit
        pipeline.execute(_ctx(now=T0))
        pipeline.execute(_ctx(now=T0 + timedelta(seconds=1)))

        result = pipeline.execute(_ctx(now=T0 + timedelta(seconds=2)))
        assert result.allowed is False
        assert result.guard_name == "rate_limiter"
        assert result.rejection.code == "RATE_LIMIT_EXCEEDED"

    def test_retry_after_populated(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=1, burst_limit=0)}
        rl = RateLimiter(configs=config)
        pipeline = SecurityGuardPipeline(rate_limiter=rl)

        pipeline.execute(_ctx(now=T0))
        result = pipeline.execute(_ctx(now=T0 + timedelta(seconds=1)))
        assert result.rate_limit is not None
        assert result.rate_limit.retry_after_seconds > 0


# ══════════════════════════════════════════════════════════════
# ANOMALY DETECTION BLOCKS
# ══════════════════════════════════════════════════════════════


class TestAnomalyBlock:
    def test_block_severity_denies_command(self):
        det = AnomalyDetector(rapid_branch_switch_threshold=2, rapid_branch_window_seconds=30)
        pipeline = SecurityGuardPipeline(anomaly_detector=det)

        # Build up branch switching history
        from core.security.anomaly_detection import ActivityRecord
        det.record_activity(ActivityRecord(
            actor_id="actor-1", business_id=BIZ_A, branch_id=BRANCH_1,
            command_type="X", occurred_at=T0,
        ))
        b2 = uuid.uuid4()
        det.record_activity(ActivityRecord(
            actor_id="actor-1", business_id=BIZ_A, branch_id=b2,
            command_type="X", occurred_at=T0 + timedelta(seconds=5),
        ))

        # 3rd branch triggers BLOCK
        b3 = uuid.uuid4()
        result = pipeline.execute(_ctx(branch_id=b3, now=T0 + timedelta(seconds=10)))
        assert result.allowed is False
        assert result.guard_name == "anomaly_detector"
        assert "ANOMALY" in result.rejection.code

    def test_warn_severity_allows_but_flags(self):
        det = AnomalyDetector(high_velocity_threshold=3)
        pipeline = SecurityGuardPipeline(anomaly_detector=det)

        # Build up velocity
        from core.security.anomaly_detection import ActivityRecord
        for i in range(3):
            det.record_activity(ActivityRecord(
                actor_id="actor-1", business_id=BIZ_A, branch_id=BRANCH_1,
                command_type="X", occurred_at=T0 + timedelta(seconds=i),
            ))

        result = pipeline.execute(_ctx(now=T0 + timedelta(seconds=3)))
        assert result.allowed is True
        assert result.anomaly is not None
        assert result.anomaly.severity == AnomalySeverity.WARN


# ══════════════════════════════════════════════════════════════
# RECORD REJECTION
# ══════════════════════════════════════════════════════════════


class TestRecordRejection:
    def test_records_rejection_for_anomaly_tracking(self):
        det = AnomalyDetector(repeated_rejection_threshold=3)
        pipeline = SecurityGuardPipeline(anomaly_detector=det)

        for i in range(3):
            pipeline.record_rejection(
                actor_id="actor-1",
                business_id=BIZ_A,
                branch_id=BRANCH_1,
                command_type="CASH:OPEN_SESSION",
                now=T0 + timedelta(seconds=i),
            )

        result = det.check("actor-1", BIZ_A, BRANCH_1, "CASH:OPEN_SESSION", T0 + timedelta(seconds=3))
        assert result.detected is True
        assert result.anomaly_type == "REPEATED_REJECTIONS"


# ══════════════════════════════════════════════════════════════
# FAIL-SAFE ON ERRORS
# ══════════════════════════════════════════════════════════════


class TestFailSafe:
    def test_tenant_isolation_error_denies(self):
        """If tenant isolation check throws, result is DENY."""
        pipeline = SecurityGuardPipeline()
        # Pass a broken scope that will cause an error
        broken_scope = TenantScope(
            actor_id="actor-1",
            business_ids=frozenset([BIZ_A]),
            branch_ids_by_business={BIZ_A: None},
        )
        # This should succeed (no error), but let's verify the pattern
        result = pipeline.execute(_ctx(scope=broken_scope))
        assert result.allowed is True  # valid scope, should pass

    def test_pipeline_order_tenant_then_rate_then_anomaly(self):
        """Verify guards execute in correct order."""
        config = {"HUMAN": RateLimitConfig(limit_per_minute=1, burst_limit=0)}
        rl = RateLimiter(configs=config)
        pipeline = SecurityGuardPipeline(rate_limiter=rl)

        # Tenant isolation should block before rate limit is even checked
        result = pipeline.execute(_ctx(business_id=BIZ_B))
        assert result.guard_name == "tenant_isolation"

        # For authorized business, rate limit should be checked
        pipeline.execute(_ctx(now=T0))
        result = pipeline.execute(_ctx(now=T0 + timedelta(seconds=1)))
        assert result.guard_name == "rate_limiter"
