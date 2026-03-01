"""
BOS Core Audit — Immutable Audit Models
==========================================
Append-only audit log entries and consent records.
These are frozen dataclasses — once created, never modified.
Deletion of audit records is forbidden.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ══════════════════════════════════════════════════════════════
# AUDIT LOG ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AuditEntry:
    """
    Immutable record of an action taken in the system.

    Every command execution, rejection, and significant system event
    produces an AuditEntry. These are append-only.
    """

    entry_id: uuid.UUID
    event_id: uuid.UUID
    actor_id: str
    actor_type: str
    action: str
    resource_type: str
    resource_id: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    status: str  # EXECUTED | REJECTED | ERROR
    occurred_at: datetime
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in ("EXECUTED", "REJECTED", "ERROR"):
            raise ValueError(
                f"AuditEntry status must be EXECUTED|REJECTED|ERROR, got '{self.status}'."
            )


# ══════════════════════════════════════════════════════════════
# CONSENT RECORD
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConsentRecord:
    """
    Immutable consent tracking record.

    Consent is required before certain data collection (e.g. biometrics).
    Revocation creates a new record — original is never deleted.
    """

    consent_id: uuid.UUID
    subject_id: str
    consent_type: str  # BIOMETRIC_CAPTURE | DATA_PROCESSING | MARKETING
    business_id: uuid.UUID
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    def is_valid(self, now: datetime) -> bool:
        """Check if consent is currently valid (not revoked, not expired)."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and now > self.expires_at:
            return False
        return True
