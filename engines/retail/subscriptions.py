"""
BOS Retail Engine — Event Subscriptions
=========================================
Retail subscribes to no external events in Phase 6.
Other engines subscribe TO retail events:
- inventory subscribes to retail.sale.completed → stock issue
- cash subscribes to retail.sale.completed → payment record
- accounting subscribes to retail.sale.completed → journal post
"""

from __future__ import annotations


RETAIL_SUBSCRIPTIONS = {}


class RetailSubscriptionHandler:
    """Retail currently does not subscribe to external events."""
    pass
