"""
BOS Actor Primitive — Reusable Identity Building Block
=======================================================
Phase 4: Business Primitive Layer
Authority: BOS Core Technical Appendix — Mandatory Event Schema

The Actor Primitive captures WHO performed an action.
Every event in BOS has an actor field using this primitive.

Actor types:
    HUMAN   — A real human user (branch cashier, manager, owner)
    SYSTEM  — Automated system action (scheduled job, migration)
    DEVICE  — Hardware device (POS terminal, barcode scanner, biometric reader)
    AI      — AI advisory output (NEVER commits state — advisory only)

RULES (NON-NEGOTIABLE):
- Every event MUST identify its actor
- AI actors CANNOT be used on state-changing commands (only advisory logs)
- Device actors MUST include a device_id
- Human actors MUST include a user_id
- System actors MUST include a system_component name
- Multi-tenant: actor is scoped to business_id

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ActorType(Enum):
    """The type of entity that performed an action."""
    HUMAN = "Human"
    SYSTEM = "System"
    DEVICE = "Device"
    AI = "AI"


# ══════════════════════════════════════════════════════════════
# ACTOR DEFINITION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Actor:
    """
    Identifies who performed an action in BOS.

    This is embedded in every event payload as the actor field.

    Fields:
        actor_type:     HUMAN | SYSTEM | DEVICE | AI
        actor_id:       User/device/component identifier
        display_name:   Human-readable name for audit display
        business_id:    Tenant scope of this actor
        branch_id:      Branch scope (optional — AI/System may be business-scoped)
        source:         Optional extra context (e.g. "POS Terminal #3", "CRON Job")
    """
    actor_type: ActorType
    actor_id: str
    display_name: str
    business_id: uuid.UUID

    branch_id: Optional[uuid.UUID] = None
    source: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.actor_type, ActorType):
            raise ValueError("actor_type must be ActorType enum.")
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")
        if not self.display_name or not isinstance(self.display_name, str):
            raise ValueError("display_name must be a non-empty string.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

    @property
    def is_ai(self) -> bool:
        return self.actor_type == ActorType.AI

    @property
    def is_human(self) -> bool:
        return self.actor_type == ActorType.HUMAN

    @property
    def is_system(self) -> bool:
        return self.actor_type == ActorType.SYSTEM

    @property
    def is_device(self) -> bool:
        return self.actor_type == ActorType.DEVICE

    def to_dict(self) -> dict:
        return {
            "actor_type": self.actor_type.value,
            "actor_id": self.actor_id,
            "display_name": self.display_name,
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Actor:
        return cls(
            actor_type=ActorType(data["actor_type"]),
            actor_id=data["actor_id"],
            display_name=data["display_name"],
            business_id=uuid.UUID(data["business_id"]),
            branch_id=uuid.UUID(data["branch_id"]) if data.get("branch_id") else None,
            source=data.get("source"),
        )

    @classmethod
    def human(
        cls,
        user_id: str,
        display_name: str,
        business_id: uuid.UUID,
        branch_id: Optional[uuid.UUID] = None,
    ) -> Actor:
        """Factory for human actors."""
        return cls(
            actor_type=ActorType.HUMAN,
            actor_id=user_id,
            display_name=display_name,
            business_id=business_id,
            branch_id=branch_id,
        )

    @classmethod
    def system(
        cls,
        component: str,
        business_id: uuid.UUID,
    ) -> Actor:
        """Factory for system actors (automated jobs, migrations)."""
        return cls(
            actor_type=ActorType.SYSTEM,
            actor_id=f"system:{component}",
            display_name=f"System ({component})",
            business_id=business_id,
            source=component,
        )

    @classmethod
    def device(
        cls,
        device_id: str,
        device_name: str,
        business_id: uuid.UUID,
        branch_id: Optional[uuid.UUID] = None,
    ) -> Actor:
        """Factory for device actors (POS terminals, scanners)."""
        return cls(
            actor_type=ActorType.DEVICE,
            actor_id=device_id,
            display_name=device_name,
            business_id=business_id,
            branch_id=branch_id,
        )

    @classmethod
    def ai(
        cls,
        model_id: str,
        business_id: uuid.UUID,
    ) -> Actor:
        """
        Factory for AI actors.
        AI actors may only appear in advisory/journal events.
        NEVER use on state-changing commands.
        """
        return cls(
            actor_type=ActorType.AI,
            actor_id=f"ai:{model_id}",
            display_name=f"AI Advisory ({model_id})",
            business_id=business_id,
            source=model_id,
        )
