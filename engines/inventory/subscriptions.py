"""
BOS Inventory Engine — Event Subscriptions
=============================================
Inventory reacts to events from other engines (read-only).

Subscriptions:
- procurement.order.received.v1  → auto-receive stock for each received line
- retail.sale.completed.v1       → auto-issue stock for each sold line
- restaurant.order.placed.v1     → auto-issue stock for each ordered item
                                   (deduction at order time, when kitchen prepares)

Doctrine: AGENTS.md Rule 4 — Engines communicate ONLY via events.
The subscription handler receives an event from another engine and
triggers internal Inventory commands. No direct cross-engine calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from engines.inventory.commands import StockReceiveRequest, StockIssueRequest


INVENTORY_SUBSCRIPTIONS: Dict[str, str] = {
    "procurement.order.received.v1": "handle_procurement_received",
    "retail.sale.completed.v1": "handle_retail_sale",
    "restaurant.order.placed.v1": "handle_restaurant_order",
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
                    actor_type="SYSTEM",
                    actor_id="system:inventory.subscription",
                    command_id=uuid.uuid4(),
                    correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                    issued_at=datetime.now(tz=timezone.utc),
                )
                self._inventory_service._execute_command(command)
            except (KeyError, ValueError, TypeError):
                # Log failure per-line but continue processing other lines
                continue

    def handle_retail_sale(self, event_data: dict) -> None:
        """
        When Retail completes a sale, auto-issue stock for each sold line.

        Event source: retail.sale.completed.v1
        Payload fields used:
            business_id, branch_id, sale_id, lines (list of {item_id, sku, quantity, ...})
        """
        if self._inventory_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        sale_id = str(payload.get("sale_id", ""))
        lines = payload.get("lines", [])

        if not business_id_raw or not lines:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        for line in lines:
            try:
                request = StockIssueRequest(
                    item_id=str(line["item_id"]),
                    sku=str(line.get("sku", line["item_id"])),
                    quantity=int(line["quantity"]),
                    location_id="DEFAULT",
                    location_name="Default Store Location",
                    reason="SALE",
                    reference_id=f"SALE:{sale_id}",
                    branch_id=branch_id,
                )
                command = request.to_command(
                    business_id=business_id,
                    actor_type="SYSTEM",
                    actor_id="system:inventory.subscription",
                    command_id=uuid.uuid4(),
                    correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                    issued_at=datetime.now(tz=timezone.utc),
                )
                self._inventory_service._execute_command(command)
            except (KeyError, ValueError, TypeError):
                continue

    def handle_restaurant_order(self, event_data: dict) -> None:
        """
        When Restaurant places an order, auto-issue stock for each ordered item.
        Stock is deducted at order placement (kitchen begins preparation).

        Event source: restaurant.order.placed.v1
        Payload fields used:
            business_id, branch_id, order_id, items (list of {item_id, sku, quantity, ...})
        """
        if self._inventory_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        order_id = str(payload.get("order_id", ""))
        items = payload.get("items", [])

        if not business_id_raw or not items:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        for item in items:
            try:
                request = StockIssueRequest(
                    item_id=str(item["item_id"]),
                    sku=str(item.get("sku", item["item_id"])),
                    quantity=int(item.get("quantity", 1)),
                    location_id="DEFAULT",
                    location_name="Default Store Location",
                    reason="CONSUMPTION",
                    reference_id=f"ORDER:{order_id}",
                    branch_id=branch_id,
                )
                command = request.to_command(
                    business_id=business_id,
                    actor_type="SYSTEM",
                    actor_id="system:inventory.subscription",
                    command_id=uuid.uuid4(),
                    correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                    issued_at=datetime.now(tz=timezone.utc),
                )
                self._inventory_service._execute_command(command)
            except (KeyError, ValueError, TypeError):
                continue
