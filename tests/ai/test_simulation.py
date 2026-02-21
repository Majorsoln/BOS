"""
Tests for ai.decision_simulation — What-if scenario engine.
"""

import uuid
import pytest
from datetime import datetime, timezone

from ai.decision_simulation.simulator import (
    SimulationScenario,
    SimulationResult,
    Simulator,
    simulate_price_change,
    simulate_reorder,
)


BIZ_ID = uuid.uuid4()
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _scenario(engine: str, **params) -> SimulationScenario:
    return SimulationScenario(
        scenario_id=uuid.uuid4(),
        tenant_id=BIZ_ID,
        engine=engine,
        description="Test scenario",
        parameters=params,
        created_at=NOW,
    )


# ── SimulationResult Tests ───────────────────────────────────

class TestSimulationResult:
    def test_valid_result(self):
        result = SimulationResult(
            scenario_id=uuid.uuid4(),
            tenant_id=BIZ_ID,
            engine="retail",
            projected_impacts={"revenue": 1000},
            risk_level="LOW",
            risk_factors=[],
            recommendation="Proceed",
            confidence=0.8,
            computed_at=NOW,
        )
        assert result.risk_level == "LOW"

    def test_invalid_risk_level(self):
        with pytest.raises(ValueError, match="risk_level"):
            SimulationResult(
                scenario_id=uuid.uuid4(),
                tenant_id=BIZ_ID,
                engine="test",
                projected_impacts={},
                risk_level="INVALID",
                risk_factors=[],
                recommendation="",
                confidence=0.5,
                computed_at=NOW,
            )

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            SimulationResult(
                scenario_id=uuid.uuid4(),
                tenant_id=BIZ_ID,
                engine="test",
                projected_impacts={},
                risk_level="LOW",
                risk_factors=[],
                recommendation="",
                confidence=2.0,
                computed_at=NOW,
            )


# ── Simulator Engine Tests ───────────────────────────────────

class TestSimulator:
    def test_register_and_simulate(self):
        sim = Simulator()
        sim.register("retail", simulate_price_change)
        assert "retail" in sim.registered_engines

        scenario = _scenario(
            "retail",
            item_id="ITEM-1",
            new_price=12.0,
        )
        state = {
            "prices": {"ITEM-1": 10.0},
            "daily_volumes": {"ITEM-1": 100},
        }
        result = sim.simulate(scenario, state)
        assert result.scenario_id == scenario.scenario_id
        assert "daily_revenue_impact" in result.projected_impacts

    def test_unregistered_engine_raises(self):
        sim = Simulator()
        scenario = _scenario("unknown")
        with pytest.raises(ValueError, match="No simulation rule"):
            sim.simulate(scenario, {})


# ── Price Change Simulation Tests ────────────────────────────

class TestPriceChangeSimulation:
    def test_price_increase(self):
        scenario = _scenario(
            "retail",
            item_id="ITEM-1",
            new_price=12.0,
        )
        state = {
            "prices": {"ITEM-1": 10.0},
            "daily_volumes": {"ITEM-1": 100},
        }
        result = simulate_price_change(scenario, state)
        assert result.projected_impacts["price_change_pct"] == 20.0
        assert result.confidence > 0

    def test_large_price_change_flags_risk(self):
        scenario = _scenario(
            "retail",
            item_id="ITEM-1",
            new_price=15.0,  # 50% increase
        )
        state = {
            "prices": {"ITEM-1": 10.0},
            "daily_volumes": {"ITEM-1": 100},
        }
        result = simulate_price_change(scenario, state)
        assert len(result.risk_factors) > 0
        assert result.risk_level in ("MEDIUM", "HIGH")

    def test_zero_price_no_crash(self):
        scenario = _scenario("retail", item_id="NEW", new_price=5.0)
        state = {"prices": {}, "daily_volumes": {}}
        result = simulate_price_change(scenario, state)
        assert result.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ── Reorder Simulation Tests ────────────────────────────────

class TestReorderSimulation:
    def test_reorder_with_adequate_stock(self):
        scenario = _scenario(
            "inventory",
            item_id="SKU-1",
            order_quantity=100,
            unit_cost=5.0,
            lead_time_days=7,
        )
        state = {
            "stock_levels": {"SKU-1": 50},
            "consumption_rates": {"SKU-1": 5},
        }
        result = simulate_reorder(scenario, state)
        assert result.projected_impacts["stock_after_order"] == 150
        assert result.projected_impacts["total_cost"] == 500.0
        assert result.risk_level == "LOW"

    def test_reorder_with_stockout_risk(self):
        scenario = _scenario(
            "inventory",
            item_id="SKU-2",
            order_quantity=50,
            unit_cost=3.0,
            lead_time_days=14,
        )
        state = {
            "stock_levels": {"SKU-2": 10},
            "consumption_rates": {"SKU-2": 5},
        }
        result = simulate_reorder(scenario, state)
        assert result.projected_impacts["stockout_before_delivery"] is True
        assert result.risk_level == "HIGH"
        assert any("stockout" in f.lower() or "delivery" in f.lower()
                    for f in result.risk_factors)

    def test_reorder_excessive_coverage(self):
        scenario = _scenario(
            "inventory",
            item_id="SKU-3",
            order_quantity=1000,
            unit_cost=2.0,
            lead_time_days=3,
        )
        state = {
            "stock_levels": {"SKU-3": 100},
            "consumption_rates": {"SKU-3": 5},
        }
        result = simulate_reorder(scenario, state)
        assert result.projected_impacts["days_coverage"] > 90
        assert result.risk_level == "MEDIUM"
