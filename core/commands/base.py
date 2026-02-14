"""
BOS Command Layer — Command Base Contract
============================================
Every action in BOS begins as a Command.

A Command is a frozen, auditable declaration of business intent.
It carries identity, context, and payload — nothing else.

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

from core.context.scope import (
    SCOPE_BUSINESS_ALLOWED,
    VALID_SCOPE_REQUIREMENTS,
)


# ══════════════════════════════════════════════════════════════
# ACTOR TYPES (mirrors Event Store ActorType, no Django import)
# ══════════════════════════════════════════════════════════════

VALID_ACTOR_TYPES = frozenset({"HUMAN", "SYSTEM", "DEVICE", "AI"})


# ══════════════════════════════════════════════════════════════
# CANONICAL COMMAND
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Command:
    """
    Canonical BOS Command — declaration of business intent.

    Fields:
        command_id:     Unique identifier (UUID).
        command_type:   Namespaced type ending in '.request'
                        (e.g. 'inventory.stock.move.request').
        business_id:    Tenant boundary (UUID).
        branch_id:      Branch scope (nullable UUID).
        scope_requirement:
                        Scope requirement declaration for this command.
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

    def __post_init__(self):
        # ── command_id must be UUID ───────────────────────────
        if not isinstance(self.command_id, uuid.UUID):
            raise ValueError(
                f"command_id must be UUID, got {type(self.command_id).__name__}"
            )

        # ── command_type must end with .request ───────────────
        if not self.command_type or not isinstance(self.command_type, str):
            raise ValueError("command_type must be a non-empty string.")

        if not self.command_type.endswith(".request"):
            raise ValueError(
                f"command_type '{self.command_type}' must end with "
                f"'.request' (e.g. 'inventory.stock.move.request')."
            )

        # ── command_type minimum 4 segments ───────────────────
        parts = self.command_type.split(".")
        if len(parts) < 4:
            raise ValueError(
                f"command_type '{self.command_type}' must follow "
                f"engine.domain.action.request format (minimum 4 segments)."
            )

        # ── source_engine must match first segment ────────────
        if parts[0] != self.source_engine:
            raise ValueError(
                f"command_type namespace '{parts[0]}' does not match "
                f"source_engine '{self.source_engine}'."
            )

        # ── business_id must be UUID ──────────────────────────
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        # ── scope requirement must be valid ───────────────────
        if self.scope_requirement not in VALID_SCOPE_REQUIREMENTS:
            raise ValueError(
                f"scope_requirement '{self.scope_requirement}' not valid. "
                f"Must be one of: {sorted(VALID_SCOPE_REQUIREMENTS)}"
            )

        # ── actor_type must be valid ──────────────────────────
        if self.actor_type not in VALID_ACTOR_TYPES:
            raise ValueError(
                f"actor_type '{self.actor_type}' not valid. "
                f"Must be one of: {sorted(VALID_ACTOR_TYPES)}"
            )

        # ── actor_id must be non-empty ────────────────────────
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")

        # ── payload must be dict ──────────────────────────────
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict.")

        # ── correlation_id must be UUID ───────────────────────
        if not isinstance(self.correlation_id, uuid.UUID):
            raise ValueError("correlation_id must be UUID.")


# ══════════════════════════════════════════════════════════════
# EVENT NAMING LAW (derivation helpers)
# ══════════════════════════════════════════════════════════════

def derive_rejection_event_type(command_type: str) -> str:
    """
    Derive rejected event type from command type.

    inventory.stock.move.request → inventory.stock.move.rejected

    Rule: Strip '.request', append '.rejected'.
    """
    if not command_type.endswith(".request"):
        raise ValueError(
            f"Cannot derive rejection event type from "
            f"'{command_type}' — must end with '.request'."
        )

    base = command_type[: -len(".request")]
    return f"{base}.rejected"


def derive_source_engine(command_type: str) -> str:
    """
    Extract source engine from command type.

    inventory.stock.move.request → inventory
    """
    return command_type.split(".")[0]
