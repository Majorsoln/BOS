"""Tests for core/platform/observability.py"""
from datetime import datetime

import pytest

from core.platform.observability import (
    PLATFORM_METRIC_RECORDED_V1,
    PLATFORM_SLO_BREACHED_V1,
    PLATFORM_SLO_RECOVERED_V1,
    PLATFORM_HEALTH_SNAPSHOT_V1,
    ObservabilityProjection,
    ObservabilityService,
    SLOStatus,
    MetricKind,
)


@pytest.fixture
def projection():
    return ObservabilityProjection()


@pytest.fixture
def service(projection):
    return ObservabilityService(projection)


NOW = datetime(2026, 3, 5, 12, 0, 0)


class TestMetricRecording:
    def test_record_gauge_metric(self, service, projection):
        result = service.record_metric(
            metric_name="command_latency.p95_ms",
            value=120.0,
            kind="GAUGE",
            recorded_at=NOW,
        )
        events = result["events"]
        assert any(e["event_type"] == PLATFORM_METRIC_RECORDED_V1 for e in events)
        sample = projection.get_latest_metric("command_latency.p95_ms")
        assert sample is not None
        assert sample.value == 120.0
        assert sample.kind == MetricKind.GAUGE

    def test_record_metric_with_tenant_scope(self, service, projection):
        service.record_metric(
            metric_name="replay.duration_seconds",
            value=5.0,
            tenant_id="tenant-abc",
            recorded_at=NOW,
        )
        # with tenant scope
        sample = projection.get_latest_metric("replay.duration_seconds", tenant_id="tenant-abc")
        assert sample is not None
        assert sample.tenant_id == "tenant-abc"

        # no cross-contamination with global scope
        global_sample = projection.get_latest_metric("replay.duration_seconds")
        assert global_sample is None

    def test_record_metric_with_region(self, service, projection):
        service.record_metric(
            metric_name="api.error_rate_5xx",
            value=0.03,
            region_code="KE",
            recorded_at=NOW,
        )
        sample = projection.get_latest_metric("api.error_rate_5xx")
        assert sample.region_code == "KE"


class TestSLOEvaluation:
    def test_slo_ok_when_within_threshold(self, service, projection):
        service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        assert projection.evaluate_slo_status("command_latency.p95_ms") == SLOStatus.OK

    def test_slo_warning_when_between_thresholds(self, service, projection):
        # warning threshold is 150ms, breach is 200ms
        service.record_metric("command_latency.p95_ms", 170.0, recorded_at=NOW)
        assert projection.evaluate_slo_status("command_latency.p95_ms") == SLOStatus.WARNING

    def test_slo_breached_when_over_threshold(self, service, projection):
        service.record_metric("command_latency.p95_ms", 250.0, recorded_at=NOW)
        assert projection.evaluate_slo_status("command_latency.p95_ms") == SLOStatus.BREACHED

    def test_slo_unknown_when_no_metric(self, projection):
        assert projection.evaluate_slo_status("command_latency.p95_ms") == SLOStatus.UNKNOWN

    def test_slo_unknown_for_invalid_slo_id(self, projection):
        assert projection.evaluate_slo_status("nonexistent.slo") == SLOStatus.UNKNOWN

    def test_integrity_slo_ok_at_zero(self, service, projection):
        service.record_metric("hash_chain.integrity_violations", 0.0, recorded_at=NOW)
        assert projection.evaluate_slo_status("hash_chain.integrity_violations") == SLOStatus.OK

    def test_integrity_slo_breached_at_one(self, service, projection):
        service.record_metric("hash_chain.integrity_violations", 1.0, recorded_at=NOW)
        assert projection.evaluate_slo_status("hash_chain.integrity_violations") == SLOStatus.BREACHED

    def test_persist_event_success_rate_ok(self, service, projection):
        service.record_metric("persist_event.success_rate", 99.95, recorded_at=NOW)
        assert projection.evaluate_slo_status("persist_event.success_rate") == SLOStatus.OK

    def test_persist_event_success_rate_warning(self, service, projection):
        service.record_metric("persist_event.success_rate", 99.7, recorded_at=NOW)
        assert projection.evaluate_slo_status("persist_event.success_rate") == SLOStatus.WARNING

    def test_persist_event_success_rate_breached(self, service, projection):
        service.record_metric("persist_event.success_rate", 99.0, recorded_at=NOW)
        assert projection.evaluate_slo_status("persist_event.success_rate") == SLOStatus.BREACHED


class TestSLOBreachAndRecovery:
    def test_breach_event_fires_automatically(self, service, projection):
        result = service.record_metric("command_latency.p95_ms", 300.0, recorded_at=NOW)
        event_types = [e["event_type"] for e in result["events"]]
        assert PLATFORM_SLO_BREACHED_V1 in event_types

    def test_active_breach_tracked(self, service, projection):
        service.record_metric("command_latency.p95_ms", 300.0, recorded_at=NOW)
        breaches = projection.get_active_breaches()
        assert len(breaches) == 1
        assert breaches[0].slo_id == "command_latency.p95_ms"

    def test_breach_does_not_double_fire(self, service, projection):
        service.record_metric("command_latency.p95_ms", 300.0, recorded_at=NOW)
        result2 = service.record_metric("command_latency.p95_ms", 350.0, recorded_at=NOW)
        # second recording should NOT add another breach event
        event_types = [e["event_type"] for e in result2["events"]]
        assert PLATFORM_SLO_BREACHED_V1 not in event_types

    def test_recovery_event_fires_on_return_to_ok(self, service, projection):
        service.record_metric("command_latency.p95_ms", 300.0, recorded_at=NOW)
        result = service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        event_types = [e["event_type"] for e in result["events"]]
        assert PLATFORM_SLO_RECOVERED_V1 in event_types

    def test_no_active_breaches_after_recovery(self, service, projection):
        service.record_metric("command_latency.p95_ms", 300.0, recorded_at=NOW)
        service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        assert len(projection.get_active_breaches()) == 0

    def test_breach_history_retained_after_recovery(self, service, projection):
        service.record_metric("command_latency.p95_ms", 300.0, recorded_at=NOW)
        service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        history = projection.get_breach_history()
        assert len(history) == 1
        assert history[0].recovered_at is not None


class TestHealthSnapshot:
    def test_health_snapshot_ok_state(self, service, projection):
        service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        service.record_metric("command_latency.p99_ms", 200.0, recorded_at=NOW)
        service.record_metric("persist_event.success_rate", 99.95, recorded_at=NOW)
        service.record_metric("hash_chain.integrity_violations", 0.0, recorded_at=NOW)
        service.record_metric("api.error_rate_5xx", 0.02, recorded_at=NOW)
        service.record_metric("replay.duration_seconds", 10.0, recorded_at=NOW)

        result = service.take_health_snapshot(taken_at=NOW)
        assert result["overall_status"] == SLOStatus.OK.value
        assert result["active_breaches"] == 0

    def test_health_snapshot_breached_state(self, service, projection):
        service.record_metric("command_latency.p95_ms", 500.0, recorded_at=NOW)
        result = service.take_health_snapshot(taken_at=NOW)
        assert result["overall_status"] == SLOStatus.BREACHED.value
        assert result["active_breaches"] >= 1

    def test_snapshot_event_stored(self, service, projection):
        service.take_health_snapshot(taken_at=NOW)
        snap = projection.get_latest_snapshot()
        assert snap is not None
        assert snap.taken_at == NOW

    def test_get_health_summary_no_event(self, service, projection):
        service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        summary = service.get_health_summary()
        assert "slo_statuses" in summary
        assert "active_breaches" in summary
        assert "latest_snapshot" in summary


class TestProjectionTruncate:
    def test_truncate_clears_state(self, service, projection):
        service.record_metric("command_latency.p95_ms", 100.0, recorded_at=NOW)
        projection.truncate()
        assert projection.get_latest_metric("command_latency.p95_ms") is None
        assert projection.get_active_breaches() == []
