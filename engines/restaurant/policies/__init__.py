"""
BOS Restaurant Engine — Policies
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def table_must_be_open_policy(
    command: Command, table_lookup=None,
) -> Optional[RejectionReason]:
    """Orders/bills require an open table."""
    if table_lookup is None:
        return None
    if command.command_type not in (
        "restaurant.order.place.request",
        "restaurant.bill.settle.request",
    ):
        return None
    table_id = command.payload.get("table_id")
    table = table_lookup(table_id)
    if table is None:
        return RejectionReason(
            code="TABLE_NOT_FOUND",
            message=f"Table '{table_id}' not found.",
            policy_name="table_must_be_open_policy",
        )
    if table.get("status") != "OPEN":
        return RejectionReason(
            code="TABLE_NOT_OPEN",
            message=f"Table '{table_id}' is {table.get('status', 'UNKNOWN')}.",
            policy_name="table_must_be_open_policy",
        )
    return None
