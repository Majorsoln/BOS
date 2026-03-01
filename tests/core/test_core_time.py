"""
Tests for core.time — Clock protocol and temporal helpers.
"""

import pytest
from datetime import datetime, timezone, timedelta

from core.time.clock import (
    Clock,
    FixedClock,
    SystemClock,
    set_default_clock,
    get_default_clock,
    now_utc,
)
from core.time.temporal import TimeWindow, is_expired, seconds_until_expiry, clamp_to_window


# ── Clock Tests ──────────────────────────────────────────────

class TestSystemClock:
    def test_returns_utc_datetime(self):
        clock = SystemClock()
        dt = clock.now_utc()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_time_advances(self):
        clock = SystemClock()
        t1 = clock.now_utc()
        t2 = clock.now_utc()
        assert t2 >= t1


class TestFixedClock:
    def test_returns_fixed_time(self):
        fixed = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed)
        assert clock.now_utc() == fixed
        assert clock.now_utc() == fixed  # Same every time

    def test_rejects_naive_datetime(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            FixedClock(datetime(2025, 1, 1))

    def test_advance(self):
        fixed = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed)
        clock.advance(60)
        assert clock.now_utc() == fixed + timedelta(seconds=60)


class TestDefaultClock:
    def test_set_and_get_default(self):
        original = get_default_clock()
        fixed = FixedClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
        set_default_clock(fixed)
        try:
            assert now_utc() == datetime(2025, 1, 1, tzinfo=timezone.utc)
        finally:
            set_default_clock(original)


# ── TimeWindow Tests ─────────────────────────────────────────

class TestTimeWindow:
    def test_contains(self):
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        window = TimeWindow(start=start, end=end)

        assert window.contains(datetime(2025, 6, 15, tzinfo=timezone.utc))
        assert window.contains(start)  # inclusive
        assert window.contains(end)    # inclusive
        assert not window.contains(datetime(2024, 12, 31, tzinfo=timezone.utc))

    def test_overlaps(self):
        w1 = TimeWindow(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 6, 30, tzinfo=timezone.utc),
        )
        w2 = TimeWindow(
            start=datetime(2025, 3, 1, tzinfo=timezone.utc),
            end=datetime(2025, 9, 30, tzinfo=timezone.utc),
        )
        w3 = TimeWindow(
            start=datetime(2025, 7, 1, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        assert w1.overlaps(w2)
        assert not w1.overlaps(w3)

    def test_rejects_start_after_end(self):
        with pytest.raises(ValueError, match="start"):
            TimeWindow(
                start=datetime(2025, 12, 31, tzinfo=timezone.utc),
                end=datetime(2025, 1, 1, tzinfo=timezone.utc),
            )

    def test_duration(self):
        w = TimeWindow(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )
        assert w.duration() == timedelta(days=1)


# ── Pure Temporal Functions ──────────────────────────────────

class TestIsExpired:
    def test_not_expired(self):
        issued = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = datetime(2025, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        assert not is_expired(issued, ttl_seconds=3600, now=now)

    def test_expired(self):
        issued = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        assert is_expired(issued, ttl_seconds=3600, now=now)


class TestSecondsUntilExpiry:
    def test_remaining(self):
        issued = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = datetime(2025, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        remaining = seconds_until_expiry(issued, ttl_seconds=3600, now=now)
        assert remaining == 1800.0

    def test_already_expired_returns_none(self):
        issued = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        assert seconds_until_expiry(issued, ttl_seconds=3600, now=now) is None


class TestClampToWindow:
    def test_clamp_within_window(self):
        w = TimeWindow(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        dt = datetime(2025, 6, 15, tzinfo=timezone.utc)
        assert clamp_to_window(dt, w) == dt

    def test_clamp_before_start(self):
        w = TimeWindow(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        dt = datetime(2024, 6, 15, tzinfo=timezone.utc)
        assert clamp_to_window(dt, w) == w.start

    def test_clamp_after_end(self):
        w = TimeWindow(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        dt = datetime(2026, 6, 15, tzinfo=timezone.utc)
        assert clamp_to_window(dt, w) == w.end
