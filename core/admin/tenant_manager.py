"""
BOS Admin — Tenant Lifecycle Manager
========================================
Commands and projections for business tenant lifecycle:
CREATED → ACTIVE → SUSPENDED → CLOSED

All transitions are event-sourced and deterministic.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.business.models import Business, BusinessState, Branch
from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# TENANT EVENT TYPES
# ══════════════════════════════════════════════════════════════

TENANT_CREATED_V1 = "admin.tenant.created.v1"
TENANT_ACTIVATED_V1 = "admin.tenant.activated.v1"
TENANT_SUSPENDED_V1 = "admin.tenant.suspended.v1"
TENANT_CLOSED_V1 = "admin.tenant.closed.v1"
TENANT_BRANCH_ADDED_V1 = "admin.tenant.branch_added.v1"
TENANT_BRANCH_CLOSED_V1 = "admin.tenant.branch_closed.v1"

TENANT_EVENT_TYPES = (
    TENANT_CREATED_V1,
    TENANT_ACTIVATED_V1,
    TENANT_SUSPENDED_V1,
    TENANT_CLOSED_V1,
    TENANT_BRANCH_ADDED_V1,
    TENANT_BRANCH_CLOSED_V1,
)


# ══════════════════════════════════════════════════════════════
# TENANT LIFECYCLE REQUESTS (frozen command DTOs)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CreateTenantRequest:
    business_name: str
    country_code: str
    timezone: str
    actor_id: str
    issued_at: datetime
    initial_branch_name: Optional[str] = None
    initial_branch_location: Optional[str] = None


@dataclass(frozen=True)
class ActivateTenantRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SuspendTenantRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class CloseTenantRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class AddBranchRequest:
    business_id: uuid.UUID
    branch_name: str
    actor_id: str
    issued_at: datetime
    location: Optional[str] = None


@dataclass(frozen=True)
class CloseBranchRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# VALID TRANSITIONS
# ══════════════════════════════════════════════════════════════

_VALID_TRANSITIONS: Dict[BusinessState, List[BusinessState]] = {
    BusinessState.CREATED: [BusinessState.ACTIVE, BusinessState.CLOSED],
    BusinessState.ACTIVE: [BusinessState.SUSPENDED, BusinessState.CLOSED],
    BusinessState.SUSPENDED: [BusinessState.ACTIVE, BusinessState.CLOSED],
    BusinessState.CLOSED: [],  # terminal state
}


def _can_transition(current: BusinessState, target: BusinessState) -> bool:
    return target in _VALID_TRANSITIONS.get(current, [])


# ══════════════════════════════════════════════════════════════
# TENANT PROJECTION (in-memory state from events)
# ══════════════════════════════════════════════════════════════

class TenantProjection:
    """
    In-memory projection of all tenants and their branches.

    Rebuilt deterministically from tenant events.
    """

    projection_name = "tenant_projection"

    def __init__(self) -> None:
        self._businesses: Dict[uuid.UUID, Business] = {}
        self._branches: Dict[uuid.UUID, List[Branch]] = defaultdict(list)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == TENANT_CREATED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            created_at = payload.get("created_at", payload.get("issued_at"))
            self._businesses[biz_id] = Business(
                business_id=biz_id,
                name=payload["business_name"],
                state=BusinessState.CREATED,
                country_code=payload.get("country_code", ""),
                timezone=payload.get("timezone", "UTC"),
                created_at=created_at,
            )

        elif event_type == TENANT_ACTIVATED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            old = self._businesses.get(biz_id)
            if old:
                self._businesses[biz_id] = Business(
                    business_id=old.business_id,
                    name=old.name,
                    state=BusinessState.ACTIVE,
                    country_code=old.country_code,
                    timezone=old.timezone,
                    created_at=old.created_at,
                )

        elif event_type == TENANT_SUSPENDED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            old = self._businesses.get(biz_id)
            if old:
                self._businesses[biz_id] = Business(
                    business_id=old.business_id,
                    name=old.name,
                    state=BusinessState.SUSPENDED,
                    country_code=old.country_code,
                    timezone=old.timezone,
                    created_at=old.created_at,
                )

        elif event_type == TENANT_CLOSED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            old = self._businesses.get(biz_id)
            if old:
                closed_at = payload.get("closed_at", payload.get("issued_at"))
                self._businesses[biz_id] = Business(
                    business_id=old.business_id,
                    name=old.name,
                    state=BusinessState.CLOSED,
                    country_code=old.country_code,
                    timezone=old.timezone,
                    created_at=old.created_at,
                    closed_at=closed_at,
                )

        elif event_type == TENANT_BRANCH_ADDED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            branch_id = uuid.UUID(str(payload["branch_id"]))
            branch = Branch(
                branch_id=branch_id,
                business_id=biz_id,
                name=payload.get("branch_name", ""),
                created_at=payload.get("created_at", payload.get("issued_at")),
                location=payload.get("location"),
            )
            self._branches[biz_id].append(branch)

        elif event_type == TENANT_BRANCH_CLOSED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            branch_id = uuid.UUID(str(payload["branch_id"]))
            closed_at = payload.get("closed_at", payload.get("issued_at"))
            updated = []
            for b in self._branches.get(biz_id, []):
                if b.branch_id == branch_id:
                    updated.append(Branch(
                        branch_id=b.branch_id,
                        business_id=b.business_id,
                        name=b.name,
                        created_at=b.created_at,
                        location=b.location,
                        closed_at=closed_at,
                    ))
                else:
                    updated.append(b)
            self._branches[biz_id] = updated

    def get_business(self, business_id: uuid.UUID) -> Optional[Business]:
        return self._businesses.get(business_id)

    def list_businesses(self) -> List[Business]:
        return list(self._businesses.values())

    def list_active_businesses(self) -> List[Business]:
        return [b for b in self._businesses.values() if b.is_active()]

    def get_branches(self, business_id: uuid.UUID) -> List[Branch]:
        return list(self._branches.get(business_id, []))

    def get_open_branches(self, business_id: uuid.UUID) -> List[Branch]:
        return [b for b in self._branches.get(business_id, []) if b.is_open()]

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            self._businesses.pop(business_id, None)
            self._branches.pop(business_id, None)
        else:
            self._businesses.clear()
            self._branches.clear()


# ══════════════════════════════════════════════════════════════
# TENANT MANAGER (orchestrates lifecycle)
# ══════════════════════════════════════════════════════════════

class TenantManager:
    """
    Orchestrates tenant lifecycle operations.

    All mutations produce events — no direct state writes.
    """

    def __init__(self, projection: TenantProjection) -> None:
        self._projection = projection

    def create_tenant(
        self, request: CreateTenantRequest
    ) -> Dict[str, Any]:
        """Create a new business tenant. Returns event payload."""
        business_id = uuid.uuid4()
        payload = {
            "business_id": str(business_id),
            "business_name": request.business_name,
            "country_code": request.country_code,
            "timezone": request.timezone,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
            "created_at": request.issued_at,
        }
        self._projection.apply(TENANT_CREATED_V1, payload)

        # Auto-create initial branch if requested
        events = [{"event_type": TENANT_CREATED_V1, "payload": payload}]

        if request.initial_branch_name:
            branch_id = uuid.uuid4()
            branch_payload = {
                "business_id": str(business_id),
                "branch_id": str(branch_id),
                "branch_name": request.initial_branch_name,
                "location": request.initial_branch_location,
                "actor_id": request.actor_id,
                "issued_at": request.issued_at,
                "created_at": request.issued_at,
            }
            self._projection.apply(TENANT_BRANCH_ADDED_V1, branch_payload)
            events.append({"event_type": TENANT_BRANCH_ADDED_V1, "payload": branch_payload})

        return {"business_id": business_id, "events": events}

    def activate_tenant(
        self, request: ActivateTenantRequest
    ) -> Optional[RejectionReason]:
        biz = self._projection.get_business(request.business_id)
        if biz is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Business not found.",
                policy_name="activate_tenant",
            )
        if not _can_transition(biz.state, BusinessState.ACTIVE):
            return RejectionReason(
                code="INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot transition from {biz.state.value} to ACTIVE.",
                policy_name="activate_tenant",
            )
        self._projection.apply(TENANT_ACTIVATED_V1, {
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def suspend_tenant(
        self, request: SuspendTenantRequest
    ) -> Optional[RejectionReason]:
        biz = self._projection.get_business(request.business_id)
        if biz is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Business not found.",
                policy_name="suspend_tenant",
            )
        if not _can_transition(biz.state, BusinessState.SUSPENDED):
            return RejectionReason(
                code="INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot transition from {biz.state.value} to SUSPENDED.",
                policy_name="suspend_tenant",
            )
        self._projection.apply(TENANT_SUSPENDED_V1, {
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "reason": request.reason,
            "issued_at": request.issued_at,
        })
        return None

    def close_tenant(
        self, request: CloseTenantRequest
    ) -> Optional[RejectionReason]:
        biz = self._projection.get_business(request.business_id)
        if biz is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Business not found.",
                policy_name="close_tenant",
            )
        if not _can_transition(biz.state, BusinessState.CLOSED):
            return RejectionReason(
                code="INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot transition from {biz.state.value} to CLOSED.",
                policy_name="close_tenant",
            )
        self._projection.apply(TENANT_CLOSED_V1, {
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "reason": request.reason,
            "issued_at": request.issued_at,
            "closed_at": request.issued_at,
        })
        return None

    def add_branch(
        self, request: AddBranchRequest
    ) -> Optional[RejectionReason]:
        biz = self._projection.get_business(request.business_id)
        if biz is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Business not found.",
                policy_name="add_branch",
            )
        if not biz.is_operational():
            return RejectionReason(
                code="TENANT_NOT_OPERATIONAL",
                message="Cannot add branch to a non-operational business.",
                policy_name="add_branch",
            )
        branch_id = uuid.uuid4()
        self._projection.apply(TENANT_BRANCH_ADDED_V1, {
            "business_id": str(request.business_id),
            "branch_id": str(branch_id),
            "branch_name": request.branch_name,
            "location": request.location,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
            "created_at": request.issued_at,
        })
        return None

    def close_branch(
        self, request: CloseBranchRequest
    ) -> Optional[RejectionReason]:
        biz = self._projection.get_business(request.business_id)
        if biz is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Business not found.",
                policy_name="close_branch",
            )
        branches = self._projection.get_branches(request.business_id)
        target = next(
            (b for b in branches if b.branch_id == request.branch_id), None
        )
        if target is None:
            return RejectionReason(
                code="BRANCH_NOT_FOUND",
                message="Branch not found.",
                policy_name="close_branch",
            )
        if not target.is_open():
            return RejectionReason(
                code="BRANCH_ALREADY_CLOSED",
                message="Branch is already closed.",
                policy_name="close_branch",
            )
        self._projection.apply(TENANT_BRANCH_CLOSED_V1, {
            "business_id": str(request.business_id),
            "branch_id": str(request.branch_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
            "closed_at": request.issued_at,
        })
        return None
