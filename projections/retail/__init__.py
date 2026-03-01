"""
BOS Projections — Retail Read Model
=======================================
Cross-engine read model combining retail sales data
with cash payments and customer (party) information.

Built from events:
- retail.sale.completed.v1
- retail.sale.voided.v1
- retail.refund.recorded.v1
- cash.payment.recorded.v1
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class SaleSummary:
    sale_id: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    total: Decimal
    currency: str
    status: str  # COMPLETED | VOIDED | REFUNDED
    completed_at: Optional[datetime] = None
    line_count: int = 0
    customer_id: Optional[str] = None


class RetailReadModel:
    """
    Aggregated retail read model for dashboards and reporting.

    Implements ProjectionProtocol for rebuild support.
    """

    projection_name = "retail_read_model"

    def __init__(self) -> None:
        self._sales: Dict[str, SaleSummary] = {}  # sale_id → summary
        self._by_business: Dict[uuid.UUID, List[str]] = defaultdict(list)
        self._revenue: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        self._refunds: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = payload.get("business_id")
        if isinstance(biz_id, str):
            biz_id = uuid.UUID(biz_id)

        if event_type == "retail.sale.completed.v1":
            sale_id = payload.get("sale_id", "")
            total = Decimal(str(payload.get("total", 0)))
            summary = SaleSummary(
                sale_id=sale_id,
                business_id=biz_id,
                branch_id=payload.get("branch_id"),
                total=total,
                currency=payload.get("currency", "USD"),
                status="COMPLETED",
                completed_at=payload.get("completed_at"),
                line_count=payload.get("line_count", 0),
                customer_id=payload.get("customer_id"),
            )
            self._sales[sale_id] = summary
            self._by_business[biz_id].append(sale_id)
            self._revenue[biz_id] += total

        elif event_type == "retail.sale.voided.v1":
            sale_id = payload.get("sale_id", "")
            if sale_id in self._sales:
                old = self._sales[sale_id]
                self._revenue[old.business_id] -= old.total
                self._sales[sale_id] = SaleSummary(
                    sale_id=old.sale_id,
                    business_id=old.business_id,
                    branch_id=old.branch_id,
                    total=old.total,
                    currency=old.currency,
                    status="VOIDED",
                    completed_at=old.completed_at,
                    line_count=old.line_count,
                    customer_id=old.customer_id,
                )

        elif event_type == "retail.refund.recorded.v1":
            refund_amount = Decimal(str(payload.get("refund_amount", 0)))
            if biz_id:
                self._refunds[biz_id] += refund_amount

    def get_revenue(self, business_id: uuid.UUID) -> Decimal:
        return self._revenue.get(business_id, Decimal(0))

    def get_refunds(self, business_id: uuid.UUID) -> Decimal:
        return self._refunds.get(business_id, Decimal(0))

    def get_net_revenue(self, business_id: uuid.UUID) -> Decimal:
        return self.get_revenue(business_id) - self.get_refunds(business_id)

    def get_sale(self, sale_id: str) -> Optional[SaleSummary]:
        return self._sales.get(sale_id)

    def get_sale_count(self, business_id: uuid.UUID) -> int:
        return len(self._by_business.get(business_id, []))

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            sale_ids = self._by_business.pop(business_id, [])
            for sid in sale_ids:
                self._sales.pop(sid, None)
            self._revenue.pop(business_id, None)
            self._refunds.pop(business_id, None)
        else:
            self._sales.clear()
            self._by_business.clear()
            self._revenue.clear()
            self._refunds.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "revenue": str(self.get_revenue(business_id)),
            "refunds": str(self.get_refunds(business_id)),
            "net_revenue": str(self.get_net_revenue(business_id)),
            "sale_count": self.get_sale_count(business_id),
        }
