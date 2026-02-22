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


def usage_metric_value_must_be_non_negative_policy(command: Command) -> RejectionReason | None:
    metric_value = command.payload.get("metric_value")
    if metric_value is None:
        return None
    if not isinstance(metric_value, int) or metric_value < 0:
        return RejectionReason(
            code="INVALID_USAGE_METRIC",
            message="metric_value must be integer >= 0.",
            policy_name="usage_metric_value_must_be_non_negative_policy",
        )
    return None


def subscription_must_be_active_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") != "ACTIVE":
        return RejectionReason(
            code="SUBSCRIPTION_NOT_ACTIVE",
            message=f"Subscription '{subscription_id}' is not ACTIVE.",
            policy_name="subscription_must_be_active_policy",
        )
    return None


def payment_reference_must_be_unique_policy(command: Command, payment_reference_exists) -> RejectionReason | None:
    payment_reference = command.payload.get("payment_reference", "")
    if not payment_reference:
        return None
    if payment_reference_exists(payment_reference):
        return RejectionReason(
            code="DUPLICATE_PAYMENT_REFERENCE",
            message=f"payment_reference '{payment_reference}' already recorded.",
            policy_name="payment_reference_must_be_unique_policy",
        )
    return None


def subscription_must_not_be_cancelled_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") == "CANCELLED":
        return RejectionReason(
            code="SUBSCRIPTION_CANCELLED",
            message=f"Subscription '{subscription_id}' is CANCELLED and cannot transition.",
            policy_name="subscription_must_not_be_cancelled_policy",
        )
    return None


def subscription_must_be_suspended_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") != "SUSPENDED":
        return RejectionReason(
            code="SUBSCRIPTION_NOT_SUSPENDED",
            message=f"Subscription '{subscription_id}' is not SUSPENDED.",
            policy_name="subscription_must_be_suspended_policy",
        )
    return None


def plan_change_target_must_differ_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    target_plan = command.payload.get("new_plan_code", "")
    if not subscription_id or not target_plan:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("plan_code") == target_plan:
        return RejectionReason(
            code="PLAN_UNCHANGED",
            message=f"Subscription '{subscription_id}' is already on plan '{target_plan}'.",
            policy_name="plan_change_target_must_differ_policy",
        )
    return None


def subscription_must_not_be_delinquent_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") == "DELINQUENT":
        return RejectionReason(
            code="SUBSCRIPTION_DELINQUENT",
            message=f"Subscription '{subscription_id}' is DELINQUENT and cannot transition.",
            policy_name="subscription_must_not_be_delinquent_policy",
        )
    return None


def subscription_must_be_delinquent_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") != "DELINQUENT":
        return RejectionReason(
            code="SUBSCRIPTION_NOT_DELINQUENT",
            message=f"Subscription '{subscription_id}' is not DELINQUENT.",
            policy_name="subscription_must_be_delinquent_policy",
        )
    return None


def payment_reference_must_exist_policy(command: Command, payment_reference_exists) -> RejectionReason | None:
    payment_reference = command.payload.get("payment_reference", "")
    if not payment_reference:
        return None
    if not payment_reference_exists(payment_reference):
        return RejectionReason(
            code="PAYMENT_REFERENCE_NOT_FOUND",
            message=f"payment_reference '{payment_reference}' not found.",
            policy_name="payment_reference_must_exist_policy",
        )
    return None


def payment_reference_must_not_be_reversed_policy(command: Command, payment_reference_reversed) -> RejectionReason | None:
    payment_reference = command.payload.get("payment_reference", "")
    if not payment_reference:
        return None
    if payment_reference_reversed(payment_reference):
        return RejectionReason(
            code="PAYMENT_ALREADY_REVERSED",
            message=f"payment_reference '{payment_reference}' already reversed.",
            policy_name="payment_reference_must_not_be_reversed_policy",
        )
    return None


def payment_reference_must_belong_to_subscription_policy(command: Command, resolve_payment_reference) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    payment_reference = command.payload.get("payment_reference", "")
    if not subscription_id or not payment_reference:
        return None

    payment_record = resolve_payment_reference(payment_reference)
    if payment_record is None:
        return None

    if payment_record.get("subscription_id") != subscription_id:
        return RejectionReason(
            code="PAYMENT_REFERENCE_SUBSCRIPTION_MISMATCH",
            message=(
                f"payment_reference '{payment_reference}' does not belong to "
                f"subscription '{subscription_id}'."
            ),
            policy_name="payment_reference_must_belong_to_subscription_policy",
        )
    return None


def subscription_must_not_be_written_off_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") == "WRITTEN_OFF":
        return RejectionReason(
            code="SUBSCRIPTION_WRITTEN_OFF",
            message=f"Subscription '{subscription_id}' is WRITTEN_OFF and cannot transition.",
            policy_name="subscription_must_not_be_written_off_policy",
        )
    return None


def subscription_must_be_cancelled_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") != "CANCELLED":
        return RejectionReason(
            code="SUBSCRIPTION_NOT_CANCELLED",
            message=f"Subscription '{subscription_id}' is not CANCELLED.",
            policy_name="subscription_must_be_cancelled_policy",
        )
    return None


def subscription_must_not_be_closed_policy(command: Command, subscription_lookup) -> RejectionReason | None:
    subscription_id = command.payload.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = subscription_lookup(subscription_id)
    if subscription is None:
        return None

    if subscription.get("status") == "CLOSED":
        return RejectionReason(
            code="SUBSCRIPTION_CLOSED",
            message=f"Subscription '{subscription_id}' is CLOSED and cannot transition.",
            policy_name="subscription_must_not_be_closed_policy",
        )
    return None


def invoice_reference_must_be_unique_policy(command: Command, invoice_reference_exists) -> RejectionReason | None:
    invoice_reference = command.payload.get("invoice_reference", "")
    if not invoice_reference:
        return None
    if invoice_reference_exists(invoice_reference):
        return RejectionReason(
            code="DUPLICATE_INVOICE_REFERENCE",
            message=f"invoice_reference '{invoice_reference}' already issued.",
            policy_name="invoice_reference_must_be_unique_policy",
        )
    return None
