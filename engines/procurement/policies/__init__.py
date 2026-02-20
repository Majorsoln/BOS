"""
BOS Procurement Engine — Policies
====================================
Engine-specific validation policies for procurement operations.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def order_must_be_pending_for_approval_policy(
    command: Command,
    order_lookup=None,
) -> Optional[RejectionReason]:
    """Only pending orders can be approved."""
    if order_lookup is None:
        return None

    if command.command_type != "procurement.order.approve.request":
        return None

    order_id = command.payload.get("order_id")
    order = order_lookup(order_id)

    if order is None:
        return RejectionReason(
            code="ORDER_NOT_FOUND",
            message=f"Purchase order '{order_id}' not found.",
            policy_name="order_must_be_pending_for_approval_policy",
        )

    if order.get("status") != "PENDING":
        return RejectionReason(
            code="ORDER_NOT_PENDING",
            message=(
                f"Order '{order_id}' is {order.get('status', 'UNKNOWN')}. "
                f"Only pending orders can be approved."
            ),
            policy_name="order_must_be_pending_for_approval_policy",
        )

    return None


def order_must_be_approved_for_receipt_policy(
    command: Command,
    order_lookup=None,
) -> Optional[RejectionReason]:
    """Only approved orders can receive goods."""
    if order_lookup is None:
        return None

    if command.command_type != "procurement.order.receive.request":
        return None

    order_id = command.payload.get("order_id")
    order = order_lookup(order_id)

    if order is None:
        return RejectionReason(
            code="ORDER_NOT_FOUND",
            message=f"Purchase order '{order_id}' not found.",
            policy_name="order_must_be_approved_for_receipt_policy",
        )

    if order.get("status") != "APPROVED":
        return RejectionReason(
            code="ORDER_NOT_APPROVED",
            message=(
                f"Order '{order_id}' is {order.get('status', 'UNKNOWN')}. "
                f"Only approved orders can receive goods."
            ),
            policy_name="order_must_be_approved_for_receipt_policy",
        )

    return None


def invoice_amount_must_match_policy(
    command: Command,
    order_lookup=None,
    tolerance_percent: int = 5,
) -> Optional[RejectionReason]:
    """Invoice amount must be within tolerance of PO total."""
    if order_lookup is None:
        return None

    if command.command_type != "procurement.invoice.match.request":
        return None

    order_id = command.payload.get("order_id")
    order = order_lookup(order_id)

    if order is None:
        return RejectionReason(
            code="ORDER_NOT_FOUND",
            message=f"Purchase order '{order_id}' not found.",
            policy_name="invoice_amount_must_match_policy",
        )

    invoice_amount = command.payload.get("invoice_amount", 0)
    po_amount = order.get("total_amount", 0)
    max_allowed = po_amount + (po_amount * tolerance_percent // 100)

    if invoice_amount > max_allowed:
        return RejectionReason(
            code="INVOICE_EXCEEDS_PO",
            message=(
                f"Invoice amount ({invoice_amount}) exceeds "
                f"PO total ({po_amount}) by more than {tolerance_percent}%."
            ),
            policy_name="invoice_amount_must_match_policy",
        )

    return None
