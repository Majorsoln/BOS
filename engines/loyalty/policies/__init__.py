"""
BOS Loyalty Engine — Policies
=============================
Redemption guards and program enforcement.
"""

from typing import Optional

from core.commands.rejection import RejectionReason


def program_must_be_configured_policy(
    command,
    program_lookup=None,
) -> Optional[RejectionReason]:
    """Loyalty program must be configured before point operations."""
    if program_lookup is None:
        return None
    program = program_lookup()
    if program is None:
        return RejectionReason(
            code="LOYALTY_PROGRAM_NOT_CONFIGURED",
            message="Loyalty program has not been configured for this business.",
            policy_name="program_must_be_configured_policy",
        )
    return None


def sufficient_balance_policy(
    command,
    balance_lookup=None,
) -> Optional[RejectionReason]:
    """Customer must have enough points to redeem."""
    if balance_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    pts = command.payload.get("points", 0)
    if cid:
        balance = balance_lookup(cid)
        if balance < pts:
            return RejectionReason(
                code="INSUFFICIENT_POINTS",
                message=f"Customer has {balance} points, needs {pts}.",
                policy_name="sufficient_balance_policy",
            )
    return None


def min_redeem_threshold_policy(
    command,
    program_lookup=None,
) -> Optional[RejectionReason]:
    """Redemption must meet minimum point threshold."""
    if program_lookup is None:
        return None
    program = program_lookup()
    if program is None:
        return None
    pts = command.payload.get("points", 0)
    if pts < program.min_redeem_points:
        return RejectionReason(
            code="BELOW_MIN_REDEEM",
            message=f"Minimum {program.min_redeem_points} points required, got {pts}.",
            policy_name="min_redeem_threshold_policy",
        )
    return None


def redeem_step_policy(
    command,
    program_lookup=None,
) -> Optional[RejectionReason]:
    """Redemption points must be in correct step multiples."""
    if program_lookup is None:
        return None
    program = program_lookup()
    if program is None or program.redeem_step <= 1:
        return None
    pts = command.payload.get("points", 0)
    if pts % program.redeem_step != 0:
        return RejectionReason(
            code="INVALID_REDEEM_STEP",
            message=f"Points must be in multiples of {program.redeem_step}, got {pts}.",
            policy_name="redeem_step_policy",
        )
    return None


def max_redeem_percent_policy(
    command,
    program_lookup=None,
) -> Optional[RejectionReason]:
    """Redemption discount must not exceed max % of invoice."""
    if program_lookup is None:
        return None
    program = program_lookup()
    if program is None:
        return None
    discount_value = command.payload.get("discount_value", 0)
    # The invoiced amount is tracked externally; if provided in command context:
    invoice_amount = command.payload.get("invoice_amount")
    if invoice_amount and invoice_amount > 0:
        max_discount = invoice_amount * program.max_redeem_percent_per_invoice // 100
        if discount_value > max_discount:
            return RejectionReason(
                code="EXCEEDS_MAX_REDEEM_PERCENT",
                message=f"Max {program.max_redeem_percent_per_invoice}% of invoice. "
                        f"Limit: {max_discount}, got {discount_value}.",
                policy_name="max_redeem_percent_policy",
            )
    return None
