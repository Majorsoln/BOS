"""
BOS Accounting Engine — Policies
==================================
Engine-specific validation policies for accounting operations.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def balanced_entry_policy(command: Command) -> Optional[RejectionReason]:
    """Reject journal post if debits != credits."""
    if command.command_type != "accounting.journal.post.request":
        return None

    lines = command.payload.get("lines", [])
    if len(lines) < 2:
        return RejectionReason(
            code="INSUFFICIENT_LINES",
            message="Journal entry must have at least 2 lines.",
            policy_name="balanced_entry_policy",
        )

    total_debits = sum(l["amount"] for l in lines if l.get("side") == "DEBIT")
    total_credits = sum(l["amount"] for l in lines if l.get("side") == "CREDIT")

    if total_debits != total_credits:
        return RejectionReason(
            code="UNBALANCED_ENTRY",
            message=(
                f"Journal entry unbalanced: debits ({total_debits}) "
                f"!= credits ({total_credits})."
            ),
            policy_name="balanced_entry_policy",
        )

    return None


def positive_amount_policy(command: Command) -> Optional[RejectionReason]:
    """Reject if any line has zero or negative amount."""
    if command.command_type != "accounting.journal.post.request":
        return None

    lines = command.payload.get("lines", [])
    for i, line in enumerate(lines):
        if line.get("amount", 0) <= 0:
            return RejectionReason(
                code="NON_POSITIVE_AMOUNT",
                message=f"Line {i} has non-positive amount: {line.get('amount')}.",
                policy_name="positive_amount_policy",
            )

    return None
