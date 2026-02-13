"""
BOS Core Context — BusinessContext
==================================
Immutable tenant scope used across command, policy, and event boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class BusinessContext:
    """
    Immutable execution scope for a single tenant boundary.

    branch_id is optional (business-wide scope).
    allowed_branch_ids represents known branches under this business.
    """

    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID] = None
    lifecycle_state: str = "ACTIVE"
    allowed_branch_ids: FrozenSet[uuid.UUID] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")

        if self.branch_id is not None and self.allowed_branch_ids:
            if self.branch_id not in self.allowed_branch_ids:
                raise ValueError(
                    "branch_id must be included in allowed_branch_ids when provided."
                )

    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self) -> uuid.UUID:
        return self.business_id

    def get_active_branch_id(self) -> Optional[uuid.UUID]:
        return self.branch_id

    def is_branch_in_business(self, branch_id: uuid.UUID, business_id: uuid.UUID) -> bool:
        if business_id != self.business_id:
            return False

        if self.allowed_branch_ids:
            return branch_id in self.allowed_branch_ids

        if self.branch_id is None:
            return True

        return branch_id == self.branch_id

    def get_business_lifecycle_state(self) -> str:
        return self.lifecycle_state

    @property
    def scope_label(self) -> str:
        if self.branch_id is None:
            return f"{self.business_id}:*"
        return f"{self.business_id}:{self.branch_id}"
