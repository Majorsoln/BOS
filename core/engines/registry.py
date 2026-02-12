"""
BOS Engine Registry — Central Engine Registry
================================================
Controls which engines exist, what they own, and what they subscribe to.

Rules:
- Each engine registers exactly once
- Each event type has exactly one owner
- Registry locks after bootstrap (no dynamic injection)
- Thread-safe for concurrent access
- Immutable after lock

Lifecycle:
    1. Create registry
    2. Register engine contracts (during bootstrap)
    3. Lock registry (after all engines registered)
    4. Use for enforcement (ownership + subscription validation)

After lock(), the registry is read-only. No new engines, no new events.

The registry is the single source of truth for engine boundaries.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Optional

from core.engines.contracts import EngineContract

logger = logging.getLogger("bos.engines")


# ══════════════════════════════════════════════════════════════
# REGISTRY ERRORS
# ══════════════════════════════════════════════════════════════

class EngineRegistryError(Exception):
    """Base error for engine registry operations."""
    pass


class DuplicateEngineError(EngineRegistryError):
    """Engine already registered."""

    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        super().__init__(
            f"Engine '{engine_name}' is already registered."
        )


class DuplicateEventOwnerError(EngineRegistryError):
    """Event type already owned by another engine."""

    def __init__(
        self, event_type: str, existing_owner: str, new_owner: str
    ):
        self.event_type = event_type
        self.existing_owner = existing_owner
        self.new_owner = new_owner
        super().__init__(
            f"Event type '{event_type}' is already owned by "
            f"'{existing_owner}'. Cannot assign to '{new_owner}'."
        )


class RegistryLockedError(EngineRegistryError):
    """Registry is locked — no modifications allowed."""

    def __init__(self):
        super().__init__(
            "Engine Registry is locked after bootstrap. "
            "No dynamic registration allowed."
        )


class RegistryNotLockedError(EngineRegistryError):
    """Operation requires locked registry."""

    def __init__(self):
        super().__init__(
            "Engine Registry must be locked before enforcement. "
            "Call lock() after all engines are registered."
        )


# ══════════════════════════════════════════════════════════════
# ENGINE REGISTRY
# ══════════════════════════════════════════════════════════════

class EngineRegistry:
    """
    Central registry of all BOS engines and their contracts.

    Thread-safe. Lock-after-bootstrap.

    Usage:
        registry = EngineRegistry()

        # Bootstrap phase — register contracts
        registry.register_engine(inventory_contract)
        registry.register_engine(cash_contract)

        # Lock — no more registrations
        registry.lock()

        # Enforcement phase — validate ownership
        registry.is_owner("inventory", "inventory.stock.moved")  # True
        registry.is_owner("cash", "inventory.stock.moved")       # False
    """

    def __init__(self):
        self._contracts: dict[str, EngineContract] = {}
        self._event_owners: dict[str, str] = {}  # event_type → engine
        self._all_event_types: set[str] = set()
        self._locked: bool = False
        self._lock = Lock()

    # ══════════════════════════════════════════════════════════
    # REGISTRATION (bootstrap phase only)
    # ══════════════════════════════════════════════════════════

    def register_engine(self, contract: EngineContract) -> None:
        """
        Register an engine contract.

        Validates:
        - Registry is not locked
        - Engine name is unique
        - No event type owned by another engine

        Args:
            contract: Frozen EngineContract with declarations.

        Raises:
            RegistryLockedError: If registry is already locked.
            DuplicateEngineError: If engine_name already registered.
            DuplicateEventOwnerError: If event type already owned.
            TypeError: If contract is not an EngineContract.
        """
        if not isinstance(contract, EngineContract):
            raise TypeError(
                f"Expected EngineContract, got {type(contract).__name__}."
            )

        with self._lock:
            if self._locked:
                raise RegistryLockedError()

            engine_name = contract.engine_name

            # ── Check duplicate engine ────────────────────────
            if engine_name in self._contracts:
                raise DuplicateEngineError(engine_name)

            # ── Check ownership conflicts ─────────────────────
            for event_type in contract.owned_event_types:
                if event_type in self._event_owners:
                    raise DuplicateEventOwnerError(
                        event_type=event_type,
                        existing_owner=self._event_owners[event_type],
                        new_owner=engine_name,
                    )

            # ── Register ──────────────────────────────────────
            self._contracts[engine_name] = contract
            for event_type in contract.owned_event_types:
                self._event_owners[event_type] = engine_name
                self._all_event_types.add(event_type)

            logger.info(
                f"Engine registered: '{engine_name}' — "
                f"{len(contract.owned_event_types)} owned, "
                f"{len(contract.subscribed_event_types)} subscribed"
            )

    # ══════════════════════════════════════════════════════════
    # LOCK (transition to enforcement phase)
    # ══════════════════════════════════════════════════════════

    def lock(self) -> None:
        """
        Lock the registry. No more registrations allowed.

        Before locking, validates that all subscription targets
        are owned by some registered engine. If any engine subscribes
        to an unknown event type → refuse to lock.

        Idempotent — calling lock() on an already-locked registry
        is a no-op.

        Raises:
            EngineRegistryError: If subscription targets are invalid.
        """
        with self._lock:
            if self._locked:
                return  # Idempotent

            # ── Validate all subscription targets ─────────────
            errors = []
            for engine_name, contract in self._contracts.items():
                for event_type in contract.subscribed_event_types:
                    if event_type not in self._event_owners:
                        errors.append(
                            f"Engine '{engine_name}' subscribes to "
                            f"'{event_type}' which has no registered "
                            f"owner."
                        )

            if errors:
                raise EngineRegistryError(
                    "Cannot lock registry — unresolved subscriptions:\n"
                    + "\n".join(f"  • {e}" for e in errors)
                )

            self._locked = True
            logger.info(
                f"Engine Registry LOCKED — "
                f"{len(self._contracts)} engines, "
                f"{len(self._all_event_types)} event types"
            )

    # ══════════════════════════════════════════════════════════
    # QUERY (safe at any time, enforcement requires lock)
    # ══════════════════════════════════════════════════════════

    @property
    def is_locked(self) -> bool:
        """Check if registry is locked."""
        with self._lock:
            return self._locked

    def get_owner(self, event_type: str) -> Optional[str]:
        """Get the owning engine for an event type. None if unknown."""
        with self._lock:
            return self._event_owners.get(event_type)

    def get_contract(self, engine_name: str) -> Optional[EngineContract]:
        """Get engine contract. None if not registered."""
        with self._lock:
            return self._contracts.get(engine_name)

    def get_all_event_types(self) -> frozenset[str]:
        """Return all registered event types (owned by any engine)."""
        with self._lock:
            return frozenset(self._all_event_types)

    def get_all_engines(self) -> frozenset[str]:
        """Return all registered engine names."""
        with self._lock:
            return frozenset(self._contracts.keys())

    def engine_count(self) -> int:
        """Return number of registered engines."""
        with self._lock:
            return len(self._contracts)

    def event_type_count(self) -> int:
        """Return total number of registered event types."""
        with self._lock:
            return len(self._all_event_types)

    # ══════════════════════════════════════════════════════════
    # OWNERSHIP & SUBSCRIPTION VALIDATION
    # ══════════════════════════════════════════════════════════

    def is_owner(self, engine_name: str, event_type: str) -> bool:
        """Check if engine_name owns event_type."""
        with self._lock:
            return self._event_owners.get(event_type) == engine_name

    def is_subscription_declared(
        self, subscriber_engine: str, event_type: str
    ) -> bool:
        """
        Check if subscriber_engine declared subscription to event_type
        in its contract.
        """
        with self._lock:
            contract = self._contracts.get(subscriber_engine)
            if contract is None:
                return False
            return event_type in contract.subscribed_event_types

    def is_event_type_registered(self, event_type: str) -> bool:
        """Check if event type exists in any engine's ownership."""
        with self._lock:
            return event_type in self._event_owners

    # ══════════════════════════════════════════════════════════
    # INTEGRATION BRIDGES
    # ══════════════════════════════════════════════════════════

    def populate_event_type_registry(self, event_type_registry) -> int:
        """
        Register all owned event types into the EventTypeRegistry
        (the persistence gate from core.event_store.validators).

        This bridges EngineRegistry (ownership enforcement) with
        EventTypeRegistry (persistence validation). Both gates must
        pass for an event to be persisted.

        Args:
            event_type_registry: EventTypeRegistry instance.

        Returns:
            Number of event types registered.

        Raises:
            RegistryNotLockedError: If engine registry is not locked.
        """
        with self._lock:
            if not self._locked:
                raise RegistryNotLockedError()

            count = 0
            for event_type in sorted(self._all_event_types):
                event_type_registry.register(event_type)
                count += 1

        logger.info(
            f"Populated EventTypeRegistry with {count} event types "
            f"from EngineRegistry."
        )
        return count
