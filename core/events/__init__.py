"""
BOS Event Bus — Public API
============================
Event Store seals truth. Event Bus distributes truth.
Truth must exist before it is heard.
"""

from core.events.dispatcher import dispatch
from core.events.errors import (
    DuplicateSubscriberError,
    EventBusError,
    InvalidEventTypeFormat,
    SelfSubscriptionError,
)
from core.events.registry import SubscriberRegistry

__all__ = [
    "dispatch",
    "SubscriberRegistry",
    "EventBusError",
    "InvalidEventTypeFormat",
    "DuplicateSubscriberError",
    "SelfSubscriptionError",
]
