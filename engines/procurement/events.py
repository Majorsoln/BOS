"""
BOS Procurement Engine — Event Types and Payload Builders
===========================================================
Engine: Procurement (Purchase Cycle)
Authority: BOS Doctrine — Deterministic, Event-Sourced

Procurement owns: PO creation → supplier approval →
goods receipt → invoice matching.
Emits events consumed by inventory (stock receive)
and accounting (obligation create / journal post).
"""

from __future__ import annotations

from core.commands.base import Command


# ══════════════════════════════════════════════════════════════
# EVENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

PROCUREMENT_ORDER_CREATED_V1 = "procurement.order.created.v1"
PROCUREMENT_ORDER_APPROVED_V1 = "procurement.order.approved.v1"
PROCUREMENT_ORDER_RECEIVED_V1 = "procurement.order.received.v1"
PROCUREMENT_ORDER_CANCELLED_V1 = "procurement.order.cancelled.v1"
PROCUREMENT_INVOICE_MATCHED_V1 = "procurement.invoice.matched.v1"

PROCUREMENT_EVENT_TYPES = (
    PROCUREMENT_ORDER_CREATED_V1,
    PROCUREMENT_ORDER_APPROVED_V1,
    PROCUREMENT_ORDER_RECEIVED_V1,
    PROCUREMENT_ORDER_CANCELLED_V1,
    PROCUREMENT_INVOICE_MATCHED_V1,
)


# ══════════════════════════════════════════════════════════════
# COMMAND → EVENT MAPPING
# ══════════════════════════════════════════════════════════════

COMMAND_TO_EVENT_TYPE = {
    "procurement.order.create.request": PROCUREMENT_ORDER_CREATED_V1,
    "procurement.order.approve.request": PROCUREMENT_ORDER_APPROVED_V1,
    "procurement.order.receive.request": PROCUREMENT_ORDER_RECEIVED_V1,
    "procurement.order.cancel.request": PROCUREMENT_ORDER_CANCELLED_V1,
    "procurement.invoice.match.request": PROCUREMENT_INVOICE_MATCHED_V1,
}


def resolve_procurement_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_procurement_event_types(event_type_registry) -> None:
    for event_type in sorted(PROCUREMENT_EVENT_TYPES):
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


def build_order_created_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "supplier_id": command.payload["supplier_id"],
        "supplier_name": command.payload["supplier_name"],
        "lines": command.payload["lines"],
        "total_amount": command.payload["total_amount"],
        "currency": command.payload["currency"],
        "expected_delivery": command.payload.get("expected_delivery"),
        "created_at": command.issued_at,
    })
    return payload


def build_order_approved_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "approved_by": command.actor_id,
        "approved_at": command.issued_at,
    })
    return payload


def build_order_received_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "received_lines": command.payload["received_lines"],
        "location_id": command.payload["location_id"],
        "location_name": command.payload["location_name"],
        "received_by": command.actor_id,
        "received_at": command.issued_at,
    })
    return payload


def build_order_cancelled_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "reason": command.payload["reason"],
        "cancelled_at": command.issued_at,
    })
    return payload


def build_invoice_matched_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "invoice_id": command.payload["invoice_id"],
        "order_id": command.payload["order_id"],
        "invoice_amount": command.payload["invoice_amount"],
        "currency": command.payload["currency"],
        "matched_at": command.issued_at,
    })
    return payload
