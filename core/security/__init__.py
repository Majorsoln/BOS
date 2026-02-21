"""
BOS Core Security — Public API
=================================
Access control, rate limiting, tenant isolation,
anomaly detection, and security guard pipeline.
"""

from core.security.access import AccessDecision, Permission, check_access
from core.security.anomaly_detection import (
    ActivityRecord,
    AnomalyDetector,
    AnomalyResult,
    AnomalySeverity,
)
from core.security.guards import SecurityContext, SecurityGuardPipeline, SecurityGuardResult
from core.security.ratelimit import (
    RateLimitConfig,
    RateLimiter,
    RateLimitResult,
    rate_limit_rejection,
)
from core.security.tenant_isolation import (
    TenantScope,
    build_tenant_scope,
    check_tenant_isolation,
)

__all__ = [
    # Access control
    "Permission",
    "AccessDecision",
    "check_access",
    # Rate limiting
    "RateLimitConfig",
    "RateLimiter",
    "RateLimitResult",
    "rate_limit_rejection",
    # Tenant isolation
    "TenantScope",
    "build_tenant_scope",
    "check_tenant_isolation",
    # Anomaly detection
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalySeverity",
    "ActivityRecord",
    # Guard pipeline
    "SecurityContext",
    "SecurityGuardPipeline",
    "SecurityGuardResult",
]
