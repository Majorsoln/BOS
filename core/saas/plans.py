"""
BOS SaaS — Subscription Plans & Plan-Based Engine Activation
================================================================
Defines subscription plan tiers with included engines, quotas,
and pricing.  Plan-based engine activation ties feature flags
to the tenant's active plan.

All changes are event-sourced and deterministic.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# PLAN EVENT TYPES
# ══════════════════════════════════════════════════════════════

PLAN_DEFINED_V1 = "saas.plan.defined.v1"
PLAN_UPDATED_V1 = "saas.plan.updated.v1"
PLAN_DEACTIVATED_V1 = "saas.plan.deactivated.v1"

PLAN_EVENT_TYPES = (
    PLAN_DEFINED_V1,
    PLAN_UPDATED_V1,
    PLAN_DEACTIVATED_V1,
)


# ══════════════════════════════════════════════════════════════
# PLAN TIER ENUM
# ══════════════════════════════════════════════════════════════

class PlanTier(Enum):
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


# ══════════════════════════════════════════════════════════════
# PLAN DATA MODELS (frozen)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PlanQuota:
    """Usage limits included in a plan."""
    max_branches: int
    max_users: int
    max_api_calls_per_month: int
    max_documents_per_month: int


@dataclass(frozen=True)
class PlanDefinition:
    """Immutable subscription plan definition."""
    plan_id: uuid.UUID
    name: str
    tier: PlanTier
    included_engines: FrozenSet[str]
    quota: PlanQuota
    monthly_price: Decimal
    currency: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# PLAN REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DefinePlanRequest:
    name: str
    tier: str                  # PlanTier value
    included_engines: Tuple[str, ...]
    max_branches: int
    max_users: int
    max_api_calls_per_month: int
    max_documents_per_month: int
    monthly_price: Decimal
    currency: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class UpdatePlanRequest:
    plan_id: uuid.UUID
    name: Optional[str] = None
    included_engines: Optional[Tuple[str, ...]] = None
    max_branches: Optional[int] = None
    max_users: Optional[int] = None
    max_api_calls_per_month: Optional[int] = None
    max_documents_per_month: Optional[int] = None
    monthly_price: Optional[Decimal] = None
    actor_id: str = ""
    issued_at: Optional[datetime] = None


@dataclass(frozen=True)
class DeactivatePlanRequest:
    plan_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# PLAN PROJECTION (in-memory state from events)
# ══════════════════════════════════════════════════════════════

class PlanProjection:
    """
    In-memory projection of all subscription plans.

    Rebuilt deterministically from plan events.
    """

    projection_name = "plan_projection"

    def __init__(self) -> None:
        self._plans: Dict[uuid.UUID, PlanDefinition] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == PLAN_DEFINED_V1:
            plan_id = uuid.UUID(str(payload["plan_id"]))
            tier = PlanTier(payload["tier"])
            engines = frozenset(payload.get("included_engines", []))
            quota = PlanQuota(
                max_branches=payload.get("max_branches", 1),
                max_users=payload.get("max_users", 1),
                max_api_calls_per_month=payload.get("max_api_calls_per_month", 1000),
                max_documents_per_month=payload.get("max_documents_per_month", 100),
            )
            self._plans[plan_id] = PlanDefinition(
                plan_id=plan_id,
                name=payload["name"],
                tier=tier,
                included_engines=engines,
                quota=quota,
                monthly_price=Decimal(str(payload.get("monthly_price", "0"))),
                currency=payload.get("currency", "USD"),
                is_active=True,
                created_at=payload.get("issued_at"),
            )

        elif event_type == PLAN_UPDATED_V1:
            plan_id = uuid.UUID(str(payload["plan_id"]))
            old = self._plans.get(plan_id)
            if old is None:
                return
            engines = (
                frozenset(payload["included_engines"])
                if "included_engines" in payload
                else old.included_engines
            )
            quota = PlanQuota(
                max_branches=payload.get("max_branches", old.quota.max_branches),
                max_users=payload.get("max_users", old.quota.max_users),
                max_api_calls_per_month=payload.get(
                    "max_api_calls_per_month", old.quota.max_api_calls_per_month
                ),
                max_documents_per_month=payload.get(
                    "max_documents_per_month", old.quota.max_documents_per_month
                ),
            )
            self._plans[plan_id] = PlanDefinition(
                plan_id=old.plan_id,
                name=payload.get("name", old.name),
                tier=old.tier,
                included_engines=engines,
                quota=quota,
                monthly_price=Decimal(str(payload["monthly_price"]))
                if "monthly_price" in payload
                else old.monthly_price,
                currency=old.currency,
                is_active=old.is_active,
                created_at=old.created_at,
                updated_at=payload.get("issued_at"),
            )

        elif event_type == PLAN_DEACTIVATED_V1:
            plan_id = uuid.UUID(str(payload["plan_id"]))
            old = self._plans.get(plan_id)
            if old is None:
                return
            self._plans[plan_id] = PlanDefinition(
                plan_id=old.plan_id,
                name=old.name,
                tier=old.tier,
                included_engines=old.included_engines,
                quota=old.quota,
                monthly_price=old.monthly_price,
                currency=old.currency,
                is_active=False,
                created_at=old.created_at,
                updated_at=payload.get("issued_at"),
            )

    def get_plan(self, plan_id: uuid.UUID) -> Optional[PlanDefinition]:
        return self._plans.get(plan_id)

    def list_plans(self) -> List[PlanDefinition]:
        return list(self._plans.values())

    def list_active_plans(self) -> List[PlanDefinition]:
        return [p for p in self._plans.values() if p.is_active]

    def get_plan_by_tier(self, tier: PlanTier) -> Optional[PlanDefinition]:
        for p in self._plans.values():
            if p.tier == tier and p.is_active:
                return p
        return None

    def truncate(self) -> None:
        self._plans.clear()


# ══════════════════════════════════════════════════════════════
# PLAN MANAGER (orchestrates plan operations)
# ══════════════════════════════════════════════════════════════

class PlanManager:
    """
    Manages subscription plan definitions.

    All mutations produce events — no direct state writes.
    """

    def __init__(self, projection: PlanProjection) -> None:
        self._projection = projection

    def define_plan(self, request: DefinePlanRequest) -> Dict[str, Any]:
        """Define a new subscription plan. Returns event payload."""
        try:
            tier = PlanTier(request.tier)
        except ValueError:
            return {
                "rejected": RejectionReason(
                    code="INVALID_PLAN_TIER",
                    message=f"Invalid tier: {request.tier}. Must be STARTER, PROFESSIONAL, or ENTERPRISE.",
                    policy_name="define_plan",
                ),
            }

        plan_id = uuid.uuid4()
        payload = {
            "plan_id": str(plan_id),
            "name": request.name,
            "tier": tier.value,
            "included_engines": list(request.included_engines),
            "max_branches": request.max_branches,
            "max_users": request.max_users,
            "max_api_calls_per_month": request.max_api_calls_per_month,
            "max_documents_per_month": request.max_documents_per_month,
            "monthly_price": str(request.monthly_price),
            "currency": request.currency,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(PLAN_DEFINED_V1, payload)
        return {
            "plan_id": plan_id,
            "events": [{"event_type": PLAN_DEFINED_V1, "payload": payload}],
        }

    def update_plan(
        self, request: UpdatePlanRequest
    ) -> Optional[RejectionReason]:
        plan = self._projection.get_plan(request.plan_id)
        if plan is None:
            return RejectionReason(
                code="PLAN_NOT_FOUND",
                message="Plan not found.",
                policy_name="update_plan",
            )
        if not plan.is_active:
            return RejectionReason(
                code="PLAN_DEACTIVATED",
                message="Cannot update a deactivated plan.",
                policy_name="update_plan",
            )
        payload: Dict[str, Any] = {
            "plan_id": str(request.plan_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if request.name is not None:
            payload["name"] = request.name
        if request.included_engines is not None:
            payload["included_engines"] = list(request.included_engines)
        if request.max_branches is not None:
            payload["max_branches"] = request.max_branches
        if request.max_users is not None:
            payload["max_users"] = request.max_users
        if request.max_api_calls_per_month is not None:
            payload["max_api_calls_per_month"] = request.max_api_calls_per_month
        if request.max_documents_per_month is not None:
            payload["max_documents_per_month"] = request.max_documents_per_month
        if request.monthly_price is not None:
            payload["monthly_price"] = str(request.monthly_price)
        self._projection.apply(PLAN_UPDATED_V1, payload)
        return None

    def deactivate_plan(
        self, request: DeactivatePlanRequest
    ) -> Optional[RejectionReason]:
        plan = self._projection.get_plan(request.plan_id)
        if plan is None:
            return RejectionReason(
                code="PLAN_NOT_FOUND",
                message="Plan not found.",
                policy_name="deactivate_plan",
            )
        if not plan.is_active:
            return RejectionReason(
                code="PLAN_ALREADY_DEACTIVATED",
                message="Plan is already deactivated.",
                policy_name="deactivate_plan",
            )
        payload = {
            "plan_id": str(request.plan_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(PLAN_DEACTIVATED_V1, payload)
        return None

    def resolve_engines_for_plan(self, plan_id: uuid.UUID) -> FrozenSet[str]:
        """Return the set of engines included in a plan."""
        plan = self._projection.get_plan(plan_id)
        if plan is None or not plan.is_active:
            return frozenset()
        return plan.included_engines

    def check_quota(
        self, plan_id: uuid.UUID, resource: str, current_usage: int
    ) -> Optional[RejectionReason]:
        """Check if usage is within plan quota."""
        plan = self._projection.get_plan(plan_id)
        if plan is None or not plan.is_active:
            return RejectionReason(
                code="NO_ACTIVE_PLAN",
                message="No active plan found.",
                policy_name="check_quota",
            )
        limits = {
            "branches": plan.quota.max_branches,
            "users": plan.quota.max_users,
            "api_calls": plan.quota.max_api_calls_per_month,
            "documents": plan.quota.max_documents_per_month,
        }
        limit = limits.get(resource)
        if limit is None:
            return None  # unknown resource — no limit
        if current_usage >= limit:
            return RejectionReason(
                code="QUOTA_EXCEEDED",
                message=f"Quota exceeded for {resource}: {current_usage}/{limit}.",
                policy_name="check_quota",
            )
        return None
