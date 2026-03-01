"""
Tests — Tenant Lifecycle Manager
====================================
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from core.admin.tenant_manager import (
    ActivateTenantRequest,
    AddBranchRequest,
    CloseBranchRequest,
    CloseTenantRequest,
    CreateTenantRequest,
    SuspendTenantRequest,
    TenantManager,
    TenantProjection,
)
from core.business.models import BusinessState


T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _manager() -> TenantManager:
    return TenantManager(TenantProjection())


def _create(mgr: TenantManager, name: str = "Acme Corp") -> uuid.UUID:
    result = mgr.create_tenant(CreateTenantRequest(
        business_name=name,
        country_code="US",
        timezone="America/New_York",
        actor_id="admin-1",
        issued_at=T0,
        initial_branch_name="HQ",
        initial_branch_location="New York",
    ))
    return result["business_id"]


class TestCreateTenant:
    def test_creates_business(self):
        mgr = _manager()
        result = mgr.create_tenant(CreateTenantRequest(
            business_name="Test Inc",
            country_code="KE",
            timezone="Africa/Nairobi",
            actor_id="admin-1",
            issued_at=T0,
        ))
        biz_id = result["business_id"]
        biz = mgr._projection.get_business(biz_id)
        assert biz is not None
        assert biz.name == "Test Inc"
        assert biz.state == BusinessState.CREATED
        assert biz.country_code == "KE"

    def test_creates_with_initial_branch(self):
        mgr = _manager()
        biz_id = _create(mgr)
        branches = mgr._projection.get_branches(biz_id)
        assert len(branches) == 1
        assert branches[0].name == "HQ"
        assert branches[0].location == "New York"

    def test_events_emitted(self):
        mgr = _manager()
        result = mgr.create_tenant(CreateTenantRequest(
            business_name="X", country_code="US", timezone="UTC",
            actor_id="a", issued_at=T0,
            initial_branch_name="B1",
        ))
        events = result["events"]
        assert len(events) == 2
        assert events[0]["event_type"] == "admin.tenant.created.v1"
        assert events[1]["event_type"] == "admin.tenant.branch_added.v1"


class TestLifecycleTransitions:
    def test_activate_from_created(self):
        mgr = _manager()
        biz_id = _create(mgr)
        rejection = mgr.activate_tenant(ActivateTenantRequest(
            business_id=biz_id, actor_id="admin-1", issued_at=T0,
        ))
        assert rejection is None
        assert mgr._projection.get_business(biz_id).state == BusinessState.ACTIVE

    def test_suspend_from_active(self):
        mgr = _manager()
        biz_id = _create(mgr)
        mgr.activate_tenant(ActivateTenantRequest(business_id=biz_id, actor_id="a", issued_at=T0))
        rejection = mgr.suspend_tenant(SuspendTenantRequest(
            business_id=biz_id, actor_id="a", issued_at=T0, reason="Payment overdue",
        ))
        assert rejection is None
        assert mgr._projection.get_business(biz_id).state == BusinessState.SUSPENDED

    def test_reactivate_from_suspended(self):
        mgr = _manager()
        biz_id = _create(mgr)
        mgr.activate_tenant(ActivateTenantRequest(business_id=biz_id, actor_id="a", issued_at=T0))
        mgr.suspend_tenant(SuspendTenantRequest(business_id=biz_id, actor_id="a", issued_at=T0))
        rejection = mgr.activate_tenant(ActivateTenantRequest(
            business_id=biz_id, actor_id="a", issued_at=T0,
        ))
        assert rejection is None
        assert mgr._projection.get_business(biz_id).state == BusinessState.ACTIVE

    def test_close_from_active(self):
        mgr = _manager()
        biz_id = _create(mgr)
        mgr.activate_tenant(ActivateTenantRequest(business_id=biz_id, actor_id="a", issued_at=T0))
        rejection = mgr.close_tenant(CloseTenantRequest(
            business_id=biz_id, actor_id="a", issued_at=T0,
        ))
        assert rejection is None
        assert mgr._projection.get_business(biz_id).state == BusinessState.CLOSED

    def test_cannot_activate_closed(self):
        mgr = _manager()
        biz_id = _create(mgr)
        mgr.close_tenant(CloseTenantRequest(business_id=biz_id, actor_id="a", issued_at=T0))
        rejection = mgr.activate_tenant(ActivateTenantRequest(
            business_id=biz_id, actor_id="a", issued_at=T0,
        ))
        assert rejection is not None
        assert rejection.code == "INVALID_LIFECYCLE_TRANSITION"

    def test_cannot_suspend_created(self):
        mgr = _manager()
        biz_id = _create(mgr)
        rejection = mgr.suspend_tenant(SuspendTenantRequest(
            business_id=biz_id, actor_id="a", issued_at=T0,
        ))
        assert rejection is not None

    def test_not_found(self):
        mgr = _manager()
        rejection = mgr.activate_tenant(ActivateTenantRequest(
            business_id=uuid.uuid4(), actor_id="a", issued_at=T0,
        ))
        assert rejection is not None
        assert rejection.code == "TENANT_NOT_FOUND"


class TestBranchManagement:
    def test_add_branch(self):
        mgr = _manager()
        biz_id = _create(mgr)
        rejection = mgr.add_branch(AddBranchRequest(
            business_id=biz_id, branch_name="Downtown",
            actor_id="a", issued_at=T0, location="123 Main St",
        ))
        assert rejection is None
        branches = mgr._projection.get_branches(biz_id)
        assert len(branches) == 2  # HQ + Downtown

    def test_close_branch(self):
        mgr = _manager()
        biz_id = _create(mgr)
        branches = mgr._projection.get_branches(biz_id)
        branch_id = branches[0].branch_id
        rejection = mgr.close_branch(CloseBranchRequest(
            business_id=biz_id, branch_id=branch_id,
            actor_id="a", issued_at=T0,
        ))
        assert rejection is None
        assert mgr._projection.get_open_branches(biz_id) == []

    def test_cannot_close_branch_twice(self):
        mgr = _manager()
        biz_id = _create(mgr)
        branch_id = mgr._projection.get_branches(biz_id)[0].branch_id
        mgr.close_branch(CloseBranchRequest(
            business_id=biz_id, branch_id=branch_id, actor_id="a", issued_at=T0,
        ))
        rejection = mgr.close_branch(CloseBranchRequest(
            business_id=biz_id, branch_id=branch_id, actor_id="a", issued_at=T0,
        ))
        assert rejection is not None
        assert rejection.code == "BRANCH_ALREADY_CLOSED"

    def test_cannot_add_branch_to_closed_business(self):
        mgr = _manager()
        biz_id = _create(mgr)
        mgr.close_tenant(CloseTenantRequest(business_id=biz_id, actor_id="a", issued_at=T0))
        rejection = mgr.add_branch(AddBranchRequest(
            business_id=biz_id, branch_name="X", actor_id="a", issued_at=T0,
        ))
        assert rejection is not None
        assert rejection.code == "TENANT_NOT_OPERATIONAL"


class TestTenantProjection:
    def test_list_active_businesses(self):
        mgr = _manager()
        biz1 = _create(mgr, "A")
        biz2 = _create(mgr, "B")
        mgr.activate_tenant(ActivateTenantRequest(business_id=biz1, actor_id="a", issued_at=T0))
        active = mgr._projection.list_active_businesses()
        assert len(active) == 1
        assert active[0].business_id == biz1

    def test_truncate(self):
        mgr = _manager()
        biz_id = _create(mgr)
        mgr._projection.truncate(biz_id)
        assert mgr._projection.get_business(biz_id) is None
        assert mgr._projection.get_branches(biz_id) == []
