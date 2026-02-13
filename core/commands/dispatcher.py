"""
BOS Command Layer — Command Dispatcher
=========================================
Accept Command → Validate → Evaluate Policies → Produce Outcome.

The Dispatcher is the DECISION MAKER. It decides ACCEPTED or REJECTED.

The Dispatcher DOES NOT:
- Persist events
- Dispatch event bus
- Write projections
- Execute business logic

It only produces a deterministic CommandOutcome.

Policy evaluation is pluggable — policies are registered as callables
that return Optional[RejectionReason]. If any policy rejects, the
command is REJECTED with the first rejection reason.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, List, Optional

from core.commands.base import Command
from core.commands.outcomes import CommandOutcome, CommandStatus
from core.commands.rejection import RejectionReason, ReasonCode
from core.commands.validator import (
    CommandContextProtocol,
    CommandValidationError,
    validate_command,
)

logger = logging.getLogger("bos.commands")


# ══════════════════════════════════════════════════════════════
# POLICY TYPE
# ══════════════════════════════════════════════════════════════

# A policy is a callable:
#   (Command, context) → Optional[RejectionReason]
#   Returns None if policy passes, RejectionReason if it rejects.
PolicyEvaluator = Callable[
    [Command, CommandContextProtocol],
    Optional[RejectionReason],
]


# ══════════════════════════════════════════════════════════════
# BUILT-IN POLICIES
# ══════════════════════════════════════════════════════════════

def ai_execution_guard(
    command: Command, context: CommandContextProtocol
) -> Optional[RejectionReason]:
    """
    AI actors cannot produce execution commands.
    AI is advisory only — BOS Doctrine.

    This is a placeholder enforcement — full AI advisory
    policy will be richer in later phases.
    """
    if command.actor_type == "AI":
        return RejectionReason(
            code=ReasonCode.AI_EXECUTION_FORBIDDEN,
            message=(
                "AI actors cannot execute operational commands. "
                "AI is advisory only."
            ),
            policy_name="ai_execution_guard",
        )
    return None


# ══════════════════════════════════════════════════════════════
# COMMAND DISPATCHER
# ══════════════════════════════════════════════════════════════

class CommandDispatcher:
    """
    Evaluate a command through validation and policies.

    Lifecycle:
    1. Validate command structure + context
    2. Evaluate registered policies (in order)
    3. Produce CommandOutcome (ACCEPTED or REJECTED)

    Usage:
        dispatcher = CommandDispatcher(context=business_context)
        dispatcher.register_policy(ai_execution_guard)
        dispatcher.register_policy(custom_stock_policy)

        outcome = dispatcher.dispatch(command)
        # outcome.is_accepted or outcome.is_rejected

    Policies are evaluated in registration order.
    First rejection wins — remaining policies are skipped.
    """

    def __init__(self, context: CommandContextProtocol):
        self._context = context
        self._policies: List[PolicyEvaluator] = []

    def register_policy(self, policy: PolicyEvaluator) -> None:
        """
        Register a policy evaluator.

        Policies are evaluated in registration order.
        """
        if not callable(policy):
            raise TypeError(
                f"Policy must be callable, got {type(policy).__name__}."
            )
        self._policies.append(policy)

        policy_name = getattr(policy, "__qualname__", str(policy))
        logger.debug(f"Policy registered: {policy_name}")

    # ══════════════════════════════════════════════════════════
    # DISPATCH
    # ══════════════════════════════════════════════════════════

    def dispatch(self, command: Command) -> CommandOutcome:
        """
        Evaluate command and produce outcome.

        Flow:
        1. Validate structure + context → if fails, REJECTED
        2. Evaluate policies → if any rejects, REJECTED
        3. All clear → ACCEPTED

        Args:
            command: Command to evaluate.

        Returns:
            CommandOutcome — never None, never ambiguous.
        """
        now = datetime.now(timezone.utc)

        # ── Step 1: Structural validation ─────────────────────
        try:
            validate_command(command, self._context)
        except CommandValidationError as exc:
            logger.info(
                f"Command {command.command_id} validation failed: "
                f"[{exc.code}] {exc.message}"
            )
            return CommandOutcome(
                command_id=command.command_id,
                status=CommandStatus.REJECTED,
                reason=RejectionReason(
                    code=exc.code,
                    message=exc.message,
                    policy_name="command_validator",
                ),
                occurred_at=now,
            )

        # ── Step 2: Policy evaluation ─────────────────────────
        for policy in self._policies:
            rejection = policy(command, self._context)
            if rejection is not None:
                if not isinstance(rejection, RejectionReason):
                    raise TypeError(
                        f"Policy must return RejectionReason or None, "
                        f"got {type(rejection).__name__}."
                    )

                logger.info(
                    f"Command {command.command_id} rejected by "
                    f"policy '{rejection.policy_name}': "
                    f"[{rejection.code}] {rejection.message}"
                )
                return CommandOutcome(
                    command_id=command.command_id,
                    status=CommandStatus.REJECTED,
                    reason=rejection,
                    occurred_at=now,
                )

        # ── Step 3: All clear → ACCEPTED ──────────────────────
        logger.info(f"Command {command.command_id} ACCEPTED")
        return CommandOutcome(
            command_id=command.command_id,
            status=CommandStatus.ACCEPTED,
            reason=None,
            occurred_at=now,
        )
