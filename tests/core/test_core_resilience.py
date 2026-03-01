"""
Tests for core.resilience — System health modes and policies.
"""

from core.resilience.modes import ResilienceMode, SystemHealth
from core.resilience.policy import check_resilience


# ── SystemHealth Tests ───────────────────────────────────────

class TestSystemHealth:
    def test_default_is_normal(self):
        health = SystemHealth()
        assert health.mode == ResilienceMode.NORMAL
        assert health.can_write()
        assert health.can_read()
        assert health.reason is None

    def test_degraded_mode(self):
        health = SystemHealth()
        health.set_degraded("DB replication lag")
        assert health.mode == ResilienceMode.DEGRADED
        assert not health.can_write()
        assert health.can_read()
        assert health.reason == "DB replication lag"

    def test_read_only_mode(self):
        health = SystemHealth()
        health.set_read_only("Major outage")
        assert health.mode == ResilienceMode.READ_ONLY
        assert not health.can_write()
        assert health.can_read()
        assert health.reason == "Major outage"

    def test_recovery(self):
        health = SystemHealth()
        health.set_degraded("Issue")
        health.recover()
        assert health.mode == ResilienceMode.NORMAL
        assert health.can_write()
        assert health.reason is None


# ── Policy Tests ─────────────────────────────────────────────

class TestResiliencePolicy:
    def test_write_allowed_in_normal(self):
        health = SystemHealth()
        result = check_resilience(health, is_write=True)
        assert result is None

    def test_read_allowed_in_normal(self):
        health = SystemHealth()
        result = check_resilience(health, is_write=False)
        assert result is None

    def test_write_rejected_in_degraded(self):
        health = SystemHealth()
        health.set_degraded("DB lag")
        result = check_resilience(health, is_write=True)
        assert result is not None
        assert result.code == "SYSTEM_DEGRADED"
        assert "DEGRADED" in result.message

    def test_read_allowed_in_degraded(self):
        health = SystemHealth()
        health.set_degraded("DB lag")
        result = check_resilience(health, is_write=False)
        assert result is None

    def test_write_rejected_in_read_only(self):
        health = SystemHealth()
        health.set_read_only("Maintenance")
        result = check_resilience(health, is_write=True)
        assert result is not None
        assert "READ_ONLY" in result.message

    def test_read_allowed_in_read_only(self):
        health = SystemHealth()
        health.set_read_only("Maintenance")
        result = check_resilience(health, is_write=False)
        assert result is None
