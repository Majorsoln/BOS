"""
BOS Engine Registry — Contract Enforcement
=============================================
Runtime enforcement of engine contracts.

Two enforcement points:
1. EMISSION: Before persist_event() — verify source_engine owns event_type
2. SUBSCRIPTION: Before register_subscriber() — verify declaration exists

Enforcement functions are designed to be called by:
- Command handlers (before persisting events)
- Bootstrap wiring (when registering subscribers)
- Testing (contract compliance checks)

These functions do NOT modify the Event Store or Event Bus.
They add a governance layer on top of frozen infrastructure.

Event Store protects history.
Event Bus protects flow.
Engine Registry protects discipline.
"""

import logging
from typing import Any, Optional

from core.engines.registry import (
    EngineRegistry,
    RegistryNotLockedError,
)

logger = logging.getLogger("bos.engines")


# ══════════════════════════════════════════════════════════════
# ENFORCEMENT ERRORS
# ══════════════════════════════════════════════════════════════

class EngineContractViolation(Exception):
    """Base error for engine contract violations."""
    pass


class EmissionViolation(EngineContractViolation):
    """Engine attempted to emit an event it does not own."""

    def __init__(
        self,
        source_engine: str,
        event_type: str,
        owner: Optional[str] = None,
    ):
        self.source_engine = source_engine
        self.event_type = event_type
        self.owner = owner

        if owner:
            msg = (
                f"ENGINE CONTRACT VIOLATION: "
                f"Engine '{source_engine}' cannot emit '{event_type}'. "
                f"Event type is owned by '{owner}'."
            )
        else:
            msg = (
                f"ENGINE CONTRACT VIOLATION: "
                f"Engine '{source_engine}' cannot emit '{event_type}'. "
                f"Event type has no registered owner."
            )
        super().__init__(msg)


class SubscriptionViolation(EngineContractViolation):
    """Engine attempted to subscribe to an event it did not declare."""

    def __init__(self, subscriber_engine: str, event_type: str):
        self.subscriber_engine = subscriber_engine
        self.event_type = event_type
        super().__init__(
            f"ENGINE CONTRACT VIOLATION: "
            f"Engine '{subscriber_engine}' did not declare subscription "
            f"to '{event_type}' in its contract."
        )


class UnknownEventTypeViolation(EngineContractViolation):
    """Event type is not registered in any engine contract."""

    def __init__(self, event_type: str):
        self.event_type = event_type
        super().__init__(
            f"ENGINE CONTRACT VIOLATION: "
            f"Event type '{event_type}' is not registered in any "
            f"engine contract. Free-text event types are forbidden."
        )


class UnregisteredEngineViolation(EngineContractViolation):
    """Engine is not registered in the EngineRegistry."""

    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        super().__init__(
            f"ENGINE CONTRACT VIOLATION: "
            f"Engine '{engine_name}' is not registered in the "
            f"EngineRegistry. Register before emitting or subscribing."
        )


# ══════════════════════════════════════════════════════════════
# EMISSION ENFORCEMENT
# ══════════════════════════════════════════════════════════════

def enforce_emission(
    source_engine: str,
    event_type: str,
    engine_registry: EngineRegistry,
) -> None:
    """
    Verify that source_engine owns event_type before emission.

    Called BEFORE persist_event() to enforce engine boundaries.
    This is the emission gate — if it fails, the event must NOT
    be persisted.

    Args:
        source_engine:   Engine attempting to emit.
        event_type:      Event type being emitted.
        engine_registry: Locked EngineRegistry.

    Raises:
        RegistryNotLockedError: If registry is not locked.
        UnregisteredEngineViolation: If engine is not registered.
        UnknownEventTypeViolation: If event type has no owner.
        EmissionViolation: If source_engine does not own event_type.

    Returns:
        None — success is silent. Failure is loud.
    """
    if not engine_registry.is_locked:
        raise RegistryNotLockedError()

    # ── Verify engine exists ──────────────────────────────────
    contract = engine_registry.get_contract(source_engine)
    if contract is None:
        raise UnregisteredEngineViolation(source_engine)

    # ── Verify event type is registered ───────────────────────
    if not engine_registry.is_event_type_registered(event_type):
        raise UnknownEventTypeViolation(event_type)

    # ── Verify ownership ──────────────────────────────────────
    if not engine_registry.is_owner(source_engine, event_type):
        actual_owner = engine_registry.get_owner(event_type)
        raise EmissionViolation(source_engine, event_type, actual_owner)

    logger.debug(
        f"Emission enforcement passed: {source_engine} → {event_type}"
    )


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION ENFORCEMENT
# ══════════════════════════════════════════════════════════════

def enforce_subscription(
    subscriber_engine: str,
    event_type: str,
    engine_registry: EngineRegistry,
) -> None:
    """
    Verify that subscriber_engine declared subscription to event_type.

    Called BEFORE SubscriberRegistry.register_subscriber() to enforce
    that engines only listen to events they declared in their contract.

    Args:
        subscriber_engine: Engine attempting to subscribe.
        event_type:        Event type being subscribed to.
        engine_registry:   Locked EngineRegistry.

    Raises:
        RegistryNotLockedError: If registry is not locked.
        UnregisteredEngineViolation: If engine is not registered.
        UnknownEventTypeViolation: If event type has no owner.
        SubscriptionViolation: If subscription is not declared.

    Returns:
        None — success is silent. Failure is loud.
    """
    if not engine_registry.is_locked:
        raise RegistryNotLockedError()

    # ── Verify engine exists ──────────────────────────────────
    contract = engine_registry.get_contract(subscriber_engine)
    if contract is None:
        raise UnregisteredEngineViolation(subscriber_engine)

    # ── Verify event type is registered ───────────────────────
    if not engine_registry.is_event_type_registered(event_type):
        raise UnknownEventTypeViolation(event_type)

    # ── Verify subscription is declared ───────────────────────
    if not engine_registry.is_subscription_declared(
        subscriber_engine, event_type
    ):
        raise SubscriptionViolation(subscriber_engine, event_type)

    logger.debug(
        f"Subscription enforcement passed: "
        f"{subscriber_engine} ← {event_type}"
    )


# ══════════════════════════════════════════════════════════════
# ENFORCED PERSIST EVENT (WRAPPER)
# ══════════════════════════════════════════════════════════════

def enforced_persist_event(
    event_data: dict[str, Any],
    context: Any,
    event_type_registry: Any,
    engine_registry: EngineRegistry,
    subscriber_registry: Any = None,
):
    """
    Engine-contract-aware wrapper around persist_event().

    Flow:
    1. Enforce emission (source_engine owns event_type) — NEW
    2. Delegate to original persist_event() — EXISTING

    This does NOT modify persist_event(). It adds a governance
    layer on top. Frozen layers stay frozen.

    Args:
        event_data:          Raw event data dict.
        context:             Active business context (BusinessContextProtocol).
        event_type_registry: EventTypeRegistry (persistence gate).
        engine_registry:     Locked EngineRegistry (ownership gate).
        subscriber_registry: Optional SubscriberRegistry for dispatch.

    Returns:
        ValidationResult from persist_event().

    Raises:
        EngineContractViolation: If emission is not authorized.
        (All other errors from persist_event pass through.)
    """
    from core.event_store.persistence.service import persist_event

    # ── Step 0: Engine contract enforcement ───────────────────
    enforce_emission(
        source_engine=event_data.get("source_engine", ""),
        event_type=event_data.get("event_type", ""),
        engine_registry=engine_registry,
    )

    # ── Delegate to lawful persistence path ───────────────────
    return persist_event(
        event_data=event_data,
        context=context,
        registry=event_type_registry,
        subscriber_registry=subscriber_registry,
    )


# ══════════════════════════════════════════════════════════════
# ENFORCED SUBSCRIBER REGISTRATION (WRAPPER)
# ══════════════════════════════════════════════════════════════

def enforced_register_subscriber(
    subscriber_registry: Any,
    engine_registry: EngineRegistry,
    event_type: str,
    handler: Any,
    subscriber_engine: str,
    allow_self_subscription: bool = False,
) -> None:
    """
    Engine-contract-aware wrapper around
    SubscriberRegistry.register_subscriber().

    Flow:
    1. Enforce subscription declaration — NEW
    2. Delegate to original register_subscriber() — EXISTING

    Special case: If allow_self_subscription=True AND engine owns
    the event_type, the subscription declaration check is skipped.
    Self-subscription is a deliberate architectural choice, not
    a contract violation.

    Args:
        subscriber_registry: SubscriberRegistry instance.
        engine_registry:     Locked EngineRegistry.
        event_type:          Event type to subscribe to.
        handler:             Callable handler.
        subscriber_engine:   Engine registering the handler.
        allow_self_subscription: Override for engine isolation.

    Raises:
        EngineContractViolation: If subscription is not declared.
        (All other errors from register_subscriber pass through.)
    """
    # Self-subscription explicit override — if engine owns the
    # event AND explicitly allows self-subscription, skip
    # declaration check. This is intentional, not a loophole.
    if (
        allow_self_subscription
        and engine_registry.is_owner(subscriber_engine, event_type)
    ):
        logger.debug(
            f"Self-subscription override: {subscriber_engine} → "
            f"{event_type}"
        )
    else:
        enforce_subscription(
            subscriber_engine=subscriber_engine,
            event_type=event_type,
            engine_registry=engine_registry,
        )

    # ── Delegate to SubscriberRegistry ────────────────────────
    subscriber_registry.register_subscriber(
        event_type=event_type,
        handler=handler,
        subscriber_engine=subscriber_engine,
        allow_self_subscription=allow_self_subscription,
    )
