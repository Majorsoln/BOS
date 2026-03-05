"""Tests for core/platform/tenant_lifecycle.py"""
from datetime import datetime

import pytest

from core.platform.tenant_lifecycle import (
    TenantLifecycleProjection,
    TenantLifecycleManager,
    TenantState,
    SuspensionReason,
    TerminationReason,
    StartOnboardingRequest,
    ActivateTenantRequest,
    SuspendTenantRequest,
    ReinstateTenantRequest,
    TerminateTenantRequest,
)

NOW = datetime(2026, 3, 5, 12, 0, 0)
ADMIN = "platform-admin-001"


@pytest.fixture
def projection():
    return TenantLifecycleProjection()


@pytest.fixture
def manager(projection):
    return TenantLifecycleManager(projection)


@pytest.fixture
def onboarding_tenant(manager, projection):
    result = manager.start_onboarding(StartOnboardingRequest(
        business_name="Mama Mboga Ltd",
        country_code="KE",
        region_code="KE",
        actor_id=ADMIN,
        issued_at=NOW,
    ))
    return result["tenant_id"]


@pytest.fixture
def active_tenant(manager, projection, onboarding_tenant):
    manager.activate(ActivateTenantRequest(
        tenant_id=onboarding_tenant,
        actor_id=ADMIN,
        issued_at=NOW,
    ))
    return onboarding_tenant


class TestOnboarding:
    def test_start_onboarding_creates_tenant(self, manager, projection):
        result = manager.start_onboarding(StartOnboardingRequest(
            business_name="Test Shop",
            country_code="TZ",
            region_code="TZ",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        tenant_id = result["tenant_id"]
        tenant = projection.get_tenant(tenant_id)
        assert tenant is not None
        assert tenant.state == TenantState.ONBOARDING
        assert tenant.business_name == "Test Shop"
        assert tenant.region_code == "TZ"

    def test_onboarding_produces_event(self, manager):
        result = manager.start_onboarding(StartOnboardingRequest(
            business_name="X", country_code="KE", region_code="KE",
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == "platform.tenant.onboarding.started.v1"


class TestActivation:
    def test_activate_from_onboarding(self, manager, projection, onboarding_tenant):
        error = manager.activate(ActivateTenantRequest(
            tenant_id=onboarding_tenant, actor_id=ADMIN, issued_at=NOW
        ))
        assert error is None
        tenant = projection.get_tenant(onboarding_tenant)
        assert tenant.state == TenantState.ACTIVE
        assert tenant.activated_at == NOW

    def test_cannot_activate_already_active(self, manager, active_tenant):
        error = manager.activate(ActivateTenantRequest(
            tenant_id=active_tenant, actor_id=ADMIN, issued_at=NOW
        ))
        assert error is not None
        assert error.code == "INVALID_LIFECYCLE_TRANSITION"

    def test_cannot_activate_nonexistent(self, manager):
        import uuid
        error = manager.activate(ActivateTenantRequest(
            tenant_id=uuid.uuid4(), actor_id=ADMIN, issued_at=NOW
        ))
        assert error is not None
        assert error.code == "TENANT_NOT_FOUND"


class TestSuspension:
    def test_suspend_active_tenant(self, manager, projection, active_tenant):
        error = manager.suspend(SuspendTenantRequest(
            tenant_id=active_tenant,
            reason=SuspensionReason.NON_PAYMENT.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is None
        tenant = projection.get_tenant(active_tenant)
        assert tenant.state == TenantState.SUSPENDED
        assert tenant.suspension_reason == SuspensionReason.NON_PAYMENT.value

    def test_cannot_suspend_onboarding_tenant(self, manager, onboarding_tenant):
        error = manager.suspend(SuspendTenantRequest(
            tenant_id=onboarding_tenant,
            reason=SuspensionReason.NON_PAYMENT.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is not None
        assert error.code == "INVALID_LIFECYCLE_TRANSITION"

    def test_invalid_suspension_reason_rejected(self, manager, active_tenant):
        error = manager.suspend(SuspendTenantRequest(
            tenant_id=active_tenant,
            reason="ALIEN_INVASION",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is not None
        assert error.code == "INVALID_SUSPENSION_REASON"

    def test_suspended_tenant_is_blocked(self, manager, projection, active_tenant):
        manager.suspend(SuspendTenantRequest(
            tenant_id=active_tenant,
            reason=SuspensionReason.ABUSE.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert projection.is_blocked(active_tenant)


class TestReinstatement:
    def test_reinstate_suspended_tenant(self, manager, projection, active_tenant):
        manager.suspend(SuspendTenantRequest(
            tenant_id=active_tenant,
            reason=SuspensionReason.NON_PAYMENT.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        error = manager.reinstate(ReinstateTenantRequest(
            tenant_id=active_tenant, actor_id=ADMIN, issued_at=NOW
        ))
        assert error is None
        tenant = projection.get_tenant(active_tenant)
        assert tenant.state == TenantState.ACTIVE
        assert tenant.suspension_reason is None

    def test_cannot_reinstate_active_tenant(self, manager, active_tenant):
        error = manager.reinstate(ReinstateTenantRequest(
            tenant_id=active_tenant, actor_id=ADMIN, issued_at=NOW
        ))
        assert error is not None
        assert error.code == "TENANT_NOT_SUSPENDED"


class TestTermination:
    def test_terminate_active_tenant(self, manager, projection, active_tenant):
        error = manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.VOLUNTARY_CLOSURE.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is None
        tenant = projection.get_tenant(active_tenant)
        assert tenant.state == TenantState.TERMINATED
        assert tenant.termination_reason == TerminationReason.VOLUNTARY_CLOSURE.value

    def test_kill_switch_sets_flag(self, manager, projection, active_tenant):
        manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.KILL_SWITCH.value,
            kill_switch=True,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        tenant = projection.get_tenant(active_tenant)
        assert tenant.kill_switch is True

    def test_terminated_is_blocked(self, manager, projection, active_tenant):
        manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.FRAUD.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert projection.is_blocked(active_tenant)

    def test_cannot_terminate_already_terminated(self, manager, active_tenant):
        manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.VOLUNTARY_CLOSURE.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        error = manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.FRAUD.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is not None
        assert error.code == "INVALID_LIFECYCLE_TRANSITION"

    def test_invalid_termination_reason_rejected(self, manager, active_tenant):
        error = manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason="RANDOM",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is not None
        assert error.code == "INVALID_TERMINATION_REASON"

    def test_terminate_suspended_tenant(self, manager, projection, active_tenant):
        manager.suspend(SuspendTenantRequest(
            tenant_id=active_tenant,
            reason=SuspensionReason.LEGAL_HOLD.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        error = manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.LEGAL_ORDER.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert error is None
        tenant = projection.get_tenant(active_tenant)
        assert tenant.state == TenantState.TERMINATED


class TestCommandGate:
    def test_active_tenant_can_issue_commands(self, manager, active_tenant):
        error = manager.assert_tenant_can_issue_commands(active_tenant)
        assert error is None

    def test_onboarding_tenant_cannot_issue_commands(self, manager, onboarding_tenant):
        error = manager.assert_tenant_can_issue_commands(onboarding_tenant)
        assert error is not None
        assert error.code == "TENANT_ONBOARDING"

    def test_suspended_tenant_cannot_issue_commands(self, manager, active_tenant):
        manager.suspend(SuspendTenantRequest(
            tenant_id=active_tenant,
            reason=SuspensionReason.NON_PAYMENT.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        error = manager.assert_tenant_can_issue_commands(active_tenant)
        assert error is not None
        assert error.code == "TENANT_SUSPENDED"

    def test_terminated_tenant_cannot_issue_commands(self, manager, active_tenant):
        manager.terminate(TerminateTenantRequest(
            tenant_id=active_tenant,
            reason=TerminationReason.VOLUNTARY_CLOSURE.value,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        error = manager.assert_tenant_can_issue_commands(active_tenant)
        assert error is not None
        assert error.code == "TENANT_TERMINATED"


class TestListByState:
    def test_list_by_state(self, manager, projection):
        for i in range(3):
            result = manager.start_onboarding(StartOnboardingRequest(
                business_name=f"Shop {i}",
                country_code="KE",
                region_code="KE",
                actor_id=ADMIN,
                issued_at=NOW,
            ))
            manager.activate(ActivateTenantRequest(
                tenant_id=result["tenant_id"], actor_id=ADMIN, issued_at=NOW
            ))

        active = projection.list_by_state(TenantState.ACTIVE)
        assert len(active) == 3
