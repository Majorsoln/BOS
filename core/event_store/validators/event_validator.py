"""
BOS Event Store — Event Validator
===================================
Law enforcement for events. Not convenience code.

This validator:
- Checks schema presence (mandatory fields)
- Validates actor type and identity
- Enforces business context
- Enforces event type registry
- Validates status enum
- Enforces correction rules
- Flags AI actors as advisory

This validator does NOT:
- Interpret payload content
- Write to database
- Dispatch events
- Compute hash-chain (Task 0.5)
- Check idempotency (Task 0.4)
- Make business decisions

Pure function: data in → ValidationResult out. No side effects.
"""

import uuid
from typing import Any

from core.event_store.validators.context import BusinessContextProtocol
from core.event_store.validators.errors import (
    Rejection,
    RejectionCode,
    ValidationResult,
    ViolatedRule,
)
from core.event_store.validators.registry import EventTypeRegistry


# ══════════════════════════════════════════════════════════════
# MANDATORY FIELDS (no defaults, no silent fill-ins)
# ══════════════════════════════════════════════════════════════

MANDATORY_FIELDS = (
    "event_id",
    "event_type",
    "event_version",
    "business_id",
    "branch_id",
    "source_engine",
    "actor_type",
    "actor_id",
    "correlation_id",
    "payload",
    "created_at",
)


# ══════════════════════════════════════════════════════════════
# VALID ENUM VALUES
# ══════════════════════════════════════════════════════════════

VALID_ACTOR_TYPES = frozenset({"HUMAN", "SYSTEM", "DEVICE", "AI"})
VALID_STATUSES = frozenset({"FINAL", "PROVISIONAL", "REVIEW_REQUIRED"})


# ══════════════════════════════════════════════════════════════
# INDIVIDUAL VALIDATION CHECKS
# ══════════════════════════════════════════════════════════════

def _validate_schema_presence(event_data: dict[str, Any]) -> Rejection | None:
    """
    Check that all mandatory fields are present and not None.
    No defaults. No silent fill-ins.
    """
    for field in MANDATORY_FIELDS:
        if field not in event_data or event_data[field] is None:
            return Rejection(
                code=RejectionCode.MISSING_FIELD,
                message=f"Mandatory field '{field}' is missing or None.",
                violated_rule=ViolatedRule.SCHEMA_PRESENCE,
            )
    return None


def _validate_actor(event_data: dict[str, Any]) -> Rejection | None:
    """
    Validate actor_type is a known enum value and actor_id is non-empty.
    """
    actor_type = event_data.get("actor_type")
    if actor_type not in VALID_ACTOR_TYPES:
        return Rejection(
            code=RejectionCode.INVALID_ACTOR_TYPE,
            message=(
                f"actor_type '{actor_type}' is not valid. "
                f"Must be one of: {', '.join(sorted(VALID_ACTOR_TYPES))}."
            ),
            violated_rule=ViolatedRule.ACTOR_VALIDITY,
        )

    actor_id = event_data.get("actor_id", "")
    if not isinstance(actor_id, str) or not actor_id.strip():
        return Rejection(
            code=RejectionCode.EMPTY_ACTOR_ID,
            message="actor_id must be a non-empty string.",
            violated_rule=ViolatedRule.ACTOR_VALIDITY,
        )

    return None


def _validate_business_context(
    event_data: dict[str, Any],
    context: BusinessContextProtocol,
) -> Rejection | None:
    """
    Enforce business context rules. Non-negotiable.
    - Context must be active
    - business_id must match active context
    - branch_id (if present) must belong to business
    """
    if context is None:
        return Rejection(
            code=RejectionCode.NO_ACTIVE_CONTEXT,
            message="No active business context. Events require context.",
            violated_rule=ViolatedRule.BUSINESS_CONTEXT,
        )

    if not context.has_active_context():
        return Rejection(
            code=RejectionCode.NO_ACTIVE_CONTEXT,
            message="No active business context. Events require context.",
            violated_rule=ViolatedRule.BUSINESS_CONTEXT,
        )

    active_business_id = context.get_active_business_id()
    event_business_id = event_data.get("business_id")

    if event_business_id != active_business_id:
        return Rejection(
            code=RejectionCode.BUSINESS_ID_MISMATCH,
            message=(
                f"Event business_id ({event_business_id}) does not match "
                f"active context business_id ({active_business_id})."
            ),
            violated_rule=ViolatedRule.BUSINESS_CONTEXT,
        )

    active_branch_id = context.get_active_branch_id()
    event_branch_id = event_data.get("branch_id")

    if active_branch_id is not None and event_branch_id != active_branch_id:
        return Rejection(
            code=RejectionCode.BRANCH_SCOPE_MISMATCH,
            message=(
                f"Event branch_id ({event_branch_id}) does not match "
                f"active context branch_id ({active_branch_id})."
            ),
            violated_rule=ViolatedRule.BUSINESS_CONTEXT,
        )

    event_branch_id = event_data.get("branch_id")
    if event_branch_id is not None:
        if not context.is_branch_in_business(event_branch_id, event_business_id):
            return Rejection(
                code=RejectionCode.BRANCH_NOT_IN_BUSINESS,
                message=(
                    f"branch_id ({event_branch_id}) does not belong to "
                    f"business_id ({event_business_id})."
                ),
                violated_rule=ViolatedRule.BUSINESS_CONTEXT,
            )

    return None


def _validate_event_type(
    event_data: dict[str, Any],
    registry: EventTypeRegistry,
) -> Rejection | None:
    """
    Event type must exist in registry. Free-text is forbidden.
    """
    event_type = event_data.get("event_type", "")

    if not registry.is_registered(event_type):
        return Rejection(
            code=RejectionCode.EVENT_TYPE_UNKNOWN,
            message=(
                f"Event type '{event_type}' is not registered. "
                f"Free-text event types are forbidden."
            ),
            violated_rule=ViolatedRule.EVENT_TYPE_REGISTRY,
        )

    return None


def _validate_status(event_data: dict[str, Any]) -> Rejection | None:
    """
    Status must be a valid enum value.
    Default is FINAL if not provided (this is the only field
    where absence means a known default per the model).
    """
    status = event_data.get("status", "FINAL")

    if status not in VALID_STATUSES:
        return Rejection(
            code=RejectionCode.INVALID_STATUS,
            message=(
                f"Status '{status}' is not valid. "
                f"Must be one of: {', '.join(sorted(VALID_STATUSES))}."
            ),
            violated_rule=ViolatedRule.STATUS_ENUM,
        )

    return None


def _validate_correction(event_data: dict[str, Any]) -> Rejection | None:
    """
    If correction_of is present:
    - Must not self-reference (correction_of != event_id)
    - Status must be FINAL or REVIEW_REQUIRED
    """
    correction_of = event_data.get("correction_of")

    if correction_of is None:
        return None

    event_id = event_data.get("event_id")
    if correction_of == event_id:
        return Rejection(
            code=RejectionCode.CORRECTION_SELF_REFERENCE,
            message="correction_of cannot reference the event itself.",
            violated_rule=ViolatedRule.CORRECTION_RULES,
        )

    status = event_data.get("status", "FINAL")
    allowed_correction_statuses = {EventStatus.FINAL, EventStatus.REVIEW_REQUIRED}

    if status not in allowed_correction_statuses:
        return Rejection(
            code=RejectionCode.CORRECTION_INVALID_STATUS,
            message=(
                f"Correction events must have status FINAL or "
                f"REVIEW_REQUIRED, got '{status}'."
            ),
            violated_rule=ViolatedRule.CORRECTION_RULES,
        )

    return None


# ══════════════════════════════════════════════════════════════
# MAIN VALIDATOR (orchestrator)
# ══════════════════════════════════════════════════════════════

def validate_event(
    event_data: dict[str, Any],
    context: BusinessContextProtocol,
    registry: EventTypeRegistry,
) -> ValidationResult:
    """
    Validate an event against BOS system law.

    Runs all checks in order. Stops at first rejection.
    Returns ValidationResult with explicit acceptance or rejection.

    This function is PURE — no side effects, no DB writes,
    no event dispatch, no business logic.

    Args:
        event_data: Raw event data as dict (before model creation).
        context:    Active business context (dependency injection).
        registry:   Event type registry (dependency injection).

    Returns:
        ValidationResult with accepted=True or accepted=False + Rejection.
    """

    # ── 1. Schema Presence ────────────────────────────────────
    rejection = _validate_schema_presence(event_data)
    if rejection:
        return ValidationResult(accepted=False, rejection=rejection)

    # ── 2. Actor Validation ───────────────────────────────────
    rejection = _validate_actor(event_data)
    if rejection:
        return ValidationResult(accepted=False, rejection=rejection)

    # ── 3. Business Context Enforcement ───────────────────────
    rejection = _validate_business_context(event_data, context)
    if rejection:
        return ValidationResult(accepted=False, rejection=rejection)

    # ── 4. Event Type Registry ────────────────────────────────
    rejection = _validate_event_type(event_data, registry)
    if rejection:
        return ValidationResult(accepted=False, rejection=rejection)

    # ── 5. Status Validation ──────────────────────────────────
    rejection = _validate_status(event_data)
    if rejection:
        return ValidationResult(accepted=False, rejection=rejection)

    # ── 6. Correction Rules ───────────────────────────────────
    rejection = _validate_correction(event_data)
    if rejection:
        return ValidationResult(accepted=False, rejection=rejection)

    # ── All checks passed ─────────────────────────────────────
    advisory_actor = event_data.get("actor_type") == "AI"

    return ValidationResult(
        accepted=True,
        advisory_actor=advisory_actor,
    )
