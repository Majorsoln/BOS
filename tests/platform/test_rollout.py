"""Tests for core/platform/rollout.py"""
from datetime import datetime

import pytest

from core.platform.rollout import (
    RolloutProjection,
    RolloutService,
    RolloutStatus,
    RolloutTargetKind,
    DefineRolloutRequest,
    ActivateRolloutRequest,
    PauseRolloutRequest,
    CompleteRolloutRequest,
    RollbackRolloutRequest,
    evaluate_rollout_for_tenant,
)

NOW = datetime(2026, 3, 5, 12, 0, 0)
ADMIN = "platform-admin-001"
FLAG = "FLAG_ENABLE_DOCUMENT_ENGINE"


@pytest.fixture
def projection():
    return RolloutProjection()


@pytest.fixture
def service(projection):
    return RolloutService(projection)


def _define(service, target_kind="GLOBAL", **kwargs):
    result = service.define_rollout(DefineRolloutRequest(
        name="Test Rollout",
        feature_flag=FLAG,
        target_kind=target_kind,
        actor_id=ADMIN,
        issued_at=NOW,
        **kwargs,
    ))
    assert "rollout_id" in result
    return result["rollout_id"]


def _activate(service, rollout_id):
    err = service.activate(ActivateRolloutRequest(
        rollout_id=rollout_id, actor_id=ADMIN, issued_at=NOW
    ))
    assert err is None


class TestDefineRollout:
    def test_define_global_rollout(self, service, projection):
        rid = _define(service, "GLOBAL")
        rollout = projection.get_rollout(rid)
        assert rollout is not None
        assert rollout.status == RolloutStatus.DRAFT
        assert rollout.feature_flag == FLAG

    def test_invalid_target_kind_rejected(self, service):
        result = service.define_rollout(DefineRolloutRequest(
            name="Bad", feature_flag=FLAG, target_kind="UNICORN",
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert "rejected" in result

    def test_define_percentage_rollout(self, service, projection):
        rid = _define(service, "PERCENTAGE", percentage=25)
        rollout = projection.get_rollout(rid)
        assert rollout.target.kind == RolloutTargetKind.PERCENTAGE
        assert rollout.target.percentage == 25

    def test_define_region_rollout(self, service, projection):
        rid = _define(service, "REGION", regions=("KE", "TZ"))
        rollout = projection.get_rollout(rid)
        assert "KE" in rollout.target.regions
        assert "TZ" in rollout.target.regions


class TestRolloutLifecycle:
    def test_activate_draft_rollout(self, service, projection):
        rid = _define(service)
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        assert rollout.status == RolloutStatus.ACTIVE

    def test_cannot_activate_already_active(self, service):
        rid = _define(service)
        _activate(service, rid)
        err = service.activate(ActivateRolloutRequest(
            rollout_id=rid, actor_id=ADMIN, issued_at=NOW
        ))
        assert err is not None
        assert err.code == "ROLLOUT_NOT_IN_DRAFT"

    def test_pause_active_rollout(self, service, projection):
        rid = _define(service)
        _activate(service, rid)
        err = service.pause(PauseRolloutRequest(
            rollout_id=rid, actor_id=ADMIN, issued_at=NOW, reason="Investigating issue"
        ))
        assert err is None
        assert projection.get_rollout(rid).status == RolloutStatus.PAUSED

    def test_complete_active_rollout(self, service, projection):
        rid = _define(service)
        _activate(service, rid)
        err = service.complete(CompleteRolloutRequest(
            rollout_id=rid, actor_id=ADMIN, issued_at=NOW
        ))
        assert err is None
        assert projection.get_rollout(rid).status == RolloutStatus.COMPLETED

    def test_rollback_active_rollout(self, service, projection):
        rid = _define(service)
        _activate(service, rid)
        err = service.rollback(RollbackRolloutRequest(
            rollout_id=rid, actor_id=ADMIN, issued_at=NOW, reason="Bug found"
        ))
        assert err is None
        rollout = projection.get_rollout(rid)
        assert rollout.status == RolloutStatus.ROLLED_BACK
        assert rollout.rollback_reason == "Bug found"

    def test_get_active_rollout_for_flag(self, service, projection):
        rid = _define(service)
        _activate(service, rid)
        active = projection.get_active_rollout_for_flag(FLAG)
        assert active is not None
        assert active.rollout_id == rid

    def test_no_active_rollout_after_rollback(self, service, projection):
        rid = _define(service)
        _activate(service, rid)
        service.rollback(RollbackRolloutRequest(
            rollout_id=rid, actor_id=ADMIN, issued_at=NOW, reason="Problem"
        ))
        assert projection.get_active_rollout_for_flag(FLAG) is None


class TestTenantTargeting:
    def test_global_rollout_includes_all(self, service, projection):
        rid = _define(service, "GLOBAL")
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        assert evaluate_rollout_for_tenant(rollout, "tenant-123") is True

    def test_region_rollout_includes_matching_region(self, service, projection):
        rid = _define(service, "REGION", regions=("KE",))
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        assert evaluate_rollout_for_tenant(rollout, "t1", tenant_region="KE") is True
        assert evaluate_rollout_for_tenant(rollout, "t1", tenant_region="TZ") is False

    def test_plan_tier_rollout(self, service, projection):
        rid = _define(service, "PLAN_TIER", plan_tiers=("ENTERPRISE",))
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        assert evaluate_rollout_for_tenant(rollout, "t1", tenant_plan_tier="ENTERPRISE") is True
        assert evaluate_rollout_for_tenant(rollout, "t1", tenant_plan_tier="STARTER") is False

    def test_cohort_rollout(self, service, projection):
        rid = _define(service, "COHORT", cohort_name="beta_testers")
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        assert evaluate_rollout_for_tenant(
            rollout, "t1", tenant_cohorts={"beta_testers"}
        ) is True
        assert evaluate_rollout_for_tenant(
            rollout, "t1", tenant_cohorts={"prod_users"}
        ) is False

    def test_percentage_rollout_deterministic(self, service, projection):
        rid = _define(service, "PERCENTAGE", percentage=50)
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        # Same tenant should always get the same result
        result_a = evaluate_rollout_for_tenant(rollout, "fixed-tenant-id")
        result_b = evaluate_rollout_for_tenant(rollout, "fixed-tenant-id")
        assert result_a == result_b

    def test_paused_rollout_excludes_all(self, service, projection):
        rid = _define(service, "GLOBAL")
        _activate(service, rid)
        service.pause(PauseRolloutRequest(
            rollout_id=rid, actor_id=ADMIN, issued_at=NOW
        ))
        rollout = projection.get_rollout(rid)
        assert evaluate_rollout_for_tenant(rollout, "any-tenant") is False

    def test_is_feature_enabled_shortcut(self, service):
        rid = _define(service, "REGION", regions=("KE",))
        _activate(service, rid)
        assert service.is_feature_enabled_for_tenant(FLAG, "t1", tenant_region="KE") is True
        assert service.is_feature_enabled_for_tenant(FLAG, "t1", tenant_region="EU") is False

    def test_tenant_list_rollout(self, service, projection):
        rid = _define(service, "TENANT_LIST", tenant_ids=("tenant-a", "tenant-b"))
        _activate(service, rid)
        rollout = projection.get_rollout(rid)
        assert evaluate_rollout_for_tenant(rollout, "tenant-a") is True
        assert evaluate_rollout_for_tenant(rollout, "tenant-c") is False
