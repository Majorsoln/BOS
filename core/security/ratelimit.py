"""
BOS Core Security — Rate Limiting
====================================
Sliding window rate limiter to prevent abuse.
Per-actor per-business throttling with configurable limits.

Time is injected via the Clock protocol — no datetime.now() calls.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Dict, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# RATE LIMIT CONFIGURATION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for a rate limit tier."""
    limit_per_minute: int
    burst_limit: int  # allow spike up to N above base limit

    def effective_limit(self) -> int:
        return self.limit_per_minute + self.burst_limit


DEFAULT_CONFIGS: Dict[str, RateLimitConfig] = {
    "HUMAN": RateLimitConfig(limit_per_minute=60, burst_limit=10),
    "SYSTEM": RateLimitConfig(limit_per_minute=300, burst_limit=50),
    "DEVICE": RateLimitConfig(limit_per_minute=120, burst_limit=20),
    "AI": RateLimitConfig(limit_per_minute=30, burst_limit=5),
}


# ══════════════════════════════════════════════════════════════
# RATE LIMIT RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    limit: int
    retry_after_seconds: float = 0.0


# ══════════════════════════════════════════════════════════════
# SLIDING WINDOW RATE LIMITER
# ══════════════════════════════════════════════════════════════

_BucketKey = Tuple[str, uuid.UUID]  # (actor_id, business_id)


class RateLimiter:
    """
    Sliding window rate limiter.

    Tracks command timestamps per (actor_id, business_id) bucket.
    Window is 60 seconds. Time is injected — no system clock reads.
    """

    def __init__(
        self,
        configs: Optional[Dict[str, RateLimitConfig]] = None,
        window_seconds: int = 60,
    ) -> None:
        self._configs = configs or DEFAULT_CONFIGS
        self._window = timedelta(seconds=window_seconds)
        self._buckets: Dict[_BucketKey, Deque[datetime]] = defaultdict(deque)

    def check(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        actor_type: str = "HUMAN",
        now: Optional[datetime] = None,
    ) -> RateLimitResult:
        """
        Check if an actor is within rate limits.

        Args:
            actor_id: The actor making the request.
            business_id: The business being accessed.
            actor_type: HUMAN|SYSTEM|DEVICE|AI (determines limit tier).
            now: Current time (injected for determinism).

        Returns:
            RateLimitResult with allowed/remaining/retry_after.
        """
        config = self._configs.get(actor_type, self._configs.get("HUMAN"))
        if config is None:
            config = RateLimitConfig(limit_per_minute=60, burst_limit=10)

        effective_limit = config.effective_limit()
        key: _BucketKey = (actor_id, business_id)
        bucket = self._buckets[key]

        if now is None:
            from core.time.clock import now_utc
            now = now_utc()

        # Evict timestamps outside the window
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        current_count = len(bucket)

        if current_count >= effective_limit:
            # Rate limit exceeded
            oldest_in_window = bucket[0] if bucket else now
            retry_after = (oldest_in_window + self._window - now).total_seconds()
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=effective_limit,
                retry_after_seconds=max(0.0, retry_after),
            )

        # Record this request
        bucket.append(now)
        remaining = effective_limit - current_count - 1

        return RateLimitResult(
            allowed=True,
            remaining=max(0, remaining),
            limit=effective_limit,
        )

    def reset(self, actor_id: str, business_id: uuid.UUID) -> None:
        """Reset rate limit bucket for an actor (admin action)."""
        key: _BucketKey = (actor_id, business_id)
        self._buckets.pop(key, None)


# ══════════════════════════════════════════════════════════════
# RATE LIMIT REJECTION HELPER
# ══════════════════════════════════════════════════════════════

def rate_limit_rejection(result: RateLimitResult) -> Optional[RejectionReason]:
    """Convert a denied rate limit result to a RejectionReason."""
    if result.allowed:
        return None
    return RejectionReason(
        code="RATE_LIMIT_EXCEEDED",
        message=(
            f"Rate limit exceeded ({result.limit} requests/minute). "
            f"Retry after {result.retry_after_seconds:.1f} seconds."
        ),
        policy_name="rate_limit_check",
    )
