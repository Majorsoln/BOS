"""
BOS Permissions - Provider Protocol and In-Memory Provider
==========================================================
"""

from __future__ import annotations

import uuid
from typing import Iterable, Protocol

from core.permissions.models import Role, ScopeGrant


class PermissionProvider(Protocol):
    def get_grants_for_actor(
        self,
        actor_id: str,
        business_id: uuid.UUID,
    ) -> tuple[ScopeGrant, ...]:
        ...

    def get_role(self, role_id: str) -> Role | None:
        ...


class InMemoryPermissionProvider:
    """
    Deterministic in-memory provider used for bootstrap/tests.
    """

    def __init__(
        self,
        roles: Iterable[Role] | None = None,
        grants: Iterable[ScopeGrant] | None = None,
    ):
        self._roles: dict[str, Role] = {}
        self._grants_by_actor_business: dict[
            tuple[str, uuid.UUID], tuple[ScopeGrant, ...]
        ] = {}

        for role in roles or ():
            if role.role_id in self._roles:
                raise ValueError(f"Duplicate role_id '{role.role_id}'.")
            self._roles[role.role_id] = role

        temp_index: dict[tuple[str, uuid.UUID], list[ScopeGrant]] = {}
        for grant in grants or ():
            key = (grant.actor_id, grant.business_id)
            temp_index.setdefault(key, []).append(grant)

        for key, key_grants in temp_index.items():
            ordered = tuple(sorted(key_grants, key=lambda g: g.sort_key()))
            self._grants_by_actor_business[key] = ordered

    def get_grants_for_actor(
        self,
        actor_id: str,
        business_id: uuid.UUID,
    ) -> tuple[ScopeGrant, ...]:
        return self._grants_by_actor_business.get(
            (actor_id, business_id), tuple()
        )

    def get_role(self, role_id: str) -> Role | None:
        return self._roles.get(role_id)
