"""
BOS Reporting Engine — Cross-Engine Event Subscriptions
========================================================
The Reporting engine subscribes to events from all other engines
and automatically records KPI data points.

Each handler extracts the relevant metric and dispatches a
KPIRecordRequest to the reporting service.

Subscription pattern:
    SUBSCRIPTIONS = {
        "event.type.v1": "handler_method_name"
    }
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engines.reporting.services import ReportingService


SUBSCRIPTIONS = {
    # Revenue events
    "restaurant.bill.settled.v1": "handle_bill_settled",
    "retail.sale.completed.v1": "handle_sale_completed",
    "workshop.job.invoiced.v1": "handle_job_invoiced",
    # Operational events
    "restaurant.order.placed.v1": "handle_order_placed",
    "workshop.job.completed.v1": "handle_job_completed",
    "procurement.order.received.v1": "handle_procurement_received",
    # HR events
    "hr.shift.ended.v1": "handle_shift_ended",
    "hr.employee.onboarded.v1": "handle_employee_onboarded",
}


class ReportingSubscriptionHandler:
    """
    Converts cross-engine events into KPI data points in the Reporting engine.

    Each handler:
    1. Extracts metric value from the event payload
    2. Builds a KPIRecordRequest
    3. Dispatches to the ReportingService
    4. Errors are caught per-event to prevent cascade failures
    """

    def __init__(self, reporting_service: "ReportingService"):
        self._service = reporting_service

    def _record_kpi(
        self,
        kpi_key: str,
        kpi_name: str,
        value: int,
        unit: str,
        event_data: dict,
        source_engine: str,
        dimension: dict = None,
    ) -> None:
        """Helper: build and dispatch a KPIRecordRequest."""
        from engines.reporting.commands import KPIRecordRequest

        payload = event_data.get("payload", {})
        issued_at = datetime.now(tz=timezone.utc)

        # Use event's correlation_id for traceability
        kpi_id = f"kpi-{kpi_key}-{uuid.uuid4().hex[:8]}"
        period_date = issued_at.strftime("%Y-%m-%d")

        req = KPIRecordRequest(
            kpi_id=kpi_id,
            kpi_key=kpi_key,
            kpi_name=kpi_name,
            value=value,
            unit=unit,
            period_start=period_date,
            period_end=period_date,
            source_engine=source_engine,
            dimension=dimension or {},
        )
        cmd = req.to_command(
            business_id=payload.get("business_id", uuid.uuid4()),
            actor_type="SYSTEM",
            actor_id="system:reporting.subscription",
            command_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            issued_at=issued_at,
        )
        try:
            self._service._execute_command(cmd)
        except Exception:
            # Non-blocking: KPI recording failure should not crash event processing
            pass

    def handle_bill_settled(self, event_data: dict) -> None:
        payload = event_data.get("payload", {})
        total = payload.get("total_amount", 0)
        tips = payload.get("tip_amount", 0)
        if total > 0:
            self._record_kpi(
                kpi_key="REVENUE_TOTAL", kpi_name="Total Revenue (Bill)",
                value=total, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="restaurant",
            )
        if tips > 0:
            self._record_kpi(
                kpi_key="TIPS_COLLECTED", kpi_name="Tips Collected",
                value=tips, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="restaurant",
            )
        self._record_kpi(
            kpi_key="BILLS_SETTLED", kpi_name="Bills Settled",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="restaurant",
        )

    def handle_sale_completed(self, event_data: dict) -> None:
        payload = event_data.get("payload", {})
        net = payload.get("net_amount", 0)
        if net > 0:
            self._record_kpi(
                kpi_key="REVENUE_TOTAL", kpi_name="Total Revenue (Sale)",
                value=net, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="retail",
            )
        self._record_kpi(
            kpi_key="ORDERS_COMPLETED", kpi_name="Sales Completed",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="retail",
        )

    def handle_job_invoiced(self, event_data: dict) -> None:
        payload = event_data.get("payload", {})
        amount = payload.get("amount", 0)
        if amount > 0:
            self._record_kpi(
                kpi_key="REVENUE_TOTAL", kpi_name="Total Revenue (Workshop)",
                value=amount, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="workshop",
            )
        self._record_kpi(
            kpi_key="JOBS_INVOICED", kpi_name="Jobs Invoiced",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="workshop",
        )

    def handle_order_placed(self, event_data: dict) -> None:
        self._record_kpi(
            kpi_key="ORDERS_PLACED", kpi_name="Orders Placed",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="restaurant",
        )

    def handle_job_completed(self, event_data: dict) -> None:
        self._record_kpi(
            kpi_key="JOBS_COMPLETED", kpi_name="Jobs Completed",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="workshop",
        )

    def handle_procurement_received(self, event_data: dict) -> None:
        payload = event_data.get("payload", {})
        lines = payload.get("received_lines", [])
        if lines:
            self._record_kpi(
                kpi_key="STOCK_RECEIVED_LINES", kpi_name="Stock Received Lines",
                value=len(lines), unit="COUNT",
                event_data=event_data, source_engine="procurement",
            )

    def handle_shift_ended(self, event_data: dict) -> None:
        payload = event_data.get("payload", {})
        hours = payload.get("hours_worked", 0)
        if hours > 0:
            self._record_kpi(
                kpi_key="HOURS_WORKED", kpi_name="Hours Worked",
                value=hours, unit="HOURS",
                event_data=event_data, source_engine="hr",
            )
        self._record_kpi(
            kpi_key="SHIFTS_WORKED", kpi_name="Shifts Worked",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="hr",
        )

    def handle_employee_onboarded(self, event_data: dict) -> None:
        self._record_kpi(
            kpi_key="EMPLOYEES_ACTIVE", kpi_name="Employees Onboarded",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="hr",
        )
