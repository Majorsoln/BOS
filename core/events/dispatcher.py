"""
BOS Event Bus — Dispatcher
============================
Routes persisted events to registered subscribers.

Dispatch behavior:
1. Look up subscribers by event_type
2. Execute handlers sequentially
3. Catch subscriber exceptions per handler
4. Log failure
5. Continue to next subscriber
6. NEVER rollback event persistence

Subscriber failure must NOT:
- Break dispatch of other subscribers
- Break the Event Store
- Delete or modify the persisted event

This module does NOT:
- Write to DB
- Modify events
- Interpret payload meaning
- Call validator, idempotency, or hash engine
- Persist anything

It only routes. Truth must exist before it is heard.
"""

import logging
from typing import Any

from core.events.registry import SubscriberRegistry

logger = logging.getLogger("bos.events")


def _event_to_dict(event: Any) -> dict:
    """Convert an Event ORM model instance to a plain dict for handlers.

    Handlers expect dict access (event_data.get("payload", {})), not
    attribute access on a Django model. This bridges the two conventions.
    """
    if isinstance(event, dict):
        return event
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "business_id": event.business_id,
        "branch_id": event.branch_id,
        "source_engine": event.source_engine,
        "actor_type": event.actor_type,
        "actor_id": event.actor_id,
        "correlation_id": event.correlation_id,
        "causation_id": getattr(event, "causation_id", None),
        "payload": event.payload,
        "reference": getattr(event, "reference", {}),
        "created_at": event.created_at,
        "status": getattr(event, "status", "FINAL"),
    }


def dispatch(event: Any, registry: SubscriberRegistry) -> dict:
    """
    Dispatch a persisted event to all registered subscribers.

    Args:
        event:    Persisted Event model instance (read-only).
        registry: SubscriberRegistry with registered handlers.

    Returns:
        dict with dispatch results:
        {
            'event_type': str,
            'event_id': str,
            'subscribers_notified': int,
            'subscribers_failed': int,
            'failures': list[dict]
        }

    This function NEVER raises exceptions.
    All handler failures are caught, logged, and reported.
    """
    event_type = event.event_type
    event_id = str(event.event_id)

    subscribers = registry.get_subscribers(event_type)

    result = {
        "event_type": event_type,
        "event_id": event_id,
        "subscribers_notified": 0,
        "subscribers_failed": 0,
        "failures": [],
    }

    if not subscribers:
        logger.debug(
            f"No subscribers for event type '{event_type}' "
            f"(event_id: {event_id})"
        )
        return result

    # Convert Event ORM model to dict for handlers.
    # Handlers expect event_data.get("payload", {}) — dict access, not attribute access.
    event_dict = _event_to_dict(event)

    for handler, subscriber_engine in subscribers:
        handler_name = getattr(handler, "__qualname__", str(handler))

        try:
            handler(event_dict)
            result["subscribers_notified"] += 1
            logger.debug(
                f"Dispatched {event_type} → {handler_name} "
                f"(engine: {subscriber_engine})"
            )

        except Exception as exc:
            result["subscribers_failed"] += 1
            failure_info = {
                "handler": handler_name,
                "engine": subscriber_engine,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            result["failures"].append(failure_info)

            logger.error(
                f"Subscriber failed: {handler_name} for "
                f"{event_type} (event_id: {event_id}): {exc}",
                exc_info=True,
            )
            # Continue to next subscriber — NEVER break dispatch

    logger.info(
        f"Dispatch complete: {event_type} (event_id: {event_id}) — "
        f"{result['subscribers_notified']} notified, "
        f"{result['subscribers_failed']} failed"
    )

    return result
