"""
BOS Core Audit — Public API
==============================
Immutable audit logging and consent tracking.
"""

from core.audit.models import AuditEntry, ConsentRecord
from core.audit.functions import create_audit_entry, grant_consent, revoke_consent

__all__ = [
    "AuditEntry",
    "ConsentRecord",
    "create_audit_entry",
    "grant_consent",
    "revoke_consent",
]
