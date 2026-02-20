"""
BOS Inventory Engine — Event Subscriptions
=============================================
Inventory reacts to events from other engines (read-only).

Subscriptions:
- procurement.order.received → auto-receive stock for each received line
- retail.sale.completed → auto-issue stock for each sold line (if configured)

Doctrine: AGENTS.md Rule 4 — Engines communicate ONLY via events.
The subscription handler receives an event from another engine and
triggers internal Inventory commands. No direct cross-engine calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from engines.inventory.commands import StockReceiveRequest


INVENTORY_SUBSCRIPTIONS: Dict[str, str] = {
    "procurement.order.received": "handle_procurement_received",
}


class InventorySubscriptionHandler:
    """
    Handles events from other engines.
    All handlers trigger Inventory commands internally.
    The Inventory engine's service processes them normally.

    System actor is used for automated triggers (not human-initiated).
    """

    def __init__(self, inventory_service=None):
        self._inventory_service = inventory_service

    def handle_procurement_received(self, event_data: dict) -> None:
        """
        When Procurement records goods received (GRN), auto-receive stock.

        Event source: procurement.order.received.v1
        Payload fields used:
            business_id, branch_id, order_id, received_lines, location_id, location_name
        """
        if self._inventory_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        order_id = str(payload.get("order_id", ""))
        location_id = str(payload.get("location_id", ""))
        location_name = str(payload.get("location_name", ""))
        received_lines = payload.get("received_lines", [])

        if not business_id_raw or not received_lines:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        for line in received_lines:
            try:
                request = StockReceiveRequest(
                    item_id=str(line["item_id"]),
                    sku=str(line.get("sku", line["item_id"])),
                    quantity=int(line["quantity"]),
                    location_id=location_id,
                    location_name=location_name,
                    reason="PURCHASE",
                    unit_cost=line.get("unit_cost"),
                    reference_id=f"GRN:{order_id}",
                    branch_id=branch_id,
                )
                command = request.to_command(
                    business_id=business_id,
                    actor_type="System",
                    actor_id="system:inventory.subscription",
                    command_id=uuid.uuid4(),
                    correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                    issued_at=datetime.now(tz=timezone.utc),
                )
                self._inventory_service._execute_command(command)
            except (KeyError, ValueError, TypeError):
                # Log failure per-line but continue processing other lines
                continue
