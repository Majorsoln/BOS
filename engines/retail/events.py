"""
BOS Retail Engine — Event Types and Payload Builders
======================================================
Engine: Retail (Point-of-Sale)
Authority: BOS Doctrine — Deterministic, Event-Sourced

Retail owns the sale lifecycle: open sale → add lines →
apply discounts → complete → void/refund.
Emits events consumed by inventory (stock issue),
cash (payment record), and accounting (journal post).
"""

from __future__ import annotations

from core.commands.base import Command


# ══════════════════════════════════════════════════════════════
# EVENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

RETAIL_SALE_OPENED_V1 = "retail.sale.opened.v1"
RETAIL_SALE_LINE_ADDED_V1 = "retail.sale.line_added.v1"
RETAIL_SALE_LINE_REMOVED_V1 = "retail.sale.line_removed.v1"
RETAIL_SALE_DISCOUNT_APPLIED_V1 = "retail.sale.discount_applied.v1"
RETAIL_SALE_COMPLETED_V1 = "retail.sale.completed.v1"
RETAIL_SALE_VOIDED_V1 = "retail.sale.voided.v1"
RETAIL_REFUND_ISSUED_V1 = "retail.refund.issued.v1"

RETAIL_EVENT_TYPES = (
    RETAIL_SALE_OPENED_V1,
    RETAIL_SALE_LINE_ADDED_V1,
    RETAIL_SALE_LINE_REMOVED_V1,
    RETAIL_SALE_DISCOUNT_APPLIED_V1,
    RETAIL_SALE_COMPLETED_V1,
    RETAIL_SALE_VOIDED_V1,
    RETAIL_REFUND_ISSUED_V1,
)


# ══════════════════════════════════════════════════════════════
# COMMAND → EVENT MAPPING
# ══════════════════════════════════════════════════════════════

COMMAND_TO_EVENT_TYPE = {
    "retail.sale.open.request": RETAIL_SALE_OPENED_V1,
    "retail.sale.add_line.request": RETAIL_SALE_LINE_ADDED_V1,
    "retail.sale.remove_line.request": RETAIL_SALE_LINE_REMOVED_V1,
    "retail.sale.apply_discount.request": RETAIL_SALE_DISCOUNT_APPLIED_V1,
    "retail.sale.complete.request": RETAIL_SALE_COMPLETED_V1,
    "retail.sale.void.request": RETAIL_SALE_VOIDED_V1,
    "retail.refund.issue.request": RETAIL_REFUND_ISSUED_V1,
}


def resolve_retail_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_retail_event_types(event_type_registry) -> None:
    for event_type in sorted(RETAIL_EVENT_TYPES):
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


def build_sale_opened_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "sale_id": command.payload["sale_id"],
        "session_id": command.payload.get("session_id"),
        "drawer_id": command.payload.get("drawer_id"),
        "customer_id": command.payload.get("customer_id"),
        "currency": command.payload["currency"],
        "opened_at": command.issued_at,
    })
    return payload


def build_sale_line_added_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "sale_id": command.payload["sale_id"],
        "line_id": command.payload["line_id"],
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "item_name": command.payload["item_name"],
        "quantity": command.payload["quantity"],
        "unit_price": command.payload["unit_price"],
        "line_total": command.payload["quantity"] * command.payload["unit_price"],
        "tax_rate": command.payload.get("tax_rate", 0),
        "added_at": command.issued_at,
    })
    return payload


def build_sale_line_removed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "sale_id": command.payload["sale_id"],
        "line_id": command.payload["line_id"],
        "reason": command.payload.get("reason", "CUSTOMER_REQUEST"),
        "removed_at": command.issued_at,
    })
    return payload


def build_sale_discount_applied_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "sale_id": command.payload["sale_id"],
        "discount_type": command.payload["discount_type"],
        "discount_value": command.payload["discount_value"],
        "reason": command.payload.get("reason", ""),
        "applied_at": command.issued_at,
    })
    return payload


def build_sale_completed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "sale_id": command.payload["sale_id"],
        "total_amount": command.payload["total_amount"],
        "tax_amount": command.payload.get("tax_amount", 0),
        "discount_amount": command.payload.get("discount_amount", 0),
        "net_amount": command.payload["net_amount"],
        "currency": command.payload["currency"],
        "payment_method": command.payload["payment_method"],
        "lines": command.payload["lines"],
        "completed_at": command.issued_at,
    })
    return payload


def build_sale_voided_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "sale_id": command.payload["sale_id"],
        "reason": command.payload["reason"],
        "voided_at": command.issued_at,
    })
    return payload


def build_refund_issued_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "refund_id": command.payload["refund_id"],
        "original_sale_id": command.payload["original_sale_id"],
        "amount": command.payload["amount"],
        "currency": command.payload["currency"],
        "reason": command.payload["reason"],
        "lines": command.payload.get("lines", []),
        "refunded_at": command.issued_at,
    })
    return payload
