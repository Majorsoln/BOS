"""
BOS Replay â€” Scope Enum
=========================
Replay scope must be explicit for unscoped operations.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from core.replay.errors import ReplayError


class ReplayScope(str, Enum):
    BUSINESS = "BUSINESS"
    UNSCOPED = "UNSCOPED"


def validate_replay_scope(
    business_id: Optional[uuid.UUID],
    replay_scope: ReplayScope,
) -> ReplayScope:
    """
    Enforce replay scope intent.

    Default replay is business-scoped and requires business_id.
    Unscoped replay requires explicit ReplayScope.UNSCOPED.
    """
    try:
        scope = ReplayScope(replay_scope)
    except ValueError as exc:
        raise ReplayError(
            f"Invalid replay_scope '{replay_scope}'."
        ) from exc

    if scope == ReplayScope.BUSINESS:
        if business_id is None:
            raise ReplayError(
                "business_id is required unless "
                "replay_scope=ReplayScope.UNSCOPED."
            )
        return scope

    if business_id is not None:
        raise ReplayError(
            "business_id must be None when replay_scope=ReplayScope.UNSCOPED."
        )
    return scope
