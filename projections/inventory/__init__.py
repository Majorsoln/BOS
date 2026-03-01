"""
BOS Projections — Inventory Read Model
==========================================
Cross-engine read model for stock levels, movements,
and valuation snapshots.

Built from events:
- inventory.stock.received.v1
- inventory.stock.issued.v1
- inventory.stock.adjusted.v1
- inventory.stock.transferred.v1
- inventory.stock.reserved.v1
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


_LocationKey = Tuple[uuid.UUID, str, str]  # (business_id, item_id, location_id)


@dataclass
class StockLevel:
    item_id: str
    location_id: str
    quantity: Decimal = Decimal(0)
    reserved: Decimal = Decimal(0)

    @property
    def available(self) -> Decimal:
        return self.quantity - self.reserved


class InventoryReadModel:
    """
    Aggregated inventory read model for stock dashboards.

    Implements ProjectionProtocol for rebuild support.
    """

    projection_name = "inventory_read_model"

    def __init__(self) -> None:
        self._stock: Dict[_LocationKey, StockLevel] = {}
        self._movement_count: Dict[uuid.UUID, int] = defaultdict(int)

    def _key(
        self, business_id: uuid.UUID, item_id: str, location_id: str
    ) -> _LocationKey:
        return (business_id, item_id, location_id)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = payload.get("business_id")
        if isinstance(biz_id, str):
            biz_id = uuid.UUID(biz_id)
        if biz_id is None:
            return

        item_id = payload.get("item_id", "")
        location_id = payload.get("location_id", "")
        qty = Decimal(str(payload.get("quantity", 0)))
        key = self._key(biz_id, item_id, location_id)

        if event_type == "inventory.stock.received.v1":
            sl = self._stock.setdefault(key, StockLevel(item_id=item_id, location_id=location_id))
            sl.quantity += qty
            self._movement_count[biz_id] += 1

        elif event_type == "inventory.stock.issued.v1":
            sl = self._stock.setdefault(key, StockLevel(item_id=item_id, location_id=location_id))
            sl.quantity -= qty
            self._movement_count[biz_id] += 1

        elif event_type == "inventory.stock.adjusted.v1":
            sl = self._stock.setdefault(key, StockLevel(item_id=item_id, location_id=location_id))
            sl.quantity += qty  # adjustment can be + or -
            self._movement_count[biz_id] += 1

        elif event_type == "inventory.stock.reserved.v1":
            sl = self._stock.setdefault(key, StockLevel(item_id=item_id, location_id=location_id))
            sl.reserved += qty

        elif event_type == "inventory.stock.transferred.v1":
            from_loc = payload.get("from_location_id", "")
            to_loc = payload.get("to_location_id", "")
            from_key = self._key(biz_id, item_id, from_loc)
            to_key = self._key(biz_id, item_id, to_loc)
            sl_from = self._stock.setdefault(
                from_key, StockLevel(item_id=item_id, location_id=from_loc)
            )
            sl_to = self._stock.setdefault(
                to_key, StockLevel(item_id=item_id, location_id=to_loc)
            )
            sl_from.quantity -= qty
            sl_to.quantity += qty
            self._movement_count[biz_id] += 1

    def get_stock(
        self, business_id: uuid.UUID, item_id: str, location_id: str
    ) -> Optional[StockLevel]:
        return self._stock.get(self._key(business_id, item_id, location_id))

    def get_total_stock(
        self, business_id: uuid.UUID, item_id: str
    ) -> Decimal:
        """Total quantity across all locations for an item."""
        total = Decimal(0)
        for (biz, iid, _), sl in self._stock.items():
            if biz == business_id and iid == item_id:
                total += sl.quantity
        return total

    def get_movement_count(self, business_id: uuid.UUID) -> int:
        return self._movement_count.get(business_id, 0)

    def list_items(self, business_id: uuid.UUID) -> List[StockLevel]:
        return [
            sl for (biz, _, _), sl in self._stock.items()
            if biz == business_id
        ]

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            keys_to_remove = [k for k in self._stock if k[0] == business_id]
            for k in keys_to_remove:
                del self._stock[k]
            self._movement_count.pop(business_id, None)
        else:
            self._stock.clear()
            self._movement_count.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        items = self.list_items(business_id)
        return {
            "item_count": len(items),
            "total_quantity": str(sum(sl.quantity for sl in items)),
            "total_reserved": str(sum(sl.reserved for sl in items)),
            "movement_count": self.get_movement_count(business_id),
        }
