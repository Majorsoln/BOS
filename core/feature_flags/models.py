"""
BOS Feature Flags - Immutable Models
====================================
Deterministic, additive feature flag primitives.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


FEATURE_ENABLED = "ENABLED"
FEATURE_DISABLED = "DISABLED"
ROLLOUT_STATIC = "STATIC"

VALID_FEATURE_STATUSES = frozenset({FEATURE_ENABLED, FEATURE_DISABLED})
VALID_ROLLOUT_TYPES = frozenset({ROLLOUT_STATIC})


@dataclass(frozen=True)
class FeatureFlag:
    flag_key: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID] = None
    status: str = FEATURE_DISABLED
    rollout_type: str = ROLLOUT_STATIC
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")

        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        if self.branch_id is not None and not isinstance(
            self.branch_id, uuid.UUID
        ):
            raise ValueError("branch_id must be UUID or None.")

        if self.status not in VALID_FEATURE_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_FEATURE_STATUSES)}"
            )

        if self.rollout_type not in VALID_ROLLOUT_TYPES:
            raise ValueError(
                f"rollout_type '{self.rollout_type}' not valid. "
                f"Must be one of: {sorted(VALID_ROLLOUT_TYPES)}"
            )

    def scope_key(self) -> tuple[str, uuid.UUID, Optional[uuid.UUID]]:
        return (self.flag_key, self.business_id, self.branch_id)

    def sort_key(self) -> tuple[str, str, str]:
        return (
            self.flag_key,
            str(self.business_id),
            "" if self.branch_id is None else str(self.branch_id),
        )

