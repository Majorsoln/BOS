"""
BOS Inventory Engine — Policies
=================================
Engine-specific validation policies for inventory operations.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def negative_stock_policy(
    command: Command,
    stock_lookup=None,
) -> Optional[RejectionReason]:
    """
    Reject issue/transfer if it would result in negative stock.

    Only active when stock_lookup is provided (projection-aware).
    Without stock_lookup, this policy passes (optimistic mode).
    """
    if stock_lookup is None:
        return None

    if command.command_type not in (
        "inventory.stock.issue.request",
        "inventory.stock.transfer.request",
    ):
        return None

    item_id = command.payload.get("item_id")
    quantity = command.payload.get("quantity", 0)

    if command.command_type == "inventory.stock.issue.request":
        location_id = command.payload.get("location_id")
    else:
        location_id = command.payload.get("from_location_id")

    current_stock = stock_lookup(item_id, location_id)

    if current_stock < quantity:
        return RejectionReason(
            code="INSUFFICIENT_STOCK",
            message=(
                f"Insufficient stock: {current_stock} available, "
                f"{quantity} requested for item {item_id} "
                f"at location {location_id}."
            ),
            policy_name="negative_stock_policy",
        )

    return None


def same_location_transfer_policy(
    command: Command,
) -> Optional[RejectionReason]:
    """Reject transfers where source and destination are the same."""
    if command.command_type != "inventory.stock.transfer.request":
        return None

    from_loc = command.payload.get("from_location_id")
    to_loc = command.payload.get("to_location_id")

    if from_loc == to_loc:
        return RejectionReason(
            code="SAME_LOCATION_TRANSFER",
            message="Cannot transfer stock to the same location.",
            policy_name="same_location_transfer_policy",
        )

    return None
