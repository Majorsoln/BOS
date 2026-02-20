"""
BOS Cash Engine — Event Subscriptions
========================================
Cash reacts to events from other engines (read-only).

Subscriptions:
- retail.sale.completed → auto-record payment
- restaurant.order.paid → auto-record payment

Implementation deferred to Phase 6 (engine wiring).
"""

from __future__ import annotations

from typing import Dict


CASH_SUBSCRIPTIONS: Dict[str, str] = {
    "retail.sale.completed": "handle_retail_sale",
}


class CashSubscriptionHandler:
    """Handles events from other engines (read-only)."""

    def __init__(self, cash_service=None):
        self._cash_service = cash_service

    def handle_retail_sale(self, event_data: dict) -> None:
        """Auto-record payment from retail sale. Deferred to Phase 6."""
        pass
