"""BOS Billing Engine - event types and payload builders."""

from __future__ import annotations

from core.commands.base import Command

BILLING_PLAN_ASSIGNED_V1 = "billing.plan.assigned.v1"
BILLING_SUBSCRIPTION_STARTED_V1 = "billing.subscription.started.v1"
BILLING_PAYMENT_RECORDED_V1 = "billing.payment.recorded.v1"
BILLING_SUBSCRIPTION_SUSPENDED_V1 = "billing.subscription.suspended.v1"
BILLING_SUBSCRIPTION_RENEWED_V1 = "billing.subscription.renewed.v1"
BILLING_USAGE_METERED_V1 = "billing.usage.metered.v1"

BILLING_EVENT_TYPES = (
    BILLING_PLAN_ASSIGNED_V1,
    BILLING_SUBSCRIPTION_STARTED_V1,
    BILLING_PAYMENT_RECORDED_V1,
    BILLING_SUBSCRIPTION_SUSPENDED_V1,
    BILLING_SUBSCRIPTION_RENEWED_V1,
    BILLING_USAGE_METERED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "billing.plan.assign.request": BILLING_PLAN_ASSIGNED_V1,
    "billing.subscription.start.request": BILLING_SUBSCRIPTION_STARTED_V1,
    "billing.payment.record.request": BILLING_PAYMENT_RECORDED_V1,
    "billing.subscription.suspend.request": BILLING_SUBSCRIPTION_SUSPENDED_V1,
    "billing.subscription.renew.request": BILLING_SUBSCRIPTION_RENEWED_V1,
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


def build_usage_metered_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "metric_key": command.payload["metric_key"],
        "metric_value": command.payload["metric_value"],
        "period_start": command.payload["period_start"],
        "period_end": command.payload["period_end"],
        "metered_at": command.issued_at,
    })
    return payload
