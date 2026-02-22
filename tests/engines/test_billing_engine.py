"""BOS Billing Engine tests (Phase 12 implementation slice)."""

import uuid
from datetime import datetime, timezone

import pytest

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 21, 9, 0, 0, tzinfo=timezone.utc)


def kw():
    return dict(
        business_id=BIZ,
        actor_type="HUMAN",
        actor_id="owner-1",
        command_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        issued_at=NOW,
    )


class StubReg:
    def __init__(self):
        self.types = set()

    def register(self, event_type):
        self.types.add(event_type)


class StubFactory:
    def __call__(self, *, command, event_type, payload):
        return {
            "event_type": event_type,
            "payload": payload,
            "business_id": command.business_id,
            "source_engine": command.source_engine,
        }


class StubPersist:
    def __init__(self):
        self.calls = []

    def __call__(self, *, event_data, context, registry, **kwargs):
        self.calls.append(event_data)
        return {"accepted": True}


class StubBus:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, command_type, handler):
        self.handlers[command_type] = handler


class TestBillingCommands:
    def test_plan_assign_request_to_command(self):
        from engines.billing.commands import PlanAssignRequest

        cmd = PlanAssignRequest(plan_code="STARTER", seats=3).to_command(**kw())
        assert cmd.command_type == "billing.plan.assign.request"
        assert cmd.payload["seats"] == 3

    def test_invalid_plan_rejected(self):
        from engines.billing.commands import PlanAssignRequest

        with pytest.raises(ValueError, match="not valid"):
            PlanAssignRequest(plan_code="UNKNOWN")


class TestBillingService:
    def _svc(self):
        from engines.billing.services import BillingService

        return BillingService(
            business_context={"business_id": BIZ},
            command_bus=StubBus(),
            event_factory=StubFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
        )

    def test_full_flow_assign_start_pay_suspend(self):
        from engines.billing.commands import (
            PaymentRecordRequest,
            PaymentReverseRequest,
            PlanAssignRequest,
            SubscriptionStartRequest,
            SubscriptionSuspendRequest,
            SubscriptionRenewRequest,
            SubscriptionCancelRequest,
            SubscriptionResumeRequest,
            SubscriptionPlanChangeRequest,
            SubscriptionMarkDelinquentRequest,
            SubscriptionClearDelinquencyRequest,
            SubscriptionWriteOffRequest,
            SubscriptionReactivateRequest,
            UsageMeterRequest,
        )

        svc = self._svc()

        assign_result = svc._execute_command(PlanAssignRequest(
            plan_code="GROWTH", cycle="MONTHLY", seats=5,
        ).to_command(**kw()))
        assert assign_result.projection_applied is True
        assert svc.projection_store.current_plan["plan_code"] == "GROWTH"

        sub_id = "sub-001"
        start_result = svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="GROWTH",
            cycle="MONTHLY",
        ).to_command(**kw()))
        assert start_result.event_type == "billing.subscription.started.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "ACTIVE"

        pay_result = svc._execute_command(PaymentRecordRequest(
            subscription_id=sub_id,
            payment_reference="pay-001",
            amount_minor=450000,
            currency="USD",
        ).to_command(**kw()))
        assert pay_result.event_type == "billing.payment.recorded.v1"
        assert svc.projection_store.get_subscription(sub_id)["paid_minor"] == 450000

        reverse_result = svc._execute_command(PaymentReverseRequest(
            subscription_id=sub_id,
            payment_reference="pay-001",
            reversal_reason="duplicate capture",
        ).to_command(**kw()))
        assert reverse_result.event_type == "billing.payment.reversed.v1"
        assert svc.projection_store.get_subscription(sub_id)["paid_minor"] == 0

        suspend_result = svc._execute_command(SubscriptionSuspendRequest(
            subscription_id=sub_id,
            reason="payment overdue",
        ).to_command(**kw()))
        assert suspend_result.event_type == "billing.subscription.suspended.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "SUSPENDED"

        resume_result = svc._execute_command(SubscriptionResumeRequest(
            subscription_id=sub_id,
            resume_reason="manual review complete",
        ).to_command(**kw()))
        assert resume_result.event_type == "billing.subscription.resumed.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "ACTIVE"

        plan_change_result = svc._execute_command(SubscriptionPlanChangeRequest(
            subscription_id=sub_id,
            new_plan_code="ENTERPRISE",
            change_reason="upgrade requested",
        ).to_command(**kw()))
        assert plan_change_result.event_type == "billing.subscription.plan_changed.v1"
        assert svc.projection_store.get_subscription(sub_id)["plan_code"] == "ENTERPRISE"

        renew_result = svc._execute_command(SubscriptionRenewRequest(
            subscription_id=sub_id,
            renewal_reference="ren-001",
        ).to_command(**kw()))
        assert renew_result.event_type == "billing.subscription.renewed.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "ACTIVE"


        usage_result = svc._execute_command(UsageMeterRequest(
            subscription_id=sub_id,
            metric_key="API_CALLS",
            metric_value=120,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw()))
        assert usage_result.event_type == "billing.usage.metered.v1"
        assert svc.projection_store.get_usage_total("API_CALLS") == 120
        assert svc.projection_store.get_subscription_usage_total(sub_id, "API_CALLS") == 120

        delinquent_result = svc._execute_command(SubscriptionMarkDelinquentRequest(
            subscription_id=sub_id,
            delinquency_reason="invoice overdue",
        ).to_command(**kw()))
        assert delinquent_result.event_type == "billing.subscription.delinquent_marked.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "DELINQUENT"

        with pytest.raises(ValueError, match="DELINQUENT"):
            svc._execute_command(SubscriptionRenewRequest(
                subscription_id=sub_id,
                renewal_reference="ren-delinquent",
            ).to_command(**kw()))

        clear_result = svc._execute_command(SubscriptionClearDelinquencyRequest(
            subscription_id=sub_id,
            clearance_reason="arrears settled",
        ).to_command(**kw()))
        assert clear_result.event_type == "billing.subscription.delinquency_cleared.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "ACTIVE"

        renew_after_clear_result = svc._execute_command(SubscriptionRenewRequest(
            subscription_id=sub_id,
            renewal_reference="ren-after-clear",
        ).to_command(**kw()))
        assert renew_after_clear_result.event_type == "billing.subscription.renewed.v1"

        write_off_sub_id = "sub-write-off"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=write_off_sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionMarkDelinquentRequest(
            subscription_id=write_off_sub_id,
            delinquency_reason="chronic arrears",
        ).to_command(**kw()))
        write_off_result = svc._execute_command(SubscriptionWriteOffRequest(
            subscription_id=write_off_sub_id,
            write_off_reason="debt unrecoverable",
        ).to_command(**kw()))
        assert write_off_result.event_type == "billing.subscription.written_off.v1"
        assert svc.projection_store.get_subscription(write_off_sub_id)["status"] == "WRITTEN_OFF"

        cancel_result = svc._execute_command(SubscriptionCancelRequest(
            subscription_id=sub_id,
            cancellation_reason="customer requested cancellation",
        ).to_command(**kw()))
        assert cancel_result.event_type == "billing.subscription.cancelled.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "CANCELLED"

        reactivate_result = svc._execute_command(SubscriptionReactivateRequest(
            subscription_id=sub_id,
            reactivation_reason="customer returned",
        ).to_command(**kw()))
        assert reactivate_result.event_type == "billing.subscription.reactivated.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "ACTIVE"

        payment_after_reactivate = svc._execute_command(PaymentRecordRequest(
            subscription_id=sub_id,
            payment_reference="pay-after-reactivate",
            amount_minor=100,
            currency="USD",
        ).to_command(**kw()))
        assert payment_after_reactivate.event_type == "billing.payment.recorded.v1"


    def test_payment_requires_existing_subscription(self):
        from engines.billing.commands import PaymentRecordRequest

        svc = self._svc()
        cmd = PaymentRecordRequest(
            subscription_id="missing-sub",
            payment_reference="pay-xyz",
            amount_minor=1000,
            currency="USD",
        ).to_command(**kw())

        with pytest.raises(ValueError, match="not found"):
            svc._execute_command(cmd)

    def test_duplicate_subscription_start_rejected(self):
        from engines.billing.commands import SubscriptionStartRequest

        svc = self._svc()
        start_cmd = SubscriptionStartRequest(
            subscription_id="sub-dup",
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw())
        svc._execute_command(start_cmd)

        with pytest.raises(ValueError, match="already exists"):
            svc._execute_command(start_cmd)

    def test_renew_requires_existing_subscription(self):
        from engines.billing.commands import SubscriptionRenewRequest

        svc = self._svc()
        cmd = SubscriptionRenewRequest(
            subscription_id="missing-sub",
            renewal_reference="ren-missing",
        ).to_command(**kw())

        with pytest.raises(ValueError, match="not found"):
            svc._execute_command(cmd)

    def test_invalid_usage_metric_rejected(self):
        from engines.billing.commands import SubscriptionStartRequest, UsageMeterRequest

        svc = self._svc()
        sub_id = "sub-usage-invalid"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        cmd = UsageMeterRequest(
            subscription_id=sub_id,
            metric_key="API_CALLS",
            metric_value=0,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw())
        cmd.payload["metric_value"] = -1

        with pytest.raises(ValueError, match=">= 0"):
            svc._execute_command(cmd)

    def test_payment_requires_active_subscription(self):
        from engines.billing.commands import (
            PaymentRecordRequest,
            PaymentReverseRequest,
            SubscriptionCancelRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-inactive"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionCancelRequest(
            subscription_id=sub_id,
            cancellation_reason="closed",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not ACTIVE"):
            svc._execute_command(PaymentRecordRequest(
                subscription_id=sub_id,
                payment_reference="pay-after-cancel",
                amount_minor=100,
                currency="USD",
            ).to_command(**kw()))

    def test_replay_snapshot_is_deterministic(self):
        from engines.billing.commands import (
            PlanAssignRequest,
            SubscriptionStartRequest,
            PaymentRecordRequest,
            PaymentReverseRequest,
            UsageMeterRequest,
        )
        from engines.billing.services import BillingProjectionStore

        svc = self._svc()

        events = []
        assign = svc._execute_command(PlanAssignRequest(
            plan_code="GROWTH", cycle="MONTHLY", seats=3,
        ).to_command(**kw()))
        events.append(assign.event_data)

        start = svc._execute_command(SubscriptionStartRequest(
            subscription_id="sub-replay",
            plan_code="GROWTH",
            cycle="MONTHLY",
        ).to_command(**kw()))
        events.append(start.event_data)

        payment = svc._execute_command(PaymentRecordRequest(
            subscription_id="sub-replay",
            payment_reference="pay-replay",
            amount_minor=500,
            currency="USD",
        ).to_command(**kw()))
        events.append(payment.event_data)

        usage = svc._execute_command(UsageMeterRequest(
            subscription_id="sub-replay",
            metric_key="EVENTS_APPENDED",
            metric_value=10,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw()))
        events.append(usage.event_data)

        replay_store = BillingProjectionStore()
        for event in events:
            replay_store.apply(event["event_type"], event["payload"])

        assert replay_store.snapshot() == svc.projection_store.snapshot()

    def test_event_payload_has_business_scope(self):
        from engines.billing.commands import PlanAssignRequest

        svc = self._svc()
        result = svc._execute_command(PlanAssignRequest(
            plan_code="STARTER", cycle="MONTHLY", seats=2,
        ).to_command(**kw()))

        payload = result.event_data["payload"]
        assert payload["business_id"] == BIZ
        assert "branch_id" in payload

    def test_duplicate_payment_reference_rejected(self):
        from engines.billing.commands import (
            PaymentRecordRequest,
            PaymentReverseRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-pay-dup"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        first = PaymentRecordRequest(
            subscription_id=sub_id,
            payment_reference="pay-dup",
            amount_minor=1000,
            currency="USD",
        ).to_command(**kw())
        svc._execute_command(first)

        second = PaymentRecordRequest(
            subscription_id=sub_id,
            payment_reference="pay-dup",
            amount_minor=2000,
            currency="USD",
        ).to_command(**kw())
        with pytest.raises(ValueError, match="already recorded"):
            svc._execute_command(second)

    def test_renew_rejected_for_cancelled_subscription(self):
        from engines.billing.commands import (
            SubscriptionCancelRequest,
            SubscriptionRenewRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-cancelled"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="GROWTH",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionCancelRequest(
            subscription_id=sub_id,
            cancellation_reason="closed account",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="CANCELLED"):
            svc._execute_command(SubscriptionRenewRequest(
                subscription_id=sub_id,
                renewal_reference="ren-after-cancel",
            ).to_command(**kw()))

    def test_resume_requires_suspended_subscription(self):
        from engines.billing.commands import (
            SubscriptionResumeRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-not-suspended"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not SUSPENDED"):
            svc._execute_command(SubscriptionResumeRequest(
                subscription_id=sub_id,
                resume_reason="attempted resume",
            ).to_command(**kw()))

    def test_resume_rejected_for_cancelled_subscription(self):
        from engines.billing.commands import (
            SubscriptionCancelRequest,
            SubscriptionResumeRequest,
            SubscriptionStartRequest,
            SubscriptionSuspendRequest,
        )

        svc = self._svc()
        sub_id = "sub-cancelled-resume"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionSuspendRequest(
            subscription_id=sub_id,
            reason="late payment",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionCancelRequest(
            subscription_id=sub_id,
            cancellation_reason="terminated",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="CANCELLED"):
            svc._execute_command(SubscriptionResumeRequest(
                subscription_id=sub_id,
                resume_reason="resume blocked",
            ).to_command(**kw()))

    def test_plan_change_requires_active_subscription(self):
        from engines.billing.commands import (
            SubscriptionPlanChangeRequest,
            SubscriptionStartRequest,
            SubscriptionSuspendRequest,
        )

        svc = self._svc()
        sub_id = "sub-plan-inactive"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionSuspendRequest(
            subscription_id=sub_id,
            reason="risk hold",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not ACTIVE"):
            svc._execute_command(SubscriptionPlanChangeRequest(
                subscription_id=sub_id,
                new_plan_code="GROWTH",
                change_reason="upgrade",
            ).to_command(**kw()))

    def test_plan_change_rejected_when_target_same(self):
        from engines.billing.commands import (
            SubscriptionPlanChangeRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-plan-same"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="GROWTH",
            cycle="MONTHLY",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="already on plan"):
            svc._execute_command(SubscriptionPlanChangeRequest(
                subscription_id=sub_id,
                new_plan_code="GROWTH",
                change_reason="noop",
            ).to_command(**kw()))

    def test_usage_requires_existing_subscription(self):
        from engines.billing.commands import UsageMeterRequest

        svc = self._svc()
        cmd = UsageMeterRequest(
            subscription_id="missing-usage-sub",
            metric_key="API_CALLS",
            metric_value=1,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw())

        with pytest.raises(ValueError, match="not found"):
            svc._execute_command(cmd)

    def test_usage_totals_are_partitioned_by_subscription(self):
        from engines.billing.commands import SubscriptionStartRequest, UsageMeterRequest

        svc = self._svc()
        sub_a = "sub-usage-a"
        sub_b = "sub-usage-b"

        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_a,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_b,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        svc._execute_command(UsageMeterRequest(
            subscription_id=sub_a,
            metric_key="API_CALLS",
            metric_value=5,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw()))
        svc._execute_command(UsageMeterRequest(
            subscription_id=sub_b,
            metric_key="API_CALLS",
            metric_value=9,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw()))

        assert svc.projection_store.get_subscription_usage_total(sub_a, "API_CALLS") == 5
        assert svc.projection_store.get_subscription_usage_total(sub_b, "API_CALLS") == 9
        assert svc.projection_store.get_usage_total("API_CALLS") == 14

    def test_mark_delinquent_requires_existing_subscription(self):
        from engines.billing.commands import SubscriptionMarkDelinquentRequest

        svc = self._svc()
        cmd = SubscriptionMarkDelinquentRequest(
            subscription_id="missing-delinquent-sub",
            delinquency_reason="overdue",
        ).to_command(**kw())

        with pytest.raises(ValueError, match="not found"):
            svc._execute_command(cmd)

    def test_usage_rejected_for_delinquent_subscription(self):
        from engines.billing.commands import (
            SubscriptionMarkDelinquentRequest,
            SubscriptionStartRequest,
            UsageMeterRequest,
        )

        svc = self._svc()
        sub_id = "sub-delinquent-usage"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionMarkDelinquentRequest(
            subscription_id=sub_id,
            delinquency_reason="arrears",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="DELINQUENT"):
            svc._execute_command(UsageMeterRequest(
                subscription_id=sub_id,
                metric_key="API_CALLS",
                metric_value=1,
                period_start="2026-02-01",
                period_end="2026-02-01",
            ).to_command(**kw()))

    def test_clear_delinquency_requires_delinquent_status(self):
        from engines.billing.commands import (
            SubscriptionClearDelinquencyRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-clear-not-delinquent"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not DELINQUENT"):
            svc._execute_command(SubscriptionClearDelinquencyRequest(
                subscription_id=sub_id,
                clearance_reason="manual clear",
            ).to_command(**kw()))

    def test_clear_delinquency_allows_usage_again(self):
        from engines.billing.commands import (
            SubscriptionClearDelinquencyRequest,
            SubscriptionMarkDelinquentRequest,
            SubscriptionStartRequest,
            UsageMeterRequest,
        )

        svc = self._svc()
        sub_id = "sub-clear-usage"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionMarkDelinquentRequest(
            subscription_id=sub_id,
            delinquency_reason="arrears",
        ).to_command(**kw()))

        svc._execute_command(SubscriptionClearDelinquencyRequest(
            subscription_id=sub_id,
            clearance_reason="paid",
        ).to_command(**kw()))

        result = svc._execute_command(UsageMeterRequest(
            subscription_id=sub_id,
            metric_key="API_CALLS",
            metric_value=3,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw()))
        assert result.event_type == "billing.usage.metered.v1"

    def test_payment_reverse_requires_existing_reference(self):
        from engines.billing.commands import (
            PaymentReverseRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-rev-missing"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not found"):
            svc._execute_command(PaymentReverseRequest(
                subscription_id=sub_id,
                payment_reference="pay-missing",
                reversal_reason="not found",
            ).to_command(**kw()))

    def test_payment_reverse_rejects_already_reversed_reference(self):
        from engines.billing.commands import (
            PaymentRecordRequest,
            PaymentReverseRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-rev-dup"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(PaymentRecordRequest(
            subscription_id=sub_id,
            payment_reference="pay-rev-1",
            amount_minor=100,
            currency="USD",
        ).to_command(**kw()))
        svc._execute_command(PaymentReverseRequest(
            subscription_id=sub_id,
            payment_reference="pay-rev-1",
            reversal_reason="correction",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="already reversed"):
            svc._execute_command(PaymentReverseRequest(
                subscription_id=sub_id,
                payment_reference="pay-rev-1",
                reversal_reason="second reversal",
            ).to_command(**kw()))

    def test_payment_reverse_requires_reference_subscription_match(self):
        from engines.billing.commands import (
            PaymentRecordRequest,
            PaymentReverseRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_a = "sub-rev-a"
        sub_b = "sub-rev-b"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_a,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_b,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(PaymentRecordRequest(
            subscription_id=sub_a,
            payment_reference="pay-sub-a",
            amount_minor=100,
            currency="USD",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="does not belong"):
            svc._execute_command(PaymentReverseRequest(
                subscription_id=sub_b,
                payment_reference="pay-sub-a",
                reversal_reason="wrong sub",
            ).to_command(**kw()))

    def test_write_off_requires_delinquent_status(self):
        from engines.billing.commands import (
            SubscriptionStartRequest,
            SubscriptionWriteOffRequest,
        )

        svc = self._svc()
        sub_id = "sub-writeoff-not-delinquent"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not DELINQUENT"):
            svc._execute_command(SubscriptionWriteOffRequest(
                subscription_id=sub_id,
                write_off_reason="bad debt",
            ).to_command(**kw()))

    def test_clear_delinquency_rejected_for_written_off_subscription(self):
        from engines.billing.commands import (
            SubscriptionClearDelinquencyRequest,
            SubscriptionMarkDelinquentRequest,
            SubscriptionStartRequest,
            SubscriptionWriteOffRequest,
        )

        svc = self._svc()
        sub_id = "sub-writeoff-block-clear"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionMarkDelinquentRequest(
            subscription_id=sub_id,
            delinquency_reason="arrears",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionWriteOffRequest(
            subscription_id=sub_id,
            write_off_reason="collection exhausted",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="WRITTEN_OFF"):
            svc._execute_command(SubscriptionClearDelinquencyRequest(
                subscription_id=sub_id,
                clearance_reason="late payment",
            ).to_command(**kw()))

    def test_reactivate_requires_cancelled_subscription(self):
        from engines.billing.commands import (
            SubscriptionReactivateRequest,
            SubscriptionStartRequest,
        )

        svc = self._svc()
        sub_id = "sub-reactivate-not-cancelled"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="not CANCELLED"):
            svc._execute_command(SubscriptionReactivateRequest(
                subscription_id=sub_id,
                reactivation_reason="should fail",
            ).to_command(**kw()))

    def test_reactivate_rejected_for_written_off_subscription(self):
        from engines.billing.commands import (
            SubscriptionCancelRequest,
            SubscriptionMarkDelinquentRequest,
            SubscriptionReactivateRequest,
            SubscriptionStartRequest,
            SubscriptionWriteOffRequest,
        )

        svc = self._svc()
        sub_id = "sub-reactivate-written-off"
        svc._execute_command(SubscriptionStartRequest(
            subscription_id=sub_id,
            plan_code="STARTER",
            cycle="MONTHLY",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionMarkDelinquentRequest(
            subscription_id=sub_id,
            delinquency_reason="arrears",
        ).to_command(**kw()))
        svc._execute_command(SubscriptionWriteOffRequest(
            subscription_id=sub_id,
            write_off_reason="bad debt",
        ).to_command(**kw()))

        with pytest.raises(ValueError, match="WRITTEN_OFF"):
            svc._execute_command(SubscriptionReactivateRequest(
                subscription_id=sub_id,
                reactivation_reason="blocked",
            ).to_command(**kw()))
