"""
BOS Command Layer — Rejection Model
======================================
Structured rejection reasons for denied commands.

This is NOT an event. It is an explanation structure
that becomes PART of the rejection event's payload.

Every rejection must be:
- Deterministic (same input → same rejection)
- Auditable (code + message + policy)
- Machine-readable (reason_code)
- Human-readable (message)
"""

from __future__ import annotations

from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════
# REJECTION REASON (frozen explanation structure)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RejectionReason:
    """
    Structured reason for command rejection.

    Fields:
        code:        Machine-readable rejection code (e.g. 'BUSINESS_SUSPENDED').
        message:     Human-readable explanation.
        policy_name: Name of the policy that caused rejection.

    This is serializable into event payload for audit trail.
    """

    code: str
    message: str
    policy_name: str

    def __post_init__(self):
        if not self.code or not isinstance(self.code, str):
            raise ValueError("code must be a non-empty string.")

        if not self.message or not isinstance(self.message, str):
            raise ValueError("message must be a non-empty string.")

        if not self.policy_name or not isinstance(self.policy_name, str):
            raise ValueError("policy_name must be a non-empty string.")

    def to_dict(self) -> dict:
        """Serialize for event payload."""
        return {
            "code": self.code,
            "message": self.message,
            "policy_name": self.policy_name,
        }


# ══════════════════════════════════════════════════════════════
# STANDARD REJECTION CODES
# ══════════════════════════════════════════════════════════════

class ReasonCode:
    """
    Known rejection codes. Extensible by engines.

    Convention: SCREAMING_SNAKE_CASE.
    """

    # ── Business lifecycle ────────────────────────────────────
    BUSINESS_SUSPENDED = "BUSINESS_SUSPENDED"
    BUSINESS_CLOSED = "BUSINESS_CLOSED"
    BUSINESS_LEGAL_HOLD = "BUSINESS_LEGAL_HOLD"

    # ── Context / authorization ───────────────────────────────
    NO_ACTIVE_CONTEXT = "NO_ACTIVE_CONTEXT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    BRANCH_NOT_IN_BUSINESS = "BRANCH_NOT_IN_BUSINESS"

    # ── Command structure ─────────────────────────────────────
    INVALID_COMMAND_STRUCTURE = "INVALID_COMMAND_STRUCTURE"
    INVALID_COMMAND_TYPE = "INVALID_COMMAND_TYPE"
    INVALID_NAMESPACE = "INVALID_NAMESPACE"

    # ── Policy / domain ───────────────────────────────────────
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    CASH_SESSION_CLOSED = "CASH_SESSION_CLOSED"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"

    # ── Actor ─────────────────────────────────────────────────
    AI_EXECUTION_FORBIDDEN = "AI_EXECUTION_FORBIDDEN"
    INVALID_ACTOR = "INVALID_ACTOR"

    # ── General ───────────────────────────────────────────────
    POLICY_VIOLATION = "POLICY_VIOLATION"
