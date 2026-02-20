"""
BOS Cash Engine — Policies
============================
Engine-specific validation policies for cash operations.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def session_must_be_open_policy(
    command: Command,
    session_lookup=None,
) -> Optional[RejectionReason]:
    """
    Reject payment/deposit/withdrawal if session is not open.
    Only active when session_lookup is provided.
    """
    if session_lookup is None:
        return None

    if command.command_type not in (
        "cash.payment.record.request",
        "cash.deposit.record.request",
        "cash.withdrawal.record.request",
    ):
        return None

    session_id = command.payload.get("session_id")
    session = session_lookup(session_id)

    if session is None:
        return RejectionReason(
            code="SESSION_NOT_FOUND",
            message=f"Cash session '{session_id}' not found.",
            policy_name="session_must_be_open_policy",
        )

    if session.get("status") != "OPEN":
        return RejectionReason(
            code="SESSION_NOT_OPEN",
            message=(
                f"Cash session '{session_id}' is "
                f"{session.get('status', 'UNKNOWN')}. "
                f"Only open sessions accept transactions."
            ),
            policy_name="session_must_be_open_policy",
        )

    return None


def withdrawal_limit_policy(
    command: Command,
    drawer_balance_lookup=None,
) -> Optional[RejectionReason]:
    """
    Reject withdrawal if it would exceed drawer balance.
    Only active when drawer_balance_lookup is provided.
    """
    if drawer_balance_lookup is None:
        return None

    if command.command_type != "cash.withdrawal.record.request":
        return None

    drawer_id = command.payload.get("drawer_id")
    amount = command.payload.get("amount", 0)
    current_balance = drawer_balance_lookup(drawer_id)

    if current_balance < amount:
        return RejectionReason(
            code="INSUFFICIENT_DRAWER_BALANCE",
            message=(
                f"Insufficient drawer balance: {current_balance} available, "
                f"{amount} requested for drawer {drawer_id}."
            ),
            policy_name="withdrawal_limit_policy",
        )

    return None
