"""
BOS Command Layer — Command Bus
==================================
High-level orchestration of the command lifecycle.

Flow:
    1. Dispatch command → get Outcome
    2. If ACCEPTED → call engine service handler → handler persists event
    3. If REJECTED → build rejection event → persist via persist_event

The CommandBus:
- Orchestrates, does not decide
- Uses persist_event() for rejection events (never bypasses)
- Delegates accepted commands to engine service handlers
- Guarantees: no silent path, every command produces an event

The CommandBus does NOT:
- Write directly to Event.objects
- Dispatch Event Bus directly (persist_event does that)
- Modify projections
- Contain engine-specific logic
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Protocol

from core.commands.base import Command, derive_rejection_event_type
from core.commands.dispatcher import CommandDispatcher
from core.commands.outcomes import CommandOutcome, CommandStatus

logger = logging.getLogger("bos.commands")


# ══════════════════════════════════════════════════════════════
# ENGINE SERVICE PROTOCOL
# ══════════════════════════════════════════════════════════════

class EngineServiceProtocol(Protocol):
    """
    Protocol for engine service handlers.

    Each engine registers a handler that knows how to execute
    an accepted command and persist the resulting event.

    The handler is responsible for:
    - Building the accepted event data
    - Calling persist_event() (or enforced_persist_event())
    - Returning success/failure

    The CommandBus does NOT know what event the engine persists.
    That is the engine's responsibility.
    """

    def execute(self, command: Command) -> Any:
        """Execute accepted command. Engine persists its own event."""
        ...


# ══════════════════════════════════════════════════════════════
# PERSIST FUNCTION PROTOCOL
# ══════════════════════════════════════════════════════════════

class PersistEventProtocol(Protocol):
    """
    Protocol for event persistence function.

    Matches signature of persist_event() or enforced_persist_event().
    Injected into CommandBus — no direct import of Django code.
    """

    def __call__(
        self,
        event_data: dict,
        context: Any,
        registry: Any,
        **kwargs: Any,
    ) -> Any:
        ...


# ══════════════════════════════════════════════════════════════
# COMMAND BUS ERRORS
# ══════════════════════════════════════════════════════════════

class CommandBusError(Exception):
    """Base error for command bus operations."""
    pass


class NoHandlerRegistered(CommandBusError):
    """No engine service handler registered for command type."""

    def __init__(self, command_type: str):
        self.command_type = command_type
        super().__init__(
            f"No engine service handler registered for "
            f"command type '{command_type}'."
        )


# ══════════════════════════════════════════════════════════════
# COMMAND BUS RESULT
# ══════════════════════════════════════════════════════════════

class CommandResult:
    """
    Result of CommandBus.handle() — wraps outcome + execution result.
    """

    def __init__(
        self,
        outcome: CommandOutcome,
        execution_result: Any = None,
        rejection_event_persisted: bool = False,
    ):
        self.outcome = outcome
        self.execution_result = execution_result
        self.rejection_event_persisted = rejection_event_persisted

    @property
    def is_accepted(self) -> bool:
        return self.outcome.is_accepted

    @property
    def is_rejected(self) -> bool:
        return self.outcome.is_rejected


# ══════════════════════════════════════════════════════════════
# COMMAND BUS
# ══════════════════════════════════════════════════════════════

class CommandBus:
    """
    Orchestration layer for command lifecycle.

    Usage:
        bus = CommandBus(
            dispatcher=dispatcher,
            persist_event=persist_event_fn,
            context=business_context,
            event_type_registry=registry,
        )

        # Register engine handler
        bus.register_handler(
            "inventory.stock.move.request",
            inventory_service,
        )

        # Handle command
        result = bus.handle(command)
    """

    def __init__(
        self,
        dispatcher: CommandDispatcher,
        persist_event: PersistEventProtocol,
        context: Any,
        event_type_registry: Any,
    ):
        self._dispatcher = dispatcher
        self._persist_event = persist_event
        self._context = context
        self._event_type_registry = event_type_registry
        self._handlers: Dict[str, Any] = {}

    # ══════════════════════════════════════════════════════════
    # HANDLER REGISTRATION
    # ══════════════════════════════════════════════════════════

    def register_handler(
        self,
        command_type: str,
        handler: Any,
    ) -> None:
        """
        Register engine service handler for a command type.

        Handler must implement EngineServiceProtocol (have .execute()).
        """
        if not command_type.endswith(".request"):
            raise ValueError(
                f"command_type '{command_type}' must end with '.request'."
            )

        if not hasattr(handler, "execute") or not callable(handler.execute):
            raise TypeError(
                f"Handler must have callable .execute() method."
            )

        self._handlers[command_type] = handler
        logger.info(f"Handler registered: {command_type}")

    # ══════════════════════════════════════════════════════════
    # HANDLE (main orchestration)
    # ══════════════════════════════════════════════════════════

    def handle(self, command: Command) -> CommandResult:
        """
        Full command lifecycle:

        1. Dispatch → get Outcome (ACCEPTED/REJECTED)
        2. ACCEPTED → verify handler exists → execute
        3. REJECTED → build rejection event → persist

        No silent paths. Every command produces a traceable result.

        Args:
            command: Command to process.

        Returns:
            CommandResult with outcome + execution details.
        """

        # ── Step 1: Dispatch (validate + policies) ────────────
        outcome = self._dispatcher.dispatch(command)

        # ── Step 2: Route based on outcome ────────────────────
        if outcome.is_accepted:
            return self._handle_accepted(command, outcome)
        else:
            return self._handle_rejected(command, outcome)

    # ══════════════════════════════════════════════════════════
    # ACCEPTED PATH
    # ══════════════════════════════════════════════════════════

    def _handle_accepted(
        self, command: Command, outcome: CommandOutcome
    ) -> CommandResult:
        """
        Execute accepted command via engine service handler.

        The handler is responsible for persisting its own event.
        CommandBus just calls handler.execute() and returns result.
        """
        handler = self._handlers.get(command.command_type)
        if handler is None:
            raise NoHandlerRegistered(command.command_type)

        logger.info(
            f"Executing accepted command {command.command_id} "
            f"({command.command_type})"
        )

        execution_result = handler.execute(command)

        return CommandResult(
            outcome=outcome,
            execution_result=execution_result,
        )

    # ══════════════════════════════════════════════════════════
    # REJECTED PATH
    # ══════════════════════════════════════════════════════════

    def _handle_rejected(
        self, command: Command, outcome: CommandOutcome
    ) -> CommandResult:
        """
        Persist rejection event for rejected command.

        Rejection events are first-class citizens.
        They use the standard persist_event() path.

        Event type derivation:
            inventory.stock.move.request → inventory.stock.move.rejected
        """
        rejection_event_type = derive_rejection_event_type(
            command.command_type
        )
        self._ensure_rejection_event_type_registered(rejection_event_type)

        rejection_event_data = {
            "event_id": uuid.uuid4(),
            "event_type": rejection_event_type,
            "event_version": 1,
            "business_id": command.business_id,
            "branch_id": command.branch_id,
            "source_engine": command.source_engine,
            "actor_type": command.actor_type,
            "actor_id": command.actor_id,
            "correlation_id": command.correlation_id,
            "causation_id": None,
            "payload": {
                "command_id": str(command.command_id),
                "command_type": command.command_type,
                "rejection": outcome.reason.to_dict(),
                "original_payload": command.payload,
            },
            "reference": {},
            "created_at": outcome.occurred_at,
            "status": "FINAL",
            "correction_of": None,
        }

        logger.info(
            f"Persisting rejection event for command "
            f"{command.command_id}: {rejection_event_type} "
            f"(reason: {outcome.reason.code})"
        )

        persist_result = self._persist_event(
            event_data=rejection_event_data,
            context=self._context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )
        rejection_event_persisted = self._is_persist_accepted(persist_result)

        return CommandResult(
            outcome=outcome,
            rejection_event_persisted=rejection_event_persisted,
        )

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _ensure_rejection_event_type_registered(self, event_type: str) -> None:
        registry = self._event_type_registry
        if registry is None:
            return

        has_is_registered = hasattr(registry, "is_registered") and callable(
            getattr(registry, "is_registered")
        )
        has_register = hasattr(registry, "register") and callable(
            getattr(registry, "register")
        )
        if not has_is_registered or not has_register:
            return

        if not registry.is_registered(event_type):
            registry.register(event_type)
