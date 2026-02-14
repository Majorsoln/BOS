"""
BOS Event Store — Persistence Service
=======================================
The single controlled write path for persisting events.

After Task 0.6, there is exactly ONE lawful way to write an event:
    persist_event(event_data, context, registry)

Write flow (NON-NEGOTIABLE):
    1. Validate event structure      (Task 0.3)
    2. Check idempotency             (Task 0.4)
    3. Verify hash-chain             (Task 0.5)
    4. Atomic DB save                (Task 0.6)
    5. Dispatch to subscribers       (Event Bus — AFTER commit only)
    6. Return success or rejection

If ANY step fails → deterministic rejection. No partial state.

This service does NOT:
- Dispatch before commit (dispatch is AFTER commit via on_commit)
- Touch projections
- Interpret payload meaning
- Auto-generate missing fields
- Retry on failure
- Swallow errors silently
"""

import logging
from typing import Any, Optional

from django.db import IntegrityError, transaction

from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.event_store.idempotency.guard import (
    check_idempotency,
    handle_integrity_error,
)
from core.event_store.hashing.verifier import verify_hash_chain
from core.event_store.persistence.errors import (
    PersistenceRejectionCode,
    PersistenceViolatedRule,
)
from core.event_store.persistence.repository import save_event
from core.event_store.validators.context import BusinessContextProtocol
from core.event_store.validators.errors import Rejection, ValidationResult
from core.event_store.validators.event_validator import validate_event
from core.event_store.validators.registry import EventTypeRegistry


def persist_event(
    event_data: dict[str, Any],
    context: BusinessContextProtocol,
    registry: EventTypeRegistry,
    subscriber_registry: Optional["SubscriberRegistry"] = None,
    scope_requirement: str = SCOPE_BUSINESS_ALLOWED,
) -> ValidationResult:
    """
    The ONE lawful entry point for persisting events into BOS.

    Orchestrates:
        1. Schema + actor + context + type + status + correction validation
        2. Idempotency check (application level)
        3. Hash-chain verification
        4. Atomic database save with race-condition safety
        5. Dispatch to subscribers AFTER commit (if registry provided)
        6. Deterministic result (accepted or rejected)

    Args:
        event_data:           Raw event data dict with all required fields.
        context:              Active business context (dependency injection).
        registry:             Event type registry (dependency injection).
        subscriber_registry:  Optional subscriber registry for dispatch.
        scope_requirement:    Command-owned scope requirement used for
                              branch scope enforcement.

    Returns:
        ValidationResult — accepted=True with advisory_actor flag,
        or accepted=False with explicit Rejection.

    This function NEVER:
    - Partially writes
    - Silently retries
    - Auto-corrects hashes
    - Swallows exceptions
    - Dispatches before commit
    - Persists during replay mode
    """

    # ── Step 0: Replay isolation guard (HARD BLOCK) ─────────
    from core.replay.context import is_replay_active
    from core.replay.errors import ReplayIsolationError

    if is_replay_active():
        raise ReplayIsolationError(
            "Persistence forbidden during replay mode."
        )

    # ── Step 1: Validate event structure ──────────────────────
    validation_result = validate_event(
        event_data=event_data,
        context=context,
        registry=registry,
        scope_requirement=scope_requirement,
    )
    if not validation_result.accepted:
        return validation_result

    # ── Step 2: Idempotency check (application level) ─────────
    idempotency_result = check_idempotency(event_data["event_id"])
    if not idempotency_result.accepted:
        return idempotency_result

    # ── Step 3: Hash-chain verification ───────────────────────
    hash_result = verify_hash_chain(
        business_id=event_data["business_id"],
        previous_event_hash=event_data["previous_event_hash"],
        payload=event_data["payload"],
        event_hash=event_data["event_hash"],
    )
    if not hash_result.accepted:
        return hash_result

    # ── Step 4: Atomic persistence ────────────────────────────
    try:
        with transaction.atomic():
            # Re-check inside transaction for race-condition safety
            idempotency_recheck = check_idempotency(event_data["event_id"])
            if not idempotency_recheck.accepted:
                return idempotency_recheck

            hash_recheck = verify_hash_chain(
                business_id=event_data["business_id"],
                previous_event_hash=event_data["previous_event_hash"],
                payload=event_data["payload"],
                event_hash=event_data["event_hash"],
            )
            if not hash_recheck.accepted:
                return hash_recheck

            persisted_event = save_event(event_data)

            # ── Step 5: Schedule dispatch AFTER commit ────────
            if subscriber_registry is not None:
                transaction.on_commit(
                    lambda: _dispatch_after_commit(
                        persisted_event, subscriber_registry
                    )
                )

    except IntegrityError as exc:
        return handle_integrity_error(event_data["event_id"], exc)

    except Exception as exc:
        return ValidationResult(
            accepted=False,
            rejection=Rejection(
                code=PersistenceRejectionCode.TRANSACTION_ABORTED,
                message=f"Transaction aborted: {str(exc)}",
                violated_rule=PersistenceViolatedRule.ATOMIC_PERSISTENCE,
            ),
        )

    # ── Step 6: Success ───────────────────────────────────────
    return ValidationResult(
        accepted=True,
        advisory_actor=validation_result.advisory_actor,
    )


logger = logging.getLogger("bos.events")


def _dispatch_after_commit(event, subscriber_registry) -> None:
    """
    Internal helper called via transaction.on_commit().
    Dispatches event to subscribers AFTER DB commit.

    Catches all exceptions — dispatch failure must NEVER
    affect the persisted event.
    """
    try:
        from core.events.dispatcher import dispatch
        dispatch(event, subscriber_registry)
    except Exception as exc:
        logger.error(
            f"Post-commit dispatch failed for event "
            f"{event.event_id}: {exc}",
            exc_info=True,
        )
