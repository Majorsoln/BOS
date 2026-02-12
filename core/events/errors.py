"""
BOS Event Bus — Errors
========================
Error types for the event dispatch layer.
Separate from Event Store errors — bus is routing, not storage.
"""


class EventBusError(Exception):
    """Base error for Event Bus operations."""
    pass


class InvalidEventTypeFormat(EventBusError):
    """Event type does not follow engine.domain.action format."""

    def __init__(self, event_type: str):
        self.event_type = event_type
        super().__init__(
            f"Event type '{event_type}' does not follow "
            f"engine.domain.action format."
        )


class DuplicateSubscriberError(EventBusError):
    """Same handler already registered for this event type."""

    def __init__(self, event_type: str, handler_name: str):
        self.event_type = event_type
        self.handler_name = handler_name
        super().__init__(
            f"Handler '{handler_name}' already registered "
            f"for event type '{event_type}'."
        )


class SelfSubscriptionError(EventBusError):
    """Engine attempted to subscribe to its own events without explicit allow."""

    def __init__(self, engine: str, event_type: str):
        self.engine = engine
        self.event_type = event_type
        super().__init__(
            f"Engine '{engine}' cannot subscribe to its own "
            f"event type '{event_type}' without explicit allow."
        )
