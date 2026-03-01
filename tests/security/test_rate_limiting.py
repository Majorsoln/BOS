"""
Tests — Rate Limiting
========================
Verifies sliding window rate limiter behavior.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.security.ratelimit import (
    RateLimitConfig,
    RateLimiter,
    RateLimitResult,
    rate_limit_rejection,
)


# ── Helpers ──────────────────────────────────────────────────

BIZ = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_limiter(**kwargs) -> RateLimiter:
    return RateLimiter(**kwargs)


# ══════════════════════════════════════════════════════════════
# BASIC OPERATION
# ══════════════════════════════════════════════════════════════


class TestRateLimiterBasic:
    def test_first_request_allowed(self):
        rl = _make_limiter()
        result = rl.check("actor-1", BIZ, now=T0)
        assert result.allowed is True
        assert result.remaining >= 0

    def test_returns_correct_limit(self):
        rl = _make_limiter()
        result = rl.check("actor-1", BIZ, actor_type="HUMAN", now=T0)
        assert result.limit == 70  # 60 + 10 burst

    def test_remaining_decrements(self):
        rl = _make_limiter()
        r1 = rl.check("actor-1", BIZ, now=T0)
        r2 = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=1))
        assert r2.remaining == r1.remaining - 1


# ══════════════════════════════════════════════════════════════
# RATE LIMIT EXHAUSTION
# ══════════════════════════════════════════════════════════════


class TestRateLimitExhaustion:
    def test_exceeds_limit(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=5, burst_limit=0)}
        rl = _make_limiter(configs=config)
        for i in range(5):
            r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=i))
            assert r.allowed is True

        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=5))
        assert r.allowed is False
        assert r.remaining == 0
        assert r.retry_after_seconds > 0

    def test_window_slides(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=3, burst_limit=0)}
        rl = _make_limiter(configs=config)
        # Fill window
        for i in range(3):
            rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=i))

        # Blocked at T0+3s
        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=3))
        assert r.allowed is False

        # After 60s, first entry slides out
        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=61))
        assert r.allowed is True

    def test_burst_allows_extra(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=3, burst_limit=2)}
        rl = _make_limiter(configs=config)
        # Effective limit is 5
        for i in range(5):
            r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=i))
            assert r.allowed is True

        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=5))
        assert r.allowed is False


# ══════════════════════════════════════════════════════════════
# ACTOR TYPE TIERS
# ══════════════════════════════════════════════════════════════


class TestActorTypeTiers:
    def test_system_has_higher_limit(self):
        rl = _make_limiter()
        r = rl.check("sys-1", BIZ, actor_type="SYSTEM", now=T0)
        assert r.limit == 350  # 300 + 50

    def test_ai_has_lower_limit(self):
        rl = _make_limiter()
        r = rl.check("ai-1", BIZ, actor_type="AI", now=T0)
        assert r.limit == 35  # 30 + 5

    def test_unknown_type_falls_back_to_human(self):
        rl = _make_limiter()
        r = rl.check("x-1", BIZ, actor_type="UNKNOWN", now=T0)
        assert r.limit == 70  # HUMAN default


# ══════════════════════════════════════════════════════════════
# ISOLATION BETWEEN ACTORS / BUSINESSES
# ══════════════════════════════════════════════════════════════


class TestBucketIsolation:
    def test_different_actors_separate_buckets(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=2, burst_limit=0)}
        rl = _make_limiter(configs=config)
        rl.check("actor-1", BIZ, now=T0)
        rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=1))

        # actor-1 is now at limit
        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=2))
        assert r.allowed is False

        # actor-2 is unaffected
        r = rl.check("actor-2", BIZ, now=T0 + timedelta(seconds=2))
        assert r.allowed is True

    def test_different_businesses_separate_buckets(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=2, burst_limit=0)}
        rl = _make_limiter(configs=config)
        biz2 = uuid.uuid4()
        rl.check("actor-1", BIZ, now=T0)
        rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=1))

        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=2))
        assert r.allowed is False

        r = rl.check("actor-1", biz2, now=T0 + timedelta(seconds=2))
        assert r.allowed is True


# ══════════════════════════════════════════════════════════════
# RESET
# ══════════════════════════════════════════════════════════════


class TestRateLimiterReset:
    def test_reset_clears_bucket(self):
        config = {"HUMAN": RateLimitConfig(limit_per_minute=2, burst_limit=0)}
        rl = _make_limiter(configs=config)
        rl.check("actor-1", BIZ, now=T0)
        rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=1))
        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=2))
        assert r.allowed is False

        rl.reset("actor-1", BIZ)
        r = rl.check("actor-1", BIZ, now=T0 + timedelta(seconds=3))
        assert r.allowed is True


# ══════════════════════════════════════════════════════════════
# REJECTION HELPER
# ══════════════════════════════════════════════════════════════


class TestRateLimitRejection:
    def test_allowed_returns_none(self):
        result = RateLimitResult(allowed=True, remaining=5, limit=10)
        assert rate_limit_rejection(result) is None

    def test_denied_returns_rejection(self):
        result = RateLimitResult(
            allowed=False, remaining=0, limit=10, retry_after_seconds=30.0
        )
        rejection = rate_limit_rejection(result)
        assert rejection is not None
        assert rejection.code == "RATE_LIMIT_EXCEEDED"
        assert "30.0" in rejection.message
