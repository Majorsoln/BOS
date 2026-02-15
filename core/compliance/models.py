"""
BOS Compliance - Immutable Profile Models
=========================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


PROFILE_ACTIVE = "ACTIVE"
PROFILE_INACTIVE = "INACTIVE"

VALID_PROFILE_STATUSES = frozenset({PROFILE_ACTIVE, PROFILE_INACTIVE})


@dataclass(frozen=True)
class ComplianceProfile:
    profile_id: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    status: str
    version: int
    ruleset: tuple
    updated_by_actor_id: Optional[str] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.profile_id or not isinstance(self.profile_id, str):
            raise ValueError("profile_id must be a non-empty string.")

        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        if self.branch_id is not None and not isinstance(
            self.branch_id, uuid.UUID
        ):
            raise ValueError("branch_id must be UUID or None.")

        if self.status not in VALID_PROFILE_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_PROFILE_STATUSES)}"
            )

        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be int >= 1.")

        if not isinstance(self.ruleset, tuple):
            raise ValueError("ruleset must be a tuple.")

        if self.updated_by_actor_id is not None and (
            not isinstance(self.updated_by_actor_id, str)
            or not self.updated_by_actor_id
        ):
            raise ValueError(
                "updated_by_actor_id must be non-empty string or None."
            )

        if self.updated_at is not None and not isinstance(
            self.updated_at, datetime
        ):
            raise ValueError("updated_at must be datetime or None.")

    def scope_key(self) -> tuple[uuid.UUID, Optional[uuid.UUID], int]:
        return (self.business_id, self.branch_id, self.version)

    def sort_key(self) -> tuple[str, str, str, int]:
        return (
            str(self.business_id),
            "" if self.branch_id is None else str(self.branch_id),
            self.profile_id,
            self.version,
        )

