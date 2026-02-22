"""BOS Billing Engine - event types and payload builders."""

from __future__ import annotations

from core.commands.base import Command

BILLING_PLAN_ASSIGNED_V1 = "billing.plan.assigned.v1"
BILLING_SUBSCRIPTION_STARTED_V1 = "billing.subscription.started.v1"
BILLING_PAYMENT_RECORDED_V1 = "billing.payment.recorded.v1"
BILLING_PAYMENT_REVERSED_V1 = "billing.payment.reversed.v1"
BILLING_SUBSCRIPTION_SUSPENDED_V1 = "billing.subscription.suspended.v1"
BILLING_SUBSCRIPTION_RENEWED_V1 = "billing.subscription.renewed.v1"
BILLING_SUBSCRIPTION_CANCELLED_V1 = "billing.subscription.cancelled.v1"
BILLING_SUBSCRIPTION_RESUMED_V1 = "billing.subscription.resumed.v1"
BILLING_SUBSCRIPTION_PLAN_CHANGED_V1 = "billing.subscription.plan_changed.v1"
BILLING_SUBSCRIPTION_DELINQUENT_MARKED_V1 = "billing.subscription.delinquent_marked.v1"
BILLING_SUBSCRIPTION_DELINQUENCY_CLEARED_V1 = "billing.subscription.delinquency_cleared.v1"
BILLING_SUBSCRIPTION_WRITTEN_OFF_V1 = "billing.subscription.written_off.v1"
BILLING_SUBSCRIPTION_REACTIVATED_V1 = "billing.subscription.reactivated.v1"
BILLING_SUBSCRIPTION_CLOSED_V1 = "billing.subscription.closed.v1"
BILLING_INVOICE_ISSUED_V1 = "billing.invoice.issued.v1"
BILLING_INVOICE_VOIDED_V1 = "billing.invoice.voided.v1"
BILLING_INVOICE_MARKED_PAID_V1 = "billing.invoice.marked_paid.v1"
BILLING_INVOICE_DUE_DATE_EXTENDED_V1 = "billing.invoice.due_date_extended.v1"
BILLING_USAGE_METERED_V1 = "billing.usage.metered.v1"

BILLING_EVENT_TYPES = (
    BILLING_PLAN_ASSIGNED_V1,
    BILLING_SUBSCRIPTION_STARTED_V1,
    BILLING_PAYMENT_RECORDED_V1,
    BILLING_PAYMENT_REVERSED_V1,
    BILLING_SUBSCRIPTION_SUSPENDED_V1,
    BILLING_SUBSCRIPTION_RENEWED_V1,
    BILLING_SUBSCRIPTION_CANCELLED_V1,
    BILLING_SUBSCRIPTION_RESUMED_V1,
    BILLING_SUBSCRIPTION_PLAN_CHANGED_V1,
    BILLING_SUBSCRIPTION_DELINQUENT_MARKED_V1,
    BILLING_SUBSCRIPTION_DELINQUENCY_CLEARED_V1,
    BILLING_SUBSCRIPTION_WRITTEN_OFF_V1,
    BILLING_SUBSCRIPTION_REACTIVATED_V1,
    BILLING_SUBSCRIPTION_CLOSED_V1,
    BILLING_INVOICE_ISSUED_V1,
    BILLING_INVOICE_VOIDED_V1,
    BILLING_INVOICE_MARKED_PAID_V1,
    BILLING_INVOICE_DUE_DATE_EXTENDED_V1,
    BILLING_USAGE_METERED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "billing.plan.assign.request": BILLING_PLAN_ASSIGNED_V1,
    "billing.subscription.start.request": BILLING_SUBSCRIPTION_STARTED_V1,
    "billing.payment.record.request": BILLING_PAYMENT_RECORDED_V1,
    "billing.payment.reverse.request": BILLING_PAYMENT_REVERSED_V1,
    "billing.subscription.suspend.request": BILLING_SUBSCRIPTION_SUSPENDED_V1,
    "billing.subscription.renew.request": BILLING_SUBSCRIPTION_RENEWED_V1,
    "billing.subscription.cancel.request": BILLING_SUBSCRIPTION_CANCELLED_V1,
    "billing.subscription.resume.request": BILLING_SUBSCRIPTION_RESUMED_V1,
    "billing.subscription.plan_change.request": BILLING_SUBSCRIPTION_PLAN_CHANGED_V1,
    "billing.subscription.mark_delinquent.request": BILLING_SUBSCRIPTION_DELINQUENT_MARKED_V1,
    "billing.subscription.clear_delinquency.request": BILLING_SUBSCRIPTION_DELINQUENCY_CLEARED_V1,
    "billing.subscription.write_off.request": BILLING_SUBSCRIPTION_WRITTEN_OFF_V1,
    "billing.subscription.reactivate.request": BILLING_SUBSCRIPTION_REACTIVATED_V1,
    "billing.subscription.close.request": BILLING_SUBSCRIPTION_CLOSED_V1,
    "billing.invoice.issue.request": BILLING_INVOICE_ISSUED_V1,
    "billing.invoice.void.request": BILLING_INVOICE_VOIDED_V1,
    "billing.invoice.mark_paid.request": BILLING_INVOICE_MARKED_PAID_V1,
    "billing.invoice.due_date.extend.request": BILLING_INVOICE_DUE_DATE_EXTENDED_V1,
    "billing.usage.meter.request": BILLING_USAGE_METERED_V1,
}


def resolve_billing_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_billing_event_types(event_type_registry) -> None:
    for et in sorted(BILLING_EVENT_TYPES):
        event_type_registry.register(et)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "actor_id": command.actor_id,
        "actor_type": command.actor_type,
        "correlation_id": command.correlation_id,
        "command_id": command.command_id,
    }


def build_plan_assigned_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "plan_code": command.payload["plan_code"],
        "cycle": command.payload["cycle"],
        "seats": command.payload["seats"],
        "assigned_at": command.issued_at,
    })
    return payload


def build_subscription_started_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "plan_code": command.payload["plan_code"],
        "cycle": command.payload["cycle"],
        "started_at": command.issued_at,
    })
    return payload


def build_payment_recorded_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "payment_reference": command.payload["payment_reference"],
        "amount_minor": command.payload["amount_minor"],
        "currency": command.payload["currency"],
        "recorded_at": command.issued_at,
    })
    return payload


def build_payment_reversed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "payment_reference": command.payload["payment_reference"],
        "reversal_reason": command.payload["reversal_reason"],
        "reversed_at": command.issued_at,
    })
    return payload


def build_subscription_suspended_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "reason": command.payload["reason"],
        "suspended_at": command.issued_at,
    })
    return payload


def build_subscription_renewed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "renewal_reference": command.payload["renewal_reference"],
        "renewed_at": command.issued_at,
    })
    return payload


def build_subscription_cancelled_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "cancellation_reason": command.payload["cancellation_reason"],
        "cancelled_at": command.issued_at,
    })
    return payload


def build_usage_metered_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "metric_key": command.payload["metric_key"],
        "metric_value": command.payload["metric_value"],
        "period_start": command.payload["period_start"],
        "period_end": command.payload["period_end"],
        "metered_at": command.issued_at,
    })
    return payload


def build_subscription_resumed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "resume_reason": command.payload["resume_reason"],
        "resumed_at": command.issued_at,
    })
    return payload


def build_subscription_plan_changed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "new_plan_code": command.payload["new_plan_code"],
        "change_reason": command.payload["change_reason"],
        "changed_at": command.issued_at,
    })
    return payload


def build_subscription_delinquent_marked_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "delinquency_reason": command.payload["delinquency_reason"],
        "delinquent_marked_at": command.issued_at,
    })
    return payload


def build_subscription_delinquency_cleared_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "clearance_reason": command.payload["clearance_reason"],
        "delinquency_cleared_at": command.issued_at,
    })
    return payload


def build_subscription_written_off_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "write_off_reason": command.payload["write_off_reason"],
        "written_off_at": command.issued_at,
    })
    return payload


def build_subscription_reactivated_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "reactivation_reason": command.payload["reactivation_reason"],
        "reactivated_at": command.issued_at,
    })
    return payload


def build_subscription_closed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "closure_reason": command.payload["closure_reason"],
        "closed_at": command.issued_at,
    })
    return payload


def build_invoice_issued_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "invoice_reference": command.payload["invoice_reference"],
        "amount_minor": command.payload["amount_minor"],
        "currency": command.payload["currency"],
        "due_on": command.payload["due_on"],
        "issued_at": command.issued_at,
    })
    return payload


def build_invoice_voided_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "invoice_reference": command.payload["invoice_reference"],
        "void_reason": command.payload["void_reason"],
        "voided_at": command.issued_at,
    })
    return payload


def build_invoice_marked_paid_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "invoice_reference": command.payload["invoice_reference"],
        "payment_reference": command.payload["payment_reference"],
        "marked_paid_at": command.issued_at,
    })
    return payload


def build_invoice_due_date_extended_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "subscription_id": command.payload["subscription_id"],
        "invoice_reference": command.payload["invoice_reference"],
        "new_due_on": command.payload["new_due_on"],
        "extension_reason": command.payload["extension_reason"],
        "extended_at": command.issued_at,
    })
    return payload
