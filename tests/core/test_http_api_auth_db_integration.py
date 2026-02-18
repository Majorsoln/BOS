from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from core.admin.projections import AdminProjectionStore
from core.admin.repository import AdminRepository
from core.auth.models import ApiKeyCredential
from core.auth.provider import DbAuthProvider
from core.auth.service import ApiKeyService, hash_api_key
from core.http_api.contracts import (
    ApiKeyCreateHttpRequest,
    ApiKeyRevokeHttpRequest,
    ApiKeyRotateHttpRequest,
    BusinessReadRequest,
    FeatureFlagSetHttpRequest,
)
from core.http_api.dependencies import HttpApiDependencies
from core.http_api.handlers import (
    list_api_keys,
    list_feature_flags,
    post_api_key_create,
    post_api_key_revoke,
    post_api_key_rotate,
    post_feature_flag_set,
)
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_ADMIN_CONFIGURE,
    Role,
    ScopeGrant,
)

pytestmark = pytest.mark.django_db(transaction=True)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-auth-db-integration-business")
OTHER_BUSINESS_ID = uuid.uuid5(
    uuid.NAMESPACE_URL, "bos-auth-db-integration-business-other"
)
BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-auth-db-integration-branch")
OTHER_BRANCH_ID = uuid.uuid5(
    uuid.NAMESPACE_URL, "bos-auth-db-integration-branch-other"
)
ADMIN_ACTOR_ID = "integration-admin"


class FixedIdProvider:
    def __init__(self):
        self._counter = 0

    def new_command_id(self) -> uuid.UUID:
        value = uuid.uuid5(uuid.NAMESPACE_URL, f"bos-auth-db-command:{self._counter}")
        self._counter += 1
        return value

    def new_correlation_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"bos-auth-db-correlation:{self._counter}",
        )
        self._counter += 1
        return value


class FixedClock:
    def now_issued_at(self) -> datetime:
        return datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)


def _permission_provider_for_admin() -> InMemoryPermissionProvider:
    role = Role(
        role_id="admin-role",
        permissions=(PERMISSION_ADMIN_CONFIGURE,),
    )
    grant = ScopeGrant(
        actor_id=ADMIN_ACTOR_ID,
        role_id=role.role_id,
        business_id=BUSINESS_ID,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def _build_dependencies(
    *,
    permission_provider: InMemoryPermissionProvider | None = None,
) -> HttpApiDependencies:
    repository = AdminRepository(AdminProjectionStore())
    return HttpApiDependencies(
        admin_service=object(),
        admin_repository=repository,
        id_provider=FixedIdProvider(),
        clock=FixedClock(),
        auth_provider=DbAuthProvider(),
        permission_provider=permission_provider,
    )


def _create_admin_key(
    *,
    raw_key: str,
    allowed_business_ids: tuple[str, ...],
    allowed_branch_ids_by_business: dict[str, tuple[str, ...]],
) -> None:
    ApiKeyService.create_api_key_credential(
        api_key=raw_key,
        actor_id=ADMIN_ACTOR_ID,
        actor_type="USER",
        allowed_business_ids=allowed_business_ids,
        allowed_branch_ids_by_business=allowed_branch_ids_by_business,
        created_by_actor_id="bootstrap",
        label="Integration Admin Key",
    )


def _headers(raw_key: str, *, business_id: uuid.UUID, branch_id: uuid.UUID | None = None):
    value = {
        "X-API-KEY": raw_key,
        "X-BUSINESS-ID": str(business_id),
    }
    if branch_id is not None:
        value["X-BRANCH-ID"] = str(branch_id)
    return value


def test_db_auth_read_handler_succeeds_with_active_key() -> None:
    admin_key = "db-read-success-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    dependencies = _build_dependencies()

    response = list_feature_flags(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID),
    )

    assert response["ok"] is True
    assert "data" in response


def test_db_auth_rejects_unauthorized_business() -> None:
    admin_key = "db-business-denied-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(OTHER_BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    dependencies = _build_dependencies()

    response = list_feature_flags(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ACTOR_UNAUTHORIZED_BUSINESS"


def test_db_auth_rejects_unauthorized_branch() -> None:
    admin_key = "db-branch-denied-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={str(BUSINESS_ID): (str(OTHER_BRANCH_ID),)},
    )
    dependencies = _build_dependencies()

    response = post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            flag_key="ENABLE_DOCUMENT_DESIGNER",
            status="ENABLED",
            branch_id=BRANCH_ID,
        ),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID, branch_id=BRANCH_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ACTOR_UNAUTHORIZED_BRANCH"


def test_api_key_create_handler_stores_only_hash_and_returns_raw_once() -> None:
    admin_key = "db-create-admin-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    dependencies = _build_dependencies(permission_provider=_permission_provider_for_admin())

    response = post_api_key_create(
        ApiKeyCreateHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            actor_id="new-http-user",
            actor_type="HUMAN",
            allowed_business_ids=(str(BUSINESS_ID),),
            allowed_branch_ids_by_business={},
            label="Created via HTTP",
            branch_id=None,
        ),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID),
    )

    assert response["ok"] is True
    raw_created_key = response["data"]["api_key"]
    credential_id = response["data"]["credential"]["id"]

    stored = ApiKeyCredential.objects.get(id=uuid.UUID(credential_id))
    assert stored.key_hash == hash_api_key(raw_created_key)
    assert stored.key_hash != raw_created_key


def test_api_key_list_returns_metadata_without_raw_key() -> None:
    admin_key = "db-list-admin-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    ApiKeyService.create_api_key_credential(
        api_key="db-list-target-key",
        actor_id="list-user",
        actor_type="HUMAN",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
        created_by_actor_id="bootstrap",
        label="List Target",
    )
    dependencies = _build_dependencies(permission_provider=_permission_provider_for_admin())

    response = list_api_keys(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID),
    )

    assert response["ok"] is True
    assert response["data"]["count"] >= 2
    first_item = response["data"]["items"][0]
    assert "api_key" not in first_item


def test_api_key_revoke_handler_marks_credential_revoked() -> None:
    admin_key = "db-revoke-admin-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    target_raw_key = "db-revoke-target-key"
    target = ApiKeyService.create_api_key_credential(
        api_key=target_raw_key,
        actor_id="revoke-user",
        actor_type="HUMAN",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
        created_by_actor_id="bootstrap",
        label="Revoke Target",
    )
    dependencies = _build_dependencies(permission_provider=_permission_provider_for_admin())

    response = post_api_key_revoke(
        ApiKeyRevokeHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            key_id=target.id,
            key_hash=None,
            branch_id=None,
        ),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID),
    )

    assert response["ok"] is True
    assert response["data"]["revoked"] is True
    assert response["data"]["credential"]["status"] == "REVOKED"
    assert DbAuthProvider().resolve_api_key(target_raw_key) is None


def test_api_key_rotate_handler_revokes_old_and_returns_new_key() -> None:
    admin_key = "db-rotate-admin-key"
    _create_admin_key(
        raw_key=admin_key,
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    old_raw_key = "db-rotate-target-key"
    target = ApiKeyService.create_api_key_credential(
        api_key=old_raw_key,
        actor_id="rotate-user",
        actor_type="HUMAN",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
        created_by_actor_id="bootstrap",
        label="Rotate Target",
    )
    dependencies = _build_dependencies(permission_provider=_permission_provider_for_admin())

    response = post_api_key_rotate(
        ApiKeyRotateHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            key_id=target.id,
            key_hash=None,
            label="Rotated Label",
            branch_id=None,
        ),
        dependencies,
        headers=_headers(admin_key, business_id=BUSINESS_ID),
    )

    assert response["ok"] is True
    assert response["data"]["revoked_credential"]["status"] == "REVOKED"
    assert response["data"]["credential"]["status"] == "ACTIVE"
    assert response["data"]["credential"]["label"] == "Rotated Label"

    new_raw_key = response["data"]["api_key"]
    assert DbAuthProvider().resolve_api_key(old_raw_key) is None
    assert DbAuthProvider().resolve_api_key(new_raw_key) is not None
