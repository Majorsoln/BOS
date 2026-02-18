"""
BOS Event Store — Hash-Chain Verifier
=======================================
Verifies that a new event correctly links to the existing chain.

Before saving a new event, this verifier:
1. Fetches the last persisted event for that business
2. Checks previous_event_hash matches the last event's event_hash
3. Checks event_hash is correctly computed

If any check fails → deterministic rejection.

This module does NOT:
- Auto-correct hashes
- Regenerate previous_event_hash
- Reorder events
- Ignore mismatches
- Write to database
- Interpret payload meaning
- Call validator or idempotency guard

BOS prefers failure over silent corruption.
"""

import uuid
from typing import Any

from core.event_store.models import Event
from core.event_store.hashing.errors import (
    HashRejectionCode,
    HashViolatedRule,
)
from core.event_store.hashing.hasher import (
    GENESIS_HASH,
    compute_event_hash,
)
from core.event_store.validators.errors import Rejection, ValidationResult


def _get_last_event_hash(
    business_id: uuid.UUID,
    *,
    lock: bool = False,
) -> str:
    """
    Fetch the event_hash of the most recent event for a business.
    If no events exist → return GENESIS_HASH.

    Uses created_at/event_id ordering to determine the latest event.
    """
    query = (
        Event.objects.filter(business_id=business_id)
        .order_by("-created_at", "-event_id")
    )
    if lock:
        query = query.select_for_update()

    last_event = query.values_list("event_hash", flat=True).first()

    if last_event is None:
        return GENESIS_HASH

    return last_event


def verify_hash_chain(
    business_id: uuid.UUID,
    previous_event_hash: str,
    payload: Any,
    event_hash: str,
    *,
    lock: bool = False,
) -> ValidationResult:
    """
    Verify hash-chain integrity for a new event.

    Checks:
    1. previous_event_hash matches the actual last event's hash
    2. event_hash matches the computed hash

    Args:
        business_id:          Tenant scope for chain lookup.
        previous_event_hash:  Client-provided previous hash.
        payload:              Event payload for hash computation.
        event_hash:           Client-provided event hash.

    Returns:
        ValidationResult — accepted=True or rejected with explicit reason.

    This function does NOT auto-correct. Mismatch = rejection.
    """

    # ── 1. Chain continuity check ─────────────────────────────
    actual_last_hash = _get_last_event_hash(
        business_id,
        lock=lock,
    )

    if previous_event_hash != actual_last_hash:
        return ValidationResult(
            accepted=False,
            rejection=Rejection(
                code=HashRejectionCode.HASH_CHAIN_BROKEN,
                message=(
                    f"Previous event hash does not match the latest "
                    f"stored event. Provided: '{previous_event_hash}', "
                    f"expected: '{actual_last_hash}'."
                ),
                violated_rule=HashViolatedRule.EVENT_HASH_CHAIN,
            ),
        )

    # ── 2. Hash computation check ─────────────────────────────
    expected_hash = compute_event_hash(payload, previous_event_hash)

    if event_hash != expected_hash:
        return ValidationResult(
            accepted=False,
            rejection=Rejection(
                code=HashRejectionCode.HASH_COMPUTATION_MISMATCH,
                message=(
                    f"Provided event_hash does not match computed hash. "
                    f"Provided: '{event_hash}', "
                    f"computed: '{expected_hash}'."
                ),
                violated_rule=HashViolatedRule.EVENT_HASH_CHAIN,
            ),
        )

    # ── All checks passed ─────────────────────────────────────
    return ValidationResult(accepted=True)
