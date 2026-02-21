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
            PlanAssignRequest,
            SubscriptionStartRequest,
            SubscriptionSuspendRequest,
            SubscriptionRenewRequest,
            SubscriptionCancelRequest,
            SubscriptionResumeRequest,
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

        renew_result = svc._execute_command(SubscriptionRenewRequest(
            subscription_id=sub_id,
            renewal_reference="ren-001",
        ).to_command(**kw()))
        assert renew_result.event_type == "billing.subscription.renewed.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "ACTIVE"


        usage_result = svc._execute_command(UsageMeterRequest(
            metric_key="API_CALLS",
            metric_value=120,
            period_start="2026-02-01",
            period_end="2026-02-01",
        ).to_command(**kw()))
        assert usage_result.event_type == "billing.usage.metered.v1"
        assert svc.projection_store.get_usage_total("API_CALLS") == 120

        cancel_result = svc._execute_command(SubscriptionCancelRequest(
            subscription_id=sub_id,
            cancellation_reason="customer requested cancellation",
        ).to_command(**kw()))
        assert cancel_result.event_type == "billing.subscription.cancelled.v1"
        assert svc.projection_store.get_subscription(sub_id)["status"] == "CANCELLED"


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
        from engines.billing.commands import UsageMeterRequest

        svc = self._svc()
        cmd = UsageMeterRequest(
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
