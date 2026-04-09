"""
BOS BI Projections — Event Subscriptions
==========================================
Subscribes to operational events and maintains KPI counters
in the in-memory KPI store.

Subscription handlers are pure functions:
    handler(event) -> None

They NEVER write to the Event Store.
They only call kpi_store.increment() to update projection state.

Registered via: register(subscriber_registry)

RP-02  cash.session.closed.v1        → CASH_SESSIONS_CLOSED, CASH_SESSION_VARIANCE
RP-11  workshop.quote.generated.v1   → QUOTES_GENERATED, QUOTE_VALUE
RP-11  workshop.quote.accepted.v1    → QUOTES_ACCEPTED, QUOTE_ACCEPTED_VALUE
RP-11  workshop.quote.rejected.v1    → QUOTES_REJECTED
"""

from __future__ import annotations

import logging
from typing import Any

from projections.bi import kpi_store

logger = logging.getLogger("bos.bi")


# ══════════════════════════════════════════════════════════════
# RP-02 — Cash Session Reporting
# ══════════════════════════════════════════════════════════════

def handle_cash_session_closed(event: Any) -> None:
    """
    RP-02: Handle cash.session.closed.v1

    Records:
        CASH_SESSIONS_CLOSED    +1 per closed session
        CASH_SESSION_VARIANCE   +abs(variance) in minor units per session

    Expected payload keys:
        variance    int   Signed variance (actual − expected) in minor units.
                         Positive = overage, negative = shortage.
    """
    business_id = str(event.business_id)
    payload: dict[str, Any] = event.payload or {}

    kpi_store.increment(business_id, "CASH_SESSIONS_CLOSED", 1)

    variance = payload.get("variance", 0)
    if variance is not None and variance != 0:
        kpi_store.increment(business_id, "CASH_SESSION_VARIANCE", abs(variance))

    logger.debug(
        "[BI] RP-02 cash session closed — business=%s event=%s variance=%s",
        business_id,
        event.event_id,
        variance,
    )


# ══════════════════════════════════════════════════════════════
# RP-11 — Workshop Quote Pipeline Reporting
# ══════════════════════════════════════════════════════════════

def handle_workshop_quote_generated(event: Any) -> None:
    """
    RP-11: Handle workshop.quote.generated.v1

    Records:
        QUOTES_GENERATED    +1 per quote
        QUOTE_VALUE         +quote_value (cumulative pipeline value)

    Expected payload keys:
        quote_id        str   Identifier for log context
        quote_value     int   Quote amount in minor units
    """
    business_id = str(event.business_id)
    payload: dict[str, Any] = event.payload or {}

    kpi_store.increment(business_id, "QUOTES_GENERATED", 1)

    quote_value = payload.get("quote_value", 0)
    if quote_value:
        kpi_store.increment(business_id, "QUOTE_VALUE", quote_value)

    logger.debug(
        "[BI] RP-11 quote generated — business=%s event=%s value=%s",
        business_id,
        event.event_id,
        quote_value,
    )


def handle_workshop_quote_accepted(event: Any) -> None:
    """
    RP-11: Handle workshop.quote.accepted.v1

    Records:
        QUOTES_ACCEPTED         +1 per accepted quote
        QUOTE_ACCEPTED_VALUE    +quote_value (cumulative accepted value)

    Expected payload keys:
        quote_id        str   Identifier for log context
        quote_value     int   Quote amount in minor units
    """
    business_id = str(event.business_id)
    payload: dict[str, Any] = event.payload or {}

    kpi_store.increment(business_id, "QUOTES_ACCEPTED", 1)

    accepted_value = payload.get("quote_value", 0)
    if accepted_value:
        kpi_store.increment(business_id, "QUOTE_ACCEPTED_VALUE", accepted_value)

    logger.debug(
        "[BI] RP-11 quote accepted — business=%s event=%s value=%s",
        business_id,
        event.event_id,
        accepted_value,
    )


def handle_workshop_quote_rejected(event: Any) -> None:
    """
    RP-11: Handle workshop.quote.rejected.v1

    Records:
        QUOTES_REJECTED     +1 per rejected quote

    Expected payload keys:
        quote_id        str   Identifier for log context
        reason          str   Optional rejection reason
    """
    business_id = str(event.business_id)

    kpi_store.increment(business_id, "QUOTES_REJECTED", 1)

    logger.debug(
        "[BI] RP-11 quote rejected — business=%s event=%s",
        business_id,
        event.event_id,
    )


# ══════════════════════════════════════════════════════════════
# Registration
# ══════════════════════════════════════════════════════════════

def register(subscriber_registry) -> None:
    """
    Register BI projection subscriptions with the given SubscriberRegistry.

    Call this once at wiring time, AFTER the registry is created.
    """
    from engines.cash.events import CASH_SESSION_CLOSED_V1
    from engines.workshop.events import (
        WORKSHOP_QUOTE_GENERATED_V1,
        WORKSHOP_QUOTE_ACCEPTED_V1,
        WORKSHOP_QUOTE_REJECTED_V1,
    )

    subscriber_registry.register_subscriber(
        event_type=CASH_SESSION_CLOSED_V1,
        handler=handle_cash_session_closed,
        subscriber_engine="bi",
    )
    subscriber_registry.register_subscriber(
        event_type=WORKSHOP_QUOTE_GENERATED_V1,
        handler=handle_workshop_quote_generated,
        subscriber_engine="bi",
    )
    subscriber_registry.register_subscriber(
        event_type=WORKSHOP_QUOTE_ACCEPTED_V1,
        handler=handle_workshop_quote_accepted,
        subscriber_engine="bi",
    )
    subscriber_registry.register_subscriber(
        event_type=WORKSHOP_QUOTE_REJECTED_V1,
        handler=handle_workshop_quote_rejected,
        subscriber_engine="bi",
    )
