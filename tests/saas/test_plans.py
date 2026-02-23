"""
Tests for BOS SaaS — Subscription Plans & Plan-Based Engine Activation
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from core.saas.plans import (
    PLAN_DEFINED_V1,
    PLAN_DEACTIVATED_V1,
    PLAN_UPDATED_V1,
    DefinePlanRequest,
    DeactivatePlanRequest,
    PlanDefinition,
    PlanManager,
    PlanProjection,
    PlanQuota,
    PlanTier,
    UpdatePlanRequest,
)


NOW = datetime(2025, 6, 1, 12, 0, 0)


@pytest.fixture
def projection():
    return PlanProjection()


@pytest.fixture
def manager(projection):
    return PlanManager(projection)


def _define_starter(manager):
    return manager.define_plan(DefinePlanRequest(
        name="Starter",
        tier="STARTER",
        included_engines=("retail", "accounting"),
        max_branches=1,
        max_users=3,
        max_api_calls_per_month=1000,
        max_documents_per_month=100,
        monthly_price=Decimal("49.00"),
        currency="USD",
        actor_id="admin-1",
        issued_at=NOW,
    ))


class TestPlanDefinition:
    def test_define_plan_returns_plan_id(self, manager):
        result = _define_starter(manager)
        assert "plan_id" in result
        assert isinstance(result["plan_id"], uuid.UUID)

    def test_define_plan_emits_event(self, manager):
        result = _define_starter(manager)
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == PLAN_DEFINED_V1

    def test_plan_exists_in_projection(self, manager, projection):
        result = _define_starter(manager)
        plan = projection.get_plan(result["plan_id"])
        assert plan is not None
        assert plan.name == "Starter"
        assert plan.tier == PlanTier.STARTER
        assert plan.is_active is True

    def test_plan_engines_are_frozenset(self, manager, projection):
        result = _define_starter(manager)
        plan = projection.get_plan(result["plan_id"])
        assert plan.included_engines == frozenset({"retail", "accounting"})

    def test_plan_quota_values(self, manager, projection):
        result = _define_starter(manager)
        plan = projection.get_plan(result["plan_id"])
        assert plan.quota.max_branches == 1
        assert plan.quota.max_users == 3
        assert plan.quota.max_api_calls_per_month == 1000

    def test_plan_pricing(self, manager, projection):
        result = _define_starter(manager)
        plan = projection.get_plan(result["plan_id"])
        assert plan.monthly_price == Decimal("49.00")
        assert plan.currency == "USD"

    def test_invalid_tier_rejected(self, manager):
        result = manager.define_plan(DefinePlanRequest(
            name="Invalid",
            tier="INVALID_TIER",
            included_engines=("retail",),
            max_branches=1,
            max_users=1,
            max_api_calls_per_month=100,
            max_documents_per_month=10,
            monthly_price=Decimal("10.00"),
            currency="USD",
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert "rejected" in result
        assert result["rejected"].code == "INVALID_PLAN_TIER"


class TestPlanUpdate:
    def test_update_plan_name(self, manager, projection):
        result = _define_starter(manager)
        plan_id = result["plan_id"]
        rejection = manager.update_plan(UpdatePlanRequest(
            plan_id=plan_id,
            name="Starter Plus",
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert rejection is None
        plan = projection.get_plan(plan_id)
        assert plan.name == "Starter Plus"

    def test_update_plan_engines(self, manager, projection):
        result = _define_starter(manager)
        plan_id = result["plan_id"]
        manager.update_plan(UpdatePlanRequest(
            plan_id=plan_id,
            included_engines=("retail", "accounting", "inventory"),
            actor_id="admin-1",
            issued_at=NOW,
        ))
        plan = projection.get_plan(plan_id)
        assert "inventory" in plan.included_engines

    def test_update_nonexistent_plan_rejected(self, manager):
        rejection = manager.update_plan(UpdatePlanRequest(
            plan_id=uuid.uuid4(),
            name="Ghost",
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "PLAN_NOT_FOUND"

    def test_update_deactivated_plan_rejected(self, manager):
        result = _define_starter(manager)
        plan_id = result["plan_id"]
        manager.deactivate_plan(DeactivatePlanRequest(
            plan_id=plan_id, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.update_plan(UpdatePlanRequest(
            plan_id=plan_id, name="Revived", actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "PLAN_DEACTIVATED"


class TestPlanDeactivation:
    def test_deactivate_plan(self, manager, projection):
        result = _define_starter(manager)
        plan_id = result["plan_id"]
        rejection = manager.deactivate_plan(DeactivatePlanRequest(
            plan_id=plan_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        plan = projection.get_plan(plan_id)
        assert plan.is_active is False

    def test_double_deactivate_rejected(self, manager):
        result = _define_starter(manager)
        plan_id = result["plan_id"]
        manager.deactivate_plan(DeactivatePlanRequest(
            plan_id=plan_id, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.deactivate_plan(DeactivatePlanRequest(
            plan_id=plan_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "PLAN_ALREADY_DEACTIVATED"

    def test_deactivated_plan_not_in_active_list(self, manager, projection):
        result = _define_starter(manager)
        plan_id = result["plan_id"]
        manager.deactivate_plan(DeactivatePlanRequest(
            plan_id=plan_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert len(projection.list_active_plans()) == 0


class TestPlanEngineResolution:
    def test_resolve_engines_for_plan(self, manager):
        result = _define_starter(manager)
        engines = manager.resolve_engines_for_plan(result["plan_id"])
        assert engines == frozenset({"retail", "accounting"})

    def test_resolve_engines_for_missing_plan(self, manager):
        engines = manager.resolve_engines_for_plan(uuid.uuid4())
        assert engines == frozenset()


class TestPlanQuotaCheck:
    def test_quota_within_limit(self, manager):
        result = _define_starter(manager)
        rejection = manager.check_quota(result["plan_id"], "branches", 0)
        assert rejection is None

    def test_quota_exceeded(self, manager):
        result = _define_starter(manager)
        rejection = manager.check_quota(result["plan_id"], "branches", 1)
        assert rejection is not None
        assert rejection.code == "QUOTA_EXCEEDED"

    def test_quota_unknown_resource_passes(self, manager):
        result = _define_starter(manager)
        rejection = manager.check_quota(result["plan_id"], "unknown_resource", 999)
        assert rejection is None

    def test_quota_no_active_plan(self, manager):
        rejection = manager.check_quota(uuid.uuid4(), "branches", 0)
        assert rejection is not None
        assert rejection.code == "NO_ACTIVE_PLAN"


class TestPlanProjectionQueries:
    def test_list_plans(self, manager, projection):
        _define_starter(manager)
        assert len(projection.list_plans()) == 1

    def test_get_plan_by_tier(self, manager, projection):
        _define_starter(manager)
        plan = projection.get_plan_by_tier(PlanTier.STARTER)
        assert plan is not None
        assert plan.tier == PlanTier.STARTER

    def test_truncate(self, manager, projection):
        _define_starter(manager)
        projection.truncate()
        assert len(projection.list_plans()) == 0
