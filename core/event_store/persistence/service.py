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
- Auto-generate missing non-hash fields
- Retry on failure
- Swallow errors silently
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from django.db import IntegrityError, transaction

from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.event_store.idempotency.guard import (
    check_idempotency,
    handle_integrity_error,
)
from core.event_store.hashing.errors import (
    HashRejectionCode,
    HashViolatedRule,
)
from core.event_store.hashing.hasher import GENESIS_HASH, compute_event_hash
from core.event_store.persistence.errors import (
    PersistenceRejectionCode,
    PersistenceViolatedRule,
)
from core.event_store.persistence.repository import (
    get_latest_event_for_business,
    save_event,
)
from core.event_store.validators.context import BusinessContextProtocol
from core.event_store.validators.errors import Rejection, ValidationResult
from core.event_store.validators.event_validator import validate_event
from core.event_store.validators.registry import EventTypeRegistry


def _build_chain_broken_rejection(
    *,
    provided_previous_hash: str,
    expected_previous_hash: str,
) -> ValidationResult:
    return ValidationResult(
        accepted=False,
        rejection=Rejection(
            code=HashRejectionCode.HASH_CHAIN_BROKEN,
            message=(
                "Previous event hash does not match the latest stored "
                f"event. Provided: '{provided_previous_hash}', "
                f"expected: '{expected_previous_hash}'."
            ),
            violated_rule=HashViolatedRule.EVENT_HASH_CHAIN,
        ),
    )


def _build_hash_mismatch_rejection(
    *,
    provided_event_hash: str,
    expected_event_hash: str,
) -> ValidationResult:
    return ValidationResult(
        accepted=False,
        rejection=Rejection(
            code=HashRejectionCode.HASH_COMPUTATION_MISMATCH,
            message=(
                "Provided event_hash does not match computed hash. "
                f"Provided: '{provided_event_hash}', "
                f"computed: '{expected_event_hash}'."
            ),
            violated_rule=HashViolatedRule.EVENT_HASH_CHAIN,
        ),
    )


def _expected_previous_hash(
    *,
    business_id: uuid.UUID,
    lock_latest: bool,
) -> str:
    latest = get_latest_event_for_business(
        business_id,
        lock=lock_latest,
    )
    if latest is None:
        return GENESIS_HASH
    return latest.event_hash


def _resolve_and_validate_hash_fields(
    event_data: dict[str, Any],
    *,
    lock_latest: bool,
) -> ValidationResult | None:
    expected_previous_hash = _expected_previous_hash(
        business_id=event_data["business_id"],
        lock_latest=lock_latest,
    )

    provided_previous_hash = event_data.get("previous_event_hash")
    if provided_previous_hash is None:
        event_data["previous_event_hash"] = expected_previous_hash
    elif provided_previous_hash != expected_previous_hash:
        return _build_chain_broken_rejection(
            provided_previous_hash=str(provided_previous_hash),
            expected_previous_hash=expected_previous_hash,
        )

    expected_event_hash = compute_event_hash(
        event_data["payload"],
        event_data["previous_event_hash"],
    )

    provided_event_hash = event_data.get("event_hash")
    if provided_event_hash is None:
        event_data["event_hash"] = expected_event_hash
    elif provided_event_hash != expected_event_hash:
        return _build_hash_mismatch_rejection(
            provided_event_hash=str(provided_event_hash),
            expected_event_hash=expected_event_hash,
        )

    return None


def _extract_constraint_name(exc: IntegrityError) -> str | None:
    cause = getattr(exc, "__cause__", None)
    diag = getattr(cause, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if isinstance(constraint_name, str) and constraint_name:
        return constraint_name
    return None


def _is_chain_uniqueness_conflict(exc: IntegrityError) -> bool:
    constraint_name = _extract_constraint_name(exc)
    if constraint_name == "uq_evt_biz_prev_hash":
        return True
    return "uq_evt_biz_prev_hash" in str(exc)


def _build_chain_conflict_rejection(event_data: dict[str, Any]) -> ValidationResult:
    provided_previous_hash = event_data.get("previous_event_hash")
    return ValidationResult(
        accepted=False,
        rejection=Rejection(
            code=HashRejectionCode.HASH_CHAIN_BROKEN,
            message=(
                "Concurrent append conflict: previous_event_hash is no longer "
                "the chain head for this business. "
                f"Provided: '{provided_previous_hash}'."
            ),
            violated_rule=HashViolatedRule.EVENT_HASH_CHAIN,
        ),
    )


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
    hash_resolution = _resolve_and_validate_hash_fields(
        event_data,
        lock_latest=False,
    )
    if hash_resolution is not None:
        return hash_resolution

    # ── Step 4: Atomic persistence ────────────────────────────
    try:
        with transaction.atomic():
            # Re-check inside transaction for race-condition safety
            idempotency_recheck = check_idempotency(event_data["event_id"])
            if not idempotency_recheck.accepted:
                return idempotency_recheck

            hash_recheck = _resolve_and_validate_hash_fields(
                event_data,
                lock_latest=True,
            )
            if hash_recheck is not None:
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
        if _is_chain_uniqueness_conflict(exc):
            return _build_chain_conflict_rejection(event_data)
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
