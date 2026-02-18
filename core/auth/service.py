"""
BOS Auth - API Key Credential Service
=====================================
Deterministic normalization and CRUD lifecycle for API-key credentials.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from django.db import IntegrityError
from django.utils import timezone

from core.auth.models import ApiKeyActorType, ApiKeyCredential, ApiKeyStatus

_ACTOR_TYPE_NORMALIZATION = {
    "USER": ApiKeyActorType.HUMAN,
}
_VALID_ACTOR_TYPES = frozenset(
    {
        ApiKeyActorType.HUMAN,
        ApiKeyActorType.SYSTEM,
        ApiKeyActorType.DEVICE,
        ApiKeyActorType.AI,
    }
)


def _canonical_uuid_string(value: Any, *, field_name: str) -> str:
    try:
        return str(uuid.UUID(str(value).strip()))
    except Exception as exc:
        raise ValueError(f"{field_name} must contain valid UUID values.") from exc


def _ensure_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string.")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return stripped


def hash_api_key(api_key: str) -> str:
    key = _ensure_string(api_key, field_name="api_key")
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def normalize_actor_type(actor_type: str) -> str:
    normalized = _ensure_string(actor_type, field_name="actor_type").upper()
    normalized = _ACTOR_TYPE_NORMALIZATION.get(normalized, normalized)
    if normalized not in _VALID_ACTOR_TYPES:
        raise ValueError("actor_type must be one of HUMAN, SYSTEM, DEVICE, AI.")
    return normalized


def normalize_allowed_business_ids(values: Iterable[Any]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("allowed_business_ids must be a list/tuple of UUIDs.")
    normalized = {
        _canonical_uuid_string(value, field_name="allowed_business_ids")
        for value in values
    }
    if not normalized:
        raise ValueError("allowed_business_ids must contain at least one UUID.")
    return tuple(sorted(normalized))


def normalize_allowed_branch_ids_by_business(
    values: Mapping[Any, Iterable[Any]] | None,
    *,
    allowed_business_ids: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise ValueError("allowed_branch_ids_by_business must be an object.")

    allowed_business_set = set(allowed_business_ids)
    normalized: dict[str, tuple[str, ...]] = {}
    for business_id, branches in values.items():
        canonical_business_id = _canonical_uuid_string(
            business_id,
            field_name="allowed_branch_ids_by_business key",
        )
        if canonical_business_id not in allowed_business_set:
            raise ValueError(
                "allowed_branch_ids_by_business keys must exist in allowed_business_ids."
            )
        if isinstance(branches, (str, bytes)):
            raise ValueError(
                "allowed_branch_ids_by_business values must be lists/tuples."
            )
        canonical_branches = {
            _canonical_uuid_string(
                branch_id,
                field_name="allowed_branch_ids_by_business value",
            )
            for branch_id in branches
        }
        normalized[canonical_business_id] = tuple(sorted(canonical_branches))

    ordered_items = sorted(normalized.items(), key=lambda item: item[0])
    return {business_id: branch_ids for business_id, branch_ids in ordered_items}


def serialize_api_key_credential(credential: ApiKeyCredential) -> dict[str, Any]:
    return {
        "id": str(credential.id),
        "label": credential.label or None,
        "actor_id": credential.actor_id,
        "actor_type": credential.actor_type,
        "allowed_business_ids": tuple(credential.allowed_business_ids),
        "allowed_branch_ids_by_business": {
            business_id: tuple(branch_ids)
            for business_id, branch_ids in dict(
                credential.allowed_branch_ids_by_business
            ).items()
        },
        "status": credential.status,
        "created_at": credential.created_at.isoformat(),
        "revoked_at": (
            None if credential.revoked_at is None else credential.revoked_at.isoformat()
        ),
    }


class ApiKeyService:
    @staticmethod
    def create_api_key_credential(
        *,
        api_key: str,
        actor_id: str,
        actor_type: str,
        allowed_business_ids: Iterable[Any],
        allowed_branch_ids_by_business: Mapping[Any, Iterable[Any]] | None,
        created_by_actor_id: str,
        label: str | None = None,
    ) -> ApiKeyCredential:
        normalized_actor_type = normalize_actor_type(actor_type)
        normalized_business_ids = normalize_allowed_business_ids(allowed_business_ids)
        normalized_branches = normalize_allowed_branch_ids_by_business(
            allowed_branch_ids_by_business,
            allowed_business_ids=normalized_business_ids,
        )
        normalized_label = "" if label is None else str(label).strip()

        try:
            return ApiKeyCredential.objects.create(
                key_hash=hash_api_key(api_key),
                label=normalized_label,
                actor_id=_ensure_string(actor_id, field_name="actor_id"),
                actor_type=normalized_actor_type,
                allowed_business_ids=list(normalized_business_ids),
                allowed_branch_ids_by_business={
                    business_id: list(branch_ids)
                    for business_id, branch_ids in normalized_branches.items()
                },
                status=ApiKeyStatus.ACTIVE,
                created_by_actor_id=_ensure_string(
                    created_by_actor_id, field_name="created_by_actor_id"
                ),
            )
        except IntegrityError as exc:
            raise ValueError("API key hash already exists.") from exc

    @staticmethod
    def find_by_reference(
        *,
        key_id: uuid.UUID | str | None = None,
        key_hash: str | None = None,
    ) -> ApiKeyCredential | None:
        if key_id is None and (key_hash is None or not str(key_hash).strip()):
            raise ValueError("Either key_id or key_hash must be provided.")

        if key_id is not None:
            canonical_id = uuid.UUID(str(key_id))
            credential = ApiKeyCredential.objects.filter(id=canonical_id).first()
            if credential is None:
                return None
            if key_hash is not None and str(key_hash).strip():
                if credential.key_hash != str(key_hash).strip().lower():
                    raise ValueError("key_id and key_hash reference different credentials.")
            return credential

        canonical_hash = _ensure_string(key_hash, field_name="key_hash").lower()
        return ApiKeyCredential.objects.filter(key_hash=canonical_hash).first()

    @staticmethod
    def revoke_api_key_credential(
        *,
        key_id: uuid.UUID | str | None = None,
        key_hash: str | None = None,
        revoked_by_actor_id: str,
    ) -> ApiKeyCredential | None:
        credential = ApiKeyService.find_by_reference(key_id=key_id, key_hash=key_hash)
        if credential is None:
            return None
        if credential.status == ApiKeyStatus.REVOKED:
            return credential

        credential.status = ApiKeyStatus.REVOKED
        credential.revoked_at = timezone.now()
        credential.revoked_by_actor_id = _ensure_string(
            revoked_by_actor_id,
            field_name="revoked_by_actor_id",
        )
        credential.save(
            update_fields=["status", "revoked_at", "revoked_by_actor_id"]
        )
        return credential

    @staticmethod
    def rotate_api_key_credential(
        *,
        new_api_key: str,
        key_id: uuid.UUID | str | None = None,
        key_hash: str | None = None,
        rotated_by_actor_id: str,
        label: str | None = None,
    ) -> tuple[ApiKeyCredential, ApiKeyCredential] | None:
        existing = ApiKeyService.find_by_reference(key_id=key_id, key_hash=key_hash)
        if existing is None:
            return None
        if existing.status != ApiKeyStatus.ACTIVE:
            raise ValueError("Only ACTIVE API keys can be rotated.")

        replacement = ApiKeyService.create_api_key_credential(
            api_key=new_api_key,
            actor_id=existing.actor_id,
            actor_type=existing.actor_type,
            allowed_business_ids=tuple(existing.allowed_business_ids),
            allowed_branch_ids_by_business=dict(existing.allowed_branch_ids_by_business),
            created_by_actor_id=_ensure_string(
                rotated_by_actor_id,
                field_name="rotated_by_actor_id",
            ),
            label=existing.label if label is None else label,
        )
        revoked = ApiKeyService.revoke_api_key_credential(
            key_id=existing.id,
            revoked_by_actor_id=_ensure_string(
                rotated_by_actor_id,
                field_name="rotated_by_actor_id",
            ),
        )
        if revoked is None:
            raise ValueError("Failed to revoke existing API key during rotation.")
        return revoked, replacement

    @staticmethod
    def list_api_keys_for_business(
        *,
        business_id: uuid.UUID | str,
    ) -> tuple[ApiKeyCredential, ...]:
        canonical_business_id = _canonical_uuid_string(
            business_id,
            field_name="business_id",
        )
        rows = (
            ApiKeyCredential.objects.filter(
                allowed_business_ids__contains=[canonical_business_id]
            )
            .order_by("created_at", "id")
        )
        return tuple(rows)
