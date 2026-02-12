"""
BOS Event Store — Validation Errors & Results
===============================================
Every rejection is deterministic, explicit, and auditable.
No silent failures. No exception swallowing.
"""

from dataclasses import dataclass
from typing import Optional


# ══════════════════════════════════════════════════════════════
# REJECTION CODES (exhaustive, no ambiguity)
# ══════════════════════════════════════════════════════════════

class RejectionCode:
    """
    All possible rejection codes for event validation.
    Each code maps to exactly one violated rule.
    """

    # ── Schema Presence ───────────────────────────────────────
    MISSING_FIELD = "MISSING_FIELD"

    # ── Actor ─────────────────────────────────────────────────
    INVALID_ACTOR_TYPE = "INVALID_ACTOR_TYPE"
    EMPTY_ACTOR_ID = "EMPTY_ACTOR_ID"

    # ── Business Context ──────────────────────────────────────
    NO_ACTIVE_CONTEXT = "NO_ACTIVE_CONTEXT"
    BUSINESS_ID_MISMATCH = "BUSINESS_ID_MISMATCH"
    BRANCH_NOT_IN_BUSINESS = "BRANCH_NOT_IN_BUSINESS"

    # ── Event Type Registry ───────────────────────────────────
    EVENT_TYPE_UNKNOWN = "EVENT_TYPE_UNKNOWN"

    # ── Status ────────────────────────────────────────────────
    INVALID_STATUS = "INVALID_STATUS"

    # ── Correction ────────────────────────────────────────────
    CORRECTION_SELF_REFERENCE = "CORRECTION_SELF_REFERENCE"
    CORRECTION_INVALID_STATUS = "CORRECTION_INVALID_STATUS"


# ══════════════════════════════════════════════════════════════
# VIOLATED RULE IDENTIFIERS
# ══════════════════════════════════════════════════════════════

class ViolatedRule:
    """
    Rule identifiers that map to BOS doctrine sections.
    Used for audit trail — "which law was broken?"
    """

    SCHEMA_PRESENCE = "SCHEMA_PRESENCE"
    ACTOR_VALIDITY = "ACTOR_VALIDITY"
    BUSINESS_CONTEXT = "BUSINESS_CONTEXT"
    EVENT_TYPE_REGISTRY = "EVENT_TYPE_REGISTRY"
    STATUS_ENUM = "STATUS_ENUM"
    CORRECTION_RULES = "CORRECTION_RULES"


# ══════════════════════════════════════════════════════════════
# REJECTION (single validation failure)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Rejection:
    """
    One explicit, auditable reason for rejecting an event.
    Frozen — once created, it cannot be altered.
    """

    code: str
    message: str
    violated_rule: str


# ══════════════════════════════════════════════════════════════
# VALIDATION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ValidationResult:
    """
    Outcome of event validation.

    accepted=True  → event may proceed to persistence
    accepted=False → event is rejected with explicit reason

    advisory_actor: True if actor_type is AI.
    Flag only — no interpretation, no rejection.
    Downstream systems (commands, engines, audit) decide what to do.
    """

    accepted: bool
    rejection: Optional[Rejection] = None
    advisory_actor: bool = False
