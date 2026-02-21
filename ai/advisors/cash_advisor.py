"""
BOS AI Advisors — Cash Advisor
=================================
Analyzes cash flow patterns, flags reconciliation anomalies,
and provides cash position forecasts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from ai.advisors.base import Advisor, Advisory


class CashAdvisor(Advisor):
    """
    Cash management domain advisor.

    Capabilities:
    - Cash reconciliation anomaly detection
    - Cash flow pattern analysis
    - Float optimization suggestions
    """

    @property
    def engine_name(self) -> str:
        return "cash"

    def analyze(
        self,
        tenant_id: uuid.UUID,
        context: Dict[str, Any],
        now: datetime,
    ) -> List[Advisory]:
        advisories: List[Advisory] = []

        # Reconciliation variance detection
        sessions = context.get("sessions", [])
        for session in sessions:
            expected = session.get("expected_balance", 0)
            actual = session.get("actual_balance", 0)
            variance = abs(actual - expected)
            threshold = session.get("variance_threshold", 100)

            if variance > threshold:
                advisories.append(Advisory(
                    engine="cash",
                    advice_type="anomaly_flag",
                    title=f"Cash variance: {session.get('session_id', 'unknown')}",
                    description=(
                        f"Session {session.get('session_id')} has a variance of "
                        f"{variance:.2f} (expected {expected:.2f}, actual {actual:.2f}). "
                        f"Exceeds threshold of {threshold:.2f}."
                    ),
                    confidence=0.90,
                    recommended_action="Investigate cash discrepancy and reconcile",
                    data={
                        "session_id": session.get("session_id"),
                        "expected": expected,
                        "actual": actual,
                        "variance": variance,
                    },
                ))

        # Float optimization
        float_data = context.get("float_analysis", {})
        avg_float = float_data.get("average_float", 0)
        peak_demand = float_data.get("peak_demand", 0)
        if avg_float > 0 and peak_demand > 0:
            utilization = peak_demand / avg_float
            if utilization < 0.5:
                advisories.append(Advisory(
                    engine="cash",
                    advice_type="optimization",
                    title="Excess float detected",
                    description=(
                        f"Average float is {avg_float:.2f} but peak demand is only "
                        f"{peak_demand:.2f} ({utilization:.0%} utilization). "
                        f"Consider reducing float allocation."
                    ),
                    confidence=0.75,
                    recommended_action=f"Reduce float to {peak_demand * 1.3:.2f}",
                    data=float_data,
                ))

        return advisories
