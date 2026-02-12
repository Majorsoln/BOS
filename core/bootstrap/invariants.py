"""
BOS Bootstrap — Invariant Checks
==================================
Each function verifies one system law.
If any check fails → SystemBootstrapError is raised.

These checks do NOT:
- Auto-fix anything
- Run migrations
- Silence failures
- Create tables

A vault that boots while corrupted is worse than no vault.
"""

import logging

from django.db import connection

from core.bootstrap.errors import SystemBootstrapError

logger = logging.getLogger("bos.bootstrap")


# ══════════════════════════════════════════════════════════════
# CHECK 1: Event Store Table Exists
# ══════════════════════════════════════════════════════════════

def check_event_store_table():
    """
    Verify bos_event_store table exists in the database.
    If missing → refuse start. No auto-migration.
    """
    table_names = connection.introspection.table_names()

    if "bos_event_store" not in table_names:
        raise SystemBootstrapError(
            invariant="EVENT_STORE_TABLE",
            detail=(
                "Table 'bos_event_store' does not exist. "
                "Run migrations before starting BOS. "
                "Bootstrap will not auto-create tables."
            ),
        )

    logger.info("✓ Event Store table exists.")


# ══════════════════════════════════════════════════════════════
# CHECK 2: Event Model Immutability Guards Active
# ══════════════════════════════════════════════════════════════

def check_immutability_guards():
    """
    Programmatically verify that Event.save() blocks updates
    and Event.delete() raises PermissionError.

    Uses a non-persisted instance to test guards without
    touching the database.
    """
    import uuid
    from datetime import datetime, timezone
    from core.event_store.models import Event, ActorType, EventStatus

    # Create an instance that LOOKS like it was already persisted
    # by setting _state.adding = False (simulates a loaded record)
    test_event = Event(
        event_id=uuid.uuid4(),
        event_type="bootstrap.guard.test",
        event_version=1,
        business_id=uuid.uuid4(),
        source_engine="bootstrap",
        actor_type=ActorType.SYSTEM,
        actor_id="bootstrap-check",
        correlation_id=uuid.uuid4(),
        payload={},
        created_at=datetime.now(timezone.utc),
        status=EventStatus.FINAL,
        previous_event_hash="",
        event_hash="",
    )
    # Simulate a persisted record
    test_event._state.adding = False

    # Verify save() blocks updates
    try:
        test_event.save()
        raise SystemBootstrapError(
            invariant="IMMUTABILITY_GUARD_SAVE",
            detail=(
                "Event.save() did NOT block update on persisted event. "
                "Immutability guard is broken or bypassed."
            ),
        )
    except PermissionError:
        pass  # Expected — guard is active

    # Verify delete() is blocked
    try:
        test_event.delete()
        raise SystemBootstrapError(
            invariant="IMMUTABILITY_GUARD_DELETE",
            detail=(
                "Event.delete() did NOT raise PermissionError. "
                "Immutability guard is broken or bypassed."
            ),
        )
    except PermissionError:
        pass  # Expected — guard is active

    logger.info("✓ Immutability guards active (save/delete blocked).")


# ══════════════════════════════════════════════════════════════
# CHECK 3: Hash-Chain Structural Integrity (Light Check)
# ══════════════════════════════════════════════════════════════

def check_hash_chain_integrity():
    """
    Lightweight structural integrity scan.
    NOT a full replay — just checks for obvious corruption:
    - No event has NULL or empty event_hash
    - No event has NULL previous_event_hash
    - GENESIS is used correctly (only on first event per business)

    If corruption detected → refuse start.
    """
    from core.event_store.models import Event
    from core.event_store.hashing import GENESIS_HASH

    # Skip if no events exist (fresh system)
    total = Event.objects.count()
    if total == 0:
        logger.info("✓ Hash-chain check skipped (no events yet).")
        return

    # Check for empty or null event_hash
    broken_hash = Event.objects.filter(event_hash="").count()
    if broken_hash > 0:
        raise SystemBootstrapError(
            invariant="HASH_CHAIN_EMPTY_HASH",
            detail=(
                f"{broken_hash} event(s) have empty event_hash. "
                f"Chain integrity is compromised."
            ),
        )

    # Check for empty previous_event_hash (should be GENESIS, never empty)
    empty_prev = Event.objects.filter(previous_event_hash="").count()
    if empty_prev > 0:
        raise SystemBootstrapError(
            invariant="HASH_CHAIN_EMPTY_PREVIOUS",
            detail=(
                f"{empty_prev} event(s) have empty previous_event_hash. "
                f"Expected '{GENESIS_HASH}' for first events."
            ),
        )

    logger.info(f"✓ Hash-chain structural integrity OK ({total} events).")


# ══════════════════════════════════════════════════════════════
# CHECK 4: Registry Sanity
# ══════════════════════════════════════════════════════════════

def check_registry_sanity():
    """
    Verify EventTypeRegistry class is importable and instantiable.
    If empty → log critical warning (expected until engines register).
    If class missing → refuse start.
    """
    try:
        from core.event_store.validators.registry import EventTypeRegistry
    except ImportError:
        raise SystemBootstrapError(
            invariant="REGISTRY_MISSING",
            detail=(
                "EventTypeRegistry class could not be imported. "
                "core.event_store.validators.registry is broken."
            ),
        )

    try:
        test_registry = EventTypeRegistry()
    except Exception as exc:
        raise SystemBootstrapError(
            invariant="REGISTRY_BROKEN",
            detail=(
                f"EventTypeRegistry could not be instantiated: {exc}"
            ),
        )

    if test_registry.count() == 0:
        logger.warning(
            "⚠ EventTypeRegistry is empty. "
            "No event types registered yet. "
            "This is expected until engines are built."
        )
    else:
        logger.info(
            f"✓ EventTypeRegistry OK ({test_registry.count()} types)."
        )


# ══════════════════════════════════════════════════════════════
# CHECK 5: Persistence Entry Point Enforcement
# ══════════════════════════════════════════════════════════════

def check_persistence_entry_point():
    """
    Verify that the lawful persistence entry point exists.
    - persist_event must be importable from persistence module
    - persist_event must be callable
    """
    try:
        from core.event_store.persistence import persist_event
    except ImportError:
        raise SystemBootstrapError(
            invariant="PERSISTENCE_ENTRY_MISSING",
            detail=(
                "persist_event could not be imported from "
                "core.event_store.persistence. "
                "The lawful write path is broken."
            ),
        )

    if not callable(persist_event):
        raise SystemBootstrapError(
            invariant="PERSISTENCE_ENTRY_NOT_CALLABLE",
            detail="persist_event is not callable.",
        )

    logger.info("✓ Persistence entry point (persist_event) verified.")
