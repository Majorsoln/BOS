"""
BOS Replay Engine — Projection Rebuilder
==========================================
Orchestrates full projection rebuilds.

Rebuild flow:
    1. Clear checkpoint for projection
    2. Truncate projection table
    3. Replay events through bus
    4. Subscribers rebuild state
    5. Save final checkpoint

Rules:
- Projections are disposable — they can be rebuilt from events
- Rebuild MUST use the same bus path as live dispatch
- Rebuild MUST NOT touch other businesses (when scoped)
- Rebuild MUST NOT create new events

This module defines ProjectionProtocol — the interface
that projections must implement to support rebuild.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from core.events.registry import SubscriberRegistry
from core.replay.checkpoints import clear_checkpoint
from core.replay.event_replayer import ReplayResult, replay_events
from core.replay.scope import ReplayScope

logger = logging.getLogger("bos.replay")


# ══════════════════════════════════════════════════════════════
# PROJECTION PROTOCOL
# ══════════════════════════════════════════════════════════════

@runtime_checkable
class ProjectionProtocol(Protocol):
    """
    Interface that projections must implement for rebuild support.

    projection_name: Unique identifier (used for checkpoints).
    truncate():      Clear projection data (scoped by business if given).
    """

    @property
    def projection_name(self) -> str: ...

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        """
        Clear projection data.
        If business_id provided, clear only that business scope.
        If None, clear all data for this projection.
        """
        ...


# ══════════════════════════════════════════════════════════════
# REBUILD RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class RebuildResult:
    """Structured result of a projection rebuild."""

    projection_name: str
    truncated: bool = False
    replay: ReplayResult = None

    @property
    def success(self) -> bool:
        return (
            self.truncated
            and self.replay is not None
            and self.replay.success
        )


# ══════════════════════════════════════════════════════════════
# PROJECTION REBUILD
# ══════════════════════════════════════════════════════════════

def rebuild_projection(
    projection: ProjectionProtocol,
    subscriber_registry: SubscriberRegistry,
    business_id: Optional[uuid.UUID] = None,
    until: Optional[datetime] = None,
    dry_run: bool = False,
) -> RebuildResult:
    """
    Full projection rebuild: truncate → replay → checkpoint.

    Args:
        projection:          Projection implementing ProjectionProtocol.
        subscriber_registry: Bus registry with handlers for this projection.
        business_id:         Scope rebuild to single business (optional).
        until:               Replay events up to this timestamp (optional).
        dry_run:             Verify and count only, no truncation or dispatch.

    Returns:
        RebuildResult with truncation and replay status.
    """
    result = RebuildResult(projection_name=projection.projection_name)

    logger.info(
        f"Projection rebuild starting: {projection.projection_name} "
        f"(business={business_id or 'ALL'}, dry_run={dry_run})"
    )

    # ── Step 1: Clear existing checkpoint ─────────────────────
    if not dry_run:
        clear_checkpoint(
            projection_name=projection.projection_name,
            business_id=business_id,
        )

    # ── Step 2: Truncate projection ───────────────────────────
    if not dry_run:
        projection.truncate(business_id=business_id)
        result.truncated = True
        logger.info(
            f"Projection truncated: {projection.projection_name}"
        )
    else:
        result.truncated = True  # Would have truncated

    # ── Step 3: Replay events ─────────────────────────────────
    replay_result = replay_events(
        subscriber_registry=subscriber_registry,
        business_id=business_id,
        replay_scope=(
            ReplayScope.UNSCOPED
            if business_id is None
            else ReplayScope.BUSINESS
        ),
        until=until,
        projection_name=projection.projection_name,
        use_checkpoint=False,  # Full rebuild — start from beginning
        dry_run=dry_run,
    )
    result.replay = replay_result

    logger.info(
        f"Projection rebuild complete: {projection.projection_name} — "
        f"{'SUCCESS' if result.success else 'FAILED'}"
    )

    return result
