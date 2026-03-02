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
    build_payment_reversed_payload,
    build_plan_assigned_payload,
    build_subscription_started_payload,
    build_subscription_suspended_payload,
    build_subscription_renewed_payload,
    build_subscription_cancelled_payload,
    build_subscription_resumed_payload,
    build_subscription_plan_changed_payload,
    build_subscription_delinquent_marked_payload,
    build_subscription_delinquency_cleared_payload,
    build_subscription_written_off_payload,
    build_subscription_reactivated_payload,
    build_subscription_closed_payload,
    build_invoice_issued_payload,
    build_invoice_voided_payload,
    build_invoice_marked_paid_payload,
    build_invoice_due_date_extended_payload,
    build_invoice_dispute_opened_payload,
    build_invoice_dispute_resolved_payload,
    build_invoice_reminder_sent_payload,
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
    payment_reference_must_exist_policy,
    payment_reference_must_not_be_reversed_policy,
    payment_reference_must_belong_to_subscription_policy,
    subscription_must_not_be_cancelled_policy,
    subscription_must_be_suspended_policy,
    plan_change_target_must_differ_policy,
    subscription_must_not_be_delinquent_policy,
    subscription_must_be_delinquent_policy,
    subscription_must_not_be_written_off_policy,
    subscription_must_be_cancelled_policy,
    subscription_must_not_be_closed_policy,
    invoice_reference_must_be_unique_policy,
    invoice_reference_must_exist_policy,
    invoice_reference_must_not_be_voided_policy,
    invoice_reference_must_belong_to_subscription_policy,
    invoice_reference_must_not_be_paid_policy,
    invoice_reference_must_not_be_disputed_policy,
    invoice_reference_must_be_disputed_policy,
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
        self._subscription_usage_totals: Dict[str, Dict[str, int]] = {}
        self._payment_references: set[str] = set()
        self._payment_records: Dict[str, dict] = {}
        self._reversed_payment_references: set[str] = set()
        self._invoice_references: set[str] = set()
        self._invoice_records: Dict[str, dict] = {}
        self._voided_invoice_references: set[str] = set()
        self._paid_invoice_references: set[str] = set()
        self._disputed_invoice_references: set[str] = set()
        self._invoice_reminder_counts: Dict[str, int] = {}

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
            payment_reference = payload["payment_reference"]
            self._payment_references.add(payment_reference)
            self._payment_records[payment_reference] = {
                "subscription_id": payload["subscription_id"],
                "amount_minor": payload["amount_minor"],
            }
        elif event_type.startswith("billing.payment.reversed"):
            payment_reference = payload["payment_reference"]
            payment_record = self._payment_records.get(payment_reference)
            if payment_record is not None:
                subscription = self._subscriptions.get(payment_record["subscription_id"])
                if subscription is not None:
                    subscription["paid_minor"] -= payment_record["amount_minor"]
            self._reversed_payment_references.add(payment_reference)
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
        elif event_type.startswith("billing.subscription.delinquent_marked"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "DELINQUENT"
                subscription["delinquency_reason"] = payload["delinquency_reason"]
        elif event_type.startswith("billing.subscription.delinquency_cleared"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "ACTIVE"
                subscription["delinquency_cleared_reason"] = payload["clearance_reason"]
        elif event_type.startswith("billing.subscription.written_off"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "WRITTEN_OFF"
                subscription["write_off_reason"] = payload["write_off_reason"]
        elif event_type.startswith("billing.subscription.reactivated"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "ACTIVE"
                subscription["reactivation_reason"] = payload["reactivation_reason"]
        elif event_type.startswith("billing.subscription.closed"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["status"] = "CLOSED"
                subscription["closure_reason"] = payload["closure_reason"]
        elif event_type.startswith("billing.invoice.issued"):
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["invoiced_minor"] = subscription.get("invoiced_minor", 0) + payload["amount_minor"]
            invoice_reference = payload["invoice_reference"]
            self._invoice_references.add(invoice_reference)
            self._invoice_records[invoice_reference] = {
                "subscription_id": payload["subscription_id"],
                "amount_minor": payload["amount_minor"],
                "due_on": payload["due_on"],
            }
        elif event_type.startswith("billing.invoice.voided"):
            invoice_reference = payload["invoice_reference"]
            invoice_record = self._invoice_records.get(invoice_reference)
            if invoice_record is not None:
                subscription = self._subscriptions.get(invoice_record["subscription_id"])
                if subscription is not None:
                    subscription["invoiced_minor"] = subscription.get("invoiced_minor", 0) - invoice_record["amount_minor"]
            self._voided_invoice_references.add(invoice_reference)
        elif event_type.startswith("billing.invoice.marked_paid"):
            invoice_reference = payload["invoice_reference"]
            invoice_record = self._invoice_records.get(invoice_reference)
            if invoice_record is not None:
                subscription = self._subscriptions.get(invoice_record["subscription_id"])
                if subscription is not None:
                    subscription["paid_invoice_minor"] = subscription.get("paid_invoice_minor", 0) + invoice_record["amount_minor"]
            self._paid_invoice_references.add(invoice_reference)
        elif event_type.startswith("billing.invoice.due_date_extended"):
            invoice_reference = payload["invoice_reference"]
            invoice_record = self._invoice_records.get(invoice_reference)
            if invoice_record is not None:
                invoice_record["due_on"] = payload["new_due_on"]
        elif event_type.startswith("billing.invoice.dispute.opened"):
            invoice_reference = payload["invoice_reference"]
            self._disputed_invoice_references.add(invoice_reference)
        elif event_type.startswith("billing.invoice.dispute.resolved"):
            invoice_reference = payload["invoice_reference"]
            self._disputed_invoice_references.discard(invoice_reference)
        elif event_type.startswith("billing.invoice.reminder.sent"):
            invoice_reference = payload["invoice_reference"]
            self._invoice_reminder_counts[invoice_reference] = self._invoice_reminder_counts.get(invoice_reference, 0) + 1
            subscription = self._subscriptions.get(payload["subscription_id"])
            if subscription is not None:
                subscription["invoice_reminders_sent"] = subscription.get("invoice_reminders_sent", 0) + 1
        elif event_type.startswith("billing.usage.metered"):
            metric_key = payload["metric_key"]
            metric_value = payload["metric_value"]
            subscription_id = payload["subscription_id"]

            current_total = self._usage_totals.get(metric_key, 0)
            self._usage_totals[metric_key] = current_total + metric_value

            subscription_totals = self._subscription_usage_totals.setdefault(subscription_id, {})
            subscription_totals[metric_key] = subscription_totals.get(metric_key, 0) + metric_value

    def get_subscription(self, subscription_id: str) -> Optional[dict]:
        return self._subscriptions.get(subscription_id)

    @property
    def current_plan(self) -> Optional[dict]:
        return self._current_plan

    def get_usage_total(self, metric_key: str) -> int:
        return self._usage_totals.get(metric_key, 0)

    def get_subscription_usage_total(self, subscription_id: str, metric_key: str) -> int:
        subscription_totals = self._subscription_usage_totals.get(subscription_id, {})
        return subscription_totals.get(metric_key, 0)

    def has_payment_reference(self, payment_reference: str) -> bool:
        return payment_reference in self._payment_references

    def resolve_payment_reference(self, payment_reference: str) -> Optional[dict]:
        payment_record = self._payment_records.get(payment_reference)
        if payment_record is None:
            return None
        return dict(payment_record)

    def is_payment_reference_reversed(self, payment_reference: str) -> bool:
        return payment_reference in self._reversed_payment_references

    def has_invoice_reference(self, invoice_reference: str) -> bool:
        return invoice_reference in self._invoice_references

    def resolve_invoice_reference(self, invoice_reference: str) -> Optional[dict]:
        invoice_record = self._invoice_records.get(invoice_reference)
        if invoice_record is None:
            return None
        return dict(invoice_record)

    def is_invoice_reference_voided(self, invoice_reference: str) -> bool:
        return invoice_reference in self._voided_invoice_references

    def is_invoice_reference_paid(self, invoice_reference: str) -> bool:
        return invoice_reference in self._paid_invoice_references

    def is_invoice_reference_disputed(self, invoice_reference: str) -> bool:
        return invoice_reference in self._disputed_invoice_references

    def snapshot(self) -> dict:
        subscriptions = {key: dict(value) for key, value in self._subscriptions.items()}
        usage_totals = dict(self._usage_totals)
        subscription_usage_totals = {
            subscription_id: dict(metric_totals)
            for subscription_id, metric_totals in self._subscription_usage_totals.items()
        }
        return {
            "current_plan": None if self._current_plan is None else dict(self._current_plan),
            "subscriptions": subscriptions,
            "usage_totals": usage_totals,
            "subscription_usage_totals": subscription_usage_totals,
            "payment_references": tuple(sorted(self._payment_references)),
            "reversed_payment_references": tuple(sorted(self._reversed_payment_references)),
            "invoice_references": tuple(sorted(self._invoice_references)),
            "voided_invoice_references": tuple(sorted(self._voided_invoice_references)),
            "paid_invoice_references": tuple(sorted(self._paid_invoice_references)),
            "disputed_invoice_references": tuple(sorted(self._disputed_invoice_references)),
            "invoice_reminder_counts": dict(self._invoice_reminder_counts),
        }


PAYLOAD_BUILDERS = {
    "billing.plan.assign.request": build_plan_assigned_payload,
    "billing.subscription.start.request": build_subscription_started_payload,
    "billing.payment.record.request": build_payment_recorded_payload,
    "billing.payment.reverse.request": build_payment_reversed_payload,
    "billing.subscription.suspend.request": build_subscription_suspended_payload,
    "billing.subscription.renew.request": build_subscription_renewed_payload,
    "billing.subscription.cancel.request": build_subscription_cancelled_payload,
    "billing.subscription.resume.request": build_subscription_resumed_payload,
    "billing.subscription.plan_change.request": build_subscription_plan_changed_payload,
    "billing.subscription.mark_delinquent.request": build_subscription_delinquent_marked_payload,
    "billing.subscription.clear_delinquency.request": build_subscription_delinquency_cleared_payload,
    "billing.subscription.write_off.request": build_subscription_written_off_payload,
    "billing.subscription.reactivate.request": build_subscription_reactivated_payload,
    "billing.subscription.close.request": build_subscription_closed_payload,
    "billing.invoice.issue.request": build_invoice_issued_payload,
    "billing.invoice.void.request": build_invoice_voided_payload,
    "billing.invoice.mark_paid.request": build_invoice_marked_paid_payload,
    "billing.invoice.due_date.extend.request": build_invoice_due_date_extended_payload,
    "billing.invoice.dispute.open.request": build_invoice_dispute_opened_payload,
    "billing.invoice.dispute.resolve.request": build_invoice_dispute_resolved_payload,
    "billing.invoice.reminder.send.request": build_invoice_reminder_sent_payload,
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

        if command.command_type == "billing.invoice.issue.request":
            duplicate_invoice_rejection = invoice_reference_must_be_unique_policy(
                command,
                invoice_reference_exists=self._projection_store.has_invoice_reference,
            )
            if duplicate_invoice_rejection is not None:
                raise ValueError(duplicate_invoice_rejection.message)

        if command.command_type in {"billing.invoice.void.request", "billing.invoice.mark_paid.request", "billing.invoice.due_date.extend.request", "billing.invoice.dispute.open.request", "billing.invoice.dispute.resolve.request", "billing.invoice.reminder.send.request"}:
            invoice_exists_rejection = invoice_reference_must_exist_policy(
                command,
                invoice_reference_exists=self._projection_store.has_invoice_reference,
            )
            if invoice_exists_rejection is not None:
                raise ValueError(invoice_exists_rejection.message)

            invoice_subscription_match_rejection = invoice_reference_must_belong_to_subscription_policy(
                command,
                resolve_invoice_reference=self._projection_store.resolve_invoice_reference,
            )
            if invoice_subscription_match_rejection is not None:
                raise ValueError(invoice_subscription_match_rejection.message)

        if command.command_type == "billing.invoice.void.request":
            invoice_not_voided_rejection = invoice_reference_must_not_be_voided_policy(
                command,
                invoice_reference_voided=self._projection_store.is_invoice_reference_voided,
            )
            if invoice_not_voided_rejection is not None:
                raise ValueError(invoice_not_voided_rejection.message)

        if command.command_type in {"billing.invoice.mark_paid.request", "billing.invoice.due_date.extend.request", "billing.invoice.dispute.open.request", "billing.invoice.reminder.send.request"}:
            invoice_not_voided_rejection = invoice_reference_must_not_be_voided_policy(
                command,
                invoice_reference_voided=self._projection_store.is_invoice_reference_voided,
            )
            if invoice_not_voided_rejection is not None:
                raise ValueError(invoice_not_voided_rejection.message)

            invoice_not_paid_rejection = invoice_reference_must_not_be_paid_policy(
                command,
                invoice_reference_paid=self._projection_store.is_invoice_reference_paid,
            )
            if invoice_not_paid_rejection is not None:
                raise ValueError(invoice_not_paid_rejection.message)

        if command.command_type in {"billing.invoice.mark_paid.request", "billing.invoice.due_date.extend.request", "billing.invoice.reminder.send.request"}:
            invoice_not_disputed_rejection = invoice_reference_must_not_be_disputed_policy(
                command,
                invoice_reference_disputed=self._projection_store.is_invoice_reference_disputed,
            )
            if invoice_not_disputed_rejection is not None:
                raise ValueError(invoice_not_disputed_rejection.message)

        if command.command_type == "billing.invoice.dispute.open.request":
            invoice_not_disputed_rejection = invoice_reference_must_not_be_disputed_policy(
                command,
                invoice_reference_disputed=self._projection_store.is_invoice_reference_disputed,
            )
            if invoice_not_disputed_rejection is not None:
                raise ValueError(invoice_not_disputed_rejection.message)

        if command.command_type == "billing.invoice.dispute.resolve.request":
            invoice_must_be_disputed_rejection = invoice_reference_must_be_disputed_policy(
                command,
                invoice_reference_disputed=self._projection_store.is_invoice_reference_disputed,
            )
            if invoice_must_be_disputed_rejection is not None:
                raise ValueError(invoice_must_be_disputed_rejection.message)

        if command.command_type == "billing.payment.record.request":
            duplicate_payment_rejection = payment_reference_must_be_unique_policy(
                command,
                payment_reference_exists=self._projection_store.has_payment_reference,
            )
            if duplicate_payment_rejection is not None:
                raise ValueError(duplicate_payment_rejection.message)

        if command.command_type == "billing.payment.reverse.request":
            payment_exists_rejection = payment_reference_must_exist_policy(
                command,
                payment_reference_exists=self._projection_store.has_payment_reference,
            )
            if payment_exists_rejection is not None:
                raise ValueError(payment_exists_rejection.message)

            not_reversed_rejection = payment_reference_must_not_be_reversed_policy(
                command,
                payment_reference_reversed=self._projection_store.is_payment_reference_reversed,
            )
            if not_reversed_rejection is not None:
                raise ValueError(not_reversed_rejection.message)

            subscription_match_rejection = payment_reference_must_belong_to_subscription_policy(
                command,
                resolve_payment_reference=self._projection_store.resolve_payment_reference,
            )
            if subscription_match_rejection is not None:
                raise ValueError(subscription_match_rejection.message)

        if command.command_type == "billing.subscription.start.request":
            unique_rejection = subscription_must_not_exist_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if unique_rejection is not None:
                raise ValueError(unique_rejection.message)

        if command.command_type in {
            "billing.payment.record.request",
            "billing.payment.reverse.request",
            "billing.subscription.suspend.request",
            "billing.subscription.renew.request",
            "billing.subscription.cancel.request",
            "billing.subscription.resume.request",
            "billing.subscription.plan_change.request",
            "billing.subscription.mark_delinquent.request",
            "billing.subscription.clear_delinquency.request",
            "billing.subscription.write_off.request",
            "billing.subscription.reactivate.request",
            "billing.subscription.close.request",
            "billing.invoice.issue.request",
            "billing.invoice.void.request",
            "billing.invoice.mark_paid.request",
            "billing.invoice.due_date.extend.request",
            "billing.invoice.dispute.open.request",
            "billing.invoice.dispute.resolve.request",
            "billing.invoice.reminder.send.request",
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
            "billing.subscription.mark_delinquent.request",
            "billing.subscription.clear_delinquency.request",
            "billing.subscription.write_off.request",
            "billing.usage.meter.request",
        }:
            cancelled_rejection = subscription_must_not_be_cancelled_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if cancelled_rejection is not None:
                raise ValueError(cancelled_rejection.message)

        if command.command_type in {
            "billing.subscription.suspend.request",
            "billing.subscription.renew.request",
            "billing.subscription.cancel.request",
            "billing.subscription.resume.request",
            "billing.subscription.plan_change.request",
            "billing.subscription.mark_delinquent.request",
            "billing.subscription.clear_delinquency.request",
            "billing.subscription.write_off.request",
            "billing.subscription.reactivate.request",
            "billing.subscription.close.request",
            "billing.invoice.issue.request",
            "billing.invoice.void.request",
            "billing.invoice.mark_paid.request",
            "billing.invoice.due_date.extend.request",
            "billing.invoice.dispute.open.request",
            "billing.invoice.dispute.resolve.request",
            "billing.invoice.reminder.send.request",
            "billing.payment.record.request",
            "billing.payment.reverse.request",
            "billing.usage.meter.request",
        }:
            written_off_rejection = subscription_must_not_be_written_off_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if written_off_rejection is not None:
                raise ValueError(written_off_rejection.message)

        if command.command_type in {
            "billing.subscription.suspend.request",
            "billing.subscription.renew.request",
            "billing.subscription.cancel.request",
            "billing.subscription.resume.request",
            "billing.subscription.plan_change.request",
            "billing.subscription.mark_delinquent.request",
            "billing.subscription.clear_delinquency.request",
            "billing.subscription.write_off.request",
            "billing.subscription.reactivate.request",
            "billing.subscription.close.request",
            "billing.invoice.issue.request",
            "billing.invoice.void.request",
            "billing.invoice.mark_paid.request",
            "billing.invoice.due_date.extend.request",
            "billing.invoice.dispute.open.request",
            "billing.invoice.dispute.resolve.request",
            "billing.invoice.reminder.send.request",
            "billing.payment.record.request",
            "billing.payment.reverse.request",
            "billing.usage.meter.request",
        }:
            closed_rejection = subscription_must_not_be_closed_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if closed_rejection is not None:
                raise ValueError(closed_rejection.message)

        if command.command_type in {
            "billing.subscription.resume.request",
            "billing.subscription.renew.request",
            "billing.subscription.plan_change.request",
            "billing.payment.record.request",
            "billing.payment.reverse.request",
            "billing.usage.meter.request",
            "billing.subscription.mark_delinquent.request",
            "billing.invoice.issue.request",
            "billing.invoice.void.request",
            "billing.invoice.mark_paid.request",
            "billing.invoice.due_date.extend.request",
            "billing.invoice.dispute.open.request",
            "billing.invoice.dispute.resolve.request",
            "billing.invoice.reminder.send.request",
        }:
            delinquent_rejection = subscription_must_not_be_delinquent_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if delinquent_rejection is not None:
                raise ValueError(delinquent_rejection.message)

        if command.command_type in {
            "billing.subscription.clear_delinquency.request",
            "billing.subscription.write_off.request",
        }:
            must_be_delinquent_rejection = subscription_must_be_delinquent_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if must_be_delinquent_rejection is not None:
                raise ValueError(must_be_delinquent_rejection.message)

        if command.command_type in {
            "billing.subscription.reactivate.request",
            "billing.subscription.close.request",
        }:
            must_be_cancelled_rejection = subscription_must_be_cancelled_policy(
                command,
                subscription_lookup=self._projection_store.get_subscription,
            )
            if must_be_cancelled_rejection is not None:
                raise ValueError(must_be_cancelled_rejection.message)

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
            "billing.payment.reverse.request",
            "billing.usage.meter.request",
            "billing.subscription.plan_change.request",
            "billing.subscription.mark_delinquent.request",
            "billing.invoice.issue.request",
            "billing.invoice.void.request",
            "billing.invoice.mark_paid.request",
            "billing.invoice.due_date.extend.request",
            "billing.invoice.dispute.open.request",
            "billing.invoice.dispute.resolve.request",
            "billing.invoice.reminder.send.request",
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
