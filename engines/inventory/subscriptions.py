"""
BOS Inventory Engine — Event Subscriptions
=============================================
Inventory reacts to events from other engines (read-only).

Subscriptions:
- procurement.order.received → auto-receive stock
- retail.sale.completed → auto-issue stock (if configured)

Implementation deferred to Phase 6 (engine wiring).
"""

from __future__ import annotations

from typing import Dict


INVENTORY_SUBSCRIPTIONS: Dict[str, str] = {
    "procurement.order.received": "handle_procurement_received",
}


class InventorySubscriptionHandler:
    """
    Handles events from other engines.
    All handlers are READ-ONLY with respect to other engines.
    They may trigger inventory commands internally.
    """

    def __init__(self, inventory_service=None):
        self._inventory_service = inventory_service

    def handle_procurement_received(self, event_data: dict) -> None:
        """
        When procurement receives goods, create stock receive command.
        Implementation deferred to Phase 6 (engine wiring).
        """
        pass
