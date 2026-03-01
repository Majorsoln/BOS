"""
Tests — TTL Cache with Event-Driven Invalidation
====================================================
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.caching import CacheEntry, CacheStats, TTLCache


T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
BIZ_A = uuid.uuid4()
BIZ_B = uuid.uuid4()


class TestCacheBasic:
    def test_put_and_get(self):
        c = TTLCache()
        c.put("k1", "v1", T0)
        assert c.get("k1", T0) == "v1"

    def test_miss_returns_none(self):
        c = TTLCache()
        assert c.get("nonexistent", T0) is None

    def test_ttl_expiration(self):
        c = TTLCache(default_ttl_seconds=60)
        c.put("k1", "v1", T0)
        assert c.get("k1", T0 + timedelta(seconds=30)) == "v1"
        assert c.get("k1", T0 + timedelta(seconds=61)) is None

    def test_custom_ttl_per_entry(self):
        c = TTLCache(default_ttl_seconds=300)
        c.put("k1", "v1", T0, ttl_seconds=10)
        assert c.get("k1", T0 + timedelta(seconds=5)) == "v1"
        assert c.get("k1", T0 + timedelta(seconds=11)) is None

    def test_overwrite_existing_key(self):
        c = TTLCache()
        c.put("k1", "v1", T0)
        c.put("k1", "v2", T0 + timedelta(seconds=1))
        assert c.get("k1", T0 + timedelta(seconds=1)) == "v2"


class TestLRUEviction:
    def test_evicts_lru_when_full(self):
        c = TTLCache(max_size=3)
        c.put("k1", "v1", T0)
        c.put("k2", "v2", T0)
        c.put("k3", "v3", T0)
        # Cache full, adding k4 evicts k1 (oldest)
        c.put("k4", "v4", T0)
        assert c.get("k1", T0) is None
        assert c.get("k4", T0) == "v4"

    def test_accessing_entry_moves_to_end(self):
        c = TTLCache(max_size=3)
        c.put("k1", "v1", T0)
        c.put("k2", "v2", T0)
        c.put("k3", "v3", T0)
        # Access k1 → now k2 is LRU
        c.get("k1", T0)
        c.put("k4", "v4", T0)
        assert c.get("k1", T0) == "v1"
        assert c.get("k2", T0) is None  # k2 was evicted


class TestTagInvalidation:
    def test_invalidate_by_tag(self):
        c = TTLCache()
        c.put("k1", "v1", T0, tags={"retail.sale.completed.v1"})
        c.put("k2", "v2", T0, tags={"retail.sale.completed.v1"})
        c.put("k3", "v3", T0, tags={"cash.session.closed.v1"})

        count = c.invalidate_by_tag("retail.sale.completed.v1")
        assert count == 2
        assert c.get("k1", T0) is None
        assert c.get("k2", T0) is None
        assert c.get("k3", T0) == "v3"

    def test_invalidate_unknown_tag(self):
        c = TTLCache()
        count = c.invalidate_by_tag("nonexistent")
        assert count == 0


class TestBusinessInvalidation:
    def test_invalidate_by_business(self):
        c = TTLCache()
        c.put("k1", "v1", T0, business_id=BIZ_A)
        c.put("k2", "v2", T0, business_id=BIZ_A)
        c.put("k3", "v3", T0, business_id=BIZ_B)

        count = c.invalidate_by_business(BIZ_A)
        assert count == 2
        assert c.get("k1", T0) is None
        assert c.get("k3", T0) == "v3"

    def test_invalidate_single_key(self):
        c = TTLCache()
        c.put("k1", "v1", T0)
        assert c.invalidate("k1") is True
        assert c.get("k1", T0) is None
        assert c.invalidate("k1") is False  # already gone


class TestCacheStats:
    def test_hits_and_misses(self):
        c = TTLCache()
        c.put("k1", "v1", T0)
        c.get("k1", T0)  # hit
        c.get("k2", T0)  # miss
        assert c.stats.hits == 1
        assert c.stats.misses == 1
        assert c.stats.hit_rate == 0.5

    def test_eviction_counter(self):
        c = TTLCache(max_size=2)
        c.put("k1", "v1", T0)
        c.put("k2", "v2", T0)
        c.put("k3", "v3", T0)  # evicts k1
        assert c.stats.evictions == 1

    def test_invalidation_counter(self):
        c = TTLCache()
        c.put("k1", "v1", T0, tags={"tag1"})
        c.invalidate_by_tag("tag1")
        assert c.stats.invalidations == 1

    def test_stats_to_dict(self):
        s = CacheStats(hits=10, misses=5)
        d = s.to_dict()
        assert d["hit_rate"] == round(10 / 15, 4)

    def test_clear(self):
        c = TTLCache()
        c.put("k1", "v1", T0)
        c.put("k2", "v2", T0)
        c.clear()
        assert c.size == 0
