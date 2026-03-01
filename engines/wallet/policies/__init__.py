"""
BOS Credit Wallet Engine — Policies
====================================
Credit limit enforcement, freeze guard, approval thresholds.
"""

from typing import Optional

from core.commands.rejection import RejectionReason


def credit_policy_must_exist_policy(
    command,
    policy_lookup=None,
) -> Optional[RejectionReason]:
    """Credit policy must be configured before spending."""
    if policy_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    if cid and policy_lookup(cid) is None:
        return RejectionReason(
            code="CREDIT_POLICY_NOT_CONFIGURED",
            message=f"No credit policy for customer '{cid}'.",
            policy_name="credit_policy_must_exist_policy",
        )
    return None


def credit_not_frozen_policy(
    command,
    frozen_lookup=None,
) -> Optional[RejectionReason]:
    """Spending blocked if wallet is frozen by customer."""
    if frozen_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    if cid and frozen_lookup(cid):
        return RejectionReason(
            code="WALLET_FROZEN",
            message="Customer has frozen credit usage.",
            policy_name="credit_not_frozen_policy",
        )
    return None


def sufficient_credit_policy(
    command,
    balance_lookup=None,
) -> Optional[RejectionReason]:
    """Customer must have sufficient credit balance."""
    if balance_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    amount = command.payload.get("amount", 0)
    if cid:
        balance = balance_lookup(cid)
        if balance < amount:
            return RejectionReason(
                code="INSUFFICIENT_CREDIT",
                message=f"Credit balance {balance}, needs {amount}.",
                policy_name="sufficient_credit_policy",
            )
    return None


def credit_limit_not_exceeded_policy(
    command,
    balance_lookup=None,
    policy_lookup=None,
) -> Optional[RejectionReason]:
    """Issuing credit must not exceed customer's credit limit."""
    if balance_lookup is None or policy_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    amount = command.payload.get("amount", 0)
    if cid:
        policy = policy_lookup(cid)
        if policy is None:
            return None
        current_balance = balance_lookup(cid)
        if current_balance + amount > policy.customer_credit_limit:
            return RejectionReason(
                code="CREDIT_LIMIT_EXCEEDED",
                message=f"Limit {policy.customer_credit_limit}, current {current_balance}, "
                        f"requested {amount}.",
                policy_name="credit_limit_not_exceeded_policy",
            )
    return None


def approval_required_policy(
    command,
    policy_lookup=None,
) -> Optional[RejectionReason]:
    """Large credit issuance requires manager approval."""
    if policy_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    amount = command.payload.get("amount", 0)
    if cid:
        policy = policy_lookup(cid)
        if policy and policy.approval_required_above > 0:
            if amount > policy.approval_required_above:
                actor_type = getattr(command, "actor_type", None)
                if actor_type != "MANAGER" and actor_type != "ADMIN":
                    return RejectionReason(
                        code="APPROVAL_REQUIRED",
                        message=f"Credit above {policy.approval_required_above} "
                                f"requires manager approval.",
                        policy_name="approval_required_policy",
                    )
    return None


def max_apply_percent_policy(
    command,
    policy_lookup=None,
) -> Optional[RejectionReason]:
    """Credit applied must not exceed max % of invoice."""
    if policy_lookup is None:
        return None
    cid = command.payload.get("business_customer_id")
    amount = command.payload.get("amount", 0)
    invoice_amount = command.payload.get("invoice_amount")
    if cid and invoice_amount and invoice_amount > 0:
        policy = policy_lookup(cid)
        if policy:
            max_apply = invoice_amount * policy.max_apply_percent_per_invoice // 100
            if amount > max_apply:
                return RejectionReason(
                    code="EXCEEDS_MAX_APPLY_PERCENT",
                    message=f"Max {policy.max_apply_percent_per_invoice}% of invoice. "
                            f"Limit: {max_apply}, got {amount}.",
                    policy_name="max_apply_percent_policy",
                )
    return None
