"""
BOS Identity Store - DB Provider
================================
Thin provider wrapper over identity service read functions.
"""

from __future__ import annotations

import uuid
from typing import Any

from core.identity_store.service import (
    list_actors_for_business,
    list_role_assignments_for_business,
    list_roles_for_business,
)


class DbIdentityProvider:
    def list_roles(self, business_id: uuid.UUID | str) -> tuple[dict[str, Any], ...]:
        return list_roles_for_business(business_id)

    def list_role_assignments(
        self,
        business_id: uuid.UUID | str,
    ) -> tuple[dict[str, Any], ...]:
        return list_role_assignments_for_business(business_id)

    def list_actors(self, business_id: uuid.UUID | str) -> tuple[dict[str, Any], ...]:
        return list_actors_for_business(business_id)
