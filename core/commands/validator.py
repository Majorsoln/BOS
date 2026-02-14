"""
BOS Command Layer — Command Validator
========================================
Validates command structure and business context.

This validator does NOT:
- Emit events
- Write to database
- Evaluate business policies
- Dispatch anything

It only checks:
- Command structure is valid
- BusinessContext is active
- business_id matches context
- branch_id belongs to business
- actor_type is valid
- command_type format is correct (engine.domain.action.request)
- payload exists

If invalid → CommandValidationError (structured, auditable).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.commands.base import Command, VALID_ACTOR_TYPES
from core.commands.rejection import ReasonCode
from core.context.scope import SCOPE_BRANCH_REQUIRED


# ══════════════════════════════════════════════════════════════
# BUSINESS CONTEXT PROTOCOL (dependency injection)
# ══════════════════════════════════════════════════════════════

@runtime_checkable
class CommandContextProtocol(Protocol):
    """
    Context interface required by command validation.

    Compatible with existing BusinessContextProtocol from
    core.event_store.validators.context. Can be the same object.
    """

    def has_active_context(self) -> bool:
        """Is there an active business context?"""
        ...

    def get_active_business_id(self):
        """Return the active business_id (UUID)."""
        ...

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        """Check if branch belongs to business."""
        ...

    def get_business_lifecycle_state(self) -> str:
        """
        Return business lifecycle state.
        Expected: 'ACTIVE', 'SUSPENDED', 'CLOSED', 'LEGAL_HOLD'.
        """
        ...


# ══════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ══════════════════════════════════════════════════════════════

class CommandValidationError(Exception):
    """Structured validation failure for commands."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ══════════════════════════════════════════════════════════════
# VALIDATOR
# ══════════════════════════════════════════════════════════════

def validate_command(
    command: Command,
    context: CommandContextProtocol,
) -> None:
    """
    Validate command structure and business context.

    Checks (in order):
    1. Command is a Command instance
    2. BusinessContext is active
    3. Business lifecycle state allows operations
    4. business_id matches active context
    5. branch_id belongs to business (if provided)
    6. actor_type is valid
    7. command_type format is correct
    8. payload is non-empty dict

    Args:
        command: Command to validate.
        context: Active business context.

    Raises:
        CommandValidationError: If any check fails.

    Returns:
        None — success is silent. Failure is loud.
    """

    # ── 1. Type check ─────────────────────────────────────────
    if not isinstance(command, Command):
        raise CommandValidationError(
            code="INVALID_COMMAND_STRUCTURE",
            message=f"Expected Command, got {type(command).__name__}.",
        )

    # ── 2. Context shape + active context ────────────────────
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

    # ── 3. Business lifecycle state ───────────────────────────
    lifecycle_state = context.get_business_lifecycle_state()
    if lifecycle_state in ("SUSPENDED", "CLOSED", "LEGAL_HOLD"):
        raise CommandValidationError(
            code=f"BUSINESS_{lifecycle_state}",
            message=(
                f"Business is {lifecycle_state}. "
                f"Operations not permitted."
            ),
        )

    # ── 4. business_id matches context ────────────────────────
    active_business_id = context.get_active_business_id()
    if command.business_id != active_business_id:
        raise CommandValidationError(
            code="BUSINESS_ID_MISMATCH",
            message=(
                f"Command business_id ({command.business_id}) does not "
                f"match active context ({active_business_id})."
            ),
        )

    # ── 5. Scope requirement branch enforcement ───────────────
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

    # ── 6. branch_id belongs to business ──────────────────────
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

    # ── 7. actor_type valid ───────────────────────────────────
    if command.actor_type not in VALID_ACTOR_TYPES:
        raise CommandValidationError(
            code=ReasonCode.INVALID_ACTOR,
            message=(
                f"actor_type '{command.actor_type}' not valid. "
                f"Must be one of: {sorted(VALID_ACTOR_TYPES)}"
            ),
        )

    # ── 8. command_type format ────────────────────────────────
    if not command.command_type.endswith(".request"):
        raise CommandValidationError(
            code=ReasonCode.INVALID_COMMAND_TYPE,
            message=(
                f"command_type '{command.command_type}' must end "
                f"with '.request'."
            ),
        )

    parts = command.command_type.split(".")
    if len(parts) < 4:
        raise CommandValidationError(
            code=ReasonCode.INVALID_COMMAND_TYPE,
            message=(
                f"command_type '{command.command_type}' must follow "
                f"engine.domain.action.request format."
            ),
        )

    # ── 9. Namespace: first segment must match source_engine ──
    if parts[0] != command.source_engine:
        raise CommandValidationError(
            code=ReasonCode.INVALID_NAMESPACE,
            message=(
                f"command_type namespace '{parts[0]}' does not match "
                f"source_engine '{command.source_engine}'."
            ),
        )
