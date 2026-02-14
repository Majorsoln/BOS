"""
BOS Command Layer â€” Command Base Contract
============================================
Every action in BOS begins as a Command.

A Command is a frozen, auditable declaration of business intent.
It carries identity, context, and payload â€” nothing else.

Rules:
- Immutable once created (frozen dataclass)
- No business logic inside
- No DB interaction
- No event emission
- command_type must end with '.request'
- command_type follows engine.domain.action.request format

A Command is NOT an event. It is intent awaiting judgment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.context.actor_context import ActorContext
from core.context.scope import (
    SCOPE_BUSINESS_ALLOWED,
    VALID_SCOPE_REQUIREMENTS,
)
from core.identity.requirements import (
    ACTOR_REQUIRED,
    VALID_ACTOR_REQUIREMENTS,
)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ACTOR TYPES (mirrors Event Store ActorType, no Django import)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

VALID_ACTOR_TYPES = frozenset({"HUMAN", "SYSTEM", "DEVICE", "AI"})


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CANONICAL COMMAND
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass(frozen=True)
class Command:
    """
    Canonical BOS Command â€” declaration of business intent.

    Fields:
        command_id:     Unique identifier (UUID).
        command_type:   Namespaced type ending in '.request'
                        (e.g. 'inventory.stock.move.request').
        business_id:    Tenant boundary (UUID).
        branch_id:      Branch scope (nullable UUID).
        scope_requirement:
                        Scope requirement declaration for this command.
        actor_requirement:
                        Actor requirement declaration for this command.
        actor_context:  Optional resolved actor identity context.
        actor_type:     HUMAN | SYSTEM | DEVICE | AI.
        actor_id:       Identity of the actor.
        payload:        Business intent data (dict).
        issued_at:      When the command was issued.
        correlation_id: Groups related commands/events in a story.
        source_engine:  Engine that originates this command.

    Example:
        Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=uuid.UUID("..."),
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-123",
            payload={"sku": "ABC", "quantity": 10},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )
    """

    command_id: uuid.UUID
    command_type: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    actor_type: str
    actor_id: str
    payload: dict
    issued_at: datetime
    correlation_id: uuid.UUID
    source_engine: str
    scope_requirement: str = SCOPE_BUSINESS_ALLOWED
    actor_requirement: str = ACTOR_REQUIRED
    actor_context: Optional[ActorContext] = None

    def __post_init__(self):
        # â”€â”€ command_id must be UUID â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not isinstance(self.command_id, uuid.UUID):
            raise ValueError(
                f"command_id must be UUID, got {type(self.command_id).__name__}"
            )

        # â”€â”€ command_type must end with .request â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not self.command_type or not isinstance(self.command_type, str):
            raise ValueError("command_type must be a non-empty string.")

        if not self.command_type.endswith(".request"):
            raise ValueError(
                f"command_type '{self.command_type}' must end with "
                f"'.request' (e.g. 'inventory.stock.move.request')."
            )

        # â”€â”€ command_type minimum 4 segments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        parts = self.command_type.split(".")
        if len(parts) < 4:
            raise ValueError(
                f"command_type '{self.command_type}' must follow "
                f"engine.domain.action.request format (minimum 4 segments)."
            )

        # â”€â”€ source_engine must match first segment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if parts[0] != self.source_engine:
            raise ValueError(
                f"command_type namespace '{parts[0]}' does not match "
                f"source_engine '{self.source_engine}'."
            )

        # â”€â”€ business_id must be UUID â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        # â”€â”€ scope requirement must be valid â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if self.scope_requirement not in VALID_SCOPE_REQUIREMENTS:
            raise ValueError(
                f"scope_requirement '{self.scope_requirement}' not valid. "
                f"Must be one of: {sorted(VALID_SCOPE_REQUIREMENTS)}"
            )

        # Ã¢â€â‚¬Ã¢â€â‚¬ actor requirement must be valid Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        if self.actor_requirement not in VALID_ACTOR_REQUIREMENTS:
            raise ValueError(
                f"actor_requirement '{self.actor_requirement}' not valid. "
                f"Must be one of: {sorted(VALID_ACTOR_REQUIREMENTS)}"
            )

        # Ã¢â€â‚¬Ã¢â€â‚¬ actor_context shape (if provided) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

        # â”€â”€ actor_type must be valid â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if self.actor_type not in VALID_ACTOR_TYPES:
            raise ValueError(
                f"actor_type '{self.actor_type}' not valid. "
                f"Must be one of: {sorted(VALID_ACTOR_TYPES)}"
            )

        # â”€â”€ actor_id must be non-empty â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")

        # â”€â”€ payload must be dict â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict.")

        # â”€â”€ correlation_id must be UUID â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not isinstance(self.correlation_id, uuid.UUID):
            raise ValueError("correlation_id must be UUID.")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EVENT NAMING LAW (derivation helpers)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def derive_rejection_event_type(command_type: str) -> str:
    """
    Derive rejected event type from command type.

    inventory.stock.move.request â†’ inventory.stock.move.rejected

    Rule: Strip '.request', append '.rejected'.
    """
    if not command_type.endswith(".request"):
        raise ValueError(
            f"Cannot derive rejection event type from "
            f"'{command_type}' â€” must end with '.request'."
        )

    base = command_type[: -len(".request")]
    return f"{base}.rejected"


def derive_source_engine(command_type: str) -> str:
    """
    Extract source engine from command type.

    inventory.stock.move.request â†’ inventory
    """
    return command_type.split(".")[0]

