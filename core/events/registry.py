"""
BOS Event Bus — Subscriber Registry
======================================
Controls which handlers receive which events.

This is NOT the EventTypeRegistry from event_store/validators.
That registry controls which types can be PERSISTED.
This registry controls which handlers LISTEN to dispatched events.

Rules:
- Event types must follow engine.domain.action format
- Multiple subscribers per event type allowed
- Duplicate handler for same event type forbidden
- Self-subscription (engine listens to own events) blocked unless explicit
- In-memory only (no DB, no files)
- Thread-safe
- No dynamic eval, no string-based imports
"""

import logging
from threading import Lock
from typing import Callable

from core.events.errors import (
    DuplicateSubscriberError,
    EventBusError,
    InvalidEventTypeFormat,
    SelfSubscriptionError,
)

logger = logging.getLogger("bos.events")


class SubscriberRegistry:
    """
    In-memory registry of event subscribers.

    Each entry maps an event_type to a list of
    (handler, subscriber_engine) tuples.
    """

    def __init__(self):
        self._subscribers: dict[str, list[tuple[Callable, str]]] = {}
        self._lock = Lock()

    @staticmethod
    def _validate_event_type_format(event_type: str) -> None:
        """Validate engine.domain.action format."""
        if not event_type or not isinstance(event_type, str):
            raise InvalidEventTypeFormat(event_type or "")

        parts = event_type.strip().split(".")
        if len(parts) < 3:
            raise InvalidEventTypeFormat(event_type)

    @staticmethod
    def _extract_source_engine(event_type: str) -> str:
        """Extract engine name from event_type (first segment)."""
        return event_type.split(".")[0]

    def register_subscriber(
        self,
        event_type: str,
        handler: Callable,
        subscriber_engine: str,
        allow_self_subscription: bool = False,
    ) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type:             e.g. 'inventory.stock.moved'
            handler:                Callable to invoke on dispatch
            subscriber_engine:      Engine registering this handler
            allow_self_subscription: Explicit override for engine isolation

        Raises:
            InvalidEventTypeFormat:  Bad event type format
            DuplicateSubscriberError: Handler already registered
            SelfSubscriptionError:   Engine subscribing to own events
        """
        self._validate_event_type_format(event_type)

        if not callable(handler):
            raise EventBusError(
                f"Handler must be callable, got {type(handler)}."
            )

        # Engine isolation check
        source_engine = self._extract_source_engine(event_type)
        if source_engine == subscriber_engine and not allow_self_subscription:
            raise SelfSubscriptionError(subscriber_engine, event_type)

        handler_name = getattr(handler, "__qualname__", str(handler))

        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            # Check for duplicate handler
            for existing_handler, _ in self._subscribers[event_type]:
                if existing_handler is handler:
                    raise DuplicateSubscriberError(event_type, handler_name)

            self._subscribers[event_type].append(
                (handler, subscriber_engine)
            )

        logger.info(
            f"Subscriber registered: {handler_name} → {event_type} "
            f"(from engine: {subscriber_engine})"
        )

    def get_subscribers(self, event_type: str) -> list[tuple[Callable, str]]:
        """
        Get all subscribers for an event type.
        Returns empty list if no subscribers (not an error).
        """
        with self._lock:
            return list(self._subscribers.get(event_type, []))

    def has_subscribers(self, event_type: str) -> bool:
        """Check if any subscribers exist for an event type."""
        with self._lock:
            return bool(self._subscribers.get(event_type))

    def get_all_event_types(self) -> frozenset[str]:
        """Return all event types with registered subscribers."""
        with self._lock:
            return frozenset(self._subscribers.keys())

    def subscriber_count(self, event_type: str) -> int:
        """Count subscribers for an event type."""
        with self._lock:
            return len(self._subscribers.get(event_type, []))
