"""BOS Billing Engine - application service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.context.scope_guard import enforce_scope_guard
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.billing.commands import BILLING_COMMAND_TYPES
from engines.billing.events import (
    build_payment_recorded_payload,
    build_plan_assigned_payload,
    build_subscription_started_payload,
    build_subscription_suspended_payload,
    build_subscription_renewed_payload,
    build_subscription_cancelled_payload,
    build_subscription_resumed_payload,
    build_subscription_plan_changed_payload,
    build_usage_metered_payload,
    register_billing_event_types,
    resolve_billing_event_type,
)
from engines.billing.policies import (
    billing_plan_must_be_valid_policy,
    payment_amount_must_be_positive_policy,
    subscription_must_exist_policy,
    subscription_must_not_exist_policy,
    subscription_must_be_active_policy,
    usage_metric_value_must_be_non_negative_policy,
    payment_reference_must_be_unique_policy,
    subscription_must_not_be_cancelled_policy,
    subscription_must_be_suspended_policy,
    plan_change_target_must_differ_policy,
)


class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...


class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


class BillingProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._current_plan: Optional[dict] = None
        self._subscriptions: Dict[str, dict] = {}
        self._usage_totals: Dict[str, int] = {}
        self._payment_references: set[str] = set()

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})
        if event_type.startswith("billing.plan.assigned"):
            self._current_plan = {
                "plan_code": payload["plan_code"],
                "cycle": payload["cycle"],
                "seats": payload["seats"],
            }
        elif event_type.startswith("billing.subscription.started"):
            self._subscriptions[payload["subscription_id"]] = {
                "status": "ACTIVE",
                "plan_code": payload["plan_code"],
                "cycle": payload["cycle"],
                "paid_minor": 0,
            }
        elif event_type.startswith("billing.payment.recorded"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["paid_minor"] += payload["amount_minor"]
            self._payment_references.add(payload["payment_reference"])
        elif event_type.startswith("billing.subscription.suspended"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "SUSPENDED"
                subscription["suspension_reason"] = payload["reason"]
        elif event_type.startswith("billing.subscription.renewed"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "ACTIVE"
                subscription["last_renewal_reference"] = payload["renewal_reference"]
        elif event_type.startswith("billing.subscription.cancelled"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "CANCELLED"
                subscription["cancellation_reason"] = payload["cancellation_reason"]
        elif event_type.startswith("billing.subscription.resumed"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "ACTIVE"
                subscription["resume_reason"] = payload["resume_reason"]
        elif event_type.startswith("billing.subscription.plan_changed"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["plan_code"] = payload["new_plan_code"]
                subscription["plan_change_reason"] = payload["change_reason"]
        elif event_type.startswith("billing.usage.metered"):
            metric_key = payload["metric_key"]
            current_total = self._usage_totals.get(metric_key, 0)
            self._usage_totals[metric_key] = current_total + payload["metric_value"]

    def get_subscription(self, subscription_id: str) -> Optional[dict]:
        return self._subscriptions.get(subscription_id)

    @property
    def current_plan(self) -> Optional[dict]:
        return self._current_plan

    def get_usage_total(self, metric_key: str) -> int:
        return self._usage_totals.get(metric_key, 0)

    def has_payment_reference(self, payment_reference: str) -> bool:
        return payment_reference in self._payment_references

    def snapshot(self) -> dict:
        subscriptions = {key: dict(value) for key, value in self._subscriptions.items()}
        usage_totals = dict(self._usage_totals)
        return {
            "current_plan": None if self._current_plan is None else dict(self._current_plan),
            "subscriptions": subscriptions,
            "usage_totals": usage_totals,
            "payment_references": tuple(sorted(self._payment_references)),
        }


PAYLOAD_BUILDERS = {
    "billing.plan.assign.request": build_plan_assigned_payload,
    "billing.subscription.start.request": build_subscription_started_payload,
    "billing.payment.record.request": build_payment_recorded_payload,
    "billing.subscription.suspend.request": build_subscription_suspended_payload,
    "billing.subscription.renew.request": build_subscription_renewed_payload,
    "billing.subscription.cancel.request": build_subscription_cancelled_payload,
    "billing.subscription.resume.request": build_subscription_resumed_payload,
    "billing.subscription.plan_change.request": build_subscription_plan_changed_payload,
    "billing.usage.meter.request": build_usage_metered_payload,
}


@dataclass(frozen=True)
class BillingExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _BillingCommandHandler:
    def __init__(self, service: "BillingService"):
        self._service = service

    def execute(self, command: Command) -> BillingExecutionResult:
        return self._service._execute_command(command)


class BillingService:
    def __init__(self, *, business_context, command_bus,
                 event_factory: EventFactoryProtocol,
                 persist_event: PersistEventProtocol,
                 event_type_registry,
                 projection_store: BillingProjectionStore | None = None,
                 feature_flag_provider=None):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or BillingProjectionStore()
        self._feature_flag_provider = feature_flag_provider

        register_billing_event_types(self._event_type_registry)
        handler = _BillingCommandHandler(self)
        for command_type in sorted(BILLING_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, result: Any) -> bool:
        if hasattr(result, "accepted"):
            return bool(result.accepted)
        if isinstance(result, dict):
            return bool(result.get("accepted"))
        return bool(result)

    def _run_policies(self, command: Command) -> None:
        plan_rejection = billing_plan_must_be_valid_policy(command)
        if plan_rejection is not None:
            raise ValueError(plan_rejection.message)

        amount_rejection = payment_amount_must_be_positive_policy(command)
        if amount_rejection is not None:
            raise ValueError(amount_rejection.message)

        usage_rejection = usage_metric_value_must_be_non_negative_policy(command)
        if usage_rejection is not None:
            raise ValueError(usage_rejection.message)

        duplicate_payment_rejection = payment_reference_must_be_unique_policy(
            command,
            payment_reference_exists=self._projection_store.has_payment_reference,
        )
        if duplicate_payment_rejection is not None:
            raise ValueError(duplicate_payment_rejection.message)

        if command.command_type == "billing.subscription.start.request":
            unique_rejection = subscription_must_not_exist_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if unique_rejection is not None:
                raise ValueError(unique_rejection.message)

        if command.command_type in {
            "billing.payment.record.request",
            "billing.subscription.suspend.request",
            "billing.subscription.renew.request",
            "billing.subscription.cancel.request",
            "billing.subscription.resume.request",
            "billing.subscription.plan_change.request",
            "billing.usage.meter.request",
        }:
            exists_rejection = subscription_must_exist_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if exists_rejection is not None:
                raise ValueError(exists_rejection.message)

        if command.command_type in {
            "billing.subscription.suspend.request",
            "billing.subscription.renew.request",
            "billing.subscription.cancel.request",
            "billing.subscription.resume.request",
            "billing.subscription.plan_change.request",
            "billing.usage.meter.request",
        }:
            cancelled_rejection = subscription_must_not_be_cancelled_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if cancelled_rejection is not None:
                raise ValueError(cancelled_rejection.message)

        if command.command_type == "billing.subscription.resume.request":
            suspended_rejection = subscription_must_be_suspended_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if suspended_rejection is not None:
                raise ValueError(suspended_rejection.message)

        if command.command_type == "billing.subscription.plan_change.request":
            plan_change_rejection = plan_change_target_must_differ_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if plan_change_rejection is not None:
                raise ValueError(plan_change_rejection.message)

        if command.command_type in {
            "billing.payment.record.request",
            "billing.usage.meter.request",
            "billing.subscription.plan_change.request",
            "billing.usage.meter.request",
        }:
            active_rejection = subscription_must_be_active_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if active_rejection is not None:
                raise ValueError(active_rejection.message)

    def _execute_command(self, command: Command) -> BillingExecutionResult:
        enforce_scope_guard(command)
        feature_eval = FeatureFlagEvaluator.evaluate(
            command,
            self._business_context,
            self._feature_flag_provider,
        )
        if not feature_eval.allowed:
            raise ValueError(f"Feature disabled: {feature_eval.message}")

        self._run_policies(command)

        event_type = resolve_billing_event_type(command.command_type)
        if event_type is None:
            raise ValueError(f"Unsupported billing command type: {command.command_type}")

        payload_builder = PAYLOAD_BUILDERS.get(command.command_type)
        if payload_builder is None:
            raise ValueError(f"No payload builder for: {command.command_type}")

        payload = payload_builder(command)
        event_data = self._event_factory(
            command=command,
            event_type=event_type,
            payload=payload,
        )

        persist_result = self._persist_event(
            event_data=event_data,
            context=self._business_context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )

        projection_applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            projection_applied = True

        return BillingExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=projection_applied,
        )

    @property
    def projection_store(self) -> BillingProjectionStore:
        return self._projection_store
