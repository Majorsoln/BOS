"""
BOS Reporting / BI Engine — Event Types and Payload Builders
=============================================================
Engine: Reporting (Cross-Engine Analytics — Read Side)
Roadmap 5.5: Event-driven projections, Snapshot reporting, KPI calculators.

This engine receives commands to record KPIs, snapshots, and generated reports.
It is the canonical read-model / analytics write surface for BOS.

Events are ADDITIVE and APPEND-ONLY — no deletes, no corrections.
"""

from __future__ import annotations

from core.commands.base import Command


# ══════════════════════════════════════════════════════════════
# EVENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

REPORTING_SNAPSHOT_RECORDED_V1 = "reporting.snapshot.recorded.v1"
REPORTING_KPI_RECORDED_V1 = "reporting.kpi.recorded.v1"
REPORTING_REPORT_GENERATED_V1 = "reporting.report.generated.v1"

REPORTING_EVENT_TYPES = (
    REPORTING_SNAPSHOT_RECORDED_V1,
    REPORTING_KPI_RECORDED_V1,
    REPORTING_REPORT_GENERATED_V1,
)


# ══════════════════════════════════════════════════════════════
# COMMAND → EVENT MAPPING
# ══════════════════════════════════════════════════════════════

COMMAND_TO_EVENT_TYPE = {
    "reporting.snapshot.record.request": REPORTING_SNAPSHOT_RECORDED_V1,
    "reporting.kpi.record.request": REPORTING_KPI_RECORDED_V1,
    "reporting.report.generate.request": REPORTING_REPORT_GENERATED_V1,
}


def resolve_reporting_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_reporting_event_types(event_type_registry) -> None:
    for event_type in sorted(REPORTING_EVENT_TYPES):
        event_type_registry.register(event_type)


# ══════════════════════════════════════════════════════════════
# PAYLOAD BUILDERS
# ══════════════════════════════════════════════════════════════

def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "actor_id": command.actor_id,
        "actor_type": command.actor_type,
        "correlation_id": command.correlation_id,
        "command_id": command.command_id,
    }


def build_snapshot_recorded_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "snapshot_id": command.payload["snapshot_id"],
        "snapshot_type": command.payload["snapshot_type"],
        "period_start": command.payload["period_start"],
        "period_end": command.payload["period_end"],
        "period_label": command.payload.get("period_label", ""),
        "metrics": command.payload["metrics"],
        "source_engines": command.payload.get("source_engines", []),
        "recorded_at": command.issued_at,
    })
    return payload


def build_kpi_recorded_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "kpi_id": command.payload["kpi_id"],
        "kpi_key": command.payload["kpi_key"],
        "kpi_name": command.payload["kpi_name"],
        "value": command.payload["value"],
        "unit": command.payload["unit"],
        "dimension": command.payload.get("dimension", {}),
        "period_start": command.payload["period_start"],
        "period_end": command.payload["period_end"],
        "source_engine": command.payload.get("source_engine", ""),
        "recorded_at": command.issued_at,
    })
    return payload


def build_report_generated_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "report_id": command.payload["report_id"],
        "report_type": command.payload["report_type"],
        "report_name": command.payload["report_name"],
        "period_start": command.payload["period_start"],
        "period_end": command.payload["period_end"],
        "sections": command.payload["sections"],
        "kpi_ids": command.payload.get("kpi_ids", []),
        "snapshot_ids": command.payload.get("snapshot_ids", []),
        "generated_at": command.issued_at,
    })
    return payload
