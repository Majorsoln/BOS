"""
BOS Core Security — Public API
=================================
Access control and rate limiting (Phase 8 stubs).
"""

from core.security.access import AccessDecision, Permission, check_access
from core.security.ratelimit import RateLimiter, RateLimitResult

__all__ = [
    "Permission",
    "AccessDecision",
    "check_access",
    "RateLimiter",
    "RateLimitResult",
]
