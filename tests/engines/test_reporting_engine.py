"""
BOS Reporting / BI Engine Tests
================================
GAP-05: Event-driven projections, Snapshot reporting, KPI calculators.
Tests cover:
- Command validation
- Service dispatch and event routing
- Projection store queries
- KPI time-series accumulation
- Policy enforcement
- Feature flag wiring
"""

import uuid
from datetime import datetime, timezone

import pytest

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)


def kw():
    return dict(
        business_id=BIZ, actor_type="HUMAN", actor_id="analyst-1",
        command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
    )


class StubReg:
    def __init__(self):
        self._t = set()

    def register(self, et):
        self._t.add(et)

    def is_registered(self, et):
        return et in self._t


class StubFactory:
    def __call__(self, *, command, event_type, payload):
        return {"event_type": event_type, "payload": payload,
                "business_id": command.business_id, "source_engine": command.source_engine}


class StubPersist:
    def __init__(self):
        self.calls = []

    def __call__(self, *, event_data, context, registry, **k):
        self.calls.append(event_data)
        return {"accepted": True}


class StubBus:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, ct, h):
        self.handlers[ct] = h


def _svc():
    from engines.reporting.services import ReportingService
    return ReportingService(
        business_context={"business_id": BIZ}, command_bus=StubBus(),
        event_factory=StubFactory(), persist_event=StubPersist(),
        event_type_registry=StubReg(),
    )


# ══════════════════════════════════════════════════════════════
# COMMAND VALIDATION
# ══════════════════════════════════════════════════════════════

class TestSnapshotRecordRequest:
    def test_valid_request(self):
        from engines.reporting.commands import SnapshotRecordRequest
        req = SnapshotRecordRequest(
            snapshot_id="snap-1",
            snapshot_type="DAILY_OPS",
            period_start="2026-02-01",
            period_end="2026-02-01",
            metrics={"revenue": 50000, "orders": 12},
            source_engines=("restaurant", "retail"),
        )
        assert req.snapshot_id == "snap-1"
        assert req.snapshot_type == "DAILY_OPS"

    def test_empty_snapshot_id_raises(self):
        from engines.reporting.commands import SnapshotRecordRequest
        with pytest.raises(ValueError, match="snapshot_id"):
            SnapshotRecordRequest(
                snapshot_id="", snapshot_type="DAILY_OPS",
                period_start="2026-02-01", period_end="2026-02-01",
                metrics={},
            )

    def test_invalid_snapshot_type_raises(self):
        from engines.reporting.commands import SnapshotRecordRequest
        with pytest.raises(ValueError, match="not valid"):
            SnapshotRecordRequest(
                snapshot_id="s1", snapshot_type="INVALID_TYPE",
                period_start="2026-02-01", period_end="2026-02-01",
                metrics={},
            )

    def test_metrics_must_be_dict(self):
        from engines.reporting.commands import SnapshotRecordRequest
        with pytest.raises(ValueError, match="metrics"):
            SnapshotRecordRequest(
                snapshot_id="s1", snapshot_type="DAILY_OPS",
                period_start="2026-02-01", period_end="2026-02-01",
                metrics="not_a_dict",
            )

    def test_to_command(self):
        from engines.reporting.commands import SnapshotRecordRequest
        req = SnapshotRecordRequest(
            snapshot_id="snap-1", snapshot_type="WEEKLY_OPS",
            period_start="2026-02-01", period_end="2026-02-07",
            metrics={"revenue": 350000},
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == "reporting.snapshot.record.request"
        assert cmd.payload["snapshot_id"] == "snap-1"
        assert cmd.payload["metrics"]["revenue"] == 350000


class TestKPIRecordRequest:
    def test_valid_request(self):
        from engines.reporting.commands import KPIRecordRequest
        req = KPIRecordRequest(
            kpi_id="kpi-1", kpi_key="REVENUE_TOTAL",
            kpi_name="Daily Revenue", value=75000, unit="MINOR_CURRENCY",
            period_start="2026-02-20", period_end="2026-02-20",
            source_engine="restaurant",
        )
        assert req.value == 75000
        assert req.kpi_key == "REVENUE_TOTAL"

    def test_empty_kpi_id_raises(self):
        from engines.reporting.commands import KPIRecordRequest
        with pytest.raises(ValueError, match="kpi_id"):
            KPIRecordRequest(
                kpi_id="", kpi_key="REVENUE_TOTAL",
                kpi_name="Revenue", value=1000, unit="MINOR_CURRENCY",
                period_start="2026-02-20", period_end="2026-02-20",
            )

    def test_invalid_kpi_key_raises(self):
        from engines.reporting.commands import KPIRecordRequest
        with pytest.raises(ValueError, match="not valid"):
            KPIRecordRequest(
                kpi_id="k1", kpi_key="MADE_UP_KPI",
                kpi_name="X", value=100, unit="COUNT",
                period_start="2026-02-20", period_end="2026-02-20",
            )

    def test_invalid_unit_raises(self):
        from engines.reporting.commands import KPIRecordRequest
        with pytest.raises(ValueError, match="not valid"):
            KPIRecordRequest(
                kpi_id="k1", kpi_key="REVENUE_TOTAL",
                kpi_name="Revenue", value=1000, unit="DOLLARS",
                period_start="2026-02-20", period_end="2026-02-20",
            )

    def test_non_integer_value_raises(self):
        from engines.reporting.commands import KPIRecordRequest
        with pytest.raises(ValueError, match="integer"):
            KPIRecordRequest(
                kpi_id="k1", kpi_key="REVENUE_TOTAL",
                kpi_name="Revenue", value=100.5, unit="MINOR_CURRENCY",
                period_start="2026-02-20", period_end="2026-02-20",
            )

    def test_to_command(self):
        from engines.reporting.commands import KPIRecordRequest
        req = KPIRecordRequest(
            kpi_id="kpi-2", kpi_key="ORDERS_PLACED",
            kpi_name="Orders Placed Today", value=8, unit="COUNT",
            period_start="2026-02-20", period_end="2026-02-20",
            source_engine="restaurant",
            dimension={"category": "FOOD"},
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == "reporting.kpi.record.request"
        assert cmd.payload["value"] == 8
        assert cmd.payload["dimension"]["category"] == "FOOD"


class TestReportGenerateRequest:
    def _sections(self):
        return (
            {"title": "Revenue", "data": {"total": 50000}, "summary": "Good day"},
            {"title": "Operations", "data": {"orders": 12}, "summary": "Normal"},
        )

    def test_valid_request(self):
        from engines.reporting.commands import ReportGenerateRequest
        req = ReportGenerateRequest(
            report_id="rep-1", report_type="REVENUE_SUMMARY",
            report_name="Feb 20 Revenue Report",
            period_start="2026-02-20", period_end="2026-02-20",
            sections=self._sections(),
        )
        assert req.report_type == "REVENUE_SUMMARY"

    def test_empty_report_id_raises(self):
        from engines.reporting.commands import ReportGenerateRequest
        with pytest.raises(ValueError, match="report_id"):
            ReportGenerateRequest(
                report_id="", report_type="REVENUE_SUMMARY",
                report_name="R", period_start="2026-02-20",
                period_end="2026-02-20", sections=self._sections(),
            )

    def test_invalid_report_type_raises(self):
        from engines.reporting.commands import ReportGenerateRequest
        with pytest.raises(ValueError, match="not valid"):
            ReportGenerateRequest(
                report_id="r1", report_type="BAD_TYPE",
                report_name="R", period_start="2026-02-20",
                period_end="2026-02-20", sections=self._sections(),
            )

    def test_empty_sections_raises(self):
        from engines.reporting.commands import ReportGenerateRequest
        with pytest.raises(ValueError, match="sections"):
            ReportGenerateRequest(
                report_id="r1", report_type="REVENUE_SUMMARY",
                report_name="R", period_start="2026-02-20",
                period_end="2026-02-20", sections=(),
            )

    def test_to_command(self):
        from engines.reporting.commands import ReportGenerateRequest
        req = ReportGenerateRequest(
            report_id="rep-1", report_type="OPERATIONS_SUMMARY",
            report_name="Daily Ops", period_start="2026-02-20",
            period_end="2026-02-20", sections=self._sections(),
            kpi_ids=("kpi-1", "kpi-2"),
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == "reporting.report.generate.request"
        assert len(cmd.payload["sections"]) == 2
        assert "kpi-1" in cmd.payload["kpi_ids"]


# ══════════════════════════════════════════════════════════════
# SERVICE DISPATCH AND PROJECTION
# ══════════════════════════════════════════════════════════════

class TestReportingService:
    def test_handlers_registered(self):
        from engines.reporting.commands import REPORTING_COMMAND_TYPES
        svc = _svc()
        for ct in REPORTING_COMMAND_TYPES:
            assert ct in svc._command_bus.handlers

    def test_event_types_registered(self):
        svc = _svc()
        assert svc._event_type_registry.is_registered("reporting.snapshot.recorded.v1")
        assert svc._event_type_registry.is_registered("reporting.kpi.recorded.v1")
        assert svc._event_type_registry.is_registered("reporting.report.generated.v1")

    def test_snapshot_recorded_event(self):
        from engines.reporting.commands import SnapshotRecordRequest
        svc = _svc()
        req = SnapshotRecordRequest(
            snapshot_id="snap-1", snapshot_type="DAILY_OPS",
            period_start="2026-02-20", period_end="2026-02-20",
            metrics={"revenue": 50000},
        )
        result = svc._execute_command(req.to_command(**kw()))
        assert result.event_type == "reporting.snapshot.recorded.v1"
        assert result.projection_applied is True

    def test_snapshot_stored_in_projection(self):
        from engines.reporting.commands import SnapshotRecordRequest
        svc = _svc()
        svc._execute_command(SnapshotRecordRequest(
            snapshot_id="snap-1", snapshot_type="MONTHLY_OPS",
            period_start="2026-02-01", period_end="2026-02-28",
            metrics={"revenue": 1500000, "orders": 312},
            period_label="February 2026",
            source_engines=("restaurant", "retail", "workshop"),
        ).to_command(**kw()))
        snap = svc.projection_store.get_snapshot("snap-1")
        assert snap is not None
        assert snap["snapshot_type"] == "MONTHLY_OPS"
        assert snap["metrics"]["revenue"] == 1500000
        assert snap["period_label"] == "February 2026"
        assert svc.projection_store.total_snapshots == 1

    def test_kpi_recorded_event(self):
        from engines.reporting.commands import KPIRecordRequest
        svc = _svc()
        result = svc._execute_command(KPIRecordRequest(
            kpi_id="k1", kpi_key="REVENUE_TOTAL",
            kpi_name="Revenue", value=25000, unit="MINOR_CURRENCY",
            period_start="2026-02-20", period_end="2026-02-20",
        ).to_command(**kw()))
        assert result.event_type == "reporting.kpi.recorded.v1"
        assert result.projection_applied is True

    def test_kpi_stored_in_projection(self):
        from engines.reporting.commands import KPIRecordRequest
        svc = _svc()
        svc._execute_command(KPIRecordRequest(
            kpi_id="k1", kpi_key="ORDERS_PLACED",
            kpi_name="Orders Today", value=15, unit="COUNT",
            period_start="2026-02-20", period_end="2026-02-20",
            source_engine="restaurant",
        ).to_command(**kw()))
        kpi = svc.projection_store.get_kpi("k1")
        assert kpi is not None
        assert kpi["kpi_key"] == "ORDERS_PLACED"
        assert kpi["value"] == 15
        assert kpi["source_engine"] == "restaurant"
        assert svc.projection_store.total_kpis == 1

    def test_report_generated_event(self):
        from engines.reporting.commands import ReportGenerateRequest
        svc = _svc()
        result = svc._execute_command(ReportGenerateRequest(
            report_id="rep-1", report_type="REVENUE_SUMMARY",
            report_name="Feb Summary", period_start="2026-02-01",
            period_end="2026-02-28",
            sections=({"title": "Revenue", "data": {}, "summary": ""},),
        ).to_command(**kw()))
        assert result.event_type == "reporting.report.generated.v1"
        assert result.projection_applied is True

    def test_report_stored_in_projection(self):
        from engines.reporting.commands import ReportGenerateRequest
        svc = _svc()
        svc._execute_command(ReportGenerateRequest(
            report_id="rep-1", report_type="OPERATIONS_SUMMARY",
            report_name="Weekly Ops Report", period_start="2026-02-14",
            period_end="2026-02-20",
            sections=(
                {"title": "Revenue", "data": {"total": 500000}, "summary": "Up 10%"},
                {"title": "Orders", "data": {"count": 89}, "summary": "Good"},
            ),
            kpi_ids=("k1", "k2"),
            snapshot_ids=("snap-1",),
        ).to_command(**kw()))
        rep = svc.projection_store.get_report("rep-1")
        assert rep is not None
        assert rep["report_type"] == "OPERATIONS_SUMMARY"
        assert len(rep["sections"]) == 2
        assert "k1" in rep["kpi_ids"]
        assert "snap-1" in rep["snapshot_ids"]
        assert svc.projection_store.total_reports == 1


# ══════════════════════════════════════════════════════════════
# KPI TIME-SERIES ACCUMULATION
# ══════════════════════════════════════════════════════════════

class TestKPITimeSeries:
    def test_kpi_series_accumulates(self):
        from engines.reporting.commands import KPIRecordRequest
        svc = _svc()
        # Record 3 days of revenue
        for i, (date, val) in enumerate([
            ("2026-02-18", 30000),
            ("2026-02-19", 45000),
            ("2026-02-20", 52000),
        ]):
            svc._execute_command(KPIRecordRequest(
                kpi_id=f"rev-{i}", kpi_key="REVENUE_TOTAL",
                kpi_name="Daily Revenue", value=val, unit="MINOR_CURRENCY",
                period_start=date, period_end=date,
            ).to_command(**kw()))

        series = svc.projection_store.get_kpi_series("REVENUE_TOTAL")
        assert len(series) == 3
        assert series[0]["value"] == 30000
        assert series[2]["value"] == 52000

    def test_sum_kpi(self):
        from engines.reporting.commands import KPIRecordRequest
        svc = _svc()
        for i, val in enumerate([10000, 20000, 30000]):
            svc._execute_command(KPIRecordRequest(
                kpi_id=f"k-{i}", kpi_key="REVENUE_CASH",
                kpi_name="Cash Revenue", value=val, unit="MINOR_CURRENCY",
                period_start="2026-02-20", period_end="2026-02-20",
            ).to_command(**kw()))
        assert svc.projection_store.sum_kpi("REVENUE_CASH") == 60000

    def test_latest_kpi_value(self):
        from engines.reporting.commands import KPIRecordRequest
        svc = _svc()
        for i, val in enumerate([5, 8, 12]):
            svc._execute_command(KPIRecordRequest(
                kpi_id=f"ord-{i}", kpi_key="ORDERS_PLACED",
                kpi_name="Orders", value=val, unit="COUNT",
                period_start="2026-02-20", period_end="2026-02-20",
            ).to_command(**kw()))
        assert svc.projection_store.latest_kpi_value("ORDERS_PLACED") == 12

    def test_latest_kpi_none_when_missing(self):
        svc = _svc()
        assert svc.projection_store.latest_kpi_value("HOURS_WORKED") is None

    def test_snapshot_count_by_type(self):
        from engines.reporting.commands import SnapshotRecordRequest
        svc = _svc()
        for i in range(3):
            svc._execute_command(SnapshotRecordRequest(
                snapshot_id=f"snap-daily-{i}", snapshot_type="DAILY_OPS",
                period_start=f"2026-02-{18 + i:02d}", period_end=f"2026-02-{18 + i:02d}",
                metrics={"revenue": 10000 * (i + 1)},
            ).to_command(**kw()))
        svc._execute_command(SnapshotRecordRequest(
            snapshot_id="snap-weekly-1", snapshot_type="WEEKLY_OPS",
            period_start="2026-02-14", period_end="2026-02-20",
            metrics={"revenue": 100000},
        ).to_command(**kw()))
        assert svc.projection_store.snapshot_count_by_type("DAILY_OPS") == 3
        assert svc.projection_store.snapshot_count_by_type("WEEKLY_OPS") == 1
        assert svc.projection_store.total_snapshots == 4

    def test_multiple_kpi_keys_tracked_separately(self):
        from engines.reporting.commands import KPIRecordRequest
        svc = _svc()
        svc._execute_command(KPIRecordRequest(
            kpi_id="r1", kpi_key="REVENUE_TOTAL",
            kpi_name="Revenue", value=50000, unit="MINOR_CURRENCY",
            period_start="2026-02-20", period_end="2026-02-20",
        ).to_command(**kw()))
        svc._execute_command(KPIRecordRequest(
            kpi_id="j1", kpi_key="JOBS_COMPLETED",
            kpi_name="Jobs", value=3, unit="COUNT",
            period_start="2026-02-20", period_end="2026-02-20",
        ).to_command(**kw()))
        assert len(svc.projection_store.get_kpi_series("REVENUE_TOTAL")) == 1
        assert len(svc.projection_store.get_kpi_series("JOBS_COMPLETED")) == 1
        assert svc.projection_store.get_kpi_series("EMPLOYEES_ACTIVE") == []


# ══════════════════════════════════════════════════════════════
# POLICY TESTS
# ══════════════════════════════════════════════════════════════

class TestReportingPolicies:
    def test_period_valid_policy_allows_valid_dates(self):
        from engines.reporting.policies import report_period_must_be_valid_policy
        from engines.reporting.commands import ReportGenerateRequest
        cmd = ReportGenerateRequest(
            report_id="r1", report_type="REVENUE_SUMMARY",
            report_name="R", period_start="2026-02-01", period_end="2026-02-28",
            sections=({"title": "X", "data": {}, "summary": ""},),
        ).to_command(**kw())
        assert report_period_must_be_valid_policy(cmd) is None

    def test_period_valid_policy_rejects_reversed_dates(self):
        from engines.reporting.policies import report_period_must_be_valid_policy
        from engines.reporting.commands import ReportGenerateRequest
        cmd = ReportGenerateRequest(
            report_id="r1", report_type="REVENUE_SUMMARY",
            report_name="R", period_start="2026-02-28", period_end="2026-02-01",
            sections=({"title": "X", "data": {}, "summary": ""},),
        ).to_command(**kw())
        result = report_period_must_be_valid_policy(cmd)
        assert result is not None
        assert result.code == "INVALID_PERIOD"
        assert result.policy_name == "report_period_must_be_valid_policy"

    def test_snapshot_unique_policy_allows_new(self):
        from engines.reporting.policies import snapshot_id_must_be_unique_policy
        from engines.reporting.commands import SnapshotRecordRequest
        cmd = SnapshotRecordRequest(
            snapshot_id="new-snap", snapshot_type="DAILY_OPS",
            period_start="2026-02-20", period_end="2026-02-20",
            metrics={},
        ).to_command(**kw())
        result = snapshot_id_must_be_unique_policy(cmd, snapshot_lookup=lambda x: None)
        assert result is None

    def test_snapshot_unique_policy_rejects_duplicate(self):
        from engines.reporting.policies import snapshot_id_must_be_unique_policy
        from engines.reporting.commands import SnapshotRecordRequest
        existing = {"snapshot_type": "DAILY_OPS"}
        cmd = SnapshotRecordRequest(
            snapshot_id="snap-1", snapshot_type="DAILY_OPS",
            period_start="2026-02-20", period_end="2026-02-20",
            metrics={},
        ).to_command(**kw())
        result = snapshot_id_must_be_unique_policy(
            cmd, snapshot_lookup=lambda x: existing)
        assert result is not None
        assert result.code == "DUPLICATE_SNAPSHOT"
        assert result.policy_name == "snapshot_id_must_be_unique_policy"

    def test_report_sections_policy_rejects_empty(self):
        from engines.reporting.policies import report_must_have_sections_policy
        from engines.reporting.commands import ReportGenerateRequest
        # sections forced empty by mocking — test with a report that has valid sections first
        cmd = ReportGenerateRequest(
            report_id="r1", report_type="CUSTOM",
            report_name="Test", period_start="2026-02-01", period_end="2026-02-28",
            sections=({"title": "S", "data": {}, "summary": ""},),
        ).to_command(**kw())
        # Manually test the policy with empty sections in payload
        cmd_dict = {"payload": {"sections": []}}

        class FakeCmd:
            payload = {"sections": []}
        assert report_must_have_sections_policy(FakeCmd()) is not None
        assert report_must_have_sections_policy(FakeCmd()).code == "REPORT_NO_SECTIONS"


# ══════════════════════════════════════════════════════════════
# FEATURE FLAG
# ══════════════════════════════════════════════════════════════

class TestReportingFeatureFlag:
    def test_flag_registered_in_registry(self):
        from core.feature_flags.registry import (
            COMMAND_FLAG_MAP, FLAG_ENABLE_REPORTING_ENGINE,
        )
        assert "reporting.snapshot.record.request" in COMMAND_FLAG_MAP
        assert "reporting.kpi.record.request" in COMMAND_FLAG_MAP
        assert "reporting.report.generate.request" in COMMAND_FLAG_MAP
        assert COMMAND_FLAG_MAP["reporting.snapshot.record.request"] == FLAG_ENABLE_REPORTING_ENGINE

    def test_flag_exported_from_init(self):
        from core.feature_flags import FLAG_ENABLE_REPORTING_ENGINE
        assert FLAG_ENABLE_REPORTING_ENGINE == "ENABLE_REPORTING_ENGINE"


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════

class TestReportingSubscriptions:
    def test_subscription_map_exists(self):
        from engines.reporting.subscriptions import SUBSCRIPTIONS
        assert "restaurant.bill.settled.v1" in SUBSCRIPTIONS
        assert "retail.sale.completed.v1" in SUBSCRIPTIONS
        assert "workshop.job.invoiced.v1" in SUBSCRIPTIONS

    def test_handle_bill_settled_records_kpi(self):
        from engines.reporting.subscriptions import ReportingSubscriptionHandler
        svc = _svc()
        handler = ReportingSubscriptionHandler(svc)
        event_data = {
            "event_type": "restaurant.bill.settled.v1",
            "payload": {
                "business_id": BIZ,
                "total_amount": 15000,
                "tip_amount": 1500,
            },
        }
        handler.handle_bill_settled(event_data)
        # Should have recorded REVENUE_TOTAL and TIPS_COLLECTED and BILLS_SETTLED
        series_rev = svc.projection_store.get_kpi_series("REVENUE_TOTAL")
        series_tips = svc.projection_store.get_kpi_series("TIPS_COLLECTED")
        series_bills = svc.projection_store.get_kpi_series("BILLS_SETTLED")
        assert len(series_rev) == 1
        assert series_rev[0]["value"] == 15000
        assert len(series_tips) == 1
        assert series_tips[0]["value"] == 1500
        assert len(series_bills) == 1

    def test_handle_job_invoiced_records_revenue(self):
        from engines.reporting.subscriptions import ReportingSubscriptionHandler
        svc = _svc()
        handler = ReportingSubscriptionHandler(svc)
        event_data = {
            "event_type": "workshop.job.invoiced.v1",
            "payload": {
                "business_id": BIZ,
                "amount": 8500,
            },
        }
        handler.handle_job_invoiced(event_data)
        series = svc.projection_store.get_kpi_series("REVENUE_TOTAL")
        assert series[0]["value"] == 8500
        assert series[0]["source_engine"] == "workshop"

    def test_handle_shift_ended_records_hours(self):
        from engines.reporting.subscriptions import ReportingSubscriptionHandler
        svc = _svc()
        handler = ReportingSubscriptionHandler(svc)
        event_data = {
            "event_type": "hr.shift.ended.v1",
            "payload": {
                "business_id": BIZ,
                "hours_worked": 8,
            },
        }
        handler.handle_shift_ended(event_data)
        hours = svc.projection_store.get_kpi_series("HOURS_WORKED")
        assert hours[0]["value"] == 8

    def test_subscription_handler_zero_value_not_recorded(self):
        """Bill with 0 total should not record revenue KPI."""
        from engines.reporting.subscriptions import ReportingSubscriptionHandler
        svc = _svc()
        handler = ReportingSubscriptionHandler(svc)
        event_data = {
            "event_type": "restaurant.bill.settled.v1",
            "payload": {"business_id": BIZ, "total_amount": 0},
        }
        handler.handle_bill_settled(event_data)
        # Only BILLS_SETTLED should be recorded, not REVENUE_TOTAL
        assert svc.projection_store.get_kpi_series("REVENUE_TOTAL") == []
        assert len(svc.projection_store.get_kpi_series("BILLS_SETTLED")) == 1


# ══════════════════════════════════════════════════════════════
# FULL LIFECYCLE
# ══════════════════════════════════════════════════════════════

class TestReportingFullLifecycle:
    def test_full_daily_reporting_flow(self):
        from engines.reporting.commands import (
            KPIRecordRequest, SnapshotRecordRequest, ReportGenerateRequest,
        )
        svc = _svc()

        # 1. Record KPIs throughout the day
        svc._execute_command(KPIRecordRequest(
            kpi_id="rev-1", kpi_key="REVENUE_TOTAL",
            kpi_name="Total Revenue", value=75000, unit="MINOR_CURRENCY",
            period_start="2026-02-20", period_end="2026-02-20",
            source_engine="restaurant",
        ).to_command(**kw()))
        svc._execute_command(KPIRecordRequest(
            kpi_id="ord-1", kpi_key="ORDERS_PLACED",
            kpi_name="Orders Today", value=23, unit="COUNT",
            period_start="2026-02-20", period_end="2026-02-20",
            source_engine="restaurant",
        ).to_command(**kw()))
        svc._execute_command(KPIRecordRequest(
            kpi_id="hr-1", kpi_key="HOURS_WORKED",
            kpi_name="Shift Hours", value=48, unit="HOURS",
            period_start="2026-02-20", period_end="2026-02-20",
            source_engine="hr",
        ).to_command(**kw()))

        # 2. Record end-of-day snapshot
        svc._execute_command(SnapshotRecordRequest(
            snapshot_id="snap-20260220", snapshot_type="DAILY_OPS",
            period_start="2026-02-20", period_end="2026-02-20",
            period_label="Thursday 20 February 2026",
            metrics={
                "revenue_total": svc.projection_store.sum_kpi("REVENUE_TOTAL"),
                "orders_placed": svc.projection_store.sum_kpi("ORDERS_PLACED"),
                "hours_worked": svc.projection_store.sum_kpi("HOURS_WORKED"),
            },
            source_engines=("restaurant", "hr"),
        ).to_command(**kw()))

        # 3. Generate daily report
        svc._execute_command(ReportGenerateRequest(
            report_id="report-daily-20260220",
            report_type="OPERATIONS_SUMMARY",
            report_name="Daily Operations — 20 Feb 2026",
            period_start="2026-02-20", period_end="2026-02-20",
            sections=(
                {"title": "Revenue", "data": {"total": 75000}, "summary": "Strong day"},
                {"title": "Orders", "data": {"count": 23}, "summary": "Normal volume"},
                {"title": "HR", "data": {"hours": 48}, "summary": "Full shifts"},
            ),
            kpi_ids=("rev-1", "ord-1", "hr-1"),
            snapshot_ids=("snap-20260220",),
        ).to_command(**kw()))

        # 4. Verify all data captured correctly
        snap = svc.projection_store.get_snapshot("snap-20260220")
        assert snap["metrics"]["revenue_total"] == 75000
        assert snap["metrics"]["orders_placed"] == 23

        report = svc.projection_store.get_report("report-daily-20260220")
        assert report["report_name"] == "Daily Operations — 20 Feb 2026"
        assert len(report["sections"]) == 3

        assert svc.projection_store.event_count == 5
        assert svc.projection_store.total_kpis == 3
        assert svc.projection_store.total_snapshots == 1
        assert svc.projection_store.total_reports == 1
