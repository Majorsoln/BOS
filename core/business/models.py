"""
BOS Core Business — Business & Branch Lifecycle Models
========================================================
Canonical business entity and branch models.
These are the foundation for multi-tenant scoping.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════
# BUSINESS LIFECYCLE STATE
# ══════════════════════════════════════════════════════════════

class BusinessState(Enum):
    """Business lifecycle states."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


# ══════════════════════════════════════════════════════════════
# BUSINESS ENTITY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Business:
    """
    Canonical business entity (tenant).

    Every command, event, and projection is scoped to a business_id.
    """

    business_id: uuid.UUID
    name: str
    state: BusinessState
    country_code: str
    timezone: str
    created_at: datetime
    closed_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.state == BusinessState.ACTIVE

    def is_operational(self) -> bool:
        """Business can accept commands (ACTIVE or CREATED during setup)."""
        return self.state in (BusinessState.ACTIVE, BusinessState.CREATED)


# ══════════════════════════════════════════════════════════════
# BRANCH ENTITY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Branch:
    """
    Physical or logical branch location within a business.

    Commands with SCOPE_BRANCH_REQUIRED must target a valid, open branch.
    """

    branch_id: uuid.UUID
    business_id: uuid.UUID
    name: str
    created_at: datetime
    location: Optional[str] = None
    closed_at: Optional[datetime] = None

    def is_open(self) -> bool:
        return self.closed_at is None

    def belongs_to(self, business_id: uuid.UUID) -> bool:
        return self.business_id == business_id
