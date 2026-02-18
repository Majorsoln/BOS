from __future__ import annotations

import uuid

import pytest

from core.identity_store.models import Branch, Business, Role, RoleAssignment
from core.identity_store.service import (
    DEFAULT_ADMIN_ROLE,
    DEFAULT_CASHIER_ROLE,
    bootstrap_identity,
)

pytestmark = pytest.mark.django_db(transaction=True)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-identity-bootstrap-business")
BRANCH_MAIN_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-identity-bootstrap-branch-main")
BRANCH_STORE_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-identity-bootstrap-branch-store")


def _branch_specs() -> tuple[dict[str, str], ...]:
    return (
        {
            "branch_id": str(BRANCH_MAIN_ID),
            "name": "MAIN",
            "timezone": "UTC",
        },
        {
            "branch_id": str(BRANCH_STORE_ID),
            "name": "STORE",
            "timezone": "Africa/Nairobi",
        },
    )


def test_bootstrap_creates_identity_primitives_deterministically() -> None:
    first = bootstrap_identity(
        business_id=BUSINESS_ID,
        business_name="Bootstrap Biz",
        default_currency="TZS",
        default_language="sw",
        branches=_branch_specs(),
        admin_actor_id="bootstrap-admin",
        cashier_actor_id="bootstrap-cashier",
    )
    second = bootstrap_identity(
        business_id=BUSINESS_ID,
        business_name="Bootstrap Biz",
        default_currency="TZS",
        default_language="sw",
        branches=_branch_specs(),
        admin_actor_id="bootstrap-admin",
        cashier_actor_id="bootstrap-cashier",
    )

    assert first == second
    assert first["business"]["business_id"] == str(BUSINESS_ID)
    assert first["business"]["default_currency"] == "TZS"
    assert first["business"]["default_language"] == "sw"
    assert tuple(role["name"] for role in first["roles"]) == (
        DEFAULT_ADMIN_ROLE,
        DEFAULT_CASHIER_ROLE,
    )
    for role in first["roles"]:
        assert tuple(role["permissions"]) == tuple(sorted(role["permissions"]))

    assert Business.objects.filter(business_id=BUSINESS_ID).count() == 1
    assert Branch.objects.filter(business_id=BUSINESS_ID).count() == 2
    assert Role.objects.filter(business_id=BUSINESS_ID).count() == 2
    assert RoleAssignment.objects.filter(business_id=BUSINESS_ID).count() == 2


def test_bootstrap_default_branch_generation_is_stable() -> None:
    business_id = uuid.uuid5(uuid.NAMESPACE_URL, "bos-identity-bootstrap-defaults")
    first = bootstrap_identity(
        business_id=business_id,
        business_name="Default Branch Biz",
    )
    second = bootstrap_identity(
        business_id=business_id,
        business_name="Default Branch Biz",
    )

    assert first["branches"] == second["branches"]
    assert len(first["branches"]) == 2
