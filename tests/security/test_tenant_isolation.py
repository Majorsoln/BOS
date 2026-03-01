"""
Tests — Tenant Isolation
===========================
Verifies cross-tenant boundary enforcement.
"""

from __future__ import annotations

import uuid

import pytest

from core.commands.rejection import ReasonCode
from core.security.tenant_isolation import (
    TenantScope,
    build_tenant_scope,
    check_tenant_isolation,
)


# ── Helpers ──────────────────────────────────────────────────

BIZ_A = uuid.uuid4()
BIZ_B = uuid.uuid4()
BRANCH_1 = uuid.uuid4()
BRANCH_2 = uuid.uuid4()
BRANCH_3 = uuid.uuid4()


def _scope_single_biz_all_branches() -> TenantScope:
    return TenantScope(
        actor_id="actor-1",
        business_ids=frozenset([BIZ_A]),
        branch_ids_by_business={BIZ_A: None},  # all branches
    )


def _scope_single_biz_specific_branches() -> TenantScope:
    return TenantScope(
        actor_id="actor-1",
        business_ids=frozenset([BIZ_A]),
        branch_ids_by_business={BIZ_A: frozenset([BRANCH_1, BRANCH_2])},
    )


def _scope_multi_biz() -> TenantScope:
    return TenantScope(
        actor_id="actor-1",
        business_ids=frozenset([BIZ_A, BIZ_B]),
        branch_ids_by_business={BIZ_A: None, BIZ_B: frozenset([BRANCH_3])},
    )


# ══════════════════════════════════════════════════════════════
# TENANT SCOPE
# ══════════════════════════════════════════════════════════════


class TestTenantScope:
    def test_can_access_authorized_business(self):
        scope = _scope_single_biz_all_branches()
        assert scope.can_access_business(BIZ_A) is True

    def test_cannot_access_unauthorized_business(self):
        scope = _scope_single_biz_all_branches()
        assert scope.can_access_business(BIZ_B) is False

    def test_all_branches_allowed(self):
        scope = _scope_single_biz_all_branches()
        assert scope.can_access_branch(BIZ_A, BRANCH_1) is True
        assert scope.can_access_branch(BIZ_A, BRANCH_2) is True
        assert scope.can_access_branch(BIZ_A, uuid.uuid4()) is True

    def test_specific_branches_allowed(self):
        scope = _scope_single_biz_specific_branches()
        assert scope.can_access_branch(BIZ_A, BRANCH_1) is True
        assert scope.can_access_branch(BIZ_A, BRANCH_2) is True

    def test_specific_branches_denied(self):
        scope = _scope_single_biz_specific_branches()
        assert scope.can_access_branch(BIZ_A, BRANCH_3) is False

    def test_branch_access_denied_for_unauthorized_business(self):
        scope = _scope_single_biz_all_branches()
        assert scope.can_access_branch(BIZ_B, BRANCH_1) is False

    def test_multi_biz_scope(self):
        scope = _scope_multi_biz()
        assert scope.can_access_business(BIZ_A) is True
        assert scope.can_access_business(BIZ_B) is True
        # BIZ_A: all branches
        assert scope.can_access_branch(BIZ_A, uuid.uuid4()) is True
        # BIZ_B: only BRANCH_3
        assert scope.can_access_branch(BIZ_B, BRANCH_3) is True
        assert scope.can_access_branch(BIZ_B, BRANCH_1) is False


# ══════════════════════════════════════════════════════════════
# CHECK TENANT ISOLATION
# ══════════════════════════════════════════════════════════════


class TestCheckTenantIsolation:
    def test_allowed_business(self):
        scope = _scope_single_biz_all_branches()
        result = check_tenant_isolation(scope, BIZ_A)
        assert result is None

    def test_denied_business(self):
        scope = _scope_single_biz_all_branches()
        result = check_tenant_isolation(scope, BIZ_B)
        assert result is not None
        assert result.code == ReasonCode.PERMISSION_DENIED
        assert "business" in result.message.lower()

    def test_allowed_branch(self):
        scope = _scope_single_biz_specific_branches()
        result = check_tenant_isolation(scope, BIZ_A, BRANCH_1)
        assert result is None

    def test_denied_branch(self):
        scope = _scope_single_biz_specific_branches()
        result = check_tenant_isolation(scope, BIZ_A, BRANCH_3)
        assert result is not None
        assert result.code == ReasonCode.PERMISSION_DENIED
        assert "branch" in result.message.lower()

    def test_no_cross_tenant_data_leakage_in_business_denial(self):
        scope = _scope_single_biz_all_branches()
        result = check_tenant_isolation(scope, BIZ_B)
        # Error message must NOT contain BIZ_B UUID
        assert str(BIZ_B) not in result.message

    def test_no_cross_tenant_data_leakage_in_branch_denial(self):
        scope = _scope_single_biz_specific_branches()
        result = check_tenant_isolation(scope, BIZ_A, BRANCH_3)
        assert str(BRANCH_3) not in result.message

    def test_branch_check_skipped_when_no_branch_id(self):
        scope = _scope_single_biz_specific_branches()
        result = check_tenant_isolation(scope, BIZ_A, branch_id=None)
        assert result is None


# ══════════════════════════════════════════════════════════════
# BUILD TENANT SCOPE
# ══════════════════════════════════════════════════════════════


class TestBuildTenantScope:
    def test_build_from_business_grants(self):
        grants = [
            {"business_id": BIZ_A, "scope_type": "BUSINESS", "branch_id": None},
        ]
        scope = build_tenant_scope("actor-1", grants)
        assert scope.can_access_business(BIZ_A) is True
        assert scope.can_access_branch(BIZ_A, uuid.uuid4()) is True

    def test_build_from_branch_grants(self):
        grants = [
            {"business_id": BIZ_A, "scope_type": "BRANCH", "branch_id": BRANCH_1},
            {"business_id": BIZ_A, "scope_type": "BRANCH", "branch_id": BRANCH_2},
        ]
        scope = build_tenant_scope("actor-1", grants)
        assert scope.can_access_business(BIZ_A) is True
        assert scope.can_access_branch(BIZ_A, BRANCH_1) is True
        assert scope.can_access_branch(BIZ_A, BRANCH_2) is True
        assert scope.can_access_branch(BIZ_A, BRANCH_3) is False

    def test_business_grant_overrides_branch_grants(self):
        grants = [
            {"business_id": BIZ_A, "scope_type": "BRANCH", "branch_id": BRANCH_1},
            {"business_id": BIZ_A, "scope_type": "BUSINESS", "branch_id": None},
        ]
        scope = build_tenant_scope("actor-1", grants)
        # Business-level grant means all branches
        assert scope.can_access_branch(BIZ_A, uuid.uuid4()) is True

    def test_build_with_empty_grants(self):
        scope = build_tenant_scope("actor-1", [])
        assert scope.can_access_business(BIZ_A) is False

    def test_build_skips_grants_without_business_id(self):
        grants = [
            {"business_id": None, "scope_type": "BUSINESS", "branch_id": None},
        ]
        scope = build_tenant_scope("actor-1", grants)
        assert len(scope.business_ids) == 0
