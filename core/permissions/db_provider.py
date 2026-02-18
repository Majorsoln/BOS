"""
BOS Permissions - DB-backed Provider
====================================
Resolves role grants and role permissions from relational identity tables.
"""

from __future__ import annotations

import uuid

from core.permissions.constants import (
    SCOPE_GRANT_BRANCH,
    SCOPE_GRANT_BUSINESS,
    VALID_PERMISSIONS,
)
from core.permissions.models import Role, ScopeGrant


class DbPermissionProvider:
    def get_grants_for_actor(
        self,
        actor_id: str,
        business_id: uuid.UUID,
    ) -> tuple[ScopeGrant, ...]:
        if not isinstance(actor_id, str) or not actor_id.strip():
            return tuple()
        if not isinstance(business_id, uuid.UUID):
            return tuple()

        from core.identity_store.models import RoleAssignment, RoleAssignmentStatus

        rows = (
            RoleAssignment.objects.filter(
                actor_id=actor_id.strip(),
                business_id=business_id,
            )
            .order_by(
                "business_id",
                "actor_id",
                "branch_id",
                "role_id",
                "id",
            )
        )
        grants: list[ScopeGrant] = []
        for row in rows:
            if row.status not in (
                RoleAssignmentStatus.ACTIVE,
                RoleAssignmentStatus.INACTIVE,
            ):
                continue

            scope_type = (
                SCOPE_GRANT_BUSINESS
                if row.branch_id is None
                else SCOPE_GRANT_BRANCH
            )
            try:
                grants.append(
                    ScopeGrant(
                        actor_id=row.actor_id,
                        role_id=str(row.role_id),
                        business_id=row.business_id,
                        scope_type=scope_type,
                        branch_id=row.branch_id,
                        status=row.status,
                    )
                )
            except Exception:
                continue

        return tuple(sorted(grants, key=lambda grant: grant.sort_key()))

    def get_role(self, role_id: str) -> Role | None:
        try:
            canonical_role_id = uuid.UUID(str(role_id).strip())
        except Exception:
            return None

        from core.identity_store.models import Role as IdentityRole

        role = IdentityRole.objects.filter(role_id=canonical_role_id).first()
        if role is None:
            return None

        from core.permissions_store.models import RolePermission

        permission_values = tuple(
            RolePermission.objects.filter(role_id=canonical_role_id)
            .order_by("permission_key")
            .values_list("permission_key", flat=True)
        )
        filtered_permissions = tuple(
            sorted(permission for permission in permission_values if permission in VALID_PERMISSIONS)
        )
        if not filtered_permissions:
            return None

        try:
            return Role(
                role_id=str(role.role_id),
                permissions=filtered_permissions,
            )
        except Exception:
            return None
