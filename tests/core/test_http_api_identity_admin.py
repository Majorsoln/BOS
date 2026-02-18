from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from core.admin.projections import AdminProjectionStore
from core.admin.repository import AdminRepository
from core.auth.provider import DbAuthProvider
from core.auth.service import ApiKeyService
from core.http_api.contracts import (
    BusinessReadRequest,
    IdentityBootstrapHttpRequest,
    RoleAssignHttpRequest,
    RoleRevokeHttpRequest,
)
from core.http_api.dependencies import HttpApiDependencies
from core.http_api.handlers import (
    list_actors,
    list_roles,
    post_identity_bootstrap,
    post_role_assign,
    post_role_revoke,
)
from core.identity_store.service import (
    DEFAULT_CASHIER_ROLE,
    assign_role,
    bootstrap_identity,
)
from core.permissions.db_provider import DbPermissionProvider

pytestmark = pytest.mark.django_db(transaction=True)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-identity-business")
ADMIN_BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-identity-admin-branch")
CASHIER_BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-identity-cashier-branch")
ADMIN_ACTOR_ID = "identity-admin"
CASHIER_ACTOR_ID = "identity-cashier"


class FixedIdProvider:
    def new_command_id(self) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-identity-fixed-command")

    def new_correlation_id(self) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-identity-fixed-correlation")


class FixedClock:
    def now_issued_at(self) -> datetime:
        return datetime(2026, 2, 17, 13, 0, tzinfo=timezone.utc)


def _build_dependencies() -> HttpApiDependencies:
    return HttpApiDependencies(
        admin_service=object(),
        admin_repository=AdminRepository(AdminProjectionStore()),
        id_provider=FixedIdProvider(),
        clock=FixedClock(),
        auth_provider=DbAuthProvider(),
        permission_provider=DbPermissionProvider(),
    )


def _seed_identity() -> None:
    bootstrap_identity(
        business_id=BUSINESS_ID,
        business_name="Identity HTTP Biz",
        default_currency="USD",
        default_language="en",
        branches=(
            {
                "branch_id": str(ADMIN_BRANCH_ID),
                "name": "ADMIN",
                "timezone": "UTC",
            },
            {
                "branch_id": str(CASHIER_BRANCH_ID),
                "name": "CASHIER",
                "timezone": "UTC",
            },
        ),
        admin_actor_id=ADMIN_ACTOR_ID,
        cashier_actor_id=None,
    )
    assign_role(
        business_id=BUSINESS_ID,
        actor_id=CASHIER_ACTOR_ID,
        actor_type="USER",
        role_name=DEFAULT_CASHIER_ROLE,
        branch_id=CASHIER_BRANCH_ID,
    )


def _create_api_key(
    *,
    raw_key: str,
    actor_id: str,
    branch_ids: tuple[uuid.UUID, ...],
) -> None:
    ApiKeyService.create_api_key_credential(
        api_key=raw_key,
        actor_id=actor_id,
        actor_type="USER",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={
            str(BUSINESS_ID): tuple(str(branch_id) for branch_id in branch_ids)
        },
        created_by_actor_id="tests",
        label=f"{actor_id}-key",
    )


def _headers(api_key: str, *, branch_id: uuid.UUID | None = None, lang: str | None = None):
    result = {
        "X-API-KEY": api_key,
        "X-BUSINESS-ID": str(BUSINESS_ID),
    }
    if branch_id is not None:
        result["X-BRANCH-ID"] = str(branch_id)
    if lang is not None:
        result["Accept-Language"] = lang
    return result


def test_identity_bootstrap_success_and_lang_metadata_echo() -> None:
    _seed_identity()
    _create_api_key(
        raw_key="identity-admin-key",
        actor_id=ADMIN_ACTOR_ID,
        branch_ids=(ADMIN_BRANCH_ID, CASHIER_BRANCH_ID),
    )
    dependencies = _build_dependencies()

    response = post_identity_bootstrap(
        IdentityBootstrapHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            business_name="Identity HTTP Biz",
            default_currency="USD",
            default_language="en",
            branches=tuple(),
            admin_actor_id=ADMIN_ACTOR_ID,
            cashier_actor_id=CASHIER_ACTOR_ID,
            branch_id=None,
        ),
        dependencies,
        headers=_headers("identity-admin-key", lang="sw"),
    )

    assert response["ok"] is True
    assert response["meta"]["lang"] == "sw"
    assert response["data"]["business"]["business_id"] == str(BUSINESS_ID)


def test_cashier_admin_action_rejected_with_i18n_details() -> None:
    _seed_identity()
    _create_api_key(
        raw_key="identity-cashier-key",
        actor_id=CASHIER_ACTOR_ID,
        branch_ids=(CASHIER_BRANCH_ID,),
    )
    dependencies = _build_dependencies()

    response = post_role_assign(
        RoleAssignHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            actor_id="another-cashier",
            actor_type="HUMAN",
            role_name=DEFAULT_CASHIER_ROLE,
            display_name=None,
            branch_id=CASHIER_BRANCH_ID,
        ),
        dependencies,
        headers=_headers("identity-cashier-key", branch_id=CASHIER_BRANCH_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "PERMISSION_DENIED"
    assert response["error"]["message"]
    assert "message_key" in response["error"]["details"]
    assert "message_params" in response["error"]["details"]


def test_admin_can_assign_revoke_and_list_identity_roles() -> None:
    _seed_identity()
    _create_api_key(
        raw_key="identity-admin-key-2",
        actor_id=ADMIN_ACTOR_ID,
        branch_ids=(ADMIN_BRANCH_ID, CASHIER_BRANCH_ID),
    )
    dependencies = _build_dependencies()

    assign_response = post_role_assign(
        RoleAssignHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            actor_id="new-cashier",
            actor_type="HUMAN",
            role_name=DEFAULT_CASHIER_ROLE,
            display_name="New Cashier",
            branch_id=CASHIER_BRANCH_ID,
        ),
        dependencies,
        headers=_headers("identity-admin-key-2", branch_id=CASHIER_BRANCH_ID),
    )
    assert assign_response["ok"] is True
    assert assign_response["data"]["assignment"]["status"] == "ACTIVE"

    revoke_response = post_role_revoke(
        RoleRevokeHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            actor_id="new-cashier",
            role_name=DEFAULT_CASHIER_ROLE,
            branch_id=CASHIER_BRANCH_ID,
        ),
        dependencies,
        headers=_headers("identity-admin-key-2", branch_id=CASHIER_BRANCH_ID),
    )
    assert revoke_response["ok"] is True
    assert revoke_response["data"]["assignment"]["status"] == "INACTIVE"

    roles_response = list_roles(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers=_headers("identity-admin-key-2", lang="en"),
    )
    actors_response = list_actors(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers=_headers("identity-admin-key-2"),
    )

    assert roles_response["ok"] is True
    assert actors_response["ok"] is True
    assert roles_response["meta"]["lang"] == "en"
    assert roles_response["data"]["role_count"] >= 2
    assert actors_response["data"]["count"] >= 2
