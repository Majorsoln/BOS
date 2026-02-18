from __future__ import annotations

import uuid

import pytest

from core.identity_store.service import DEFAULT_ADMIN_ROLE, DEFAULT_CASHIER_ROLE, assign_role, bootstrap_identity
from core.permissions.constants import (
    PERMISSION_ADMIN_CONFIGURE,
    SCOPE_GRANT_BRANCH,
    SCOPE_GRANT_BUSINESS,
)
from core.permissions.db_provider import DbPermissionProvider

pytestmark = pytest.mark.django_db(transaction=True)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-db-permission-business")
BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-db-permission-branch")


def _bootstrap() -> None:
    bootstrap_identity(
        business_id=BUSINESS_ID,
        business_name="Permission Biz",
        branches=(
            {
                "branch_id": str(BRANCH_ID),
                "name": "MAIN",
                "timezone": "UTC",
            },
        ),
    )


def test_db_permission_provider_resolves_business_and_branch_grants() -> None:
    _bootstrap()
    assign_role(
        business_id=BUSINESS_ID,
        actor_id="permission-admin",
        actor_type="HUMAN",
        role_name=DEFAULT_ADMIN_ROLE,
        branch_id=None,
    )
    assign_role(
        business_id=BUSINESS_ID,
        actor_id="permission-cashier",
        actor_type="HUMAN",
        role_name=DEFAULT_CASHIER_ROLE,
        branch_id=BRANCH_ID,
    )

    provider = DbPermissionProvider()
    admin_grants = provider.get_grants_for_actor("permission-admin", BUSINESS_ID)
    cashier_grants = provider.get_grants_for_actor("permission-cashier", BUSINESS_ID)

    assert len(admin_grants) == 1
    assert admin_grants[0].scope_type == SCOPE_GRANT_BUSINESS
    assert admin_grants[0].branch_id is None

    assert len(cashier_grants) == 1
    assert cashier_grants[0].scope_type == SCOPE_GRANT_BRANCH
    assert cashier_grants[0].branch_id == BRANCH_ID


def test_db_permission_provider_resolves_role_permissions_deterministically() -> None:
    _bootstrap()
    assignment = assign_role(
        business_id=BUSINESS_ID,
        actor_id="permission-admin",
        actor_type="HUMAN",
        role_name=DEFAULT_ADMIN_ROLE,
        branch_id=None,
    )

    provider = DbPermissionProvider()
    grants = provider.get_grants_for_actor("permission-admin", BUSINESS_ID)
    assert len(grants) == 1

    role = provider.get_role(grants[0].role_id)
    assert role is not None
    assert role.role_id == assignment["role_id"]
    assert PERMISSION_ADMIN_CONFIGURE in role.permissions
    assert role.permissions == tuple(sorted(role.permissions))

    assert provider.get_role("not-a-uuid") is None
    assert provider.get_grants_for_actor("unknown", BUSINESS_ID) == tuple()
