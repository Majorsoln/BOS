"""
BOS Accounting Engine — Event Subscriptions
==============================================
Accounting reacts to events from other engines (read-only).

Subscriptions:
- inventory.stock.received → auto-post COGS/inventory entries
- cash.payment.recorded → auto-fulfill obligations

Implementation deferred to Phase 6 (engine wiring).
"""

from __future__ import annotations

from typing import Dict


ACCOUNTING_SUBSCRIPTIONS: Dict[str, str] = {
    "inventory.stock.received.v1": "handle_stock_received",
    "cash.payment.recorded.v1": "handle_payment_recorded",
}


class AccountingSubscriptionHandler:
    """Handles events from other engines (read-only)."""

    def __init__(self, accounting_service=None):
        self._accounting_service = accounting_service

    def handle_stock_received(self, event_data: dict) -> None:
        """Auto-post inventory/COGS journal entry. Deferred to Phase 6."""
        pass

    def handle_payment_recorded(self, event_data: dict) -> None:
        """Auto-fulfill payment obligation. Deferred to Phase 6."""
        pass
