"""
BOS Core Security — Tenant Isolation Enforcement
====================================================
Hardened cross-tenant boundary checks.

Doctrine: Every command, event, and query is scoped to a business_id.
AI components are scoped to their tenant — never global.
Error messages MUST NOT leak cross-tenant data.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Set

from core.commands.rejection import RejectionReason, ReasonCode


# ══════════════════════════════════════════════════════════════
# TENANT SCOPE — What an actor is allowed to access
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantScope:
    """
    An actor's authorized tenant boundaries.

    business_ids: set of businesses the actor can access.
    branch_ids_by_business: per-business set of authorized branches.
        Empty set means business-scope only (no branch access).
        None key means all branches allowed for that business.
    """

    actor_id: str
    business_ids: FrozenSet[uuid.UUID]
    branch_ids_by_business: dict = field(default_factory=dict)
    # { business_id: frozenset[branch_id] | None (all branches) }

    def can_access_business(self, business_id: uuid.UUID) -> bool:
        return business_id in self.business_ids

    def can_access_branch(
        self, business_id: uuid.UUID, branch_id: uuid.UUID
    ) -> bool:
        if not self.can_access_business(business_id):
            return False
        allowed = self.branch_ids_by_business.get(business_id)
        if allowed is None:
            # None means all branches allowed for this business
            return True
        return branch_id in allowed


# ══════════════════════════════════════════════════════════════
# ISOLATION CHECK
# ══════════════════════════════════════════════════════════════

def check_tenant_isolation(
    scope: TenantScope,
    business_id: uuid.UUID,
    branch_id: Optional[uuid.UUID] = None,
) -> Optional[RejectionReason]:
    """
    Verify actor is authorized for the target business/branch.

    Returns None if allowed, RejectionReason if denied.
    Error messages are generic — no cross-tenant data leakage.
    """
    if not scope.can_access_business(business_id):
        return RejectionReason(
            code=ReasonCode.PERMISSION_DENIED,
            message="Access denied: actor is not authorized for this business.",
            policy_name="check_tenant_isolation",
        )

    if branch_id is not None and not scope.can_access_branch(business_id, branch_id):
        return RejectionReason(
            code=ReasonCode.PERMISSION_DENIED,
            message="Access denied: actor is not authorized for this branch.",
            policy_name="check_tenant_isolation",
        )

    return None


# ══════════════════════════════════════════════════════════════
# SCOPE BUILDER (from permission grants)
# ══════════════════════════════════════════════════════════════

def build_tenant_scope(
    actor_id: str,
    grants: list,
) -> TenantScope:
    """
    Build a TenantScope from a list of scope grants.

    Each grant is expected to have:
      - business_id: uuid.UUID
      - branch_id: Optional[uuid.UUID] (None = business-level grant)
      - scope_type: "BUSINESS" | "BRANCH"
    """
    business_ids: Set[uuid.UUID] = set()
    branch_map: dict = {}

    for grant in grants:
        biz_id = grant.get("business_id") or getattr(grant, "business_id", None)
        branch_id = grant.get("branch_id") or getattr(grant, "branch_id", None)
        scope_type = grant.get("scope_type") or getattr(grant, "scope_type", "BUSINESS")

        if biz_id is None:
            continue

        business_ids.add(biz_id)

        if scope_type == "BUSINESS":
            # Business-level grant → all branches
            branch_map[biz_id] = None
        elif scope_type == "BRANCH" and branch_id is not None:
            if branch_map.get(biz_id) is None and biz_id in branch_map:
                # Already has full business grant
                continue
            branch_map.setdefault(biz_id, set())
            if isinstance(branch_map[biz_id], set):
                branch_map[biz_id].add(branch_id)

    # Freeze sets
    frozen_branches = {}
    for biz_id, branches in branch_map.items():
        if branches is None:
            frozen_branches[biz_id] = None
        else:
            frozen_branches[biz_id] = frozenset(branches)

    return TenantScope(
        actor_id=actor_id,
        business_ids=frozenset(business_ids),
        branch_ids_by_business=frozen_branches,
    )
