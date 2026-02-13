"""
BOS Policy Engine — Command Layer Integration (Stabilization Patch v1.0.2)
============================================================================
PolicyAwareDispatcher wraps the existing command pipeline to insert
policy evaluation AFTER validation, BEFORE outcome generation.

Patch v1.0.2 Fixes:
- Fix 2: No datetime.now(). Time comes from command.issued_at.
- Fix 5: ESCALATE forces event_status=REVIEW_REQUIRED (enforced, not advisory).

Pipeline with policy:
    Command
       ↓
    Validation          (existing — CommandValidator)
       ↓
    Policy Evaluation   ← PolicyEngine (fail-safe, never raises)
       ↓
    Legacy Policies     (existing — registered PolicyEvaluators)
       ↓
    Outcome             ← PolicyAwareOutcome

Integration rules:
- If BLOCK → REJECTED outcome with policy explanation
- If WARN → ACCEPTED outcome, warnings attached to metadata
- If ESCALATE → ACCEPTED outcome, event_status enforced to REVIEW_REQUIRED
- Existing PolicyEvaluator functions still run after policy engine
- PolicyEngine is optional — if not provided, behaves like before

This is ADDITIVE. Existing CommandDispatcher is not modified.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from core.commands.base import Command
from core.commands.outcomes import CommandOutcome, CommandStatus
from core.commands.rejection import RejectionReason
from core.commands.validator import (
    CommandContextProtocol,
    CommandValidationError,
    validate_command,
)
from core.commands.dispatcher import PolicyEvaluator
from core.policy.engine import PolicyEngine
from core.policy.result import PolicyDecision

logger = logging.getLogger("bos.commands")


# ══════════════════════════════════════════════════════════════
# ENFORCED EVENT STATUS (Fix 5)
# ══════════════════════════════════════════════════════════════

EVENT_STATUS_FINAL = "FINAL"
EVENT_STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"


# ══════════════════════════════════════════════════════════════
# POLICY-AWARE OUTCOME (extends CommandOutcome with metadata)
# ══════════════════════════════════════════════════════════════

class PolicyAwareOutcome:
    """
    Wraps CommandOutcome with policy decision metadata.

    This allows the CommandBus to:
    - Attach warnings to accepted outcomes
    - Force REVIEW_REQUIRED on escalations (Fix 5 — enforced)
    - Include policy_version in event payload
    """

    def __init__(
        self,
        outcome: CommandOutcome,
        policy_decision: Optional[PolicyDecision] = None,
    ):
        self.outcome = outcome
        self.policy_decision = policy_decision

    @property
    def is_accepted(self) -> bool:
        return self.outcome.is_accepted

    @property
    def is_rejected(self) -> bool:
        return self.outcome.is_rejected

    @property
    def requires_review(self) -> bool:
        """True if policy has escalations → event status=REVIEW_REQUIRED."""
        if self.policy_decision is None:
            return False
        return self.policy_decision.requires_review

    @property
    def has_warnings(self) -> bool:
        if self.policy_decision is None:
            return False
        return self.policy_decision.has_warnings

    @property
    def policy_version(self) -> str:
        if self.policy_decision is None:
            return ""
        return self.policy_decision.policy_version

    @property
    def enforced_event_status(self) -> str:
        """
        Fix 5: Enforced event status based on policy decision.

        If ESCALATE present → REVIEW_REQUIRED (mandatory, not advisory).
        Otherwise → FINAL.

        Callers MUST use this instead of hardcoding event status.
        """
        if self.requires_review:
            return EVENT_STATUS_REVIEW_REQUIRED
        return EVENT_STATUS_FINAL


# ══════════════════════════════════════════════════════════════
# POLICY-AWARE DISPATCHER
# ══════════════════════════════════════════════════════════════

class PolicyAwareDispatcher:
    """
    Command dispatcher with integrated policy evaluation.

    Lifecycle:
    1. Validate command structure + context
    2. Evaluate policy engine (graduated enforcement)
    3. Evaluate legacy policies (existing PolicyEvaluator functions)
    4. Produce PolicyAwareOutcome

    Fix 2: Time comes from command.issued_at. Never datetime.now().
    Fix 5: ESCALATE → enforced_event_status = REVIEW_REQUIRED.

    Usage:
        dispatcher = PolicyAwareDispatcher(
            context=business_context,
            policy_engine=policy_engine,
        )
        dispatcher.register_policy(ai_execution_guard)

        result = dispatcher.dispatch(
            command,
            projected_state={"available_stock": 50},
        )

        # Fix 5: Caller uses enforced status
        event_status = result.enforced_event_status
    """

    def __init__(
        self,
        context: CommandContextProtocol,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self._context = context
        self._policy_engine = policy_engine
        self._policies: List[PolicyEvaluator] = []

    def register_policy(self, policy: PolicyEvaluator) -> None:
        """Register legacy policy evaluator (backward compatible)."""
        if not callable(policy):
            raise TypeError(
                f"Policy must be callable, got {type(policy).__name__}."
            )
        self._policies.append(policy)

    def dispatch(
        self,
        command: Command,
        projected_state: dict = None,
        policy_version: str = None,
    ) -> PolicyAwareOutcome:
        """
        Evaluate command through validation + policy + legacy policies.

        Fix 2: Time from command.issued_at — NEVER datetime.now().

        Args:
            command:          Command to evaluate.
            projected_state:  Current projected state for policy rules.
            policy_version:   Explicit version for replay determinism.

        Returns:
            PolicyAwareOutcome — CommandOutcome + policy metadata.
        """
        # ── Fix 2: Time from command context ──────────────────
        evaluation_time = command.issued_at

        # ── Step 1: Structural validation ─────────────────────
        try:
            validate_command(command, self._context)
        except CommandValidationError as exc:
            logger.info(
                f"Command {command.command_id} validation failed: "
                f"[{exc.code}] {exc.message}"
            )
            return PolicyAwareOutcome(
                outcome=CommandOutcome(
                    command_id=command.command_id,
                    status=CommandStatus.REJECTED,
                    reason=RejectionReason(
                        code=exc.code,
                        message=exc.message,
                        policy_name="command_validator",
                    ),
                    occurred_at=evaluation_time,
                ),
                policy_decision=None,
            )

        # ── Step 2: Policy engine evaluation ──────────────────
        policy_decision = None
        if self._policy_engine is not None:
            policy_decision = self._policy_engine.evaluate(
                command=command,
                business_context=self._context,
                projected_state=projected_state or {},
                policy_version=policy_version,
                evaluation_time=evaluation_time,
            )

            # If BLOCK → REJECTED
            if not policy_decision.allowed:
                first_violation = policy_decision.violations[0]
                logger.info(
                    f"Command {command.command_id} BLOCKED by policy "
                    f"'{first_violation.rule_id}': "
                    f"{first_violation.message}"
                )
                return PolicyAwareOutcome(
                    outcome=CommandOutcome(
                        command_id=command.command_id,
                        status=CommandStatus.REJECTED,
                        reason=RejectionReason(
                            code=f"POLICY_{first_violation.rule_id}",
                            message=first_violation.message,
                            policy_name=first_violation.rule_id,
                        ),
                        occurred_at=evaluation_time,
                    ),
                    policy_decision=policy_decision,
                )

        # ── Step 3: Legacy policy evaluation ──────────────────
        for policy in self._policies:
            rejection = policy(command, self._context)
            if rejection is not None:
                if not isinstance(rejection, RejectionReason):
                    raise TypeError(
                        "Policy must return RejectionReason or None."
                    )
                logger.info(
                    f"Command {command.command_id} rejected by "
                    f"legacy policy '{rejection.policy_name}'"
                )
                return PolicyAwareOutcome(
                    outcome=CommandOutcome(
                        command_id=command.command_id,
                        status=CommandStatus.REJECTED,
                        reason=rejection,
                        occurred_at=evaluation_time,
                    ),
                    policy_decision=policy_decision,
                )

        # ── Step 4: ACCEPTED ──────────────────────────────────
        logger.info(
            f"Command {command.command_id} ACCEPTED"
        )
        return PolicyAwareOutcome(
            outcome=CommandOutcome(
                command_id=command.command_id,
                status=CommandStatus.ACCEPTED,
                reason=None,
                occurred_at=evaluation_time,
            ),
            policy_decision=policy_decision,
        )
