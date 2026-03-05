"""
BOS Document Engine — Subscription Handler
==========================================
Engine: documents
Scope:  Listens to engine events and auto-issues documents via
        DocumentIssuanceService. This is the bridge that converts
        business events into customer-facing documents.

Flow:
    Engine Event → handle_{event}() → build render_inputs → issue_*(...)
                                                                  ↓
                                                    doc.{type}.issued.v1

Doctrine:
- Every handler is safe to fail silently (document failure must NOT
  roll back the originating business transaction).
- Handlers enrich payloads with business_info and customer_details
  via resolver stubs — resolvers return empty dicts until implemented.
- All document IDs are generated fresh (uuid4) per issuance.
- actor_type = "SYSTEM" for all auto-generated documents.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.context.actor_context import ActorContext

logger = logging.getLogger("bos.documents.subscriptions")


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION MAP
# event_type → method_name on DocumentSubscriptionHandler
# ══════════════════════════════════════════════════════════════

DOCUMENT_SUBSCRIPTIONS: Dict[str, str] = {
    # Retail
    "retail.sale.completed.v1":          "handle_retail_sale_completed",
    "retail.refund.issued.v1":           "handle_retail_refund_issued",
    "retail.sale.voided.v1":             "handle_retail_sale_voided",

    # Restaurant / Bar / BBQ
    "restaurant.bill.settled.v1":        "handle_restaurant_bill_settled",
    "restaurant.bill.split.v1":          "handle_restaurant_bill_split",
    "restaurant.kitchen.ticket.sent.v1": "handle_kitchen_ticket_sent",

    # Workshop
    "workshop.quote.generated.v1":         "handle_workshop_quote_generated",
    "workshop.project.quote.generated.v1": "handle_workshop_project_quote_generated",
    "workshop.quote.accepted.v1":          "handle_workshop_quote_accepted",
    "workshop.job.assigned.v1":            "handle_workshop_job_assigned",
    "workshop.cutlist.generated.v1":       "handle_workshop_cutlist_generated",
    "workshop.job.completed.v1":           "handle_workshop_job_completed",
    "workshop.job.invoiced.v1":            "handle_workshop_job_invoiced",

    # Hotel — Reservation
    "hotel.reservation.confirmed.v1":    "handle_hotel_reservation_confirmed",
    "hotel.reservation.cancelled.v1":    "handle_hotel_reservation_cancelled",
    "hotel.reservation.no_show.v1":      "handle_hotel_reservation_no_show",
    "hotel.guest.checked_in.v1":         "handle_hotel_guest_checked_in",
    "hotel.guest.checked_out.v1":        "handle_hotel_guest_checked_out",

    # Hotel — Folio
    "hotel.folio.settled.v1":            "handle_hotel_folio_settled",
    "hotel.folio.adjusted.v1":           "handle_hotel_folio_adjusted",

    # Procurement
    "procurement.order.created.v1":      "handle_procurement_order_created",
    "procurement.order.received.v1":     "handle_procurement_order_received",
    "procurement.payment.released.v1":   "handle_procurement_payment_released",

    # Inventory
    "inventory.stock.transferred.v1":    "handle_inventory_stock_transfer",
    "inventory.stock.adjusted.v1":       "handle_inventory_stock_adjusted",

    # Cash
    "cash.withdrawal.recorded.v1":       "handle_cash_withdrawal_recorded",
}


# ══════════════════════════════════════════════════════════════
# RESOLVER STUBS
# These will be implemented properly when business/customer
# profile services are wired in.
# ══════════════════════════════════════════════════════════════

def _resolve_business_info(business_id: str) -> dict:
    """
    Default stub: resolve business name, address, TIN/VAT from business profile.
    Returns empty dict until a real BusinessInfoResolver is injected via
    DocumentSubscriptionHandler(business_info_resolver=...).

    A real resolver should return:
        {
            "business_name":    str,
            "business_address": str,
            "tax_id":           str,   # TIN / VAT registration number
            "phone":            str,
            "email":            str,
        }
    """
    return {}


def _resolve_customer_info(customer_id: str | None) -> dict:
    """
    Default stub: resolve customer name and address from customer profile.
    Returns minimal dict until a real CustomerInfoResolver is injected via
    DocumentSubscriptionHandler(customer_info_resolver=...).

    A real resolver should return:
        {
            "customer_name":    str,
            "customer_address": str,
            "customer_phone":   str,
            "customer_email":   str,
        }
    """
    if not customer_id:
        return {"customer_name": "Walk-in Customer"}
    return {"customer_name": "Customer", "customer_id": customer_id}


def _system_actor_context() -> ActorContext:
    return ActorContext(actor_type="SYSTEM", actor_id="system:documents.subscription")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ══════════════════════════════════════════════════════════════
# HANDLER
# ══════════════════════════════════════════════════════════════

class DocumentSubscriptionHandler:
    """
    Listens to engine events and issues documents automatically.

    Injected with DocumentIssuanceService at startup via
    wire_all_subscriptions().

    Optional resolver callables can be injected to enrich documents with
    real business and customer data:

        handler = DocumentSubscriptionHandler(
            document_service=svc,
            business_info_resolver=lambda biz_id: {...},
            customer_info_resolver=lambda cust_id: {...},
        )

    Resolver signature:
        business_info_resolver(business_id: str) -> dict
            Returns: {business_name, business_address, tax_id, phone, email}

        customer_info_resolver(customer_id: str | None) -> dict
            Returns: {customer_name, customer_address, customer_phone, customer_email}

    If not provided, module-level stubs are used (returning empty/minimal dicts).
    """

    def __init__(
        self,
        document_service: Any,
        *,
        business_info_resolver=None,
        customer_info_resolver=None,
    ):
        self._svc = document_service
        self._resolve_biz = business_info_resolver or _resolve_business_info
        self._resolve_cust = customer_info_resolver or _resolve_customer_info

    # ── helpers ──────────────────────────────────────────────────

    def _issue_receipt(self, *, business_id, branch_id, payload: dict) -> None:
        try:
            self._svc.issue_receipt(
                business_id=uuid.UUID(str(business_id)),
                branch_id=uuid.UUID(str(branch_id)) if branch_id else None,
                document_id=uuid.uuid4(),
                payload=payload,
                actor_context=_system_actor_context(),
                command_id=uuid.uuid4(),
                correlation_id=uuid.uuid4(),
                issued_at=_now(),
            )
        except Exception:
            logger.exception("Failed to auto-issue receipt — business: %s", business_id)

    def _issue_quote(self, *, business_id, branch_id, payload: dict) -> None:
        try:
            self._svc.issue_quote(
                business_id=uuid.UUID(str(business_id)),
                branch_id=uuid.UUID(str(branch_id)) if branch_id else None,
                document_id=uuid.uuid4(),
                payload=payload,
                actor_context=_system_actor_context(),
                command_id=uuid.uuid4(),
                correlation_id=uuid.uuid4(),
                issued_at=_now(),
            )
        except Exception:
            logger.exception("Failed to auto-issue quote — business: %s", business_id)

    def _issue_invoice(self, *, business_id, branch_id, payload: dict) -> None:
        try:
            self._svc.issue_invoice(
                business_id=uuid.UUID(str(business_id)),
                branch_id=uuid.UUID(str(branch_id)) if branch_id else None,
                document_id=uuid.uuid4(),
                payload=payload,
                actor_context=_system_actor_context(),
                command_id=uuid.uuid4(),
                correlation_id=uuid.uuid4(),
                issued_at=_now(),
            )
        except Exception:
            logger.exception("Failed to auto-issue invoice — business: %s", business_id)

    def _issue_doc(self, method_name: str, *, business_id, branch_id, payload: dict) -> None:
        """Generic issuer for document types beyond receipt/quote/invoice."""
        method = getattr(self._svc, method_name, None)
        if method is None:
            logger.warning("DocumentIssuanceService has no method: %s", method_name)
            return
        try:
            method(
                business_id=uuid.UUID(str(business_id)),
                branch_id=uuid.UUID(str(branch_id)) if branch_id else None,
                document_id=uuid.uuid4(),
                payload=payload,
                actor_context=_system_actor_context(),
                command_id=uuid.uuid4(),
                correlation_id=uuid.uuid4(),
                issued_at=_now(),
            )
        except Exception:
            logger.exception("Failed to auto-issue %s — business: %s", method_name, business_id)

    # ── RETAIL ───────────────────────────────────────────────────

    def handle_retail_sale_completed(self, event_data: dict) -> None:
        """
        retail.sale.completed.v1 → SALES_RECEIPT (always)
                                 → INVOICE (if on_account=True)
        """
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        receipt_payload = {
            **biz,
            **customer,
            "sale_id":        p.get("sale_id"),
            "cashier_id":     p.get("actor_id"),
            "date":           p.get("completed_at"),
            "payment_method": p.get("payment_method"),
            "line_items":     p.get("lines", []),
            "subtotal":       p.get("net_amount"),
            "discount_total": p.get("discount_amount", 0),
            "tax_total":      p.get("tax_amount", 0),
            "grand_total":    p.get("total_amount"),
            "currency":       p.get("currency"),
        }
        self._issue_receipt(business_id=business_id, branch_id=branch_id, payload=receipt_payload)

        # If on-account sale, also issue an invoice
        if p.get("on_account"):
            invoice_payload = {
                **biz,
                **customer,
                "sale_id":        p.get("sale_id"),
                "line_items":     p.get("lines", []),
                "subtotal":       p.get("net_amount"),
                "tax_total":      p.get("tax_amount", 0),
                "discount_total": p.get("discount_amount", 0),
                "grand_total":    p.get("total_amount"),
                "currency":       p.get("currency"),
                "payment_terms":  "DUE_ON_RECEIPT",
                "issued_at":      p.get("completed_at"),
            }
            self._issue_invoice(business_id=business_id, branch_id=branch_id, payload=invoice_payload)

    def handle_retail_refund_issued(self, event_data: dict) -> None:
        """retail.refund.issued.v1 → REFUND_NOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        payload = {
            **biz,
            **customer,
            "refund_id":          p.get("refund_id"),
            "original_sale_id":   p.get("original_sale_id"),
            "line_items":         p.get("lines", []),
            "grand_total":        p.get("amount"),
            "currency":           p.get("currency"),
            "reason":             p.get("reason", ""),
            "issued_at":          p.get("refunded_at"),
        }
        self._issue_doc("issue_refund_note", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_retail_sale_voided(self, event_data: dict) -> None:
        """retail.sale.voided.v1 → CREDIT_NOTE (if lines + amount present)"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        lines = p.get("lines", [])
        total = p.get("total_amount", 0)
        if not lines and not total:
            return  # insufficient data for a credit note

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        payload = {
            **biz,
            **customer,
            "sale_id":          p.get("sale_id"),
            "original_ref":     p.get("original_receipt_id"),
            "line_items":       lines,
            "grand_total":      total,
            "currency":         p.get("currency"),
            "reason":           p.get("reason", ""),
            "issued_at":        p.get("voided_at"),
        }
        self._issue_doc("issue_credit_note", business_id=business_id, branch_id=branch_id, payload=payload)

    # ── RESTAURANT / BAR / BBQ ────────────────────────────────────

    def handle_restaurant_bill_settled(self, event_data: dict) -> None:
        """restaurant.bill.settled.v1 → SALES_RECEIPT"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))

        payload = {
            **biz,
            "bill_id":        p.get("bill_id"),
            "table_id":       p.get("table_id"),
            "table_name":     p.get("table_name", ""),
            "covers":         p.get("covers", 0),
            "server_id":      p.get("server_id", ""),
            "line_items":     p.get("order_lines", []),
            "subtotal":       p.get("total_amount", 0),
            "tax_total":      p.get("tax_amount", 0),
            "tip":            p.get("tip_amount", 0),
            "grand_total":    (p.get("total_amount", 0) + p.get("tip_amount", 0)),
            "currency":       p.get("currency"),
            "payment_method": p.get("payment_method"),
            "issued_at":      p.get("settled_at"),
        }
        self._issue_receipt(business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_restaurant_bill_split(self, event_data: dict) -> None:
        """restaurant.bill.split.v1 → SALES_RECEIPT per split party"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        splits = p.get("splits", [])

        for split in splits:
            split_payload = {
                **biz,
                "bill_id":     p.get("bill_id"),
                "split_id":    p.get("split_id"),
                "table_id":    p.get("table_id"),
                "line_items":  split.get("lines", []),
                "grand_total": split.get("amount", 0),
                "currency":    p.get("currency"),
                "payment_method": split.get("payment_method", ""),
                "issued_at":   p.get("split_at"),
            }
            self._issue_receipt(business_id=business_id, branch_id=branch_id, payload=split_payload)

    def handle_kitchen_ticket_sent(self, event_data: dict) -> None:
        """restaurant.kitchen.ticket.sent.v1 → KITCHEN_ORDER_TICKET"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "ticket_id":  p.get("ticket_id"),
            "order_id":   p.get("order_id"),
            "table_id":   p.get("table_id"),
            "table_name": p.get("table_name", ""),
            "station":    p.get("station", ""),
            "priority":   p.get("priority", "NORMAL"),
            "line_items": p.get("items", []),
            "issued_at":  p.get("sent_at"),
        }
        self._issue_doc("issue_kitchen_order_ticket", business_id=business_id, branch_id=branch_id, payload=payload)

    # ── WORKSHOP ──────────────────────────────────────────────────

    def handle_workshop_quote_generated(self, event_data: dict) -> None:
        """workshop.quote.generated.v1 → QUOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        payload = {
            **biz,
            **customer,
            "quote_id":       p.get("quote_id"),
            "job_id":         p.get("job_id"),
            "style_id":       p.get("style_id"),
            "line_items":     p.get("pieces", []),
            "subtotal":       p.get("material_cost", 0),
            "labour_cost":    p.get("labour_cost", 0),
            "discount_total": p.get("discount_amount", 0),
            "tax_total":      p.get("tax_amount", 0),
            "grand_total":    p.get("total_price", 0),
            "currency":       p.get("currency", ""),
            "valid_until":    p.get("valid_until", ""),
            "issued_at":      p.get("generated_at"),
        }
        self._issue_quote(business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_workshop_project_quote_generated(self, event_data: dict) -> None:
        """workshop.project.quote.generated.v1 → QUOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        items = p.get("items", [])
        line_items = [
            {
                "description": f"Item {item.get('item_id', i+1)} — {item.get('style_id', '')}",
                "quantity":    item.get("unit_quantity", 1),
                "unit_price":  item.get("unit_cost", 0),
                "line_total":  item.get("item_cost", 0),
            }
            for i, item in enumerate(items)
        ]

        payload = {
            **biz,
            **customer,
            "project_quote_id": p.get("project_quote_id"),
            "job_id":           p.get("job_id"),
            "line_items":       line_items,
            "grand_total":      p.get("total_cost", 0),
            "currency":         p.get("currency", ""),
            "valid_until":      p.get("valid_until", ""),
            "issued_at":        p.get("generated_at"),
        }
        self._issue_quote(business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_workshop_quote_accepted(self, event_data: dict) -> None:
        """workshop.quote.accepted.v1 → PROFORMA_INVOICE (deposit request)"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        payload = {
            **biz,
            **customer,
            "quote_id":    p.get("quote_id"),
            "job_id":      p.get("job_id"),
            "line_items":  p.get("lines", []),
            "grand_total": p.get("total_price", 0),
            "currency":    p.get("currency", ""),
            "valid_until": p.get("valid_until", ""),
            "issued_at":   p.get("accepted_at"),
        }
        self._issue_doc("issue_proforma_invoice", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_workshop_job_assigned(self, event_data: dict) -> None:
        """workshop.job.assigned.v1 → WORK_ORDER"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        customer = self._resolve_cust(p.get("customer_id"))

        payload = {
            **customer,
            "job_id":               p.get("job_id"),
            "technician_id":        p.get("technician_id"),
            "job_description":      p.get("job_description", ""),
            "priority":             p.get("priority", "NORMAL"),
            "estimated_completion": p.get("estimated_completion", ""),
            "line_items":           p.get("parts_required", []),
            "issued_at":            p.get("assigned_at"),
        }
        self._issue_doc("issue_work_order", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_workshop_cutlist_generated(self, event_data: dict) -> None:
        """workshop.cutlist.generated.v1 → CUTTING_LIST"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "cutlist_id":  p.get("cutlist_id"),
            "job_id":      p.get("job_id"),
            "style_id":    p.get("style_id"),
            "line_items":  p.get("pieces", []),
            "issued_at":   p.get("generated_at"),
        }
        self._issue_doc("issue_cutting_list", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_workshop_job_completed(self, event_data: dict) -> None:
        """workshop.job.completed.v1 → COMPLETION_CERTIFICATE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        customer = self._resolve_cust(p.get("customer_id"))

        payload = {
            **customer,
            "job_id":      p.get("job_id"),
            "line_items":  [{"description": "Job completed as per specifications"}],
            "issued_at":   p.get("completed_at"),
        }
        self._issue_doc("issue_completion_certificate", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_workshop_job_invoiced(self, event_data: dict) -> None:
        """workshop.job.invoiced.v1 → INVOICE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        customer = self._resolve_cust(p.get("customer_id"))

        parts = p.get("parts_used", [])
        line_items = []
        if p.get("labour_total", 0):
            line_items.append({
                "description": f"Labour — {p.get('labour_hours', 0)} hrs",
                "quantity":    p.get("labour_hours", 0),
                "unit_price":  p.get("labour_rate", 0),
                "line_total":  p.get("labour_total", 0),
            })
        for part in parts:
            line_items.append({
                "description": part.get("name", part.get("material_id", "")),
                "quantity":    part.get("qty", part.get("quantity", 0)),
                "unit_price":  part.get("unit_price", 0),
                "line_total":  part.get("line_total", 0),
            })

        payload = {
            **biz,
            **customer,
            "job_id":         p.get("job_id"),
            "invoice_id":     p.get("invoice_id"),
            "line_items":     line_items,
            "subtotal":       p.get("amount", 0),
            "tax_total":      p.get("tax_amount", 0),
            "discount_total": p.get("discount_amount", 0),
            "grand_total":    p.get("amount", 0),
            "currency":       p.get("currency"),
            "payment_terms":  p.get("payment_terms", "DUE_ON_RECEIPT"),
            "due_date":       p.get("due_date", ""),
            "issued_at":      p.get("invoiced_at"),
        }
        self._issue_invoice(business_id=business_id, branch_id=branch_id, payload=payload)

    # ── HOTEL — RESERVATION ───────────────────────────────────────

    def handle_hotel_reservation_confirmed(self, event_data: dict) -> None:
        """hotel.reservation.confirmed.v1 → RESERVATION_CONFIRMATION"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))
        # Resolve guest from guest_id if name not directly in payload
        guest_id = p.get("guest_id")
        guest_info = self._resolve_cust(guest_id) if guest_id else {}
        guest_name = p.get("guest_name", "") or guest_info.get("customer_name", "")

        nights = p.get("nights", 0)
        nightly_rate = p.get("nightly_rate", 0)
        total_amount = p.get("total_amount", 0) or (nights * nightly_rate)

        line_items = []
        if nights and nightly_rate:
            line_items.append({
                "room_type":    p.get("room_type", "Room"),
                "rate_plan":    p.get("rate_plan", ""),
                "nightly_rate": nightly_rate,
                "nights":       nights,
                "total":        total_amount,
            })

        payload = {
            **biz,
            "reservation_id":  p.get("reservation_id"),
            "guest_name":      guest_name,
            "guest_email":     p.get("guest_email", ""),
            "guest_phone":     p.get("guest_phone", ""),
            "arrival_date":    p.get("arrival_date", ""),
            "departure_date":  p.get("departure_date", ""),
            "nights":          nights,
            "line_items":      line_items,
            "total_amount":    total_amount,
            "deposit_paid":    p.get("deposit_paid", 0),
            "deposit_due":     p.get("deposit_due", 0),
            "currency":        p.get("currency", ""),
            "confirmed_by":    p.get("confirmed_by"),
            "issued_at":       p.get("confirmed_at"),
        }
        self._issue_doc("issue_reservation_confirmation", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_hotel_reservation_cancelled(self, event_data: dict) -> None:
        """hotel.reservation.cancelled.v1 → CANCELLATION_NOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "reservation_id":      p.get("reservation_id"),
            "cancellation_charge": p.get("cancellation_charge", 0),
            "refund_amount":       p.get("refund_amount", 0),
            "reason":              p.get("reason", ""),
            "line_items":          [],
            "issued_at":           p.get("cancelled_at"),
        }
        self._issue_doc("issue_cancellation_note", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_hotel_reservation_no_show(self, event_data: dict) -> None:
        """hotel.reservation.no_show.v1 → CANCELLATION_NOTE (if charge applied)"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        charge = p.get("no_show_charge", 0)
        if not charge:
            return  # no charge, no document needed

        payload = {
            "reservation_id":      p.get("reservation_id"),
            "cancellation_charge": charge,
            "refund_amount":       0,
            "reason":              "NO_SHOW",
            "line_items":          [],
            "issued_at":           p.get("recorded_at"),
        }
        self._issue_doc("issue_cancellation_note", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_hotel_guest_checked_in(self, event_data: dict) -> None:
        """hotel.guest.checked_in.v1 → REGISTRATION_CARD"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))

        payload = {
            **biz,
            "reservation_id": p.get("reservation_id"),
            "folio_id":       p.get("folio_id"),
            "room_id":        p.get("room_id"),
            "room_number":    p.get("room_number", ""),
            "line_items":     [],
            "issued_at":      p.get("checked_in_at"),
        }
        self._issue_doc("issue_registration_card", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_hotel_guest_checked_out(self, event_data: dict) -> None:
        """
        hotel.guest.checked_out.v1 → INVOICE (company/corporate billing only)

        Standard individual checkout bill is generated by handle_hotel_folio_settled.
        This handler only fires an INVOICE when company_id is present in the payload,
        indicating the stay should be invoiced to a corporate account rather than
        settled by the guest directly.
        """
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        # Only issue invoice for company/corporate billing
        company_id = p.get("company_id")
        if not company_id:
            return

        biz = self._resolve_biz(str(business_id))
        company_info = self._resolve_cust(company_id)

        folio_total = p.get("folio_total", 0)
        line_items = []
        if folio_total:
            line_items.append({
                "description": f"Hotel stay — Folio {p.get('folio_id', '')}",
                "qty":         1,
                "unit_price":  folio_total,
                "line_total":  folio_total,
            })

        payload = {
            **biz,
            **company_info,
            "reservation_id": p.get("reservation_id"),
            "folio_id":       p.get("folio_id"),
            "line_items":     line_items,
            "subtotal":       folio_total,
            "tax_total":      0,
            "grand_total":    folio_total,
            "payment_terms":  "NET_30",
            "issued_at":      p.get("checked_out_at"),
        }
        self._issue_invoice(business_id=business_id, branch_id=branch_id, payload=payload)

    # ── HOTEL — FOLIO ─────────────────────────────────────────────

    def handle_hotel_folio_settled(self, event_data: dict) -> None:
        """hotel.folio.settled.v1 → FOLIO (guest bill)"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))

        payload = {
            **biz,
            "folio_id":       p.get("folio_id"),
            "guest_name":     p.get("guest_name", ""),
            "room_number":    p.get("room_number", ""),
            "arrival_date":   p.get("arrival_date", ""),
            "departure_date": p.get("departure_date", ""),
            "nights":         p.get("nights", 0),
            "line_items":     p.get("charge_lines", []),
            "subtotal":       p.get("total_charges", 0),
            "tax_total":      p.get("tax_amount", 0),
            "grand_total":    p.get("total_charges", 0),
            "currency":       p.get("currency"),
            "payment_method": p.get("payment_method", ""),
            "issued_at":      p.get("settled_at"),
        }
        self._issue_doc("issue_folio", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_hotel_folio_adjusted(self, event_data: dict) -> None:
        """hotel.folio.adjusted.v1 → CREDIT_NOTE or DEBIT_NOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        adj_type = p.get("adjustment_type", "")
        payload = {
            "folio_id":      p.get("folio_id"),
            "adjustment_id": p.get("adjustment_id"),
            "original_ref":  p.get("folio_id"),
            "line_items":    [{"description": p.get("reason", "Adjustment"), "amount": p.get("amount", 0)}],
            "grand_total":   p.get("amount", 0),
            "reason":        p.get("reason", ""),
            "issued_at":     p.get("adjusted_at"),
        }
        if adj_type == "CREDIT":
            self._issue_doc("issue_credit_note", business_id=business_id, branch_id=branch_id, payload=payload)
        elif adj_type == "DEBIT":
            self._issue_doc("issue_debit_note", business_id=business_id, branch_id=branch_id, payload=payload)

    # ── PROCUREMENT ───────────────────────────────────────────────

    def handle_procurement_order_created(self, event_data: dict) -> None:
        """procurement.order.created.v1 → PURCHASE_ORDER"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))

        payload = {
            **biz,
            "po_id":          p.get("po_id"),
            "supplier_id":    p.get("supplier_id"),
            "supplier_name":  p.get("supplier_name", ""),
            "delivery_date":  p.get("delivery_date", ""),
            "line_items":     p.get("lines", []),
            "subtotal":       p.get("total_amount", 0),
            "tax_total":      p.get("tax_amount", 0),
            "grand_total":    p.get("total_amount", 0),
            "currency":       p.get("currency", ""),
            "payment_terms":  p.get("payment_terms", ""),
            "issued_at":      p.get("created_at"),
        }
        self._issue_doc("issue_purchase_order", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_procurement_order_received(self, event_data: dict) -> None:
        """procurement.order.received.v1 → GOODS_RECEIPT_NOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "po_id":          p.get("po_id"),
            "supplier_id":    p.get("supplier_id"),
            "supplier_name":  p.get("supplier_name", ""),
            "po_ref":         p.get("po_id"),
            "line_items":     p.get("received_lines", []),
            "received_by":    p.get("received_by", p.get("actor_id", "")),
            "issued_at":      p.get("received_at"),
        }
        self._issue_doc("issue_goods_receipt_note", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_procurement_payment_released(self, event_data: dict) -> None:
        """procurement.payment.released.v1 → PAYMENT_VOUCHER"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "payment_id":     p.get("payment_id"),
            "payee_name":     p.get("supplier_name", ""),
            "line_items":     [{"description": p.get("description", "Payment"), "amount": p.get("amount", 0)}],
            "grand_total":    p.get("amount", 0),
            "currency":       p.get("currency", ""),
            "payment_method": p.get("payment_method", ""),
            "approved_by":    p.get("approved_by", p.get("actor_id", "")),
            "issued_at":      p.get("released_at"),
        }
        self._issue_doc("issue_payment_voucher", business_id=business_id, branch_id=branch_id, payload=payload)

    # ── INVENTORY ─────────────────────────────────────────────────

    def handle_inventory_stock_transfer(self, event_data: dict) -> None:
        """inventory.stock.transfer.v1 → STOCK_TRANSFER_NOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "transfer_id":    p.get("transfer_id"),
            "from_location":  p.get("from_location_id", ""),
            "to_location":    p.get("to_location_id", ""),
            "line_items":     p.get("items", []),
            "transferred_by": p.get("actor_id", ""),
            "issued_at":      p.get("transferred_at"),
        }
        self._issue_doc("issue_stock_transfer_note", business_id=business_id, branch_id=branch_id, payload=payload)

    def handle_inventory_stock_adjusted(self, event_data: dict) -> None:
        """inventory.stock.adjusted.v1 → STOCK_ADJUSTMENT_NOTE"""
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        payload = {
            "adjustment_id":   p.get("adjustment_id"),
            "adjustment_type": p.get("adjustment_type", ""),
            "location":        p.get("location_id", ""),
            "line_items":      p.get("items", []),
            "reason":          p.get("reason", ""),
            "approved_by":     p.get("actor_id", ""),
            "issued_at":       p.get("adjusted_at"),
        }
        self._issue_doc("issue_stock_adjustment_note", business_id=business_id, branch_id=branch_id, payload=payload)

    # ── CASH ──────────────────────────────────────────────────────

    def handle_cash_withdrawal_recorded(self, event_data: dict) -> None:
        """
        cash.withdrawal.recorded.v1 → PETTY_CASH_VOUCHER

        Fires whenever a cash withdrawal is recorded against a drawer session.
        Covers both petty cash disbursements (expense_payout) and authorised
        withdrawals (bank/safe transfers).

        The document type is PETTY_CASH_VOUCHER for both cases — the admin
        can configure separate templates per reason code if needed.
        """
        p = event_data.get("payload", {})
        business_id = p.get("business_id")
        branch_id = p.get("branch_id")
        if not business_id:
            return

        biz = self._resolve_biz(str(business_id))

        payload = {
            **biz,
            "withdrawal_id": p.get("withdrawal_id"),
            "session_id":    p.get("session_id"),
            "drawer_id":     p.get("drawer_id"),
            "amount":        p.get("amount", 0),
            "currency":      p.get("currency", ""),
            "reason":        p.get("reason", ""),
            "approved_by":   p.get("actor_id", ""),
            "line_items":    [],
            "grand_total":   p.get("amount", 0),
            "issued_at":     p.get("recorded_at"),
        }
        self._issue_doc("issue_petty_cash_voucher", business_id=business_id, branch_id=branch_id, payload=payload)
