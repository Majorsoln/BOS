"""
BOS Decision Simulation — What-If Engine
============================================
Simulates the impact of potential decisions without
committing any state changes. All simulations are read-only
and produce SimulationResult records.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# SIMULATION SCENARIO
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SimulationScenario:
    """
    A what-if scenario to evaluate.

    Describes a hypothetical action and the parameters
    under which to simulate its outcome.
    """

    scenario_id: uuid.UUID
    tenant_id: uuid.UUID
    engine: str
    description: str
    parameters: Dict[str, Any]
    created_at: datetime


# ══════════════════════════════════════════════════════════════
# SIMULATION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SimulationResult:
    """
    Outcome of a what-if simulation.

    Contains projected impacts and risk assessment.
    """

    scenario_id: uuid.UUID
    tenant_id: uuid.UUID
    engine: str
    projected_impacts: Dict[str, Any]  # key metrics that would change
    risk_level: str                    # LOW | MEDIUM | HIGH | CRITICAL
    risk_factors: List[str]
    recommendation: str
    confidence: float                  # 0.0 to 1.0
    computed_at: datetime

    def __post_init__(self) -> None:
        if self.risk_level not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValueError(f"risk_level must be LOW|MEDIUM|HIGH|CRITICAL, got {self.risk_level}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")


# ══════════════════════════════════════════════════════════════
# SIMULATION RULE
# ══════════════════════════════════════════════════════════════

SimulationFn = Callable[
    [SimulationScenario, Dict[str, Any]],
    SimulationResult,
]


# ══════════════════════════════════════════════════════════════
# SIMULATOR ENGINE
# ══════════════════════════════════════════════════════════════

class Simulator:
    """
    What-if simulation engine.

    Register simulation functions per engine, then run scenarios
    to get projected outcomes without committing state.
    """

    def __init__(self) -> None:
        self._rules: Dict[str, SimulationFn] = {}

    def register(self, engine: str, simulation_fn: SimulationFn) -> None:
        """Register a simulation function for an engine."""
        self._rules[engine] = simulation_fn

    def simulate(
        self,
        scenario: SimulationScenario,
        current_state: Dict[str, Any],
    ) -> SimulationResult:
        """
        Run a what-if simulation.

        Args:
            scenario: The hypothetical to evaluate
            current_state: Current projection state (read-only)

        Returns:
            SimulationResult with projected impacts

        Raises:
            ValueError: If no simulation rule is registered for the engine
        """
        fn = self._rules.get(scenario.engine)
        if fn is None:
            raise ValueError(
                f"No simulation rule registered for engine '{scenario.engine}'."
            )
        return fn(scenario, current_state)

    @property
    def registered_engines(self) -> List[str]:
        return list(self._rules.keys())


# ══════════════════════════════════════════════════════════════
# BUILT-IN SIMULATION FUNCTIONS
# ══════════════════════════════════════════════════════════════

def simulate_price_change(
    scenario: SimulationScenario,
    current_state: Dict[str, Any],
) -> SimulationResult:
    """Simulate the impact of changing item prices."""
    params = scenario.parameters
    item_id = params.get("item_id", "unknown")
    new_price = params.get("new_price", 0)
    old_price = current_state.get("prices", {}).get(item_id, 0)
    daily_volume = current_state.get("daily_volumes", {}).get(item_id, 0)

    if old_price == 0:
        price_change_pct = 0
    else:
        price_change_pct = (new_price - old_price) / old_price

    # Simple elasticity model
    elasticity = params.get("price_elasticity", -1.2)
    volume_change_pct = price_change_pct * elasticity
    new_volume = daily_volume * (1 + volume_change_pct)
    new_daily_revenue = new_price * new_volume
    old_daily_revenue = old_price * daily_volume
    revenue_impact = new_daily_revenue - old_daily_revenue

    risk_factors = []
    if abs(price_change_pct) > 0.2:
        risk_factors.append("Large price change (>20%) may cause customer churn")
    if new_volume < daily_volume * 0.5:
        risk_factors.append("Projected volume drop exceeds 50%")

    risk_level = "LOW"
    if len(risk_factors) >= 2:
        risk_level = "HIGH"
    elif len(risk_factors) == 1:
        risk_level = "MEDIUM"

    return SimulationResult(
        scenario_id=scenario.scenario_id,
        tenant_id=scenario.tenant_id,
        engine=scenario.engine,
        projected_impacts={
            "price_change_pct": round(price_change_pct * 100, 1),
            "volume_change_pct": round(volume_change_pct * 100, 1),
            "new_daily_volume": round(new_volume, 1),
            "daily_revenue_impact": round(revenue_impact, 2),
        },
        risk_level=risk_level,
        risk_factors=risk_factors,
        recommendation=(
            f"Price change from {old_price} to {new_price} projected to "
            f"{'increase' if revenue_impact > 0 else 'decrease'} daily revenue by "
            f"{abs(revenue_impact):.2f}."
        ),
        confidence=0.65,
        computed_at=scenario.created_at,
    )


def simulate_reorder(
    scenario: SimulationScenario,
    current_state: Dict[str, Any],
) -> SimulationResult:
    """Simulate the impact of a reorder decision."""
    params = scenario.parameters
    item_id = params.get("item_id", "unknown")
    order_qty = params.get("order_quantity", 0)
    unit_cost = params.get("unit_cost", 0)
    current_stock = current_state.get("stock_levels", {}).get(item_id, 0)
    daily_consumption = current_state.get("consumption_rates", {}).get(item_id, 0)
    lead_time_days = params.get("lead_time_days", 7)

    stock_after_order = current_stock + order_qty
    days_coverage = (
        stock_after_order / daily_consumption
        if daily_consumption > 0
        else float("inf")
    )
    total_cost = order_qty * unit_cost
    stockout_risk = current_stock < (daily_consumption * lead_time_days)

    risk_factors = []
    if stockout_risk:
        risk_factors.append("Current stock may not last until delivery arrives")
    if days_coverage > 90:
        risk_factors.append("Order creates >90 days coverage — risk of obsolescence")

    risk_level = "LOW"
    if stockout_risk:
        risk_level = "HIGH"
    elif days_coverage > 90:
        risk_level = "MEDIUM"

    return SimulationResult(
        scenario_id=scenario.scenario_id,
        tenant_id=scenario.tenant_id,
        engine=scenario.engine,
        projected_impacts={
            "stock_after_order": stock_after_order,
            "days_coverage": round(days_coverage, 1),
            "total_cost": total_cost,
            "stockout_before_delivery": stockout_risk,
        },
        risk_level=risk_level,
        risk_factors=risk_factors,
        recommendation=(
            f"Order {order_qty} units of {item_id} at {unit_cost}/unit "
            f"(total {total_cost:.2f}). Provides {days_coverage:.0f} days coverage."
        ),
        confidence=0.80,
        computed_at=scenario.created_at,
    )
