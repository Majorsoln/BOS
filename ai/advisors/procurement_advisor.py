"""
BOS AI Advisors — Procurement Advisor
========================================
Analyzes procurement patterns, suggests optimal ordering,
and flags supplier performance issues.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from ai.advisors.base import Advisor, Advisory


class ProcurementAdvisor(Advisor):
    """
    Procurement domain advisor.

    Capabilities:
    - Supplier lead time analysis
    - Order consolidation suggestions
    - Supplier performance anomaly detection
    """

    @property
    def engine_name(self) -> str:
        return "procurement"

    def analyze(
        self,
        tenant_id: uuid.UUID,
        context: Dict[str, Any],
        now: datetime,
    ) -> List[Advisory]:
        advisories: List[Advisory] = []

        # Supplier performance analysis
        suppliers = context.get("supplier_performance", [])
        for supplier in suppliers:
            on_time_rate = supplier.get("on_time_delivery_rate", 1.0)
            defect_rate = supplier.get("defect_rate", 0.0)
            supplier_id = supplier.get("supplier_id", "unknown")

            if on_time_rate < 0.8:
                advisories.append(Advisory(
                    engine="procurement",
                    advice_type="anomaly_flag",
                    title=f"Supplier delays: {supplier_id}",
                    description=(
                        f"Supplier {supplier_id} has an on-time delivery rate of "
                        f"{on_time_rate:.0%}, below the 80% threshold."
                    ),
                    confidence=0.85,
                    recommended_action="Review supplier contract or seek alternative",
                    data=supplier,
                ))

            if defect_rate > 0.05:
                advisories.append(Advisory(
                    engine="procurement",
                    advice_type="anomaly_flag",
                    title=f"Quality issue: {supplier_id}",
                    description=(
                        f"Supplier {supplier_id} has a defect rate of "
                        f"{defect_rate:.1%}, exceeding the 5% threshold."
                    ),
                    confidence=0.80,
                    recommended_action="Request corrective action from supplier",
                    data=supplier,
                ))

        # Order consolidation opportunities
        pending_orders = context.get("pending_orders", [])
        by_supplier: Dict[str, list] = {}
        for order in pending_orders:
            sid = order.get("supplier_id", "")
            by_supplier.setdefault(sid, []).append(order)

        for sid, orders in by_supplier.items():
            if len(orders) >= 3:
                total_value = sum(o.get("value", 0) for o in orders)
                advisories.append(Advisory(
                    engine="procurement",
                    advice_type="optimization",
                    title=f"Consolidate orders: {sid}",
                    description=(
                        f"{len(orders)} pending orders for supplier {sid} "
                        f"(total value: {total_value:.2f}). "
                        f"Consolidating may reduce shipping costs."
                    ),
                    confidence=0.70,
                    recommended_action=f"Consolidate {len(orders)} orders into single PO",
                    data={
                        "supplier_id": sid,
                        "order_count": len(orders),
                        "total_value": total_value,
                    },
                ))

        return advisories
