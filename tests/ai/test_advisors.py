"""
Tests for ai.advisors — Domain-specific advisory modules.
"""

import uuid
import pytest
from datetime import datetime, timezone

from ai.advisors.base import Advisory
from ai.advisors.inventory_advisor import InventoryAdvisor
from ai.advisors.cash_advisor import CashAdvisor
from ai.advisors.procurement_advisor import ProcurementAdvisor
from ai.journal.models import DecisionMode


BIZ_ID = uuid.uuid4()
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


# ── Advisory Model Tests ─────────────────────────────────────

class TestAdvisory:
    def test_valid_advisory(self):
        adv = Advisory(
            engine="inventory",
            advice_type="reorder_suggestion",
            title="Low stock: SKU-001",
            description="Stock is below reorder point.",
            confidence=0.85,
            recommended_action="Reorder 50 units",
        )
        assert adv.confidence == 0.85

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            Advisory(
                engine="test",
                advice_type="test",
                title="T",
                description="D",
                confidence=1.5,
            )

    def test_to_advice_payload(self):
        adv = Advisory(
            engine="cash",
            advice_type="anomaly_flag",
            title="Variance",
            description="Cash variance detected",
            confidence=0.9,
            recommended_action="Investigate",
            data={"amount": 500},
        )
        payload = adv.to_advice_payload()
        assert payload["title"] == "Variance"
        assert payload["data"]["amount"] == 500


# ── Inventory Advisor Tests ──────────────────────────────────

class TestInventoryAdvisor:
    def test_low_stock_detection(self):
        advisor = InventoryAdvisor()
        assert advisor.engine_name == "inventory"

        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "stock_levels": {"SKU-001": 5},
                "reorder_points": {"SKU-001": 10},
                "consumption_rates": {"SKU-001": 2},
            },
            now=NOW,
        )
        assert len(advisories) >= 1
        reorder = [a for a in advisories if a.advice_type == "reorder_suggestion"]
        assert len(reorder) == 1
        assert "SKU-001" in reorder[0].title

    def test_stockout_detection(self):
        advisor = InventoryAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "stock_levels": {"SKU-002": 0},
                "reorder_points": {"SKU-002": 10},
                "consumption_rates": {"SKU-002": 5},
            },
            now=NOW,
        )
        anomalies = [a for a in advisories if a.advice_type == "anomaly_flag"]
        assert len(anomalies) >= 1
        assert anomalies[0].confidence >= 0.9

    def test_slow_mover_detection(self):
        advisor = InventoryAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "stock_levels": {},
                "reorder_points": {},
                "consumption_rates": {},
                "slow_movers": [
                    {"item_id": "SKU-OLD", "days_stale": 120},
                ],
            },
            now=NOW,
        )
        optimizations = [a for a in advisories if a.advice_type == "optimization"]
        assert len(optimizations) == 1

    def test_no_issues_returns_empty(self):
        advisor = InventoryAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "stock_levels": {"SKU-OK": 100},
                "reorder_points": {"SKU-OK": 10},
                "consumption_rates": {"SKU-OK": 1},
            },
            now=NOW,
        )
        assert len(advisories) == 0


# ── Cash Advisor Tests ───────────────────────────────────────

class TestCashAdvisor:
    def test_variance_detection(self):
        advisor = CashAdvisor()
        assert advisor.engine_name == "cash"

        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "sessions": [
                    {
                        "session_id": "sess-1",
                        "expected_balance": 10000,
                        "actual_balance": 9500,
                        "variance_threshold": 100,
                    }
                ],
            },
            now=NOW,
        )
        anomalies = [a for a in advisories if a.advice_type == "anomaly_flag"]
        assert len(anomalies) == 1
        assert "500" in anomalies[0].description

    def test_float_optimization(self):
        advisor = CashAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "sessions": [],
                "float_analysis": {
                    "average_float": 50000,
                    "peak_demand": 15000,
                },
            },
            now=NOW,
        )
        optimizations = [a for a in advisories if a.advice_type == "optimization"]
        assert len(optimizations) == 1

    def test_no_issues(self):
        advisor = CashAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "sessions": [
                    {
                        "session_id": "ok",
                        "expected_balance": 1000,
                        "actual_balance": 1000,
                        "variance_threshold": 100,
                    }
                ],
            },
            now=NOW,
        )
        assert len(advisories) == 0


# ── Procurement Advisor Tests ────────────────────────────────

class TestProcurementAdvisor:
    def test_supplier_delay_detection(self):
        advisor = ProcurementAdvisor()
        assert advisor.engine_name == "procurement"

        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "supplier_performance": [
                    {
                        "supplier_id": "SUP-1",
                        "on_time_delivery_rate": 0.6,
                        "defect_rate": 0.02,
                    }
                ],
                "pending_orders": [],
            },
            now=NOW,
        )
        anomalies = [a for a in advisories if a.advice_type == "anomaly_flag"]
        assert len(anomalies) >= 1
        assert "SUP-1" in anomalies[0].title

    def test_quality_issue_detection(self):
        advisor = ProcurementAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "supplier_performance": [
                    {
                        "supplier_id": "SUP-2",
                        "on_time_delivery_rate": 0.95,
                        "defect_rate": 0.10,
                    }
                ],
                "pending_orders": [],
            },
            now=NOW,
        )
        quality = [a for a in advisories if "Quality" in a.title]
        assert len(quality) == 1

    def test_order_consolidation(self):
        advisor = ProcurementAdvisor()
        advisories = advisor.analyze(
            tenant_id=BIZ_ID,
            context={
                "supplier_performance": [],
                "pending_orders": [
                    {"supplier_id": "SUP-A", "value": 100},
                    {"supplier_id": "SUP-A", "value": 200},
                    {"supplier_id": "SUP-A", "value": 300},
                ],
            },
            now=NOW,
        )
        consolidations = [a for a in advisories if a.advice_type == "optimization"]
        assert len(consolidations) == 1
        assert consolidations[0].data["order_count"] == 3


# ── Decision Entry Creation ──────────────────────────────────

class TestDecisionEntryCreation:
    def test_advisor_creates_decision_entry(self):
        advisor = InventoryAdvisor()
        advisory = Advisory(
            engine="inventory",
            advice_type="reorder_suggestion",
            title="Test",
            description="Test description",
            confidence=0.8,
        )
        entry = advisor.create_decision_entry(
            advisory=advisory,
            tenant_id=BIZ_ID,
            mode=DecisionMode.ADVISORY,
            now=NOW,
        )
        assert entry.engine == "inventory"
        assert entry.is_pending()
        assert entry.tenant_id == BIZ_ID
