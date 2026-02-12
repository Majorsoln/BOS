"""
BOS Event Store — Event Type Registry
=======================================
Controls which event types are permitted in BOS.
Free-text event types are forbidden.

Rules:
- Registry starts EMPTY
- Engines register their types at bootstrap
- Validator rejects any unregistered event type
- No hardcoded types, no defaults
- Format: engine.domain.action (e.g. inventory.stock.moved)

The registry prefers to reject over accepting something unknown.
"""

from threading import Lock


class EventTypeRegistry:
    """
    In-memory registry of permitted event types.
    Thread-safe for concurrent registration and lookup.

    Usage:
        registry = EventTypeRegistry()
        registry.register("inventory.stock.moved")
        registry.register("cash.session.closed")

        registry.is_registered("inventory.stock.moved")  # True
        registry.is_registered("foo.bar.baz")             # False
    """

    def __init__(self):
        self._registered_types: set[str] = set()
        self._lock = Lock()

    def register(self, event_type: str) -> None:
        """
        Register a permitted event type.
        Called by engines at bootstrap time.
        """
        if not event_type or not isinstance(event_type, str):
            raise ValueError(
                "Event type must be a non-empty string."
            )

        parts = event_type.strip().split(".")
        if len(parts) < 3:
            raise ValueError(
                f"Event type '{event_type}' does not follow "
                f"engine.domain.action format."
            )

        with self._lock:
            self._registered_types.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        """Check if an event type is registered."""
        with self._lock:
            return event_type in self._registered_types

    def get_all_registered(self) -> frozenset[str]:
        """Return all registered types (immutable copy)."""
        with self._lock:
            return frozenset(self._registered_types)

    def count(self) -> int:
        """Return number of registered event types."""
        with self._lock:
            return len(self._registered_types)
