"""
BOS Procurement Engine — Event Subscriptions
===============================================
Procurement does not subscribe to external events in Phase 6.
Other engines subscribe TO procurement events:
- inventory subscribes to procurement.order.received → stock receive
- accounting subscribes to procurement.order.received → create payable
"""

from __future__ import annotations


PROCUREMENT_SUBSCRIPTIONS = {}


class ProcurementSubscriptionHandler:
    """Procurement currently does not subscribe to external events."""
    pass
