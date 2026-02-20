"""
BOS Reporting / BI Engine — Request Commands
=============================================
Commands for recording KPIs, snapshots, and generating reports.
All commands are additive — reporting data is append-only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED


# ══════════════════════════════════════════════════════════════
# COMMAND TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

REPORTING_SNAPSHOT_RECORD_REQUEST = "reporting.snapshot.record.request"
REPORTING_KPI_RECORD_REQUEST = "reporting.kpi.record.request"
REPORTING_REPORT_GENERATE_REQUEST = "reporting.report.generate.request"

REPORTING_COMMAND_TYPES = frozenset({
    REPORTING_SNAPSHOT_RECORD_REQUEST,
    REPORTING_KPI_RECORD_REQUEST,
    REPORTING_REPORT_GENERATE_REQUEST,
})

# ── Snapshot types ────────────────────────────────────────────
VALID_SNAPSHOT_TYPES = frozenset({
    "DAILY_OPS",       # Daily operations snapshot
    "WEEKLY_OPS",      # Weekly operations summary
    "MONTHLY_OPS",     # Monthly close snapshot
    "INVENTORY_LEVEL", # Point-in-time stock levels
    "REVENUE_PERIOD",  # Period revenue snapshot
    "CUSTOM",          # Ad-hoc custom snapshot
})

# ── KPI keys ─────────────────────────────────────────────────
VALID_KPI_KEYS = frozenset({
    "REVENUE_TOTAL",         # Total revenue (minor currency units)
    "REVENUE_CASH",          # Cash revenue
    "REVENUE_CARD",          # Card revenue
    "ORDERS_PLACED",         # Count of orders placed
    "ORDERS_COMPLETED",      # Count of orders completed
    "ORDERS_CANCELLED",      # Count of orders cancelled
    "BILLS_SETTLED",         # Count of bills settled
    "JOBS_CREATED",          # Workshop jobs created
    "JOBS_COMPLETED",        # Workshop jobs completed
    "JOBS_INVOICED",         # Workshop jobs invoiced
    "STOCK_ISSUES",          # Inventory issues count
    "STOCK_RECEIVED_LINES",  # Procurement received lines
    "CAMPAIGNS_ACTIVE",      # Active promotion campaigns
    "COUPONS_REDEEMED",      # Coupons redeemed count
    "EMPLOYEES_ACTIVE",      # Active employee count
    "SHIFTS_WORKED",         # Total shifts worked
    "HOURS_WORKED",          # Total hours worked
    "TIPS_COLLECTED",        # Tips collected (restaurant)
    "TABLES_SERVED",         # Tables served (restaurant)
    "CUSTOM",                # Custom KPI
})

# ── KPI units ─────────────────────────────────────────────────
VALID_KPI_UNITS = frozenset({
    "MINOR_CURRENCY",  # Minor currency units (cents, fils, etc.)
    "COUNT",           # Simple count
    "HOURS",           # Hours (for HR shifts)
    "MM",              # Millimeters (for workshop offcuts)
    "SQM",             # Square meters
    "KG",              # Kilograms
    "PERCENT",         # Percentage
    "CUSTOM",          # Custom unit
})

# ── Report types ──────────────────────────────────────────────
VALID_REPORT_TYPES = frozenset({
    "REVENUE_SUMMARY",       # Revenue across all engines
    "OPERATIONS_SUMMARY",    # Cross-engine operations
    "INVENTORY_SUMMARY",     # Stock levels and movements
    "PROCUREMENT_SUMMARY",   # PO lifecycle summary
    "WORKSHOP_SUMMARY",      # Job + cutting summary
    "HR_SUMMARY",            # Employee, shift, leave summary
    "PROMOTION_SUMMARY",     # Campaign + coupon summary
    "PERIOD_COMPARISON",     # Two-period comparison
    "CUSTOM",                # Custom report
})


# ══════════════════════════════════════════════════════════════
# COMMAND HELPER
# ══════════════════════════════════════════════════════════════

def _cmd(ct, payload, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None):
    return Command(
        command_id=command_id, command_type=ct,
        business_id=business_id, branch_id=branch_id,
        actor_type=actor_type, actor_id=actor_id,
        payload=payload, issued_at=issued_at,
        correlation_id=correlation_id, source_engine="reporting",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


# ══════════════════════════════════════════════════════════════
# REQUEST COMMANDS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SnapshotRecordRequest:
    """
    Record a business-state snapshot at a point in time.

    Snapshots capture the aggregate state of one or more engines
    for a given period. Used for period-close, dashboards, and audits.
    """
    snapshot_id: str
    snapshot_type: str
    period_start: str    # ISO 8601 date string (YYYY-MM-DD)
    period_end: str      # ISO 8601 date string (YYYY-MM-DD)
    metrics: dict        # Metric key → value (engine-specific KPIs)
    period_label: str = ""
    source_engines: tuple = ()
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty.")
        if self.snapshot_type not in VALID_SNAPSHOT_TYPES:
            raise ValueError(
                f"snapshot_type '{self.snapshot_type}' not valid. "
                f"Must be one of {sorted(VALID_SNAPSHOT_TYPES)}."
            )
        if not self.period_start:
            raise ValueError("period_start must be non-empty.")
        if not self.period_end:
            raise ValueError("period_end must be non-empty.")
        if not isinstance(self.metrics, dict):
            raise ValueError("metrics must be a dict.")

    def to_command(self, **kw) -> Command:
        return _cmd(REPORTING_SNAPSHOT_RECORD_REQUEST, {
            "snapshot_id": self.snapshot_id,
            "snapshot_type": self.snapshot_type,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "period_label": self.period_label,
            "metrics": self.metrics,
            "source_engines": list(self.source_engines),
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class KPIRecordRequest:
    """
    Record a single KPI data point for a business period.

    KPIs are time-series data points tied to a specific period.
    They can be rolled up across periods for trend analysis.
    """
    kpi_id: str
    kpi_key: str
    kpi_name: str
    value: int           # Integer value (minor units, count, mm, etc.)
    unit: str
    period_start: str    # ISO 8601
    period_end: str      # ISO 8601
    source_engine: str = ""
    dimension: dict = None   # e.g. {"branch_id": "...", "category": "FOOD"}
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.kpi_id:
            raise ValueError("kpi_id must be non-empty.")
        if self.kpi_key not in VALID_KPI_KEYS:
            raise ValueError(
                f"kpi_key '{self.kpi_key}' not valid. "
                f"Must be one of {sorted(VALID_KPI_KEYS)}."
            )
        if not self.kpi_name:
            raise ValueError("kpi_name must be non-empty.")
        if not isinstance(self.value, int):
            raise ValueError("value must be an integer.")
        if self.unit not in VALID_KPI_UNITS:
            raise ValueError(
                f"unit '{self.unit}' not valid. "
                f"Must be one of {sorted(VALID_KPI_UNITS)}."
            )
        if not self.period_start:
            raise ValueError("period_start must be non-empty.")
        if not self.period_end:
            raise ValueError("period_end must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(REPORTING_KPI_RECORD_REQUEST, {
            "kpi_id": self.kpi_id,
            "kpi_key": self.kpi_key,
            "kpi_name": self.kpi_name,
            "value": self.value,
            "unit": self.unit,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "source_engine": self.source_engine,
            "dimension": self.dimension or {},
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class ReportGenerateRequest:
    """
    Generate a structured report covering one or more engines over a period.

    Reports aggregate KPIs and snapshots into human/machine-readable sections.
    Each section is a dict with keys: title, data, summary.
    """
    report_id: str
    report_type: str
    report_name: str
    period_start: str    # ISO 8601
    period_end: str      # ISO 8601
    sections: tuple      # tuple of dicts: [{title, data, summary}, ...]
    kpi_ids: tuple = ()
    snapshot_ids: tuple = ()
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.report_id:
            raise ValueError("report_id must be non-empty.")
        if self.report_type not in VALID_REPORT_TYPES:
            raise ValueError(
                f"report_type '{self.report_type}' not valid. "
                f"Must be one of {sorted(VALID_REPORT_TYPES)}."
            )
        if not self.report_name:
            raise ValueError("report_name must be non-empty.")
        if not self.period_start:
            raise ValueError("period_start must be non-empty.")
        if not self.period_end:
            raise ValueError("period_end must be non-empty.")
        if not isinstance(self.sections, tuple) or len(self.sections) == 0:
            raise ValueError("sections must be a non-empty tuple.")

    def to_command(self, **kw) -> Command:
        return _cmd(REPORTING_REPORT_GENERATE_REQUEST, {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "report_name": self.report_name,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "sections": list(self.sections),
            "kpi_ids": list(self.kpi_ids),
            "snapshot_ids": list(self.snapshot_ids),
        }, branch_id=self.branch_id, **kw)
