"""
BOS Policy Engine - Command Layer Integration (Stabilization Patch v1.0.2)
============================================================================
PolicyAwareDispatcher wraps the existing command pipeline to insert
policy evaluation AFTER validation and boundary checks.

Patch v1.0.2 Fixes:
- Fix 2: No datetime.now(). Time comes from command.issued_at.
- Fix 5: ESCALATE forces event_status=REVIEW_REQUIRED (enforced, not advisory).

Pipeline with policy:
    Command
       v
    Validation          (existing - CommandValidator)
       v
    Boundary Policies   (actor, then permission)
       v
    Policy Evaluation   <- PolicyEngine (fail-safe, never raises)
       v
    Legacy Policies     (existing - registered PolicyEvaluators)
       v
    Outcome             <- PolicyAwareOutcome

Integration rules:
- If BLOCK -> REJECTED outcome with policy explanation
- If WARN -> ACCEPTED outcome, warnings attached to metadata
- If ESCALATE -> ACCEPTED outcome, event_status enforced to REVIEW_REQUIRED
- Existing PolicyEvaluator functions still run after policy engine
- PolicyEngine is optional - if not provided, behaves like before

This is ADDITIVE. Existing CommandDispatcher is not modified.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from core.commands.base import Command
from core.commands.dispatcher import PolicyEvaluator
from core.commands.outcomes import CommandOutcome, CommandStatus
from core.commands.rejection import RejectionReason
from core.commands.validator import (
    CommandContextProtocol,
    CommandValidationError,
    validate_command,
)
from core.identity.policy import actor_scope_authorization_guard
from core.policy.compliance_policy import compliance_authorization_guard
from core.policy.engine import PolicyEngine
from core.policy.feature_flag_policy import feature_flag_authorization_guard
from core.policy.permission_policy import permission_authorization_guard
from core.policy.result import PolicyDecision

logger = logging.getLogger("bos.commands")

EVENT_STATUS_FINAL = "FINAL"
EVENT_STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"


class PolicyAwareOutcome:
    """
    Wraps CommandOutcome with policy decision metadata.

    This allows the CommandBus to:
    - Attach warnings to accepted outcomes
    - Force REVIEW_REQUIRED on escalations (Fix 5 - enforced)
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
        if self.requires_review:
            return EVENT_STATUS_REVIEW_REQUIRED
        return EVENT_STATUS_FINAL


class PolicyAwareDispatcher:
    """
    Command dispatcher with integrated policy evaluation.

    Lifecycle:
    1. Validate command structure + context
    2. Evaluate boundary policies (actor then permission)
    3. Evaluate policy engine (graduated enforcement)
    4. Evaluate legacy policies (existing PolicyEvaluator functions)
    5. Produce PolicyAwareOutcome

    Fix 2: Time comes from command.issued_at. Never datetime.now().
    Fix 5: ESCALATE -> enforced_event_status = REVIEW_REQUIRED.
    """

    def __init__(
        self,
        context: CommandContextProtocol,
        policy_engine: Optional[PolicyEngine] = None,
        permission_provider=None,
        feature_flag_provider=None,
        compliance_provider=None,
    ):
        self._context = context
        self._policy_engine = policy_engine
        self._permission_provider = permission_provider
        self._feature_flag_provider = feature_flag_provider
        self._compliance_provider = compliance_provider
        self._boundary_policies: List[PolicyEvaluator] = [
            actor_scope_authorization_guard,
            self._permission_authorization_policy,
            self._feature_flag_authorization_policy,
            self._compliance_authorization_policy,
        ]
        self._policies: List[PolicyEvaluator] = []

    def _permission_authorization_policy(
        self,
        command: Command,
        context: CommandContextProtocol,
    ) -> Optional[RejectionReason]:
        return permission_authorization_guard(
            command=command,
            context=context,
            provider=self._permission_provider,
        )

    def _feature_flag_authorization_policy(
        self,
        command: Command,
        context: CommandContextProtocol,
    ) -> Optional[RejectionReason]:
        return feature_flag_authorization_guard(
            command=command,
            context=context,
            provider=self._feature_flag_provider,
        )

    def _compliance_authorization_policy(
        self,
        command: Command,
        context: CommandContextProtocol,
    ) -> Optional[RejectionReason]:
        return compliance_authorization_guard(
            command=command,
            context=context,
            compliance_provider=self._compliance_provider,
            feature_flag_provider=self._feature_flag_provider,
        )

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
        Evaluate command through validation + boundary + policy + legacy policies.

        Fix 2: Time from command.issued_at - NEVER datetime.now().
        """
        evaluation_time = command.issued_at

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

        for policy in self._boundary_policies:
            rejection = policy(command, self._context)
            if rejection is not None:
                if not isinstance(rejection, RejectionReason):
                    raise TypeError(
                        "Policy must return RejectionReason or None."
                    )
                logger.info(
                    f"Command {command.command_id} rejected by "
                    f"boundary policy '{rejection.policy_name}'"
                )
                return PolicyAwareOutcome(
                    outcome=CommandOutcome(
                        command_id=command.command_id,
                        status=CommandStatus.REJECTED,
                        reason=rejection,
                        occurred_at=evaluation_time,
                    ),
                    policy_decision=None,
                )

        policy_decision = None
        if self._policy_engine is not None:
            policy_decision = self._policy_engine.evaluate(
                command=command,
                business_context=self._context,
                projected_state=projected_state or {},
                policy_version=policy_version,
                evaluation_time=evaluation_time,
            )

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

        logger.info(f"Command {command.command_id} ACCEPTED")
        return PolicyAwareOutcome(
            outcome=CommandOutcome(
                command_id=command.command_id,
                status=CommandStatus.ACCEPTED,
                reason=None,
                occurred_at=evaluation_time,
            ),
            policy_decision=policy_decision,
        )
