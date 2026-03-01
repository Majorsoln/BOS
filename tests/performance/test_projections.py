"""
Tests — Projection Registry, Snapshots & Metrics
====================================================
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.projections.registry import ProjectionHealth, ProjectionInfo, ProjectionRegistry
from core.projections.snapshots import SnapshotEntry, SnapshotStore
from core.projections.metrics import MetricsCollector, ProjectionMetrics


T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
BIZ = uuid.uuid4()


# ══════════════════════════════════════════════════════════════
# PROJECTION REGISTRY
# ══════════════════════════════════════════════════════════════


class TestProjectionRegistry:
    def test_register_and_get(self):
        reg = ProjectionRegistry()
        info = ProjectionInfo(
            projection_name="retail_read_model",
            event_types=frozenset(["retail.sale.completed.v1"]),
        )
        reg.register(info)
        assert reg.get("retail_read_model") is info

    def test_get_projections_for_event(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(
            projection_name="retail_rm",
            event_types=frozenset(["retail.sale.completed.v1"]),
        ))
        reg.register(ProjectionInfo(
            projection_name="finance_rm",
            event_types=frozenset(["accounting.journal.posted.v1"]),
        ))
        result = reg.get_projections_for_event("retail.sale.completed.v1")
        assert len(result) == 1
        assert result[0].projection_name == "retail_rm"

    def test_multiple_projections_same_event(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(
            projection_name="p1",
            event_types=frozenset(["shared.event.v1"]),
        ))
        reg.register(ProjectionInfo(
            projection_name="p2",
            event_types=frozenset(["shared.event.v1"]),
        ))
        result = reg.get_projections_for_event("shared.event.v1")
        assert len(result) == 2

    def test_record_event_processed(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(
            projection_name="p1", event_types=frozenset(["e1"]),
        ))
        reg.record_event_processed("p1", T0)
        health = reg.get_health("p1")
        assert health.events_processed == 1
        assert health.last_event_at == T0

    def test_record_rebuild(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(
            projection_name="p1", event_types=frozenset(["e1"]),
        ))
        reg.record_rebuild("p1", T0)
        health = reg.get_health("p1")
        assert health.last_rebuild_at == T0
        assert health.is_healthy is True

    def test_record_error(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(
            projection_name="p1", event_types=frozenset(["e1"]),
        ))
        reg.record_error("p1", "Something broke")
        health = reg.get_health("p1")
        assert health.is_healthy is False
        assert "broke" in health.error_message

    def test_list_unhealthy(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(projection_name="ok", event_types=frozenset()))
        reg.register(ProjectionInfo(projection_name="bad", event_types=frozenset()))
        reg.record_error("bad", "fail")
        assert reg.list_unhealthy() == ["bad"]

    def test_summary(self):
        reg = ProjectionRegistry()
        reg.register(ProjectionInfo(
            projection_name="p1",
            event_types=frozenset(["e1", "e2"]),
            schema_version=2,
        ))
        s = reg.summary()
        assert "p1" in s
        assert s["p1"]["schema_version"] == 2


# ══════════════════════════════════════════════════════════════
# SNAPSHOT STORE
# ══════════════════════════════════════════════════════════════


class TestSnapshotStore:
    def test_create_and_get_latest(self):
        store = SnapshotStore()
        store.create_snapshot(
            projection_name="retail_rm",
            business_id=BIZ,
            snapshot_at=T0,
            created_at=T0,
            schema_version=1,
            data={"revenue": "1000"},
        )
        latest = store.get_latest("retail_rm", BIZ)
        assert latest is not None
        assert latest.data["revenue"] == "1000"

    def test_get_latest_returns_most_recent(self):
        store = SnapshotStore()
        store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0, created_at=T0,
            schema_version=1, data={"v": 1},
        )
        store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0 + timedelta(hours=1), created_at=T0 + timedelta(hours=1),
            schema_version=1, data={"v": 2},
        )
        latest = store.get_latest("p1", BIZ)
        assert latest.data["v"] == 2

    def test_time_travel_query(self):
        store = SnapshotStore()
        store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0, created_at=T0,
            schema_version=1, data={"state": "early"},
        )
        store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0 + timedelta(hours=2), created_at=T0 + timedelta(hours=2),
            schema_version=1, data={"state": "late"},
        )
        # Ask for state at T0+1h → should get first snapshot
        snap = store.get_at("p1", BIZ, T0 + timedelta(hours=1))
        assert snap.data["state"] == "early"

    def test_get_at_returns_none_before_first(self):
        store = SnapshotStore()
        store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0, created_at=T0,
            schema_version=1, data={},
        )
        snap = store.get_at("p1", BIZ, T0 - timedelta(hours=1))
        assert snap is None

    def test_list_snapshots(self):
        store = SnapshotStore()
        for i in range(3):
            store.create_snapshot(
                projection_name="p1", business_id=BIZ,
                snapshot_at=T0 + timedelta(hours=i),
                created_at=T0 + timedelta(hours=i),
                schema_version=1, data={"i": i},
            )
        snaps = store.list_snapshots("p1", BIZ)
        assert len(snaps) == 3
        assert snaps[0].data["i"] == 0
        assert snaps[2].data["i"] == 2

    def test_snapshot_is_frozen(self):
        store = SnapshotStore()
        snap = store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0, created_at=T0,
            schema_version=1, data={},
        )
        with pytest.raises(AttributeError):
            snap.projection_name = "changed"

    def test_tenant_isolation(self):
        store = SnapshotStore()
        biz2 = uuid.uuid4()
        store.create_snapshot(
            projection_name="p1", business_id=BIZ,
            snapshot_at=T0, created_at=T0,
            schema_version=1, data={"biz": "A"},
        )
        store.create_snapshot(
            projection_name="p1", business_id=biz2,
            snapshot_at=T0, created_at=T0,
            schema_version=1, data={"biz": "B"},
        )
        assert store.get_latest("p1", BIZ).data["biz"] == "A"
        assert store.get_latest("p1", biz2).data["biz"] == "B"


# ══════════════════════════════════════════════════════════════
# METRICS COLLECTOR
# ══════════════════════════════════════════════════════════════


class TestMetricsCollector:
    def test_record_event_applied(self):
        mc = MetricsCollector()
        mc.record_event_applied("p1", 1.5)
        mc.record_event_applied("p1", 2.5)
        m = mc.get("p1")
        assert m.total_events_processed == 2
        assert m.avg_apply_duration_ms == 2.0
        assert m.peak_apply_duration_ms == 2.5

    def test_record_rebuild(self):
        mc = MetricsCollector()
        mc.record_rebuild("p1", duration_ms=5000, events_count=10000)
        m = mc.get("p1")
        assert m.events_per_second == 2000.0

    def test_slowest_projections(self):
        mc = MetricsCollector()
        mc.record_event_applied("fast", 0.1)
        mc.record_event_applied("slow", 10.0)
        mc.record_event_applied("medium", 1.0)
        slowest = mc.slowest_projections(top_n=2)
        assert slowest[0].projection_name == "slow"
        assert slowest[1].projection_name == "medium"

    def test_summary(self):
        mc = MetricsCollector()
        mc.record_event_applied("p1", 1.0)
        s = mc.summary()
        assert "p1" in s
        assert s["p1"]["total_events_processed"] == 1
