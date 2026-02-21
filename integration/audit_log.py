"""
BOS Integration — Audit Log
===============================
Immutable audit trail for all external system interactions.
Append-only: no updates, no deletes.

Every inbound and outbound interaction is logged with
full context for compliance and forensic review.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from integration.adapters import Direction


# ══════════════════════════════════════════════════════════════
# AUDIT ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IntegrationAuditEntry:
    """
    Immutable record of an integration interaction.

    Never mutated after creation. Append-only log.
    """

    audit_id: uuid.UUID
    business_id: uuid.UUID
    external_system_id: str
    direction: Direction
    event_type: str
    actor_id: str
    payload_hash: str
    status: str  # SUCCESS | FAILED | RETRIED
    occurred_at: datetime
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    external_event_id: Optional[str] = None
    confirmed_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "audit_id": str(self.audit_id),
            "business_id": str(self.business_id),
            "external_system_id": self.external_system_id,
            "direction": self.direction.value,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "payload_hash": self.payload_hash,
            "status": self.status,
            "occurred_at": self.occurred_at.isoformat(),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "external_event_id": self.external_event_id,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }


# ══════════════════════════════════════════════════════════════
# AUDIT LOG (append-only store)
# ══════════════════════════════════════════════════════════════

class IntegrationAuditLog:
    """
    Append-only audit log for integration events.

    In-memory implementation for core layer.
    Production may persist to database via adapter.
    """

    def __init__(self) -> None:
        self._entries: List[IntegrationAuditEntry] = []

    def append(self, entry: IntegrationAuditEntry) -> None:
        """Append an entry. Immutable once appended."""
        self._entries.append(entry)

    def record_success(
        self,
        *,
        business_id: uuid.UUID,
        external_system_id: str,
        direction: Direction,
        event_type: str,
        actor_id: str,
        payload_hash: str,
        occurred_at: datetime,
        external_event_id: Optional[str] = None,
        confirmed_at: Optional[datetime] = None,
    ) -> IntegrationAuditEntry:
        entry = IntegrationAuditEntry(
            audit_id=uuid.uuid4(),
            business_id=business_id,
            external_system_id=external_system_id,
            direction=direction,
            event_type=event_type,
            actor_id=actor_id,
            payload_hash=payload_hash,
            status="SUCCESS",
            occurred_at=occurred_at,
            external_event_id=external_event_id,
            confirmed_at=confirmed_at,
        )
        self._entries.append(entry)
        return entry

    def record_failure(
        self,
        *,
        business_id: uuid.UUID,
        external_system_id: str,
        direction: Direction,
        event_type: str,
        actor_id: str,
        payload_hash: str,
        occurred_at: datetime,
        error_code: str,
        error_message: str,
        retry_count: int = 0,
        external_event_id: Optional[str] = None,
    ) -> IntegrationAuditEntry:
        entry = IntegrationAuditEntry(
            audit_id=uuid.uuid4(),
            business_id=business_id,
            external_system_id=external_system_id,
            direction=direction,
            event_type=event_type,
            actor_id=actor_id,
            payload_hash=payload_hash,
            status="FAILED",
            occurred_at=occurred_at,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
            external_event_id=external_event_id,
        )
        self._entries.append(entry)
        return entry

    def query_by_business(self, business_id: uuid.UUID) -> List[IntegrationAuditEntry]:
        """Query entries for a specific business (tenant-scoped)."""
        return [e for e in self._entries if e.business_id == business_id]

    def query_by_system(
        self, business_id: uuid.UUID, system_id: str
    ) -> List[IntegrationAuditEntry]:
        return [
            e for e in self._entries
            if e.business_id == business_id and e.external_system_id == system_id
        ]

    def query_failures(self, business_id: uuid.UUID) -> List[IntegrationAuditEntry]:
        return [
            e for e in self._entries
            if e.business_id == business_id and e.status == "FAILED"
        ]

    @property
    def entries(self) -> List[IntegrationAuditEntry]:
        """Read-only access to all entries."""
        return list(self._entries)
