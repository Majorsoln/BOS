"""
BOS Platform — Rollout / Delivery Plane
=========================================
Staged canary rollout of features and configuration changes.

Rollout design principles:
  - Additive-only: features are enabled progressively. Rollbacks produce
    a new "disable" rollout — never patch an existing one.
  - Targeting: by region_code | plan_tier | tenant_cohort | percentage
  - Versioned: every rollout is a versioned config; tenants stay on their
    pinned version until they opt in to a new one.
  - Audit trail: every rollout state change is an event.

Rollout lifecycle:
  DRAFT → ACTIVE → PAUSED → COMPLETED | ROLLED_BACK

Targeting resolution order (most specific wins):
  1. Tenant-level override (explicit allow/block list)
  2. Region targeting
  3. Plan tier targeting
  4. Cohort (named group)
  5. Percentage rollout (hash-based, deterministic)
  6. Global default
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# ROLLOUT EVENT TYPES
# ══════════════════════════════════════════════════════════════

ROLLOUT_DEFINED_V1       = "platform.rollout.defined.v1"
ROLLOUT_ACTIVATED_V1     = "platform.rollout.activated.v1"
ROLLOUT_PAUSED_V1        = "platform.rollout.paused.v1"
ROLLOUT_RESUMED_V1       = "platform.rollout.resumed.v1"
ROLLOUT_COMPLETED_V1     = "platform.rollout.completed.v1"
ROLLOUT_ROLLED_BACK_V1   = "platform.rollout.rolled_back.v1"
ROLLOUT_TARGET_ADDED_V1  = "platform.rollout.target_added.v1"

ROLLOUT_EVENT_TYPES = (
    ROLLOUT_DEFINED_V1,
    ROLLOUT_ACTIVATED_V1,
    ROLLOUT_PAUSED_V1,
    ROLLOUT_RESUMED_V1,
    ROLLOUT_COMPLETED_V1,
    ROLLOUT_ROLLED_BACK_V1,
    ROLLOUT_TARGET_ADDED_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class RolloutStatus(Enum):
    DRAFT       = "DRAFT"
    ACTIVE      = "ACTIVE"
    PAUSED      = "PAUSED"
    COMPLETED   = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"


class RolloutTargetKind(Enum):
    GLOBAL      = "GLOBAL"        # all tenants
    REGION      = "REGION"        # tenants in specific region(s)
    PLAN_TIER   = "PLAN_TIER"     # tenants on specific plan tier(s)
    COHORT      = "COHORT"        # named cohort (beta testers, early adopters)
    PERCENTAGE  = "PERCENTAGE"    # hash-based percentage (0–100)
    TENANT_LIST = "TENANT_LIST"   # explicit list of tenant IDs


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RolloutTarget:
    """Defines who receives this rollout."""
    kind: RolloutTargetKind
    regions: FrozenSet[str] = frozenset()
    plan_tiers: FrozenSet[str] = frozenset()
    cohort_name: Optional[str] = None
    percentage: int = 100            # 0–100 for PERCENTAGE kind
    tenant_ids: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class ConfigVersion:
    """A versioned configuration snapshot attached to a rollout."""
    version: int
    config_key: str
    config_value: Any
    schema_version: int = 1


@dataclass(frozen=True)
class RolloutDefinition:
    """Immutable rollout definition."""
    rollout_id: uuid.UUID
    name: str
    feature_flag: str               # e.g. "FLAG_ENABLE_DOCUMENT_ENGINE"
    status: RolloutStatus
    target: RolloutTarget
    config_version: Optional[ConfigVersion]
    created_at: Optional[datetime]
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rollback_reason: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DefineRolloutRequest:
    name: str
    feature_flag: str
    target_kind: str               # RolloutTargetKind value
    actor_id: str
    issued_at: datetime
    regions: tuple = ()
    plan_tiers: tuple = ()
    cohort_name: Optional[str] = None
    percentage: int = 100
    tenant_ids: tuple = ()
    config_key: Optional[str] = None
    config_value: Any = None
    config_schema_version: int = 1


@dataclass(frozen=True)
class ActivateRolloutRequest:
    rollout_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class PauseRolloutRequest:
    rollout_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class CompleteRolloutRequest:
    rollout_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class RollbackRolloutRequest:
    rollout_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# TARGETING ENGINE
# ══════════════════════════════════════════════════════════════

def _hash_tenant_for_percentage(
    tenant_id: str, rollout_id: str
) -> int:
    """
    Deterministic hash → 0–99.
    Same tenant always gets the same bucket for a given rollout.
    """
    raw = f"{rollout_id}:{tenant_id}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) % 100


def evaluate_rollout_for_tenant(
    rollout: RolloutDefinition,
    tenant_id: str,
    tenant_region: Optional[str] = None,
    tenant_plan_tier: Optional[str] = None,
    tenant_cohorts: Optional[Set[str]] = None,
) -> bool:
    """
    Returns True if the given tenant is included in this rollout.
    Rollout must be ACTIVE, else always False.
    """
    if rollout.status != RolloutStatus.ACTIVE:
        return False

    target = rollout.target
    kind = target.kind

    if kind == RolloutTargetKind.GLOBAL:
        return True

    if kind == RolloutTargetKind.TENANT_LIST:
        return tenant_id in target.tenant_ids

    if kind == RolloutTargetKind.REGION:
        return bool(tenant_region and tenant_region in target.regions)

    if kind == RolloutTargetKind.PLAN_TIER:
        return bool(tenant_plan_tier and tenant_plan_tier in target.plan_tiers)

    if kind == RolloutTargetKind.COHORT:
        cohorts = tenant_cohorts or set()
        return target.cohort_name in cohorts if target.cohort_name else False

    if kind == RolloutTargetKind.PERCENTAGE:
        bucket = _hash_tenant_for_percentage(tenant_id, str(rollout.rollout_id))
        return bucket < target.percentage

    return False


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class RolloutProjection:
    """
    In-memory projection of rollout definitions and their states.
    Rebuilt deterministically from rollout events.
    """

    projection_name = "rollout_projection"

    def __init__(self) -> None:
        self._rollouts: Dict[uuid.UUID, RolloutDefinition] = {}
        # feature_flag → list of rollout_ids (all versions, newest last)
        self._by_flag: Dict[str, List[uuid.UUID]] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        rollout_id = uuid.UUID(str(payload["rollout_id"]))

        if event_type == ROLLOUT_DEFINED_V1:
            target_kind = RolloutTargetKind(payload["target_kind"])
            config_data = payload.get("config_version")
            config_version = (
                ConfigVersion(
                    version=config_data["version"],
                    config_key=config_data["config_key"],
                    config_value=config_data["config_value"],
                    schema_version=config_data.get("schema_version", 1),
                )
                if config_data else None
            )
            target = RolloutTarget(
                kind=target_kind,
                regions=frozenset(payload.get("regions", [])),
                plan_tiers=frozenset(payload.get("plan_tiers", [])),
                cohort_name=payload.get("cohort_name"),
                percentage=payload.get("percentage", 100),
                tenant_ids=frozenset(payload.get("tenant_ids", [])),
            )
            rollout = RolloutDefinition(
                rollout_id=rollout_id,
                name=payload["name"],
                feature_flag=payload["feature_flag"],
                status=RolloutStatus.DRAFT,
                target=target,
                config_version=config_version,
                created_at=payload.get("issued_at"),
            )
            self._rollouts[rollout_id] = rollout
            flag = payload["feature_flag"]
            self._by_flag.setdefault(flag, []).append(rollout_id)

        elif event_type == ROLLOUT_ACTIVATED_V1:
            old = self._rollouts.get(rollout_id)
            if old:
                self._rollouts[rollout_id] = RolloutDefinition(
                    rollout_id=old.rollout_id,
                    name=old.name,
                    feature_flag=old.feature_flag,
                    status=RolloutStatus.ACTIVE,
                    target=old.target,
                    config_version=old.config_version,
                    created_at=old.created_at,
                    activated_at=payload.get("issued_at"),
                )

        elif event_type in (ROLLOUT_PAUSED_V1, ROLLOUT_RESUMED_V1):
            old = self._rollouts.get(rollout_id)
            if old:
                new_status = (
                    RolloutStatus.PAUSED
                    if event_type == ROLLOUT_PAUSED_V1
                    else RolloutStatus.ACTIVE
                )
                self._rollouts[rollout_id] = RolloutDefinition(
                    rollout_id=old.rollout_id,
                    name=old.name,
                    feature_flag=old.feature_flag,
                    status=new_status,
                    target=old.target,
                    config_version=old.config_version,
                    created_at=old.created_at,
                    activated_at=old.activated_at,
                )

        elif event_type == ROLLOUT_COMPLETED_V1:
            old = self._rollouts.get(rollout_id)
            if old:
                self._rollouts[rollout_id] = RolloutDefinition(
                    rollout_id=old.rollout_id,
                    name=old.name,
                    feature_flag=old.feature_flag,
                    status=RolloutStatus.COMPLETED,
                    target=old.target,
                    config_version=old.config_version,
                    created_at=old.created_at,
                    activated_at=old.activated_at,
                    completed_at=payload.get("issued_at"),
                )

        elif event_type == ROLLOUT_ROLLED_BACK_V1:
            old = self._rollouts.get(rollout_id)
            if old:
                self._rollouts[rollout_id] = RolloutDefinition(
                    rollout_id=old.rollout_id,
                    name=old.name,
                    feature_flag=old.feature_flag,
                    status=RolloutStatus.ROLLED_BACK,
                    target=old.target,
                    config_version=old.config_version,
                    created_at=old.created_at,
                    activated_at=old.activated_at,
                    rollback_reason=payload.get("reason"),
                )

    def get_rollout(self, rollout_id: uuid.UUID) -> Optional[RolloutDefinition]:
        return self._rollouts.get(rollout_id)

    def get_active_rollout_for_flag(
        self, feature_flag: str
    ) -> Optional[RolloutDefinition]:
        """Return the most recent ACTIVE rollout for a feature flag."""
        ids = self._by_flag.get(feature_flag, [])
        for rid in reversed(ids):
            r = self._rollouts.get(rid)
            if r and r.status == RolloutStatus.ACTIVE:
                return r
        return None

    def list_active_rollouts(self) -> List[RolloutDefinition]:
        return [r for r in self._rollouts.values() if r.status == RolloutStatus.ACTIVE]

    def truncate(self) -> None:
        self._rollouts.clear()
        self._by_flag.clear()


# ══════════════════════════════════════════════════════════════
# ROLLOUT SERVICE
# ══════════════════════════════════════════════════════════════

class RolloutService:
    """
    Manages feature flag rollouts with canary targeting.

    All mutations produce events. Rollbacks create a new ROLLED_BACK
    event — the history is never erased (additive-only).
    """

    def __init__(self, projection: RolloutProjection) -> None:
        self._projection = projection

    def define_rollout(
        self, request: DefineRolloutRequest
    ) -> Dict[str, Any]:
        """Define a new rollout in DRAFT state."""
        try:
            RolloutTargetKind(request.target_kind)
        except ValueError:
            return {
                "rejected": RejectionReason(
                    code="INVALID_TARGET_KIND",
                    message=f"Unknown target kind: {request.target_kind}.",
                    policy_name="define_rollout",
                ),
            }

        rollout_id = uuid.uuid4()
        payload: Dict[str, Any] = {
            "rollout_id": str(rollout_id),
            "name": request.name,
            "feature_flag": request.feature_flag,
            "target_kind": request.target_kind,
            "percentage": request.percentage,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if request.regions:
            payload["regions"] = list(request.regions)
        if request.plan_tiers:
            payload["plan_tiers"] = list(request.plan_tiers)
        if request.cohort_name:
            payload["cohort_name"] = request.cohort_name
        if request.tenant_ids:
            payload["tenant_ids"] = list(request.tenant_ids)
        if request.config_key is not None:
            payload["config_version"] = {
                "version": 1,
                "config_key": request.config_key,
                "config_value": request.config_value,
                "schema_version": request.config_schema_version,
            }

        self._projection.apply(ROLLOUT_DEFINED_V1, payload)
        return {
            "rollout_id": rollout_id,
            "events": [{"event_type": ROLLOUT_DEFINED_V1, "payload": payload}],
        }

    def activate(
        self, request: ActivateRolloutRequest
    ) -> Optional[RejectionReason]:
        rollout = self._projection.get_rollout(request.rollout_id)
        if rollout is None:
            return RejectionReason(
                code="ROLLOUT_NOT_FOUND",
                message="Rollout not found.",
                policy_name="activate_rollout",
            )
        if rollout.status != RolloutStatus.DRAFT:
            return RejectionReason(
                code="ROLLOUT_NOT_IN_DRAFT",
                message=f"Can only activate DRAFT rollouts. Current: {rollout.status.value}.",
                policy_name="activate_rollout",
            )
        self._projection.apply(ROLLOUT_ACTIVATED_V1, {
            "rollout_id": str(request.rollout_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def pause(
        self, request: PauseRolloutRequest
    ) -> Optional[RejectionReason]:
        rollout = self._projection.get_rollout(request.rollout_id)
        if rollout is None:
            return RejectionReason(
                code="ROLLOUT_NOT_FOUND",
                message="Rollout not found.",
                policy_name="pause_rollout",
            )
        if rollout.status != RolloutStatus.ACTIVE:
            return RejectionReason(
                code="ROLLOUT_NOT_ACTIVE",
                message="Only ACTIVE rollouts can be paused.",
                policy_name="pause_rollout",
            )
        self._projection.apply(ROLLOUT_PAUSED_V1, {
            "rollout_id": str(request.rollout_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def complete(
        self, request: CompleteRolloutRequest
    ) -> Optional[RejectionReason]:
        rollout = self._projection.get_rollout(request.rollout_id)
        if rollout is None:
            return RejectionReason(
                code="ROLLOUT_NOT_FOUND",
                message="Rollout not found.",
                policy_name="complete_rollout",
            )
        if rollout.status not in (RolloutStatus.ACTIVE, RolloutStatus.PAUSED):
            return RejectionReason(
                code="ROLLOUT_CANNOT_COMPLETE",
                message=f"Cannot complete rollout in status {rollout.status.value}.",
                policy_name="complete_rollout",
            )
        self._projection.apply(ROLLOUT_COMPLETED_V1, {
            "rollout_id": str(request.rollout_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def rollback(
        self, request: RollbackRolloutRequest
    ) -> Optional[RejectionReason]:
        """Roll back an ACTIVE or PAUSED rollout (additive — creates ROLLED_BACK event)."""
        rollout = self._projection.get_rollout(request.rollout_id)
        if rollout is None:
            return RejectionReason(
                code="ROLLOUT_NOT_FOUND",
                message="Rollout not found.",
                policy_name="rollback_rollout",
            )
        if rollout.status not in (RolloutStatus.ACTIVE, RolloutStatus.PAUSED):
            return RejectionReason(
                code="ROLLOUT_CANNOT_ROLLBACK",
                message=f"Cannot roll back rollout in status {rollout.status.value}.",
                policy_name="rollback_rollout",
            )
        self._projection.apply(ROLLOUT_ROLLED_BACK_V1, {
            "rollout_id": str(request.rollout_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def is_feature_enabled_for_tenant(
        self,
        feature_flag: str,
        tenant_id: str,
        tenant_region: Optional[str] = None,
        tenant_plan_tier: Optional[str] = None,
        tenant_cohorts: Optional[Set[str]] = None,
    ) -> bool:
        """
        Resolve whether a feature flag is enabled for a specific tenant.
        Returns True only if an ACTIVE rollout covers this tenant.
        """
        rollout = self._projection.get_active_rollout_for_flag(feature_flag)
        if rollout is None:
            return False
        return evaluate_rollout_for_tenant(
            rollout=rollout,
            tenant_id=tenant_id,
            tenant_region=tenant_region,
            tenant_plan_tier=tenant_plan_tier,
            tenant_cohorts=tenant_cohorts,
        )
