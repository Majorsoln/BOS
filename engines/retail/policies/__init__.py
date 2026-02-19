"""
BOS Retail Engine — Policies
===============================
Engine-specific validation policies for retail operations.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def sale_must_be_open_policy(
    command: Command,
    sale_lookup=None,
) -> Optional[RejectionReason]:
    """
    Reject add_line / remove_line / apply_discount / complete
    if the sale is not in OPEN status.
    """
    if sale_lookup is None:
        return None

    guarded_types = (
        "retail.sale.add_line.request",
        "retail.sale.remove_line.request",
        "retail.sale.apply_discount.request",
        "retail.sale.complete.request",
    )
    if command.command_type not in guarded_types:
        return None

    sale_id = command.payload.get("sale_id")
    sale = sale_lookup(sale_id)

    if sale is None:
        return RejectionReason(
            code="SALE_NOT_FOUND",
            message=f"Sale '{sale_id}' not found.",
            policy_name="sale_must_be_open_policy",
        )

    if sale.get("status") != "OPEN":
        return RejectionReason(
            code="SALE_NOT_OPEN",
            message=(
                f"Sale '{sale_id}' is {sale.get('status', 'UNKNOWN')}. "
                f"Only open sales accept modifications."
            ),
            policy_name="sale_must_be_open_policy",
        )

    return None


def void_requires_completed_policy(
    command: Command,
    sale_lookup=None,
) -> Optional[RejectionReason]:
    """Only completed sales can be voided."""
    if sale_lookup is None:
        return None

    if command.command_type != "retail.sale.void.request":
        return None

    sale_id = command.payload.get("sale_id")
    sale = sale_lookup(sale_id)

    if sale is None:
        return RejectionReason(
            code="SALE_NOT_FOUND",
            message=f"Sale '{sale_id}' not found.",
            policy_name="void_requires_completed_policy",
        )

    if sale.get("status") != "COMPLETED":
        return RejectionReason(
            code="SALE_NOT_COMPLETED",
            message=(
                f"Sale '{sale_id}' is {sale.get('status', 'UNKNOWN')}. "
                f"Only completed sales can be voided."
            ),
            policy_name="void_requires_completed_policy",
        )

    return None


def refund_within_sale_amount_policy(
    command: Command,
    sale_lookup=None,
) -> Optional[RejectionReason]:
    """Refund amount cannot exceed original sale net amount."""
    if sale_lookup is None:
        return None

    if command.command_type != "retail.refund.issue.request":
        return None

    original_sale_id = command.payload.get("original_sale_id")
    sale = sale_lookup(original_sale_id)

    if sale is None:
        return RejectionReason(
            code="ORIGINAL_SALE_NOT_FOUND",
            message=f"Original sale '{original_sale_id}' not found.",
            policy_name="refund_within_sale_amount_policy",
        )

    refund_amount = command.payload.get("amount", 0)
    sale_net = sale.get("net_amount", 0)

    if refund_amount > sale_net:
        return RejectionReason(
            code="REFUND_EXCEEDS_SALE",
            message=(
                f"Refund amount ({refund_amount}) exceeds "
                f"sale net amount ({sale_net})."
            ),
            policy_name="refund_within_sale_amount_policy",
        )

    return None
