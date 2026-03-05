"""
BOS Platform — Tenant Lifecycle Manager
=========================================
Full tenant lifecycle state machine:

    ONBOARDING → ACTIVE → SUSPENDED → TERMINATED

Rules:
  - Every state transition is an event (fully auditable).
  - TERMINATED is a terminal state — no re-activation.
  - A SUSPENDED tenant cannot issue commands (enforced at command boundary).
  - Kill switch is an explicit TERMINATED transition with an abuse/legal reason.
  - Data archival is a separate async job triggered by TERMINATED event.
  - REINSTATED: SUSPENDED → ACTIVE only (not from TERMINATED).

State diagram:
  ONBOARDING ──► ACTIVE ──► SUSPENDED ──► ACTIVE   (reinstated)
                       │         │
                       │         └──────► TERMINATED  (kill switch or non-payment)
                       └────────────────► TERMINATED  (direct termination)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# TENANT LIFECYCLE EVENT TYPES
# ══════════════════════════════════════════════════════════════

TENANT_ONBOARDING_STARTED_V1  = "platform.tenant.onboarding.started.v1"
TENANT_ACTIVATED_V1           = "platform.tenant.activated.v1"
TENANT_SUSPENDED_V1           = "platform.tenant.suspended.v1"
TENANT_REINSTATED_V1          = "platform.tenant.reinstated.v1"
TENANT_TERMINATED_V1          = "platform.tenant.terminated.v1"

TENANT_LIFECYCLE_EVENT_TYPES = (
    TENANT_ONBOARDING_STARTED_V1,
    TENANT_ACTIVATED_V1,
    TENANT_SUSPENDED_V1,
    TENANT_REINSTATED_V1,
    TENANT_TERMINATED_V1,
)


# ══════════════════════════════════════════════════════════════
# STATES & TRANSITIONS
# ══════════════════════════════════════════════════════════════

class TenantState(Enum):
    ONBOARDING  = "ONBOARDING"
    ACTIVE      = "ACTIVE"
    SUSPENDED   = "SUSPENDED"
    TERMINATED  = "TERMINATED"   # terminal


class SuspensionReason(Enum):
    NON_PAYMENT          = "NON_PAYMENT"
    ABUSE                = "ABUSE"
    LEGAL_HOLD           = "LEGAL_HOLD"
    VOLUNTARY_PAUSE      = "VOLUNTARY_PAUSE"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"


class TerminationReason(Enum):
    NON_PAYMENT          = "NON_PAYMENT"
    ABUSE                = "ABUSE"
    LEGAL_ORDER          = "LEGAL_ORDER"
    VOLUNTARY_CLOSURE    = "VOLUNTARY_CLOSURE"
    FRAUD                = "FRAUD"
    KILL_SWITCH          = "KILL_SWITCH"


# Valid transitions map
_VALID_TRANSITIONS: Dict[TenantState, List[TenantState]] = {
    TenantState.ONBOARDING:  [TenantState.ACTIVE, TenantState.TERMINATED],
    TenantState.ACTIVE:      [TenantState.SUSPENDED, TenantState.TERMINATED],
    TenantState.SUSPENDED:   [TenantState.ACTIVE, TenantState.TERMINATED],
    TenantState.TERMINATED:  [],    # terminal — no exit
}


def _can_transition(current: TenantState, target: TenantState) -> bool:
    return target in _VALID_TRANSITIONS.get(current, [])


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantRecord:
    """Immutable snapshot of a tenant's lifecycle state."""
    tenant_id: uuid.UUID
    business_name: str
    country_code: str
    region_code: str
    state: TenantState
    onboarding_started_at: Optional[datetime]
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    suspension_reason: Optional[str] = None
    termination_reason: Optional[str] = None
    kill_switch: bool = False        # True if terminated via kill switch
    data_archived: bool = False      # True after archival job runs


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StartOnboardingRequest:
    business_name: str
    country_code: str
    region_code: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ActivateTenantRequest:
    tenant_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SuspendTenantRequest:
    tenant_id: uuid.UUID
    reason: str              # SuspensionReason value
    actor_id: str
    issued_at: datetime
    notes: str = ""


@dataclass(frozen=True)
class ReinstateTenantRequest:
    tenant_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    notes: str = ""


@dataclass(frozen=True)
class TerminateTenantRequest:
    tenant_id: uuid.UUID
    reason: str              # TerminationReason value
    actor_id: str
    issued_at: datetime
    kill_switch: bool = False
    notes: str = ""


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class TenantLifecycleProjection:
    """
    In-memory projection of tenant lifecycle states.
    Rebuilt deterministically from lifecycle events.
    """

    projection_name = "tenant_lifecycle_projection"

    def __init__(self) -> None:
        self._tenants: Dict[uuid.UUID, TenantRecord] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        tenant_id = uuid.UUID(str(payload["tenant_id"]))

        if event_type == TENANT_ONBOARDING_STARTED_V1:
            self._tenants[tenant_id] = TenantRecord(
                tenant_id=tenant_id,
                business_name=payload["business_name"],
                country_code=payload.get("country_code", ""),
                region_code=payload.get("region_code", ""),
                state=TenantState.ONBOARDING,
                onboarding_started_at=payload.get("issued_at"),
            )

        elif event_type == TENANT_ACTIVATED_V1:
            old = self._tenants.get(tenant_id)
            if old is None:
                return
            self._tenants[tenant_id] = TenantRecord(
                tenant_id=old.tenant_id,
                business_name=old.business_name,
                country_code=old.country_code,
                region_code=old.region_code,
                state=TenantState.ACTIVE,
                onboarding_started_at=old.onboarding_started_at,
                activated_at=payload.get("issued_at"),
            )

        elif event_type == TENANT_SUSPENDED_V1:
            old = self._tenants.get(tenant_id)
            if old is None:
                return
            self._tenants[tenant_id] = TenantRecord(
                tenant_id=old.tenant_id,
                business_name=old.business_name,
                country_code=old.country_code,
                region_code=old.region_code,
                state=TenantState.SUSPENDED,
                onboarding_started_at=old.onboarding_started_at,
                activated_at=old.activated_at,
                suspended_at=payload.get("issued_at"),
                suspension_reason=payload.get("reason"),
                terminated_at=old.terminated_at,
                termination_reason=old.termination_reason,
                kill_switch=old.kill_switch,
                data_archived=old.data_archived,
            )

        elif event_type == TENANT_REINSTATED_V1:
            old = self._tenants.get(tenant_id)
            if old is None:
                return
            self._tenants[tenant_id] = TenantRecord(
                tenant_id=old.tenant_id,
                business_name=old.business_name,
                country_code=old.country_code,
                region_code=old.region_code,
                state=TenantState.ACTIVE,
                onboarding_started_at=old.onboarding_started_at,
                activated_at=payload.get("issued_at"),    # re-activation time
                suspension_reason=None,
                kill_switch=False,
                data_archived=old.data_archived,
            )

        elif event_type == TENANT_TERMINATED_V1:
            old = self._tenants.get(tenant_id)
            if old is None:
                return
            self._tenants[tenant_id] = TenantRecord(
                tenant_id=old.tenant_id,
                business_name=old.business_name,
                country_code=old.country_code,
                region_code=old.region_code,
                state=TenantState.TERMINATED,
                onboarding_started_at=old.onboarding_started_at,
                activated_at=old.activated_at,
                suspended_at=old.suspended_at,
                terminated_at=payload.get("issued_at"),
                termination_reason=payload.get("reason"),
                kill_switch=bool(payload.get("kill_switch", False)),
                data_archived=False,
            )

    def get_tenant(self, tenant_id: uuid.UUID) -> Optional[TenantRecord]:
        return self._tenants.get(tenant_id)

    def is_active(self, tenant_id: uuid.UUID) -> bool:
        t = self._tenants.get(tenant_id)
        return t is not None and t.state == TenantState.ACTIVE

    def is_blocked(self, tenant_id: uuid.UUID) -> bool:
        """True if tenant CANNOT issue commands (suspended or terminated)."""
        t = self._tenants.get(tenant_id)
        if t is None:
            return True
        return t.state in (TenantState.SUSPENDED, TenantState.TERMINATED)

    def list_by_state(self, state: TenantState) -> List[TenantRecord]:
        return [t for t in self._tenants.values() if t.state == state]

    def list_all(self) -> List[TenantRecord]:
        return list(self._tenants.values())

    def truncate(self) -> None:
        self._tenants.clear()


# ══════════════════════════════════════════════════════════════
# TENANT LIFECYCLE MANAGER
# ══════════════════════════════════════════════════════════════

class TenantLifecycleManager:
    """
    Manages the full lifecycle of a tenant from ONBOARDING to TERMINATED.

    All state changes produce events — no direct state writes.
    The kill switch immediately transitions a tenant to TERMINATED and
    blocks all subsequent commands at the policy layer.
    """

    def __init__(self, projection: TenantLifecycleProjection) -> None:
        self._projection = projection

    # ── onboarding ───────────────────────────────────────────

    def start_onboarding(
        self, request: StartOnboardingRequest
    ) -> Dict[str, Any]:
        """Register a new tenant entering the onboarding pipeline."""
        tenant_id = uuid.uuid4()
        payload: Dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "business_name": request.business_name,
            "country_code": request.country_code,
            "region_code": request.region_code,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(TENANT_ONBOARDING_STARTED_V1, payload)
        return {
            "tenant_id": tenant_id,
            "events": [{"event_type": TENANT_ONBOARDING_STARTED_V1, "payload": payload}],
        }

    # ── activation ───────────────────────────────────────────

    def activate(
        self, request: ActivateTenantRequest
    ) -> Optional[RejectionReason]:
        """Transition tenant from ONBOARDING → ACTIVE."""
        tenant = self._projection.get_tenant(request.tenant_id)
        if tenant is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Tenant not found.",
                policy_name="activate_tenant",
            )
        if not _can_transition(tenant.state, TenantState.ACTIVE):
            return RejectionReason(
                code="INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot activate tenant in state {tenant.state.value}.",
                policy_name="activate_tenant",
            )
        self._projection.apply(TENANT_ACTIVATED_V1, {
            "tenant_id": str(request.tenant_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    # ── suspension ───────────────────────────────────────────

    def suspend(
        self, request: SuspendTenantRequest
    ) -> Optional[RejectionReason]:
        """Suspend a tenant — blocks all commands until reinstated."""
        tenant = self._projection.get_tenant(request.tenant_id)
        if tenant is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Tenant not found.",
                policy_name="suspend_tenant",
            )
        if not _can_transition(tenant.state, TenantState.SUSPENDED):
            return RejectionReason(
                code="INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot suspend tenant in state {tenant.state.value}.",
                policy_name="suspend_tenant",
            )
        try:
            SuspensionReason(request.reason)
        except ValueError:
            return RejectionReason(
                code="INVALID_SUSPENSION_REASON",
                message=f"Unknown suspension reason: {request.reason}.",
                policy_name="suspend_tenant",
            )
        self._projection.apply(TENANT_SUSPENDED_V1, {
            "tenant_id": str(request.tenant_id),
            "reason": request.reason,
            "notes": request.notes,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    # ── reinstatement ────────────────────────────────────────

    def reinstate(
        self, request: ReinstateTenantRequest
    ) -> Optional[RejectionReason]:
        """Reinstate a SUSPENDED tenant back to ACTIVE."""
        tenant = self._projection.get_tenant(request.tenant_id)
        if tenant is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Tenant not found.",
                policy_name="reinstate_tenant",
            )
        if tenant.state != TenantState.SUSPENDED:
            return RejectionReason(
                code="TENANT_NOT_SUSPENDED",
                message=f"Tenant is {tenant.state.value} — can only reinstate SUSPENDED tenants.",
                policy_name="reinstate_tenant",
            )
        self._projection.apply(TENANT_REINSTATED_V1, {
            "tenant_id": str(request.tenant_id),
            "notes": request.notes,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    # ── termination / kill switch ────────────────────────────

    def terminate(
        self, request: TerminateTenantRequest
    ) -> Optional[RejectionReason]:
        """
        Terminate a tenant (ACTIVE or SUSPENDED → TERMINATED).

        If request.kill_switch=True, the tenant is immediately blocked.
        TERMINATED is a terminal state — no re-activation is possible.
        """
        tenant = self._projection.get_tenant(request.tenant_id)
        if tenant is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Tenant not found.",
                policy_name="terminate_tenant",
            )
        if not _can_transition(tenant.state, TenantState.TERMINATED):
            return RejectionReason(
                code="INVALID_LIFECYCLE_TRANSITION",
                message=f"Cannot terminate tenant in state {tenant.state.value}.",
                policy_name="terminate_tenant",
            )
        try:
            TerminationReason(request.reason)
        except ValueError:
            return RejectionReason(
                code="INVALID_TERMINATION_REASON",
                message=f"Unknown termination reason: {request.reason}.",
                policy_name="terminate_tenant",
            )
        self._projection.apply(TENANT_TERMINATED_V1, {
            "tenant_id": str(request.tenant_id),
            "reason": request.reason,
            "kill_switch": request.kill_switch,
            "notes": request.notes,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    # ── command gate ─────────────────────────────────────────

    def assert_tenant_can_issue_commands(
        self, tenant_id: uuid.UUID
    ) -> Optional[RejectionReason]:
        """
        Returns RejectionReason if tenant is not allowed to issue commands.
        Called at the command boundary before any business command is processed.
        """
        tenant = self._projection.get_tenant(tenant_id)
        if tenant is None:
            return RejectionReason(
                code="TENANT_NOT_FOUND",
                message="Tenant not found in platform registry.",
                policy_name="tenant_command_gate",
            )
        if tenant.state == TenantState.ONBOARDING:
            return RejectionReason(
                code="TENANT_ONBOARDING",
                message="Tenant is still in onboarding. Complete setup first.",
                policy_name="tenant_command_gate",
            )
        if tenant.state == TenantState.SUSPENDED:
            return RejectionReason(
                code="TENANT_SUSPENDED",
                message=f"Tenant is suspended ({tenant.suspension_reason}). "
                        "Contact platform support.",
                policy_name="tenant_command_gate",
            )
        if tenant.state == TenantState.TERMINATED:
            return RejectionReason(
                code="TENANT_TERMINATED",
                message="Tenant account is terminated. No operations permitted.",
                policy_name="tenant_command_gate",
            )
        return None
