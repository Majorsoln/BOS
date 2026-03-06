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
    "restaurant.bill.settled.v1":      "handle_bill_settled",
    "retail.sale.completed.v1":        "handle_sale_completed",
    "retail.refund.issued.v1":         "handle_retail_refund",
    "workshop.job.invoiced.v1":        "handle_job_invoiced",
    "hotel.folio.settled.v1":          "handle_hotel_folio_settled",
    # Operational events
    "restaurant.order.placed.v1":      "handle_order_placed",
    "restaurant.order.cancelled.v1":   "handle_order_cancelled",
    "workshop.job.completed.v1":       "handle_job_completed",
    "procurement.order.received.v1":   "handle_procurement_received",
    # Hotel operational events
    "hotel.reservation.confirmed.v1":  "handle_reservation_confirmed",
    "hotel.guest.checked_in.v1":       "handle_guest_checked_in",
    "hotel.guest.checked_out.v1":      "handle_guest_checked_out",
    # Inventory events
    "inventory.stock.adjusted.v1":     "handle_stock_adjusted",
    "inventory.stock.transferred.v1":  "handle_stock_transferred",
    # HR events
    "hr.shift.ended.v1":               "handle_shift_ended",
    "hr.employee.onboarded.v1":        "handle_employee_onboarded",
    # Cash session events (RP-02)
    "cash.session.closed.v1":          "handle_cash_session_closed",
    # Workshop quote pipeline events (RP-11)
    "workshop.quote.generated.v1":     "handle_workshop_quote_generated",
    "workshop.quote.accepted.v1":      "handle_workshop_quote_accepted",
    "workshop.quote.rejected.v1":      "handle_workshop_quote_rejected",
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
        payment_method = payload.get("payment_method", "")
        dim = {"payment_method": payment_method} if payment_method else {}
        if total > 0:
            self._record_kpi(
                kpi_key="REVENUE_TOTAL", kpi_name="Total Revenue (Bill)",
                value=total, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="restaurant",
                dimension=dim,
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
        # Use total_amount (gross) for revenue KPI; net_amount fallback
        total = payload.get("total_amount", 0) or payload.get("net_amount", 0)
        payment_method = payload.get("payment_method", "")
        dim = {"payment_method": payment_method} if payment_method else {}
        if total > 0:
            self._record_kpi(
                kpi_key="REVENUE_TOTAL", kpi_name="Total Revenue (Sale)",
                value=total, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="retail",
                dimension=dim,
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

    def handle_retail_refund(self, event_data: dict) -> None:
        """
        Record refund as negative revenue KPI.
        Event source: retail.refund.issued.v1
        """
        payload = event_data.get("payload", {})
        amount = payload.get("amount", 0)
        if amount > 0:
            self._record_kpi(
                kpi_key="REFUNDS_ISSUED", kpi_name="Refunds Issued (Amount)",
                value=amount, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="retail",
            )
        self._record_kpi(
            kpi_key="REFUND_COUNT", kpi_name="Refunds Issued (Count)",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="retail",
        )

    def handle_order_cancelled(self, event_data: dict) -> None:
        """
        Record cancelled/voided restaurant orders for waste/void reporting.
        Event source: restaurant.order.cancelled.v1
        """
        self._record_kpi(
            kpi_key="ORDERS_CANCELLED", kpi_name="Orders Cancelled",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="restaurant",
        )

    def handle_hotel_folio_settled(self, event_data: dict) -> None:
        """
        Record hotel revenue KPIs: total charges, room nights, ADR.
        Event source: hotel.folio.settled.v1
        """
        payload = event_data.get("payload", {})
        total_charges = payload.get("total_charges", 0)
        nights = payload.get("nights", 0)
        payment_method = payload.get("payment_method", "")
        dim = {"payment_method": payment_method} if payment_method else {}

        if total_charges > 0:
            self._record_kpi(
                kpi_key="HOTEL_REVENUE_TOTAL", kpi_name="Hotel Revenue Total",
                value=total_charges, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="hotel_folio",
                dimension=dim,
            )
        if nights > 0:
            self._record_kpi(
                kpi_key="HOTEL_ROOM_NIGHTS", kpi_name="Hotel Room Nights",
                value=nights, unit="COUNT",
                event_data=event_data, source_engine="hotel_folio",
            )
            # ADR = total_charges / nights (stored in minor currency)
            if total_charges > 0:
                adr = total_charges // nights
                self._record_kpi(
                    kpi_key="HOTEL_ADR", kpi_name="Hotel Average Daily Rate",
                    value=adr, unit="MINOR_CURRENCY",
                    event_data=event_data, source_engine="hotel_folio",
                )
        self._record_kpi(
            kpi_key="HOTEL_CHECKOUTS", kpi_name="Hotel Checkouts",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="hotel_folio",
        )

    def handle_reservation_confirmed(self, event_data: dict) -> None:
        """
        Record confirmed reservations count.
        Event source: hotel.reservation.confirmed.v1
        """
        self._record_kpi(
            kpi_key="RESERVATIONS_CONFIRMED", kpi_name="Reservations Confirmed",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="hotel_reservation",
        )

    def handle_guest_checked_in(self, event_data: dict) -> None:
        """
        Record guest check-ins.
        Event source: hotel.guest.checked_in.v1
        """
        self._record_kpi(
            kpi_key="GUESTS_CHECKED_IN", kpi_name="Guests Checked In",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="hotel_reservation",
        )

    def handle_guest_checked_out(self, event_data: dict) -> None:
        """
        Record guest check-outs.
        Event source: hotel.guest.checked_out.v1
        """
        self._record_kpi(
            kpi_key="GUESTS_CHECKED_OUT", kpi_name="Guests Checked Out",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="hotel_reservation",
        )

    def handle_stock_adjusted(self, event_data: dict) -> None:
        """
        Record stock adjustment events for inventory KPIs.
        Tracks both adjustment count and quantity delta (when available).
        Event source: inventory.stock.adjusted.v1
        """
        payload = event_data.get("payload", {})
        self._record_kpi(
            kpi_key="STOCK_ADJUSTMENTS", kpi_name="Stock Adjustments",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="inventory",
        )
        items = payload.get("items", [])
        qty_delta = sum(abs(int(item.get("quantity_delta", item.get("quantity", 0)))) for item in items)
        if qty_delta > 0:
            self._record_kpi(
                kpi_key="STOCK_ADJUSTED_UNITS", kpi_name="Stock Adjusted Units",
                value=qty_delta, unit="COUNT",
                event_data=event_data, source_engine="inventory",
            )

    def handle_stock_transferred(self, event_data: dict) -> None:
        """
        Record stock transfer events for inventory KPIs.
        Tracks transfer count and total units moved.
        Event source: inventory.stock.transferred.v1
        """
        payload = event_data.get("payload", {})
        self._record_kpi(
            kpi_key="STOCK_TRANSFERS", kpi_name="Stock Transfers",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="inventory",
        )
        items = payload.get("items", [])
        qty_moved = sum(int(item.get("quantity", 0)) for item in items)
        if qty_moved > 0:
            self._record_kpi(
                kpi_key="STOCK_TRANSFERRED_UNITS", kpi_name="Stock Transferred Units",
                value=qty_moved, unit="COUNT",
                event_data=event_data, source_engine="inventory",
            )

    def handle_cash_session_closed(self, event_data: dict) -> None:
        """
        When a cash drawer session is closed, record:
        - CASH_SESSIONS_CLOSED: count of sessions closed (always 1)
        - CASH_SESSION_VARIANCE: absolute variance (over/short) in minor units.
          Zero-variance closings contribute 0 to this metric.

        Event source: cash.session.closed.v1
        Payload fields used: business_id, branch_id, session_id,
                             closing_balance, expected_balance, variance
        """
        payload = event_data.get("payload", {})
        self._record_kpi(
            kpi_key="CASH_SESSIONS_CLOSED", kpi_name="Cash Sessions Closed",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="cash",
        )
        variance = int(payload.get("variance", payload.get("difference", 0)))
        abs_variance = abs(variance)
        if abs_variance > 0:
            self._record_kpi(
                kpi_key="CASH_SESSION_VARIANCE", kpi_name="Cash Session Variance",
                value=abs_variance, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="cash",
            )

    def handle_workshop_quote_generated(self, event_data: dict) -> None:
        """
        When a workshop quote is generated, record:
        - QUOTES_GENERATED: count (always 1)
        - QUOTE_VALUE: total_price of the quote in minor currency units.

        Event source: workshop.quote.generated.v1
        Payload fields used: business_id, branch_id, quote_id, total_price
        """
        payload = event_data.get("payload", {})
        self._record_kpi(
            kpi_key="QUOTES_GENERATED", kpi_name="Workshop Quotes Generated",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="workshop",
        )
        total_price = int(payload.get("total_price", 0))
        if total_price > 0:
            self._record_kpi(
                kpi_key="QUOTE_VALUE", kpi_name="Workshop Quote Value",
                value=total_price, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="workshop",
            )

    def handle_workshop_quote_accepted(self, event_data: dict) -> None:
        """
        When a customer accepts a workshop quote, record:
        - QUOTES_ACCEPTED: count (always 1)
        - QUOTE_ACCEPTED_VALUE: total_price of the accepted quote.

        This feeds the quote conversion rate: QUOTES_ACCEPTED / QUOTES_GENERATED.

        Event source: workshop.quote.accepted.v1
        Payload fields used: business_id, branch_id, quote_id, total_price
        """
        payload = event_data.get("payload", {})
        self._record_kpi(
            kpi_key="QUOTES_ACCEPTED", kpi_name="Workshop Quotes Accepted",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="workshop",
        )
        total_price = int(payload.get("total_price", 0))
        if total_price > 0:
            self._record_kpi(
                kpi_key="QUOTE_ACCEPTED_VALUE", kpi_name="Workshop Quote Accepted Value",
                value=total_price, unit="MINOR_CURRENCY",
                event_data=event_data, source_engine="workshop",
            )

    def handle_workshop_quote_rejected(self, event_data: dict) -> None:
        """
        When a customer rejects a workshop quote, record:
        - QUOTES_REJECTED: count (always 1)

        Event source: workshop.quote.rejected.v1
        Payload fields used: business_id, branch_id, quote_id
        """
        self._record_kpi(
            kpi_key="QUOTES_REJECTED", kpi_name="Workshop Quotes Rejected",
            value=1, unit="COUNT",
            event_data=event_data, source_engine="workshop",
        )
