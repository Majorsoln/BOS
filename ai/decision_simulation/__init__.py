"""
BOS Decision Simulation — Public API
========================================
What-if scenario engine for projected outcome analysis.
"""

from ai.decision_simulation.simulator import (
    SimulationScenario,
    SimulationResult,
    Simulator,
    simulate_price_change,
    simulate_reorder,
)

__all__ = [
    "SimulationScenario",
    "SimulationResult",
    "Simulator",
    "simulate_price_change",
    "simulate_reorder",
]
