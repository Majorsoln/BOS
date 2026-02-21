"""
BOS Core Caching — TTL Cache with Event-Driven Invalidation
================================================================
Fast read access for projection data.

Doctrine: Cache is disposable — always rebuildable from projections.
Event-driven invalidation keeps cache consistent.
Time is injected — no datetime.now() calls.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, Optional, Set, TypeVar


# ══════════════════════════════════════════════════════════════
# CACHE ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class CacheEntry:
    """A single cached value with TTL metadata."""

    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    business_id: Optional[uuid.UUID] = None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


# ══════════════════════════════════════════════════════════════
# CACHE STATISTICS
# ══════════════════════════════════════════════════════════════

@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    total_entries: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "total_entries": self.total_entries,
            "hit_rate": round(self.hit_rate, 4),
        }


# ══════════════════════════════════════════════════════════════
# TTL CACHE (LRU + TTL + event-driven invalidation)
# ══════════════════════════════════════════════════════════════

class TTLCache:
    """
    In-memory LRU cache with TTL expiration and event-driven invalidation.

    Features:
    - TTL-based expiration (configurable per entry or global default)
    - LRU eviction when max_size exceeded
    - Event-driven invalidation via invalidation tags
    - Business-scoped entries (tenant isolation)
    - Performance statistics

    Time is injected — never reads system clock.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 300,
    ) -> None:
        self._max_size = max_size
        self._default_ttl = timedelta(seconds=default_ttl_seconds)
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._tags: Dict[str, Set[str]] = {}  # tag → set of cache keys
        self._stats = CacheStats()

    def get(self, key: str, now: datetime) -> Optional[Any]:
        """
        Get a cached value by key.

        Returns None on miss or expired entry.
        """
        entry = self._entries.get(key)
        if entry is None:
            self._stats.misses += 1
            return None

        if entry.is_expired(now):
            self._evict(key)
            self._stats.misses += 1
            return None

        # LRU: move to end
        self._entries.move_to_end(key)
        self._stats.hits += 1
        return entry.value

    def put(
        self,
        key: str,
        value: Any,
        now: datetime,
        ttl_seconds: Optional[int] = None,
        business_id: Optional[uuid.UUID] = None,
        tags: Optional[Set[str]] = None,
    ) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            now: Current time (injected).
            ttl_seconds: Override TTL for this entry.
            business_id: Tenant scope for this entry.
            tags: Invalidation tags (event types that should clear this entry).
        """
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self._default_ttl

        # Evict if at capacity (before adding)
        if key not in self._entries and len(self._entries) >= self._max_size:
            self._evict_lru()

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + ttl,
            business_id=business_id,
        )
        self._entries[key] = entry
        self._entries.move_to_end(key)
        self._stats.total_entries = len(self._entries)

        # Register tags for invalidation
        if tags:
            for tag in tags:
                self._tags.setdefault(tag, set()).add(key)

    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries associated with a tag.

        Returns number of entries invalidated.
        Used for event-driven cache invalidation.
        """
        keys = self._tags.pop(tag, set())
        count = 0
        for key in keys:
            if key in self._entries:
                del self._entries[key]
                count += 1
        self._stats.invalidations += count
        self._stats.total_entries = len(self._entries)
        return count

    def invalidate_by_business(self, business_id: uuid.UUID) -> int:
        """Invalidate all entries for a specific business (tenant flush)."""
        keys_to_remove = [
            k for k, v in self._entries.items()
            if v.business_id == business_id
        ]
        for key in keys_to_remove:
            self._evict(key)
        self._stats.invalidations += len(keys_to_remove)
        return len(keys_to_remove)

    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        if key in self._entries:
            self._evict(key)
            self._stats.invalidations += 1
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries.clear()
        self._tags.clear()
        self._stats.total_entries = 0

    @property
    def stats(self) -> CacheStats:
        return self._stats

    @property
    def size(self) -> int:
        return len(self._entries)

    def _evict(self, key: str) -> None:
        """Remove a single entry and clean up tags."""
        self._entries.pop(key, None)
        for tag_keys in self._tags.values():
            tag_keys.discard(key)
        self._stats.evictions += 1
        self._stats.total_entries = len(self._entries)

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._entries:
            oldest_key = next(iter(self._entries))
            self._evict(oldest_key)
