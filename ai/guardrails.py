"""
BOS AI Guardrails — Non-Negotiable Execution Boundaries
==========================================================
Doctrine (BOS_MASTER_REFERENCE §4):
  AI is advisory only. AI CANNOT commit state autonomously.

This module enforces that AI actors never bypass the command pipeline
and that all AI actions are bounded to their tenant scope.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# AI ACTION CLASSIFICATION
# ══════════════════════════════════════════════════════════════

class AIActionType(Enum):
    """What the AI is attempting to do."""
    ANALYZE = "ANALYZE"             # Read projections, compute metrics
    RECOMMEND = "RECOMMEND"         # Provide advisory output
    SIMULATE = "SIMULATE"           # Run what-if scenarios
    PREPARE_COMMAND = "PREPARE_COMMAND"  # Draft command for human review
    FLAG_ANOMALY = "FLAG_ANOMALY"   # Raise anomaly for human review
    EXECUTE_COMMAND = "EXECUTE_COMMAND"  # Attempt autonomous execution


# Actions that are always allowed (read-only)
ALWAYS_ALLOWED = frozenset({
    AIActionType.ANALYZE,
    AIActionType.RECOMMEND,
    AIActionType.SIMULATE,
    AIActionType.FLAG_ANOMALY,
})

# Actions that require human approval
REQUIRES_APPROVAL = frozenset({
    AIActionType.PREPARE_COMMAND,
})

# Actions that are NEVER allowed without explicit policy grant
RESTRICTED = frozenset({
    AIActionType.EXECUTE_COMMAND,
})


# ══════════════════════════════════════════════════════════════
# FORBIDDEN AI OPERATIONS
# ══════════════════════════════════════════════════════════════

FORBIDDEN_OPERATIONS = frozenset({
    "approve_purchase",
    "sign_contract",
    "borrow_funds",
    "authorize_payment",
    "dismiss_staff",
    "modify_hr_record",
    "delete_data",
    "alter_historical_record",
    "cross_tenant_access",
})


# ══════════════════════════════════════════════════════════════
# GUARDRAIL CHECK
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GuardrailResult:
    """Result of a guardrail check."""
    allowed: bool
    reason: str
    action_type: AIActionType
    requires_human_approval: bool = False


def check_ai_guardrail(
    action_type: AIActionType,
    operation_name: str,
    business_id: uuid.UUID,
    actor_business_id: uuid.UUID,
    has_automation_policy: bool = False,
) -> GuardrailResult:
    """
    Enforce AI guardrails before any AI action.

    Returns GuardrailResult indicating whether the action is allowed.
    """
    # Rule 1: AI is tenant-scoped — reject cross-tenant access
    if business_id != actor_business_id:
        return GuardrailResult(
            allowed=False,
            reason=f"AI cross-tenant access denied: actor tenant {actor_business_id} "
                   f"cannot access business {business_id}.",
            action_type=action_type,
        )

    # Rule 2: Certain operations are absolutely forbidden
    if operation_name in FORBIDDEN_OPERATIONS:
        return GuardrailResult(
            allowed=False,
            reason=f"AI forbidden operation: '{operation_name}' is never allowed for AI actors.",
            action_type=action_type,
        )

    # Rule 3: Read-only actions are always allowed
    if action_type in ALWAYS_ALLOWED:
        return GuardrailResult(
            allowed=True,
            reason="Advisory action — read-only, no guardrail restriction.",
            action_type=action_type,
        )

    # Rule 4: Command preparation requires human approval
    if action_type in REQUIRES_APPROVAL:
        return GuardrailResult(
            allowed=True,
            reason="Command prepared for human review — requires approval before dispatch.",
            action_type=action_type,
            requires_human_approval=True,
        )

    # Rule 5: Autonomous execution requires explicit policy grant
    if action_type in RESTRICTED:
        if has_automation_policy:
            return GuardrailResult(
                allowed=True,
                reason="Limited automation — explicit policy grant found.",
                action_type=action_type,
                requires_human_approval=False,
            )
        return GuardrailResult(
            allowed=False,
            reason="AI autonomous execution denied: no explicit automation policy grant.",
            action_type=action_type,
        )

    # Default deny
    return GuardrailResult(
        allowed=False,
        reason=f"Unknown AI action type: {action_type}",
        action_type=action_type,
    )


def ai_rejection_reason(result: GuardrailResult) -> Optional[RejectionReason]:
    """Convert a denied guardrail result into a RejectionReason."""
    if result.allowed:
        return None
    return RejectionReason(
        code="AI_EXECUTION_FORBIDDEN",
        message=result.reason,
        policy_name="check_ai_guardrail",
    )
