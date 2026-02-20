"""
BOS Reporting / BI Engine — Application Service
=================================================
Event-driven projections, Snapshot reporting, KPI calculators.
Roadmap 5.5: Read-side analytics engine.

This engine is ADDITIVE ONLY:
- All recorded KPIs and snapshots are permanent
- Reports are generated from recorded data (never modified)
- Multi-tenant: all data keyed by business_id
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.reporting.commands import REPORTING_COMMAND_TYPES
from engines.reporting.events import (
    resolve_reporting_event_type,
    register_reporting_event_types,
    build_snapshot_recorded_payload,
    build_kpi_recorded_payload,
    build_report_generated_payload,
)


# ══════════════════════════════════════════════════════════════
# PROTOCOLS
# ══════════════════════════════════════════════════════════════

class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...


class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


# ══════════════════════════════════════════════════════════════
# PROJECTION STORE
# ══════════════════════════════════════════════════════════════

class ReportingProjectionStore:
    """
    In-memory analytics projection store for the reporting engine.

    Stores KPI time-series, business snapshots, and generated reports.
    All data is append-only and multi-tenant safe.
    """

    def __init__(self):
        self._events: List[dict] = []
        self._snapshots: Dict[str, dict] = {}          # snapshot_id → snapshot data
        self._kpis: Dict[str, dict] = {}               # kpi_id → kpi data
        self._kpi_series: Dict[str, List[dict]] = {}   # kpi_key → [data points]
        self._reports: Dict[str, dict] = {}            # report_id → report data

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("reporting.snapshot.recorded"):
            sid = payload["snapshot_id"]
            self._snapshots[sid] = {
                "snapshot_type": payload["snapshot_type"],
                "period_start": payload["period_start"],
                "period_end": payload["period_end"],
                "period_label": payload.get("period_label", ""),
                "metrics": payload["metrics"],
                "source_engines": payload.get("source_engines", []),
                "recorded_at": payload["recorded_at"],
            }

        elif event_type.startswith("reporting.kpi.recorded"):
            kid = payload["kpi_id"]
            kpi_key = payload["kpi_key"]
            kpi_entry = {
                "kpi_key": kpi_key,
                "kpi_name": payload["kpi_name"],
                "value": payload["value"],
                "unit": payload["unit"],
                "period_start": payload["period_start"],
                "period_end": payload["period_end"],
                "source_engine": payload.get("source_engine", ""),
                "dimension": payload.get("dimension", {}),
                "recorded_at": payload["recorded_at"],
            }
            self._kpis[kid] = kpi_entry
            self._kpi_series.setdefault(kpi_key, []).append(kpi_entry)

        elif event_type.startswith("reporting.report.generated"):
            rid = payload["report_id"]
            self._reports[rid] = {
                "report_type": payload["report_type"],
                "report_name": payload["report_name"],
                "period_start": payload["period_start"],
                "period_end": payload["period_end"],
                "sections": payload["sections"],
                "kpi_ids": payload.get("kpi_ids", []),
                "snapshot_ids": payload.get("snapshot_ids", []),
                "generated_at": payload["generated_at"],
            }

    # ── Query Interface ────────────────────────────────────────

    def get_snapshot(self, snapshot_id: str) -> Optional[dict]:
        return self._snapshots.get(snapshot_id)

    def get_kpi(self, kpi_id: str) -> Optional[dict]:
        return self._kpis.get(kpi_id)

    def get_kpi_series(self, kpi_key: str) -> List[dict]:
        """Return all recorded data points for a KPI key, in recording order."""
        return list(self._kpi_series.get(kpi_key, []))

    def get_report(self, report_id: str) -> Optional[dict]:
        return self._reports.get(report_id)

    def latest_kpi_value(self, kpi_key: str) -> Optional[int]:
        """Return the most recently recorded value for a KPI key."""
        series = self._kpi_series.get(kpi_key, [])
        if not series:
            return None
        return series[-1]["value"]

    def sum_kpi(self, kpi_key: str) -> int:
        """Sum all recorded values for a KPI key (e.g. total revenue over time)."""
        return sum(entry["value"] for entry in self._kpi_series.get(kpi_key, []))

    def snapshot_count_by_type(self, snapshot_type: str) -> int:
        return sum(
            1 for s in self._snapshots.values()
            if s["snapshot_type"] == snapshot_type
        )

    @property
    def total_snapshots(self) -> int:
        return len(self._snapshots)

    @property
    def total_kpis(self) -> int:
        return len(self._kpis)

    @property
    def total_reports(self) -> int:
        return len(self._reports)

    @property
    def event_count(self) -> int:
        return len(self._events)


# ══════════════════════════════════════════════════════════════
# PAYLOAD DISPATCHER
# ══════════════════════════════════════════════════════════════

PAYLOAD_BUILDERS = {
    "reporting.snapshot.record.request": build_snapshot_recorded_payload,
    "reporting.kpi.record.request": build_kpi_recorded_payload,
    "reporting.report.generate.request": build_report_generated_payload,
}


# ══════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReportingExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLER
# ══════════════════════════════════════════════════════════════

class _ReportingCommandHandler:
    def __init__(self, service: "ReportingService"):
        self._service = service

    def execute(self, command: Command) -> ReportingExecutionResult:
        return self._service._execute_command(command)


# ══════════════════════════════════════════════════════════════
# APPLICATION SERVICE
# ══════════════════════════════════════════════════════════════

class ReportingService:
    """
    Reporting / BI Engine — analytics and KPI tracking.

    Receives commands to record snapshots, KPI data points, and reports.
    All data is additive and event-sourced.
    """

    def __init__(
        self,
        *,
        business_context,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: ReportingProjectionStore | None = None,
        feature_flag_provider=None,
    ):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or ReportingProjectionStore()
        self._feature_flag_provider = feature_flag_provider

        register_reporting_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _ReportingCommandHandler(self)
        for command_type in sorted(REPORTING_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_command(self, command: Command) -> ReportingExecutionResult:
        ff = FeatureFlagEvaluator.evaluate(
            command, self._business_context, self._feature_flag_provider
        )
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_reporting_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported reporting command type: {command.command_type}"
            )

        builder = PAYLOAD_BUILDERS.get(command.command_type)
        if builder is None:
            raise ValueError(f"No payload builder for: {command.command_type}")

        payload = builder(command)

        event_data = self._event_factory(
            command=command,
            event_type=event_type,
            payload=payload,
        )

        persist_result = self._persist_event(
            event_data=event_data,
            context=self._business_context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )

        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            applied = True

        return ReportingExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> ReportingProjectionStore:
        return self._projection_store
