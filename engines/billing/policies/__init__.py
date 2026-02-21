"""BOS Billing Engine - policies."""

from __future__ import annotations

from core.commands.base import Command
from core.commands.rejection import RejectionReason
from engines.billing.commands import VALID_BILLING_PLANS


def billing_plan_must_be_valid_policy(command: Command) -> RejectionReason | None:
    plan_code = command.payload.get("plan_code", "")
    if plan_code and plan_code not in VALID_BILLING_PLANS:
        return RejectionReason(
            code="INVALID_PLAN",
            message=f"plan_code '{plan_code}' is not valid.",
            policy_name="billing_plan_must_be_valid_policy",
        )
    return None


def payment_amount_must_be_positive_policy(command: Command) -> RejectionReason | None:
    amount_minor = command.payload.get("amount_minor")
    if amount_minor is None:
        return None
    if not isinstance(amount_minor, int) or amount_minor <= 0:
        return RejectionReason(
            code="INVALID_AMOUNT",
            message="amount_minor must be integer > 0.",
            policy_name="payment_amount_must_be_positive_policy",
        )
    return None


def subscription_must_exist_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if subscription_id and subscription_lookup(subscription_id) is None:
        return RejectionReason(
            code="SUBSCRIPTION_NOT_FOUND",
            message=f"Subscription '{subscription_id}' not found.",
            policy_name="subscription_must_exist_policy",
        )
    return None


def subscription_must_not_exist_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if subscription_id and subscription_lookup(subscription_id) is not None:
        return RejectionReason(
            code="SUBSCRIPTION_ALREADY_EXISTS",
            message=f"Subscription '{subscription_id}' already exists.",
            policy_name="subscription_must_not_exist_policy",
        )
    return None
