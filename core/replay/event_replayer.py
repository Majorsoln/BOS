"""
BOS Replay Engine â€” Event Replayer
=====================================
Reads historical events and replays them through the Event Bus.

Replay doctrine:
- READ events only â€” never write to Event Store
- Never modify events
- Deterministic order: received_at ASC
- Verify hash-chain before replay
- Support full, business-scoped, and time-scoped modes
- Support checkpoint resume
- Dispatch through bus (same path as live events)
- Block persistence during replay (isolation)

Event Store = truth archive
Replay Engine = time machine
Time machine must never change history.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from django.db.models import QuerySet, Q

from core.event_store.models import Event
from core.event_store.hashing import GENESIS_HASH, compute_event_hash
from core.events.dispatcher import dispatch as bus_dispatch
from core.events.registry import SubscriberRegistry
from core.replay.checkpoints import (
    load_checkpoint,
    save_checkpoint,
    clear_checkpoint,
)
from core.replay.context import ReplayContext, is_replay_active
from core.replay.errors import ReplayChainBrokenError
from core.replay.scope import ReplayScope, validate_replay_scope

logger = logging.getLogger("bos.replay")


# ReplayContext and is_replay_active are imported from core.replay.context


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# REPLAY RESULT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class ReplayResult:
    """Structured result of a replay operation."""

    events_processed: int = 0
    events_dispatched: int = 0
    dispatch_failures: int = 0
    chain_verified: bool = False
    checkpoint_saved: bool = False
    dry_run: bool = False
    errors: list[dict] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.chain_verified and self.dispatch_failures == 0


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EVENT QUERY BUILDER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _build_event_queryset(
    business_id: Optional[uuid.UUID] = None,
    until: Optional[datetime] = None,
    after_received_at: Optional[datetime] = None,
    after_event_id: Optional[uuid.UUID] = None,
) -> QuerySet:
    """
    Build deterministic event queryset.
    Always ordered by received_at ASC, event_id ASC (composite cursor).

    Resume uses composite cursor to prevent skipping same-timestamp events:
        (received_at > last) OR (received_at == last AND event_id > last_id)
    """
    qs = Event.objects.all()

    if business_id is not None:
        qs = qs.filter(business_id=business_id)

    if until is not None:
        qs = qs.filter(received_at__lte=until)

    if after_received_at is not None and after_event_id is not None:
        # Composite cursor: skip past checkpoint precisely
        qs = qs.filter(
            Q(received_at__gt=after_received_at)
            | Q(received_at=after_received_at, event_id__gt=after_event_id)
        )
    elif after_received_at is not None:
        # Fallback: timestamp only (backward compat)
        qs = qs.filter(received_at__gt=after_received_at)

    return qs.order_by("received_at", "event_id")



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CHAIN VERIFICATION (PRE-REPLAY)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def verify_chain_before_replay(
    business_id: Optional[uuid.UUID] = None,
) -> bool:
    """
    Lightweight chain verification before replay starts.
    Checks structural integrity â€” not full hash recomputation.

    Verifies:
    - No empty event_hash
    - No empty previous_event_hash
    - GENESIS used correctly for first event per business

    Raises ReplayChainBrokenError if corruption detected.
    Returns True if chain is structurally sound.
    """
    if business_id is not None:
        businesses = [business_id]
    else:
        businesses = (
            Event.objects
            .values_list("business_id", flat=True)
            .distinct()
        )

    for biz_id in businesses:
        events = (
            Event.objects
            .filter(business_id=biz_id)
            .order_by("received_at")
        )

        if not events.exists():
            continue

        # Check first event has GENESIS
        first_event = events.first()
        if first_event.previous_event_hash != GENESIS_HASH:
            raise ReplayChainBrokenError(
                business_id=biz_id,
                detail=(
                    f"First event {first_event.event_id} has "
                    f"previous_event_hash='{first_event.previous_event_hash}'"
                    f" instead of '{GENESIS_HASH}'."
                ),
            )

        # Check no empty hashes
        empty_hash = events.filter(event_hash="").count()
        if empty_hash > 0:
            raise ReplayChainBrokenError(
                business_id=biz_id,
                detail=f"{empty_hash} event(s) with empty event_hash.",
            )

        empty_prev = events.filter(previous_event_hash="").count()
        if empty_prev > 0:
            raise ReplayChainBrokenError(
                business_id=biz_id,
                detail=(
                    f"{empty_prev} event(s) with empty "
                    f"previous_event_hash."
                ),
            )

    logger.info("Hash-chain verification passed.")
    return True


def _verify_full_hash_chain(
    business_id: Optional[uuid.UUID] = None,
) -> bool:
    """
    Full hash recomputation â€” verifies every event's hash by recomputing.

    For each event:
    - Recompute: compute_event_hash(payload, previous_event_hash)
    - Compare with stored event_hash
    - If mismatch â†’ raise ReplayIntegrityError

    This is expensive. Use only when tamper detection is needed.
    """
    from core.replay.errors import ReplayIntegrityError

    if business_id is not None:
        businesses = [business_id]
    else:
        businesses = list(
            Event.objects
            .values_list("business_id", flat=True)
            .distinct()
        )

    for biz_id in businesses:
        events = (
            Event.objects
            .filter(business_id=biz_id)
            .order_by("received_at", "event_id")
        )

        for event in events.iterator(chunk_size=500):
            recomputed = compute_event_hash(
                event.payload,
                event.previous_event_hash,
            )
            if recomputed != event.event_hash:
                raise ReplayIntegrityError(
                    event_id=event.event_id,
                    expected_hash=event.event_hash,
                    actual_hash=recomputed,
                )

    logger.info("Full hash recomputation passed â€” no tampering detected.")
    return True


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CORE REPLAY FUNCTION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def replay_events(
    subscriber_registry: SubscriberRegistry,
    business_id: Optional[uuid.UUID] = None,
    replay_scope: ReplayScope = ReplayScope.BUSINESS,
    until: Optional[datetime] = None,
    projection_name: Optional[str] = None,
    use_checkpoint: bool = False,
    dry_run: bool = False,
    full_hash_verify: bool = False,
    batch_size: int = 500,
) -> ReplayResult:
    """
    Replay historical events through the Event Bus.

    This is the core replay function. It:
    1. Verifies hash-chain integrity (structural or full recompute)
    2. Builds event queryset (scoped by business/time)
    3. Optionally resumes from checkpoint (composite cursor)
    4. Dispatches each event through the bus
    5. Saves checkpoint progress
    6. Returns structured result

    Args:
        subscriber_registry: Bus registry with handlers for replay.
        business_id:         Business scope identifier.
        replay_scope:        BUSINESS (default) or explicit UNSCOPED.
        until:               Replay events up to this timestamp (optional).
        projection_name:     Name for checkpoint tracking (optional).
        use_checkpoint:      Resume from last checkpoint if available.
        dry_run:             Verify chain and count events, skip dispatch.
        full_hash_verify:    Recompute ALL hashes before replay (optional).
        batch_size:          Events per batch for memory efficiency.

    Returns:
        ReplayResult with counts and status.

    Raises:
        ReplayChainBrokenError: If structural integrity check fails.
        ReplayIntegrityError:   If full hash recompute detects mismatch.
    """
    result = ReplayResult(dry_run=dry_run)
    resolved_scope = validate_replay_scope(
        business_id=business_id,
        replay_scope=replay_scope,
    )
    scoped_business_id = (
        None if resolved_scope == ReplayScope.UNSCOPED else business_id
    )

    # â”€â”€ Step 1: Verify chain integrity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    verify_chain_before_replay(business_id=scoped_business_id)
    result.chain_verified = True

    # â”€â”€ Step 1b: Optional full hash recompute â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if full_hash_verify:
        _verify_full_hash_chain(business_id=scoped_business_id)
        logger.info("Full hash recomputation verified.")

    # â”€â”€ Step 2: Determine resume point (composite cursor) â”€â”€â”€â”€â”€
    after_received_at = None
    after_event_id = None

    if use_checkpoint and projection_name:
        checkpoint = load_checkpoint(
            projection_name=projection_name,
            business_id=scoped_business_id,
        )
        if checkpoint is not None:
            after_received_at = checkpoint.last_received_at
            after_event_id = checkpoint.last_event_id
            logger.info(
                f"Resuming from checkpoint: {projection_name} "
                f"(after {after_received_at}, event {after_event_id})"
            )

    # â”€â”€ Step 3: Build queryset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    events_qs = _build_event_queryset(
        business_id=scoped_business_id,
        until=until,
        after_received_at=after_received_at,
        after_event_id=after_event_id,
    )

    total = events_qs.count()
    logger.info(
        f"Replay starting: {total} events to process "
        f"(dry_run={dry_run})"
    )

    if dry_run:
        result.events_processed = total
        return result

    # â”€â”€ Step 4: Replay with isolation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    last_event = None

    with ReplayContext():
        for event in events_qs.iterator(chunk_size=batch_size):
            result.events_processed += 1

            try:
                dispatch_result = bus_dispatch(event, subscriber_registry)
                result.events_dispatched += 1

                if dispatch_result["subscribers_failed"] > 0:
                    result.dispatch_failures += dispatch_result[
                        "subscribers_failed"
                    ]
                    result.errors.extend(dispatch_result["failures"])

            except Exception as exc:
                result.dispatch_failures += 1
                result.errors.append({
                    "event_id": str(event.event_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                })
                logger.error(
                    f"Replay dispatch failed for event "
                    f"{event.event_id}: {exc}",
                    exc_info=True,
                )

            last_event = event

    # â”€â”€ Step 5: Save checkpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if last_event is not None and projection_name:
        save_checkpoint(
            projection_name=projection_name,
            last_event_id=last_event.event_id,
            last_received_at=last_event.received_at,
            business_id=scoped_business_id,
        )
        result.checkpoint_saved = True
        logger.info(
            f"Checkpoint saved: {projection_name} â†’ "
            f"{last_event.event_id}"
        )

    logger.info(
        f"Replay complete: {result.events_processed} processed, "
        f"{result.events_dispatched} dispatched, "
        f"{result.dispatch_failures} failures"
    )

    return result

