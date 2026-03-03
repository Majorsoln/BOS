"""
BOS Retail Engine — Event Subscriptions
=========================================
Retail subscribes to cart_qr events to auto-open POS sales from QR transfers.
Other engines subscribe TO retail events:
- inventory subscribes to retail.sale.completed.v1 → stock issue
- cash subscribes to retail.sale.completed.v1 → payment record
- accounting subscribes to retail.sale.completed.v1 → journal post
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from engines.retail.commands import SaleOpenRequest, SaleAddLineRequest


RETAIL_SUBSCRIPTIONS: Dict[str, str] = {
    "cart_qr.transferred_to_pos.v1": "handle_cart_qr_transfer",
}


class RetailSubscriptionHandler:
    """
    Handles events from other engines.
    Triggers Retail commands internally.
    """

    def __init__(self, retail_service=None):
        self._retail_service = retail_service

    def handle_cart_qr_transfer(self, event_data: dict) -> None:
        """
        When a Cart QR is transferred to POS, auto-open a sale and add the
        selected items as line items so the cashier can proceed directly to payment.

        The cart_qr.transferred_to_pos.v1 event must include:
          - pos_sale_id:     the sale ID to open in the POS
          - selected_items:  list of {item_id, sku, item_name, unit_price, quantity}
          - currency:        3-letter ISO currency code (set when the Cart QR was created)

        If currency is missing, the handoff cannot proceed (sale cannot be opened).

        Event source: cart_qr.transferred_to_pos.v1
        """
        if self._retail_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        pos_sale_id = str(payload.get("pos_sale_id", ""))
        selected_items = payload.get("selected_items", [])
        currency = str(payload.get("currency", ""))

        if not business_id_raw or not pos_sale_id or not selected_items or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        correlation_id = uuid.UUID(str(payload.get("correlation_id", uuid.uuid4())))
        actor_kwargs = dict(
            business_id=business_id,
            actor_type="SYSTEM",
            actor_id="system:retail.subscription",
            command_id=uuid.uuid4(),
            correlation_id=correlation_id,
            issued_at=datetime.now(tz=timezone.utc),
        )

        # Open the sale with the pos_sale_id provided by the cart_qr engine.
        try:
            open_request = SaleOpenRequest(
                sale_id=pos_sale_id,
                currency=currency,
                branch_id=branch_id,
            )
            self._retail_service._execute_command(open_request.to_command(**actor_kwargs))
        except (KeyError, ValueError, TypeError):
            return

        # Add each selected item as a sale line.
        for item in selected_items:
            try:
                add_request = SaleAddLineRequest(
                    sale_id=pos_sale_id,
                    line_id=str(uuid.uuid4()),
                    item_id=str(item["item_id"]),
                    sku=str(item.get("sku", item["item_id"])),
                    item_name=str(item.get("item_name", item["item_id"])),
                    quantity=int(item.get("quantity", 1)),
                    unit_price=int(item["unit_price"]),
                    branch_id=branch_id,
                )
                actor_kwargs["command_id"] = uuid.uuid4()
                self._retail_service._execute_command(add_request.to_command(**actor_kwargs))
            except (KeyError, ValueError, TypeError):
                continue
