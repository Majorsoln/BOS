"""
BOS Policy Engine — Versioning
=================================
Policy versions are explicit, immutable, and stored in event payloads.

Replay must use the same policy version as the original evaluation.
No retroactive reinterpretation.

A PolicyVersion is a frozen snapshot identifier that maps to a specific
set of rules at a specific point in time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PolicyVersion:
    """
    Immutable policy version identifier.

    Fields:
        version_id:  Unique version string (e.g. '2026.02.13-001').
        created_at:  When this version was defined.
        description: Human-readable description.

    Convention:
        version_id should be monotonically increasing.
        Format: YYYY.MM.DD-NNN or semver (e.g. '1.0.0').
    """

    version_id: str
    created_at: datetime
    description: str = ""

    def __post_init__(self):
        if not self.version_id or not isinstance(self.version_id, str):
            raise ValueError("version_id must be a non-empty string.")

        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime.")


# ══════════════════════════════════════════════════════════════
# DEFAULT VERSION (for development / testing)
# ══════════════════════════════════════════════════════════════

INITIAL_POLICY_VERSION = "1.0.0"
