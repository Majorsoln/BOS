"""
BOS AI Advisors — Inventory Advisor
======================================
Analyzes inventory levels and suggests reorder actions,
flags stock anomalies, and identifies slow-moving items.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from ai.advisors.base import Advisor, Advisory


class InventoryAdvisor(Advisor):
    """
    Inventory domain advisor.

    Capabilities:
    - Reorder point suggestions based on consumption rates
    - Stock anomaly detection (sudden drops, unusual patterns)
    - Slow-moving inventory identification
    """

    @property
    def engine_name(self) -> str:
        return "inventory"

    def analyze(
        self,
        tenant_id: uuid.UUID,
        context: Dict[str, Any],
        now: datetime,
    ) -> List[Advisory]:
        advisories: List[Advisory] = []

        # Analyze stock levels
        stock_levels = context.get("stock_levels", {})
        reorder_points = context.get("reorder_points", {})
        consumption_rates = context.get("consumption_rates", {})

        for item_id, current_qty in stock_levels.items():
            reorder_point = reorder_points.get(item_id, 0)
            daily_rate = consumption_rates.get(item_id, 0)

            # Low stock detection
            if reorder_point > 0 and current_qty <= reorder_point:
                days_remaining = (
                    current_qty / daily_rate if daily_rate > 0 else float("inf")
                )
                advisories.append(Advisory(
                    engine="inventory",
                    advice_type="reorder_suggestion",
                    title=f"Low stock: {item_id}",
                    description=(
                        f"Item {item_id} has {current_qty} units remaining, "
                        f"below reorder point of {reorder_point}. "
                        f"At current consumption rate, stock will last "
                        f"{days_remaining:.1f} days."
                    ),
                    confidence=0.85,
                    recommended_action=f"Reorder {reorder_point * 2 - current_qty} units of {item_id}",
                    data={
                        "item_id": item_id,
                        "current_qty": current_qty,
                        "reorder_point": reorder_point,
                        "daily_rate": daily_rate,
                        "days_remaining": days_remaining,
                    },
                ))

            # Zero stock — critical
            if current_qty == 0 and daily_rate > 0:
                advisories.append(Advisory(
                    engine="inventory",
                    advice_type="anomaly_flag",
                    title=f"Stockout: {item_id}",
                    description=f"Item {item_id} is at zero stock with active consumption.",
                    confidence=0.95,
                    recommended_action=f"Urgent reorder for {item_id}",
                    data={"item_id": item_id, "daily_rate": daily_rate},
                ))

        # Slow-moving inventory detection
        slow_movers = context.get("slow_movers", [])
        for item in slow_movers:
            advisories.append(Advisory(
                engine="inventory",
                advice_type="optimization",
                title=f"Slow-moving: {item.get('item_id', 'unknown')}",
                description=(
                    f"Item {item.get('item_id')} has not moved in "
                    f"{item.get('days_stale', 0)} days. Consider markdown or return."
                ),
                confidence=0.70,
                recommended_action="Review for markdown or supplier return",
                data=item,
            ))

        return advisories
