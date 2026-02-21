"""BOS Billing Engine - request commands."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED

BILLING_PLAN_ASSIGN_REQUEST = "billing.plan.assign.request"
BILLING_SUBSCRIPTION_START_REQUEST = "billing.subscription.start.request"
BILLING_PAYMENT_RECORD_REQUEST = "billing.payment.record.request"
BILLING_SUBSCRIPTION_SUSPEND_REQUEST = "billing.subscription.suspend.request"
BILLING_SUBSCRIPTION_RENEW_REQUEST = "billing.subscription.renew.request"
BILLING_SUBSCRIPTION_CANCEL_REQUEST = "billing.subscription.cancel.request"
BILLING_SUBSCRIPTION_RESUME_REQUEST = "billing.subscription.resume.request"
BILLING_SUBSCRIPTION_PLAN_CHANGE_REQUEST = "billing.subscription.plan_change.request"
BILLING_SUBSCRIPTION_MARK_DELINQUENT_REQUEST = "billing.subscription.mark_delinquent.request"
BILLING_SUBSCRIPTION_CLEAR_DELINQUENCY_REQUEST = "billing.subscription.clear_delinquency.request"
BILLING_USAGE_METER_REQUEST = "billing.usage.meter.request"

BILLING_COMMAND_TYPES = frozenset({
    BILLING_PLAN_ASSIGN_REQUEST,
    BILLING_SUBSCRIPTION_START_REQUEST,
    BILLING_PAYMENT_RECORD_REQUEST,
    BILLING_SUBSCRIPTION_SUSPEND_REQUEST,
    BILLING_SUBSCRIPTION_RENEW_REQUEST,
    BILLING_SUBSCRIPTION_CANCEL_REQUEST,
    BILLING_SUBSCRIPTION_RESUME_REQUEST,
    BILLING_SUBSCRIPTION_PLAN_CHANGE_REQUEST,
    BILLING_SUBSCRIPTION_MARK_DELINQUENT_REQUEST,
    BILLING_SUBSCRIPTION_CLEAR_DELINQUENCY_REQUEST,
    BILLING_USAGE_METER_REQUEST,
})

VALID_BILLING_PLANS = frozenset({"FREE", "STARTER", "GROWTH", "ENTERPRISE"})
VALID_BILLING_CYCLES = frozenset({"MONTHLY", "YEARLY"})
VALID_USAGE_METRIC_KEYS = frozenset({"API_CALLS", "EVENTS_APPENDED", "STORAGE_BYTES"})


def _cmd(command_type: str, payload: dict, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None) -> Command:
    return Command(
        command_id=command_id,
        command_type=command_type,
        business_id=business_id,
        branch_id=branch_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        issued_at=issued_at,
        correlation_id=correlation_id,
        source_engine="billing",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


@dataclass(frozen=True)
class PlanAssignRequest:
    plan_code: str
    cycle: str = "MONTHLY"
    seats: int = 1

    def __post_init__(self):
        if self.plan_code not in VALID_BILLING_PLANS:
            raise ValueError(f"plan_code '{self.plan_code}' is not valid.")
        if self.cycle not in VALID_BILLING_CYCLES:
            raise ValueError(f"cycle '{self.cycle}' is not valid.")
        if not isinstance(self.seats, int) or self.seats < 1:
            raise ValueError("seats must be integer >= 1.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_PLAN_ASSIGN_REQUEST,
            {"plan_code": self.plan_code, "cycle": self.cycle, "seats": self.seats},
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionStartRequest:
    subscription_id: str
    plan_code: str
    cycle: str = "MONTHLY"

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if self.plan_code not in VALID_BILLING_PLANS:
            raise ValueError(f"plan_code '{self.plan_code}' is not valid.")
        if self.cycle not in VALID_BILLING_CYCLES:
            raise ValueError(f"cycle '{self.cycle}' is not valid.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_START_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "plan_code": self.plan_code,
                "cycle": self.cycle,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class PaymentRecordRequest:
    subscription_id: str
    payment_reference: str
    amount_minor: int
    currency: str = "USD"

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.payment_reference.strip():
            raise ValueError("payment_reference must be non-empty.")
        if not isinstance(self.amount_minor, int) or self.amount_minor <= 0:
            raise ValueError("amount_minor must be integer > 0.")
        if not self.currency.strip():
            raise ValueError("currency must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_PAYMENT_RECORD_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "payment_reference": self.payment_reference,
                "amount_minor": self.amount_minor,
                "currency": self.currency,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionSuspendRequest:
    subscription_id: str
    reason: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_SUSPEND_REQUEST,
            {"subscription_id": self.subscription_id, "reason": self.reason},
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionRenewRequest:
    subscription_id: str
    renewal_reference: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.renewal_reference.strip():
            raise ValueError("renewal_reference must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_RENEW_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "renewal_reference": self.renewal_reference,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionCancelRequest:
    subscription_id: str
    cancellation_reason: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.cancellation_reason.strip():
            raise ValueError("cancellation_reason must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_CANCEL_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "cancellation_reason": self.cancellation_reason,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionResumeRequest:
    subscription_id: str
    resume_reason: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.resume_reason.strip():
            raise ValueError("resume_reason must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_RESUME_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "resume_reason": self.resume_reason,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionPlanChangeRequest:
    subscription_id: str
    new_plan_code: str
    change_reason: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if self.new_plan_code not in VALID_BILLING_PLANS:
            raise ValueError(f"new_plan_code '{self.new_plan_code}' is not valid.")
        if not self.change_reason.strip():
            raise ValueError("change_reason must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_PLAN_CHANGE_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "new_plan_code": self.new_plan_code,
                "change_reason": self.change_reason,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionMarkDelinquentRequest:
    subscription_id: str
    delinquency_reason: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.delinquency_reason.strip():
            raise ValueError("delinquency_reason must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_MARK_DELINQUENT_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "delinquency_reason": self.delinquency_reason,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class SubscriptionClearDelinquencyRequest:
    subscription_id: str
    clearance_reason: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if not self.clearance_reason.strip():
            raise ValueError("clearance_reason must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_SUBSCRIPTION_CLEAR_DELINQUENCY_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "clearance_reason": self.clearance_reason,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )


@dataclass(frozen=True)
class UsageMeterRequest:
    subscription_id: str
    metric_key: str
    metric_value: int
    period_start: str
    period_end: str

    def __post_init__(self):
        if not self.subscription_id.strip():
            raise ValueError("subscription_id must be non-empty.")
        if self.metric_key not in VALID_USAGE_METRIC_KEYS:
            raise ValueError(f"metric_key '{self.metric_key}' is not valid.")
        if not isinstance(self.metric_value, int) or self.metric_value < 0:
            raise ValueError("metric_value must be integer >= 0.")
        if not self.period_start.strip() or not self.period_end.strip():
            raise ValueError("period_start and period_end must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id=None,
                   correlation_id=None,
                   issued_at: datetime, branch_id=None) -> Command:
        return _cmd(
            BILLING_USAGE_METER_REQUEST,
            {
                "subscription_id": self.subscription_id,
                "metric_key": self.metric_key,
                "metric_value": self.metric_value,
                "period_start": self.period_start,
                "period_end": self.period_end,
            },
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            command_id=command_id or uuid.uuid4(),
            correlation_id=correlation_id or uuid.uuid4(),
            issued_at=issued_at,
            branch_id=branch_id,
        )
