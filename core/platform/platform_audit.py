"""
BOS Platform — Platform Audit Store
======================================
A dedicated event log for platform-level operations.

SEPARATE from tenant event stores. Tenant events record business facts.
Platform audit events record infrastructure facts:
  - Tenant lifecycle changes (onboarded, suspended, terminated)
  - Plan assignments and upgrades
  - Region pack applications
  - Feature flag toggles
  - Kill switch activations
  - Schema migrations applied
  - Service-to-service key rotations

This is the "truth of the platform" — immutable, append-only.
Every entry includes: actor_id, issued_at, correlation_id.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# PLATFORM AUDIT EVENT TYPES
# ══════════════════════════════════════════════════════════════

PLATFORM_TENANT_ONBOARDED_V1      = "platform.audit.tenant.onboarded.v1"
PLATFORM_TENANT_ACTIVATED_V1      = "platform.audit.tenant.activated.v1"
PLATFORM_TENANT_SUSPENDED_V1      = "platform.audit.tenant.suspended.v1"
PLATFORM_TENANT_REINSTATED_V1     = "platform.audit.tenant.reinstated.v1"
PLATFORM_TENANT_TERMINATED_V1     = "platform.audit.tenant.terminated.v1"
PLATFORM_PLAN_ASSIGNED_V1         = "platform.audit.plan.assigned.v1"
PLATFORM_PLAN_UPGRADED_V1         = "platform.audit.plan.upgraded.v1"
PLATFORM_REGION_PACK_APPLIED_V1   = "platform.audit.region_pack.applied.v1"
PLATFORM_FLAG_TOGGLED_V1          = "platform.audit.flag.toggled.v1"
PLATFORM_KILL_SWITCH_ACTIVATED_V1 = "platform.audit.kill_switch.activated.v1"
PLATFORM_SCHEMA_MIGRATED_V1       = "platform.audit.schema.migrated.v1"
PLATFORM_KEY_ROTATED_V1           = "platform.audit.key.rotated.v1"
PLATFORM_ROLLOUT_STARTED_V1       = "platform.audit.rollout.started.v1"
PLATFORM_ROLLOUT_COMPLETED_V1     = "platform.audit.rollout.completed.v1"
PLATFORM_COMPLIANCE_PACK_VERSIONED_V1 = "platform.audit.compliance_pack.versioned.v1"

PLATFORM_AUDIT_EVENT_TYPES = (
    PLATFORM_TENANT_ONBOARDED_V1,
    PLATFORM_TENANT_ACTIVATED_V1,
    PLATFORM_TENANT_SUSPENDED_V1,
    PLATFORM_TENANT_REINSTATED_V1,
    PLATFORM_TENANT_TERMINATED_V1,
    PLATFORM_PLAN_ASSIGNED_V1,
    PLATFORM_PLAN_UPGRADED_V1,
    PLATFORM_REGION_PACK_APPLIED_V1,
    PLATFORM_FLAG_TOGGLED_V1,
    PLATFORM_KILL_SWITCH_ACTIVATED_V1,
    PLATFORM_SCHEMA_MIGRATED_V1,
    PLATFORM_KEY_ROTATED_V1,
    PLATFORM_ROLLOUT_STARTED_V1,
    PLATFORM_ROLLOUT_COMPLETED_V1,
    PLATFORM_COMPLIANCE_PACK_VERSIONED_V1,
)


# ══════════════════════════════════════════════════════════════
# AUDIT ENTRY MODEL (immutable)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PlatformAuditEntry:
    """One immutable platform audit log entry."""
    entry_id: uuid.UUID
    event_type: str
    actor_id: str              # platform admin or "SYSTEM"
    actor_type: str            # "PLATFORM_ADMIN" | "SYSTEM" | "AUTOMATION"
    issued_at: datetime
    subject_type: str          # "TENANT" | "PLAN" | "REGION_PACK" | "FLAG" | etc.
    subject_id: str            # UUID or identifier of the affected entity
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None   # links related audit entries
    region_code: Optional[str] = None
    notes: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RecordAuditEntryRequest:
    event_type: str
    actor_id: str
    actor_type: str
    issued_at: datetime
    subject_type: str
    subject_id: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    region_code: Optional[str] = None
    notes: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class PlatformAuditProjection:
    """
    In-memory platform audit log.

    Rebuilt deterministically from platform audit events.
    In production this would be backed by an append-only DB table.
    """

    projection_name = "platform_audit_projection"

    def __init__(self) -> None:
        self._entries: List[PlatformAuditEntry] = []
        # subject_id → [entry_id, ...]  — for fast per-entity lookups
        self._by_subject: Dict[str, List[uuid.UUID]] = {}
        # actor_id → [entry_id, ...]
        self._by_actor: Dict[str, List[uuid.UUID]] = {}
        # entry_id → index in _entries
        self._index: Dict[uuid.UUID, int] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        entry_id = uuid.UUID(str(payload["entry_id"]))
        issued_at = payload.get("issued_at", datetime.utcnow())
        entry = PlatformAuditEntry(
            entry_id=entry_id,
            event_type=payload["event_type"],
            actor_id=payload["actor_id"],
            actor_type=payload.get("actor_type", "SYSTEM"),
            issued_at=issued_at,
            subject_type=payload["subject_type"],
            subject_id=payload["subject_id"],
            payload=payload.get("payload", {}),
            correlation_id=payload.get("correlation_id"),
            region_code=payload.get("region_code"),
            notes=payload.get("notes"),
        )
        idx = len(self._entries)
        self._entries.append(entry)
        self._index[entry_id] = idx

        subj = entry.subject_id
        self._by_subject.setdefault(subj, []).append(entry_id)
        self._by_actor.setdefault(entry.actor_id, []).append(entry_id)

    def get_entry(self, entry_id: uuid.UUID) -> Optional[PlatformAuditEntry]:
        idx = self._index.get(entry_id)
        return self._entries[idx] if idx is not None else None

    def get_by_subject(self, subject_id: str) -> List[PlatformAuditEntry]:
        ids = self._by_subject.get(subject_id, [])
        return [self._entries[self._index[i]] for i in ids if i in self._index]

    def get_by_actor(self, actor_id: str) -> List[PlatformAuditEntry]:
        ids = self._by_actor.get(actor_id, [])
        return [self._entries[self._index[i]] for i in ids if i in self._index]

    def get_by_event_type(self, event_type: str) -> List[PlatformAuditEntry]:
        return [e for e in self._entries if e.event_type == event_type]

    def get_recent(self, limit: int = 50) -> List[PlatformAuditEntry]:
        return self._entries[-limit:]

    def truncate(self) -> None:
        self._entries.clear()
        self._by_subject.clear()
        self._by_actor.clear()
        self._index.clear()


# ══════════════════════════════════════════════════════════════
# PLATFORM AUDIT SERVICE
# ══════════════════════════════════════════════════════════════

class PlatformAuditService:
    """
    Records platform-level audit events.

    Every platform operation (tenant lifecycle, plan assignment,
    kill switch, flag toggle, schema migration) must call this service
    to produce a durable audit trail.

    All entries are append-only — never deleted, never patched.
    """

    def __init__(self, projection: PlatformAuditProjection) -> None:
        self._projection = projection

    def record(self, request: RecordAuditEntryRequest) -> Dict[str, Any]:
        """Record a platform audit entry. Returns the generated entry_id."""
        entry_id = uuid.uuid4()
        payload: Dict[str, Any] = {
            "entry_id": str(entry_id),
            "event_type": request.event_type,
            "actor_id": request.actor_id,
            "actor_type": request.actor_type,
            "issued_at": request.issued_at,
            "subject_type": request.subject_type,
            "subject_id": request.subject_id,
            "payload": request.payload,
        }
        if request.correlation_id:
            payload["correlation_id"] = request.correlation_id
        if request.region_code:
            payload["region_code"] = request.region_code
        if request.notes:
            payload["notes"] = request.notes

        self._projection.apply(request.event_type, payload)
        return {
            "entry_id": entry_id,
            "events": [{"event_type": request.event_type, "payload": payload}],
        }

    # ── convenience factory methods ──────────────────────────

    def record_tenant_onboarded(
        self, tenant_id: str, business_name: str, region_code: str,
        actor_id: str, issued_at: datetime,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_TENANT_ONBOARDED_V1,
            actor_id=actor_id,
            actor_type="PLATFORM_ADMIN",
            issued_at=issued_at,
            subject_type="TENANT",
            subject_id=tenant_id,
            payload={"business_name": business_name, "region_code": region_code},
            correlation_id=correlation_id,
            region_code=region_code,
        ))

    def record_tenant_suspended(
        self, tenant_id: str, reason: str,
        actor_id: str, issued_at: datetime,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_TENANT_SUSPENDED_V1,
            actor_id=actor_id,
            actor_type="PLATFORM_ADMIN",
            issued_at=issued_at,
            subject_type="TENANT",
            subject_id=tenant_id,
            payload={"reason": reason},
        ))

    def record_tenant_terminated(
        self, tenant_id: str, reason: str,
        actor_id: str, issued_at: datetime,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_TENANT_TERMINATED_V1,
            actor_id=actor_id,
            actor_type="PLATFORM_ADMIN",
            issued_at=issued_at,
            subject_type="TENANT",
            subject_id=tenant_id,
            payload={"reason": reason},
            notes="KILL SWITCH — tenant data archived, access blocked.",
        ))

    def record_kill_switch(
        self, tenant_id: str, reason: str,
        actor_id: str, issued_at: datetime,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_KILL_SWITCH_ACTIVATED_V1,
            actor_id=actor_id,
            actor_type="PLATFORM_ADMIN",
            issued_at=issued_at,
            subject_type="TENANT",
            subject_id=tenant_id,
            payload={"reason": reason},
            notes=f"Kill switch by {actor_id} at {issued_at.isoformat()}.",
        ))

    def record_flag_toggled(
        self, flag_name: str, enabled: bool, scope: str, scope_id: str,
        actor_id: str, issued_at: datetime,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_FLAG_TOGGLED_V1,
            actor_id=actor_id,
            actor_type="PLATFORM_ADMIN",
            issued_at=issued_at,
            subject_type="FLAG",
            subject_id=flag_name,
            payload={"enabled": enabled, "scope": scope, "scope_id": scope_id},
        ))

    def record_region_pack_applied(
        self, business_id: str, region_code: str, pack_version: int,
        actor_id: str, issued_at: datetime,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_REGION_PACK_APPLIED_V1,
            actor_id=actor_id,
            actor_type="PLATFORM_ADMIN",
            issued_at=issued_at,
            subject_type="TENANT",
            subject_id=business_id,
            payload={
                "region_code": region_code,
                "pack_version": pack_version,
            },
            region_code=region_code,
        ))

    def record_schema_migrated(
        self, migration_id: str, version_from: str, version_to: str,
        actor_id: str, issued_at: datetime,
        region_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.record(RecordAuditEntryRequest(
            event_type=PLATFORM_SCHEMA_MIGRATED_V1,
            actor_id=actor_id,
            actor_type="SYSTEM",
            issued_at=issued_at,
            subject_type="SCHEMA",
            subject_id=migration_id,
            payload={"version_from": version_from, "version_to": version_to},
            region_code=region_code,
        ))

    # ── query helpers ────────────────────────────────────────

    def get_tenant_history(self, tenant_id: str) -> List[PlatformAuditEntry]:
        return self._projection.get_by_subject(tenant_id)

    def get_recent_platform_events(self, limit: int = 50) -> List[PlatformAuditEntry]:
        return self._projection.get_recent(limit)
