"""
BOS Projections — Restaurant Read Model
===========================================
Cross-engine read model for table utilization,
order timings, and kitchen performance.

Built from events:
- restaurant.order.created.v1
- restaurant.order.completed.v1
- restaurant.order.cancelled.v1
- restaurant.kitchen.ticket.sent.v1
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class OrderSummary:
    order_id: str
    status: str  # CREATED | COMPLETED | CANCELLED
    total: Decimal = Decimal(0)
    item_count: int = 0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RestaurantReadModel:
    """
    Aggregated restaurant read model for dashboards.

    Implements ProjectionProtocol for rebuild support.
    """

    projection_name = "restaurant_read_model"

    def __init__(self) -> None:
        self._orders: Dict[str, OrderSummary] = {}
        self._by_business: Dict[uuid.UUID, List[str]] = defaultdict(list)
        self._revenue: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        self._tickets_sent: Dict[uuid.UUID, int] = defaultdict(int)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = payload.get("business_id")
        if isinstance(biz_id, str):
            biz_id = uuid.UUID(biz_id)
        if biz_id is None:
            return

        if event_type == "restaurant.order.created.v1":
            order_id = payload.get("order_id", "")
            self._orders[order_id] = OrderSummary(
                order_id=order_id,
                status="CREATED",
                item_count=payload.get("item_count", 0),
                created_at=payload.get("created_at"),
            )
            self._by_business[biz_id].append(order_id)

        elif event_type == "restaurant.order.completed.v1":
            order_id = payload.get("order_id", "")
            if order_id in self._orders:
                o = self._orders[order_id]
                o.status = "COMPLETED"
                o.total = Decimal(str(payload.get("total", 0)))
                o.completed_at = payload.get("completed_at")
                self._revenue[biz_id] += o.total

        elif event_type == "restaurant.order.cancelled.v1":
            order_id = payload.get("order_id", "")
            if order_id in self._orders:
                self._orders[order_id].status = "CANCELLED"

        elif event_type == "restaurant.kitchen.ticket.sent.v1":
            self._tickets_sent[biz_id] += 1

    def get_revenue(self, business_id: uuid.UUID) -> Decimal:
        return self._revenue.get(business_id, Decimal(0))

    def get_order_count(self, business_id: uuid.UUID) -> int:
        return len(self._by_business.get(business_id, []))

    def get_tickets_sent(self, business_id: uuid.UUID) -> int:
        return self._tickets_sent.get(business_id, 0)

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            order_ids = self._by_business.pop(business_id, [])
            for oid in order_ids:
                self._orders.pop(oid, None)
            self._revenue.pop(business_id, None)
            self._tickets_sent.pop(business_id, None)
        else:
            self._orders.clear()
            self._by_business.clear()
            self._revenue.clear()
            self._tickets_sent.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "order_count": self.get_order_count(business_id),
            "revenue": str(self.get_revenue(business_id)),
            "tickets_sent": self.get_tickets_sent(business_id),
        }
