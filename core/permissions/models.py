"""
BOS Permissions - Immutable Role/Grant Models
=============================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from core.permissions.constants import (
    GRANT_STATUS_ACTIVE,
    SCOPE_GRANT_BRANCH,
    SCOPE_GRANT_BUSINESS,
    VALID_GRANT_STATUSES,
    VALID_PERMISSIONS,
    VALID_SCOPE_TYPES,
)


@dataclass(frozen=True)
class Role:
    role_id: str
    permissions: tuple[str, ...]

    def __post_init__(self):
        if not self.role_id or not isinstance(self.role_id, str):
            raise ValueError("role_id must be a non-empty string.")

        if not isinstance(self.permissions, tuple):
            raise ValueError("permissions must be a tuple.")

        normalized = tuple(sorted(set(self.permissions)))
        if not normalized:
            raise ValueError("permissions must contain at least one value.")

        for permission in normalized:
            if not isinstance(permission, str) or not permission:
                raise ValueError("permission values must be non-empty strings.")
            if permission not in VALID_PERMISSIONS:
                raise ValueError(
                    f"permission '{permission}' not valid. "
                    f"Must be one of: {sorted(VALID_PERMISSIONS)}"
                )

        object.__setattr__(self, "permissions", normalized)


@dataclass(frozen=True)
class ScopeGrant:
    actor_id: str
    role_id: str
    business_id: uuid.UUID
    scope_type: str = SCOPE_GRANT_BUSINESS
    branch_id: Optional[uuid.UUID] = None
    status: str = GRANT_STATUS_ACTIVE

    def __post_init__(self):
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")

        if not self.role_id or not isinstance(self.role_id, str):
            raise ValueError("role_id must be a non-empty string.")

        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        if self.scope_type not in VALID_SCOPE_TYPES:
            raise ValueError(
                f"scope_type '{self.scope_type}' not valid. "
                f"Must be one of: {sorted(VALID_SCOPE_TYPES)}"
            )

        if self.status not in VALID_GRANT_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_GRANT_STATUSES)}"
            )

        if self.scope_type == SCOPE_GRANT_BRANCH:
            if not isinstance(self.branch_id, uuid.UUID):
                raise ValueError(
                    "branch_id must be UUID when scope_type is BRANCH."
                )
        elif self.branch_id is not None:
            raise ValueError(
                "branch_id must be None when scope_type is BUSINESS."
            )

    def sort_key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.actor_id,
            str(self.business_id),
            self.scope_type,
            "" if self.branch_id is None else str(self.branch_id),
            self.role_id,
            self.status,
        )
