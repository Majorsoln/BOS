"""
Tests for BOS SaaS — Subscription Lifecycle Management
"""

import uuid
from datetime import datetime

import pytest

from core.saas.subscriptions import (
    SUBSCRIPTION_ACTIVATED_V1,
    SUBSCRIPTION_CANCELLED_V1,
    SUBSCRIPTION_RENEWED_V1,
    SUBSCRIPTION_SUSPENDED_V1,
    SUBSCRIPTION_UPGRADED_V1,
    ActivateSubscriptionRequest,
    CancelSubscriptionRequest,
    RenewSubscriptionRequest,
    SubscriptionManager,
    SubscriptionProjection,
    SubscriptionStatus,
    SuspendSubscriptionRequest,
    UpgradeSubscriptionRequest,
)


NOW = datetime(2025, 6, 1, 12, 0, 0)
BIZ_ID = uuid.uuid4()
PLAN_A = uuid.uuid4()
PLAN_B = uuid.uuid4()


@pytest.fixture
def projection():
    return SubscriptionProjection()


@pytest.fixture
def manager(projection):
    return SubscriptionManager(projection)


def _activate(manager, biz_id=None, plan_id=None):
    return manager.activate(ActivateSubscriptionRequest(
        business_id=biz_id or BIZ_ID,
        plan_id=plan_id or PLAN_A,
        actor_id="admin-1",
        issued_at=NOW,
    ))


class TestSubscriptionActivation:
    def test_activate_returns_subscription_id(self, manager):
        result = _activate(manager)
        assert "subscription_id" in result
        assert isinstance(result["subscription_id"], uuid.UUID)

    def test_activate_emits_event(self, manager):
        result = _activate(manager)
        assert result["events"][0]["event_type"] == SUBSCRIPTION_ACTIVATED_V1

    def test_activate_creates_active_subscription(self, manager, projection):
        _activate(manager)
        sub = projection.get_subscription(BIZ_ID)
        assert sub is not None
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.plan_id == PLAN_A

    def test_double_activate_rejected(self, manager):
        _activate(manager)
        result = _activate(manager)
        assert "rejected" in result
        assert result["rejected"].code == "SUBSCRIPTION_ALREADY_ACTIVE"

    def test_reactivate_after_cancel(self, manager):
        _activate(manager)
        manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        result = _activate(manager)
        assert "subscription_id" in result


class TestSubscriptionRenewal:
    def test_renew_active_subscription(self, manager, projection):
        _activate(manager)
        rejection = manager.renew(RenewSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        sub = projection.get_subscription(BIZ_ID)
        assert sub.renewal_count == 1

    def test_double_renew_increments_count(self, manager, projection):
        _activate(manager)
        manager.renew(RenewSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        manager.renew(RenewSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        sub = projection.get_subscription(BIZ_ID)
        assert sub.renewal_count == 2

    def test_renew_no_subscription_rejected(self, manager):
        rejection = manager.renew(RenewSubscriptionRequest(
            business_id=uuid.uuid4(), actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "NO_SUBSCRIPTION"

    def test_renew_cancelled_rejected(self, manager):
        _activate(manager)
        manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.renew(RenewSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "SUBSCRIPTION_NOT_ACTIVE"


class TestSubscriptionCancellation:
    def test_cancel_active_subscription(self, manager, projection):
        _activate(manager)
        rejection = manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        sub = projection.get_subscription(BIZ_ID)
        assert sub.status == SubscriptionStatus.CANCELLED

    def test_cancel_suspended_subscription(self, manager, projection):
        _activate(manager)
        manager.suspend(SuspendSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        sub = projection.get_subscription(BIZ_ID)
        assert sub.status == SubscriptionStatus.CANCELLED

    def test_double_cancel_rejected(self, manager):
        _activate(manager)
        manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "INVALID_SUBSCRIPTION_TRANSITION"


class TestSubscriptionSuspension:
    def test_suspend_active_subscription(self, manager, projection):
        _activate(manager)
        rejection = manager.suspend(SuspendSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        sub = projection.get_subscription(BIZ_ID)
        assert sub.status == SubscriptionStatus.SUSPENDED

    def test_reactivate_after_suspend(self, manager, projection):
        _activate(manager)
        manager.suspend(SuspendSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        # After suspension, activating creates a new subscription
        result = _activate(manager)
        assert "subscription_id" in result
        sub = projection.get_subscription(BIZ_ID)
        assert sub.status == SubscriptionStatus.ACTIVE


class TestSubscriptionUpgrade:
    def test_upgrade_plan(self, manager, projection):
        _activate(manager)
        rejection = manager.upgrade(UpgradeSubscriptionRequest(
            business_id=BIZ_ID, new_plan_id=PLAN_B,
            actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        sub = projection.get_subscription(BIZ_ID)
        assert sub.plan_id == PLAN_B
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_upgrade_same_plan_rejected(self, manager):
        _activate(manager)
        rejection = manager.upgrade(UpgradeSubscriptionRequest(
            business_id=BIZ_ID, new_plan_id=PLAN_A,
            actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "SAME_PLAN"

    def test_upgrade_no_subscription_rejected(self, manager):
        rejection = manager.upgrade(UpgradeSubscriptionRequest(
            business_id=uuid.uuid4(), new_plan_id=PLAN_B,
            actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "NO_SUBSCRIPTION"

    def test_upgrade_cancelled_rejected(self, manager):
        _activate(manager)
        manager.cancel(CancelSubscriptionRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.upgrade(UpgradeSubscriptionRequest(
            business_id=BIZ_ID, new_plan_id=PLAN_B,
            actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "SUBSCRIPTION_NOT_ACTIVE"


class TestSubscriptionProjectionQueries:
    def test_list_active_subscriptions(self, manager, projection):
        _activate(manager)
        biz2 = uuid.uuid4()
        _activate(manager, biz_id=biz2)
        assert len(projection.list_active_subscriptions()) == 2

    def test_list_by_plan(self, manager, projection):
        _activate(manager)
        biz2 = uuid.uuid4()
        _activate(manager, biz_id=biz2, plan_id=PLAN_B)
        assert len(projection.list_by_plan(PLAN_A)) == 1
        assert len(projection.list_by_plan(PLAN_B)) == 1

    def test_is_active(self, manager):
        _activate(manager)
        assert manager.is_active(BIZ_ID) is True
        assert manager.is_active(uuid.uuid4()) is False

    def test_truncate_specific(self, manager, projection):
        _activate(manager)
        projection.truncate(BIZ_ID)
        assert projection.get_subscription(BIZ_ID) is None

    def test_truncate_all(self, manager, projection):
        _activate(manager)
        projection.truncate()
        assert len(projection.list_active_subscriptions()) == 0
