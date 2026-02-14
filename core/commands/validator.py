"""
BOS Command Layer - Command Validator
====================================
Validates command structure and business context.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.commands.base import Command, VALID_ACTOR_TYPES
from core.commands.rejection import ReasonCode
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BRANCH_REQUIRED
from core.identity.requirements import ACTOR_REQUIRED, SYSTEM_ALLOWED


@runtime_checkable
class CommandContextProtocol(Protocol):
    """Context interface required by command validation."""

    def has_active_context(self) -> bool:
        ...

    def get_active_business_id(self):
        ...

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        ...

    def get_business_lifecycle_state(self) -> str:
        ...


class CommandValidationError(Exception):
    """Structured validation failure for commands."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def validate_command(
    command: Command,
    context: CommandContextProtocol,
) -> None:
    """
    Validate command structure and business context.

    Checks (in order):
    1. Command type shape
    2. Context presence + active state
    3. Business lifecycle
    4. business_id boundary
    5. scope requirement branch rules
    6. branch ownership hook
    7. actor requirement + actor context integrity
    8. actor_type validity
    9. command_type format
    10. namespace alignment
    """

    if not isinstance(command, Command):
        raise CommandValidationError(
            code=ReasonCode.INVALID_COMMAND_STRUCTURE,
            message=f"Expected Command, got {type(command).__name__}.",
        )

    if context is None or not isinstance(context, CommandContextProtocol):
        raise CommandValidationError(
            code=ReasonCode.INVALID_CONTEXT,
            message=(
                "Invalid business context. Commands require "
                "BusinessContext-compatible context."
            ),
        )

    if not context.has_active_context():
        raise CommandValidationError(
            code=ReasonCode.NO_ACTIVE_CONTEXT,
            message="No active business context. Commands require context.",
        )

    lifecycle_state = context.get_business_lifecycle_state()
    if lifecycle_state in ("SUSPENDED", "CLOSED", "LEGAL_HOLD"):
        raise CommandValidationError(
            code=f"BUSINESS_{lifecycle_state}",
            message=(
                f"Business is {lifecycle_state}. "
                "Operations not permitted."
            ),
        )

    active_business_id = context.get_active_business_id()
    if command.business_id != active_business_id:
        raise CommandValidationError(
            code="BUSINESS_ID_MISMATCH",
            message=(
                f"Command business_id ({command.business_id}) does not "
                f"match active context ({active_business_id})."
            ),
        )

    if (
        command.scope_requirement == SCOPE_BRANCH_REQUIRED
        and command.branch_id is None
    ):
        raise CommandValidationError(
            code=ReasonCode.BRANCH_REQUIRED_MISSING,
            message=(
                "branch_id is required when scope_requirement is "
                "SCOPE_BRANCH_REQUIRED."
            ),
        )

    if command.branch_id is not None:
        if not context.is_branch_in_business(
            command.branch_id, command.business_id
        ):
            raise CommandValidationError(
                code=ReasonCode.BRANCH_NOT_IN_BUSINESS,
                message=(
                    f"branch_id ({command.branch_id}) does not belong "
                    f"to business_id ({command.business_id})."
                ),
            )

    if (
        command.actor_requirement == ACTOR_REQUIRED
        and command.actor_context is None
    ):
        raise CommandValidationError(
            code=ReasonCode.ACTOR_REQUIRED_MISSING,
            message="actor_context is required for this command.",
        )

    if command.actor_context is not None:
        actor_context = command.actor_context

        if not isinstance(actor_context, ActorContext):
            raise CommandValidationError(
                code=ReasonCode.ACTOR_INVALID,
                message="actor_context must be ActorContext.",
            )

        if actor_context.actor_type != command.actor_type:
            raise CommandValidationError(
                code=ReasonCode.ACTOR_INVALID,
                message=(
                    "actor_context.actor_type must match "
                    "command.actor_type."
                ),
            )

        if actor_context.actor_id != command.actor_id:
            raise CommandValidationError(
                code=ReasonCode.ACTOR_INVALID,
                message=(
                    "actor_context.actor_id must match command.actor_id."
                ),
            )

    if command.actor_requirement == SYSTEM_ALLOWED:
        if command.actor_type != "SYSTEM":
            raise CommandValidationError(
                code=ReasonCode.ACTOR_INVALID,
                message=(
                    "SYSTEM_ALLOWED commands must use "
                    "actor_type='SYSTEM'."
                ),
            )

    if command.actor_type not in VALID_ACTOR_TYPES:
        raise CommandValidationError(
            code=ReasonCode.INVALID_ACTOR,
            message=(
                f"actor_type '{command.actor_type}' not valid. "
                f"Must be one of: {sorted(VALID_ACTOR_TYPES)}"
            ),
        )

    if not command.command_type.endswith(".request"):
        raise CommandValidationError(
            code=ReasonCode.INVALID_COMMAND_TYPE,
            message=(
                f"command_type '{command.command_type}' must end "
                "with '.request'."
            ),
        )

    parts = command.command_type.split(".")
    if len(parts) < 4:
        raise CommandValidationError(
            code=ReasonCode.INVALID_COMMAND_TYPE,
            message=(
                f"command_type '{command.command_type}' must follow "
                "engine.domain.action.request format."
            ),
        )

    if parts[0] != command.source_engine:
        raise CommandValidationError(
            code=ReasonCode.INVALID_NAMESPACE,
            message=(
                f"command_type namespace '{parts[0]}' does not match "
                f"source_engine '{command.source_engine}'."
            ),
        )
