"""
BOS Core Audit — Pure Audit Functions
========================================
Factory functions for creating audit entries and consent records.
All functions are pure — they return new frozen objects, never mutate.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from core.audit.models import AuditEntry, ConsentRecord


# ══════════════════════════════════════════════════════════════
# AUDIT LOG CREATION
# ══════════════════════════════════════════════════════════════

def create_audit_entry(
    event_id: uuid.UUID,
    actor_id: str,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str,
    business_id: uuid.UUID,
    status: str,
    occurred_at: datetime,
    branch_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict] = None,
) -> AuditEntry:
    """Create an immutable audit entry."""
    return AuditEntry(
        entry_id=uuid.uuid4(),
        event_id=event_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        business_id=business_id,
        branch_id=branch_id,
        status=status,
        occurred_at=occurred_at,
        metadata=metadata or {},
    )


# ══════════════════════════════════════════════════════════════
# CONSENT MANAGEMENT
# ══════════════════════════════════════════════════════════════

def grant_consent(
    subject_id: str,
    consent_type: str,
    business_id: uuid.UUID,
    granted_at: datetime,
    expires_at: Optional[datetime] = None,
) -> ConsentRecord:
    """Create a new consent grant record."""
    return ConsentRecord(
        consent_id=uuid.uuid4(),
        subject_id=subject_id,
        consent_type=consent_type,
        business_id=business_id,
        granted_at=granted_at,
        expires_at=expires_at,
    )


def revoke_consent(
    record: ConsentRecord,
    revoked_at: datetime,
) -> ConsentRecord:
    """
    Create a new ConsentRecord representing revocation.

    The original record is never modified (immutable).
    Returns a new record with revoked_at set.
    """
    return ConsentRecord(
        consent_id=record.consent_id,
        subject_id=record.subject_id,
        consent_type=record.consent_type,
        business_id=record.business_id,
        granted_at=record.granted_at,
        expires_at=record.expires_at,
        revoked_at=revoked_at,
    )
