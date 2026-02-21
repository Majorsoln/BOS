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
