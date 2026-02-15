"""
BOS HTTP API Auth - Provider and Principal Models
=================================================
Deterministic API-key principal resolution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Mapping, Protocol


def _canonical_uuid_string(value: str, *, field_name: str) -> str:
    try:
        return str(uuid.UUID(str(value).strip()))
    except Exception as exc:
        raise ValueError(f"{field_name} must be a valid UUID string.") from exc


def _normalize_uuid_tuple(values, *, field_name: str) -> tuple[str, ...]:
    normalized = {
        _canonical_uuid_string(value, field_name=field_name) for value in values
    }
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class AuthPrincipal:
    actor_id: str
    actor_type: str
    allowed_business_ids: tuple[str, ...]
    allowed_branch_ids_by_business: dict[str, tuple[str, ...]]

    def __post_init__(self):
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")
        if not self.actor_type or not isinstance(self.actor_type, str):
            raise ValueError("actor_type must be a non-empty string.")

        if not isinstance(self.allowed_business_ids, tuple):
            raise ValueError("allowed_business_ids must be a tuple.")
        if not isinstance(self.allowed_branch_ids_by_business, dict):
            raise ValueError("allowed_branch_ids_by_business must be a dict.")

        normalized_business_ids = _normalize_uuid_tuple(
            self.allowed_business_ids,
            field_name="allowed_business_ids",
        )
        object.__setattr__(self, "allowed_business_ids", normalized_business_ids)

        normalized_branch_map: dict[str, tuple[str, ...]] = {}
        for business_id, branch_ids in self.allowed_branch_ids_by_business.items():
            canonical_business_id = _canonical_uuid_string(
                business_id,
                field_name="allowed_branch_ids_by_business key",
            )
            if not isinstance(branch_ids, tuple):
                raise ValueError(
                    "allowed_branch_ids_by_business values must be tuples."
                )
            normalized_branch_map[canonical_business_id] = _normalize_uuid_tuple(
                branch_ids,
                field_name="allowed_branch_ids_by_business value",
            )

        ordered_items = sorted(normalized_branch_map.items(), key=lambda item: item[0])
        object.__setattr__(
            self,
            "allowed_branch_ids_by_business",
            {key: value for key, value in ordered_items},
        )


class AuthProvider(Protocol):
    def resolve_api_key(self, api_key: str) -> AuthPrincipal | None:
        ...


class InMemoryAuthProvider:
    """
    Deterministic in-memory auth provider for tests/bootstrap.
    """

    def __init__(self, api_key_to_principal: Mapping[str, AuthPrincipal] | None = None):
        normalized: dict[str, AuthPrincipal] = {}
        for api_key, principal in sorted(
            dict(api_key_to_principal or {}).items(),
            key=lambda item: item[0],
        ):
            if not isinstance(api_key, str) or not api_key.strip():
                raise ValueError("API key must be a non-empty string.")
            if not isinstance(principal, AuthPrincipal):
                raise ValueError("Principal must be AuthPrincipal.")
            normalized[api_key] = principal
        self._api_key_to_principal = normalized

    def resolve_api_key(self, api_key: str) -> AuthPrincipal | None:
        if not isinstance(api_key, str):
            return None
        return self._api_key_to_principal.get(api_key)

