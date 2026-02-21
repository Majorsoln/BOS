"""
BOS Core Security — Rate Limiting
====================================
Prevent abuse via command frequency limits.
Phase 8 stub — interface defined, enforcement deferred.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    limit: int
    retry_after_seconds: float = 0.0


class RateLimiter:
    """
    Command rate limiter.

    Phase 8 stub: currently always allows.
    Production implementation would use a sliding window counter.
    """

    def __init__(self, max_per_minute: int = 60) -> None:
        self.max_per_minute = max_per_minute

    def check(self, actor_id: str, business_id: uuid.UUID) -> RateLimitResult:
        """
        Check if an actor is within rate limits.

        Phase 8 stub: always allows.
        """
        return RateLimitResult(
            allowed=True,
            remaining=self.max_per_minute,
            limit=self.max_per_minute,
        )
