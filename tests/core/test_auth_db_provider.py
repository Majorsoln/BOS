from __future__ import annotations

import uuid

import pytest

from core.auth.models import ApiKeyCredential, ApiKeyStatus
from core.auth.provider import DbAuthProvider
from core.auth.service import ApiKeyService, hash_api_key

pytestmark = pytest.mark.django_db(transaction=True)


def test_db_auth_provider_resolves_active_key_to_principal() -> None:
    business_id = uuid.uuid4()
    branch_id = uuid.uuid4()
    raw_api_key = "provider-active-key"
    actor_id = "db-auth-admin"

    ApiKeyService.create_api_key_credential(
        api_key=raw_api_key,
        actor_id=actor_id,
        actor_type="USER",
        allowed_business_ids=(str(business_id),),
        allowed_branch_ids_by_business={str(business_id): (str(branch_id),)},
        created_by_actor_id="bootstrap",
        label="Provider Active Key",
    )

    principal = DbAuthProvider().resolve_api_key(raw_api_key)

    assert principal is not None
    assert principal.actor_id == actor_id
    assert principal.actor_type == "HUMAN"
    assert principal.allowed_business_ids == (str(business_id),)
    assert principal.allowed_branch_ids_by_business[str(business_id)] == (str(branch_id),)


def test_db_auth_provider_returns_none_for_revoked_key() -> None:
    business_id = uuid.uuid4()
    raw_api_key = "provider-revoked-key"

    credential = ApiKeyService.create_api_key_credential(
        api_key=raw_api_key,
        actor_id="db-auth-user",
        actor_type="HUMAN",
        allowed_business_ids=(str(business_id),),
        allowed_branch_ids_by_business={},
        created_by_actor_id="bootstrap",
        label="Provider Revoked Key",
    )
    ApiKeyService.revoke_api_key_credential(
        key_id=credential.id,
        revoked_by_actor_id="bootstrap",
    )

    principal = DbAuthProvider().resolve_api_key(raw_api_key)
    assert principal is None


def test_service_normalization_and_hash_storage_are_deterministic() -> None:
    business_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    business_b = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    branch_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    branch_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    raw_api_key = "normalization-key"

    credential = ApiKeyService.create_api_key_credential(
        api_key=raw_api_key,
        actor_id="normalize-user",
        actor_type="user",
        allowed_business_ids=(str(business_b).upper(), str(business_a), str(business_b)),
        allowed_branch_ids_by_business={
            str(business_b).upper(): (str(branch_2), str(branch_1), str(branch_2)),
            str(business_a): tuple(),
        },
        created_by_actor_id="bootstrap",
        label="Normalize Key",
    )

    row = ApiKeyCredential.objects.get(id=credential.id)

    assert row.key_hash == hash_api_key(raw_api_key)
    assert row.status == ApiKeyStatus.ACTIVE
    assert row.actor_type == "HUMAN"
    assert row.allowed_business_ids == [str(business_a), str(business_b)]
    assert row.allowed_branch_ids_by_business == {
        str(business_a): [],
        str(business_b): [str(branch_1), str(branch_2)],
    }
