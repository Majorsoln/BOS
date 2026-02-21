"""
BOS Integration — Integration Permissions
=============================================
Controls who can activate, configure, and trigger integrations.
Business-scoped — each business manages its own adapters.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Set


# ══════════════════════════════════════════════════════════════
# PERMISSION CONSTANTS
# ══════════════════════════════════════════════════════════════

INTEGRATION_CONFIGURE = "integration.adapter.configure"
INTEGRATION_ENABLE = "integration.adapter.enable"
INTEGRATION_DISABLE = "integration.adapter.disable"
INTEGRATION_TEST = "integration.adapter.test"
INTEGRATION_VIEW_AUDIT = "integration.audit.view"


# ══════════════════════════════════════════════════════════════
# INTEGRATION SCOPE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IntegrationGrant:
    """Permission grant for integration operations."""

    actor_id: str
    business_id: uuid.UUID
    permissions: FrozenSet[str]


# ══════════════════════════════════════════════════════════════
# INTEGRATION PERMISSION CHECKER
# ══════════════════════════════════════════════════════════════

class IntegrationPermissionChecker:
    """
    Checks if an actor has integration permissions for a business.

    In-memory store — production wires to DB provider.
    """

    def __init__(self) -> None:
        self._grants: Dict[str, IntegrationGrant] = {}  # key: actor_id:business_id

    def grant(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        permissions: FrozenSet[str],
    ) -> IntegrationGrant:
        key = f"{actor_id}:{business_id}"
        g = IntegrationGrant(
            actor_id=actor_id,
            business_id=business_id,
            permissions=permissions,
        )
        self._grants[key] = g
        return g

    def check(
        self,
        actor_id: str,
        business_id: uuid.UUID,
        permission: str,
    ) -> bool:
        key = f"{actor_id}:{business_id}"
        grant = self._grants.get(key)
        if grant is None:
            return False
        return permission in grant.permissions

    def revoke(self, actor_id: str, business_id: uuid.UUID) -> None:
        key = f"{actor_id}:{business_id}"
        self._grants.pop(key, None)
