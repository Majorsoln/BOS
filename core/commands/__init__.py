"""
BOS Command Layer — System Governance
========================================
Every action begins as a Command.
Every Command produces exactly one Outcome.
REJECTED commands are first-class citizens.

Command → Outcome → Event chain is fully deterministic.
"""

from core.commands.base import (
    Command,
    VALID_ACTOR_TYPES,
    derive_rejection_event_type,
    derive_source_engine,
)
from core.commands.outcomes import (
    CommandOutcome,
    CommandStatus,
)
from core.commands.rejection import (
    ReasonCode,
    RejectionReason,
)
from core.commands.validator import (
    CommandContextProtocol,
    CommandValidationError,
    validate_command,
)
from core.commands.dispatcher import (
    CommandDispatcher,
    PolicyEvaluator,
    ai_execution_guard,
)
from core.commands.bus import (
    CommandBus,
    CommandBusError,
    CommandResult,
    NoHandlerRegistered,
)

__all__ = [
    # ── Base ──────────────────────────────────────────────────
    "Command",
    "VALID_ACTOR_TYPES",
    "derive_rejection_event_type",
    "derive_source_engine",
    # ── Outcomes ──────────────────────────────────────────────
    "CommandOutcome",
    "CommandStatus",
    # ── Rejection ─────────────────────────────────────────────
    "RejectionReason",
    "ReasonCode",
    # ── Validator ─────────────────────────────────────────────
    "CommandContextProtocol",
    "CommandValidationError",
    "validate_command",
    # ── Dispatcher ────────────────────────────────────────────
    "CommandDispatcher",
    "PolicyEvaluator",
    "ai_execution_guard",
    # ── Bus ────────────────────────────────────────────────────
    "CommandBus",
    "CommandBusError",
    "CommandResult",
    "NoHandlerRegistered",
]
