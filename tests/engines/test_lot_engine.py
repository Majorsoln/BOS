"""
BOS GAP-07 — Inventory FIFO/LIFO/WAC Lot Tracking Tests
==========================================================
Tests the lot engine, lot store, and projection store integration.
"""

import uuid
from datetime import datetime, timezone

import pytest

from engines.inventory.lot_engine import (
    LotLedger, LotStore, StockLot, ConsumedLot,
    LotConsumptionResult, ValuationMethod,
)
from engines.inventory.services import InventoryProjectionStore

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════
# UNIT: LotLedger
# ══════════════════════════════════════════════════════════════

class TestLotLedger:
    def test_receive_adds_lot(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 100, 1500, "2026-01-01")
        assert ledger.get_total_quantity() == 100
        assert ledger.get_total_value() == 150000  # 100 × 1500
        assert ledger.lot_count == 1

    def test_receive_multiple_lots(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 50, 1000, "2026-01-01")
        ledger.receive("LOT-2", 30, 1200, "2026-01-15")
        assert ledger.get_total_quantity() == 80
        assert ledger.get_total_value() == 50 * 1000 + 30 * 1200  # 86000

    def test_receive_rejects_zero_quantity(self):
        ledger = LotLedger()
        with pytest.raises(ValueError, match="positive"):
            ledger.receive("LOT-1", 0, 1500, "2026-01-01")

    def test_receive_rejects_negative_cost(self):
        ledger = LotLedger()
        with pytest.raises(ValueError, match="negative"):
            ledger.receive("LOT-1", 10, -100, "2026-01-01")

    # ── FIFO ──────────────────────────────────────────────────

    def test_fifo_consumes_oldest_first(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 50, 1000, "2026-01-01")   # old, cheap
        ledger.receive("LOT-2", 30, 1500, "2026-02-01")   # new, expensive

        result = ledger.consume(40, ValuationMethod.FIFO)
        assert result.fully_fulfilled
        assert result.quantity_consumed == 40
        assert result.total_cost == 40 * 1000   # all from LOT-1
        assert len(result.consumed) == 1
        assert result.consumed[0].lot_id == "LOT-1"
        assert result.consumed[0].unit_cost == 1000

    def test_fifo_spans_multiple_lots(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 20, 1000, "2026-01-01")
        ledger.receive("LOT-2", 30, 1500, "2026-02-01")

        result = ledger.consume(35, ValuationMethod.FIFO)
        assert result.fully_fulfilled
        assert result.quantity_consumed == 35
        assert len(result.consumed) == 2
        assert result.consumed[0].lot_id == "LOT-1"
        assert result.consumed[0].quantity_consumed == 20
        assert result.consumed[1].lot_id == "LOT-2"
        assert result.consumed[1].quantity_consumed == 15
        expected_cost = 20 * 1000 + 15 * 1500  # 42500
        assert result.total_cost == expected_cost

    def test_fifo_understock(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 10, 1000, "2026-01-01")

        result = ledger.consume(25, ValuationMethod.FIFO)
        assert not result.fully_fulfilled
        assert result.quantity_consumed == 10
        assert result.quantity_unfulfilled == 15
        assert result.total_cost == 10000

    # ── LIFO ──────────────────────────────────────────────────

    def test_lifo_consumes_newest_first(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 50, 1000, "2026-01-01")   # old
        ledger.receive("LOT-2", 30, 1500, "2026-02-01")   # new

        result = ledger.consume(25, ValuationMethod.LIFO)
        assert result.fully_fulfilled
        assert result.quantity_consumed == 25
        assert result.total_cost == 25 * 1500   # all from LOT-2 (newest)
        assert result.consumed[0].lot_id == "LOT-2"

    def test_lifo_spans_multiple_lots(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 20, 1000, "2026-01-01")
        ledger.receive("LOT-2", 10, 1500, "2026-02-01")

        result = ledger.consume(25, ValuationMethod.LIFO)
        assert result.fully_fulfilled
        assert len(result.consumed) == 2
        assert result.consumed[0].lot_id == "LOT-2"
        assert result.consumed[0].quantity_consumed == 10
        assert result.consumed[1].lot_id == "LOT-1"
        assert result.consumed[1].quantity_consumed == 15
        expected_cost = 10 * 1500 + 15 * 1000
        assert result.total_cost == expected_cost

    # ── WAC ───────────────────────────────────────────────────

    def test_wac_uses_weighted_average(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 50, 1000, "2026-01-01")
        ledger.receive("LOT-2", 50, 2000, "2026-02-01")
        # WAC = (50*1000 + 50*2000) / 100 = 1500

        result = ledger.consume(30, ValuationMethod.WAC)
        assert result.fully_fulfilled
        assert result.quantity_consumed == 30
        # Each consumed unit at WAC=1500
        assert result.total_cost == 30 * 1500

    def test_weighted_average_cost(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 60, 1000, "2026-01-01")
        ledger.receive("LOT-2", 40, 2000, "2026-02-01")
        # WAC = (60000 + 80000) / 100 = 1400
        assert ledger.get_weighted_average_cost() == 1400

    def test_wac_empty_ledger(self):
        ledger = LotLedger()
        assert ledger.get_weighted_average_cost() == 0

    # ── Snapshots ─────────────────────────────────────────────

    def test_get_lots_returns_immutable_snapshots(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 10, 500, "2026-01-01", "PO-001")
        lots = ledger.get_lots()
        assert len(lots) == 1
        assert isinstance(lots[0], StockLot)
        assert lots[0].lot_id == "LOT-1"
        assert lots[0].quantity_original == 10
        assert lots[0].quantity_remaining == 10
        assert lots[0].unit_cost == 500
        assert lots[0].reference_id == "PO-001"
        assert lots[0].current_value == 5000

    def test_get_active_lots_excludes_exhausted(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 5, 1000, "2026-01-01")
        ledger.receive("LOT-2", 10, 2000, "2026-02-01")
        ledger.consume(5, ValuationMethod.FIFO)  # exhausts LOT-1
        active = ledger.get_active_lots()
        assert len(active) == 1
        assert active[0].lot_id == "LOT-2"
        # All lots still includes exhausted
        assert len(ledger.get_lots()) == 2

    def test_consume_rejects_zero(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 10, 1000, "2026-01-01")
        with pytest.raises(ValueError, match="positive"):
            ledger.consume(0, ValuationMethod.FIFO)

    def test_cost_per_unit(self):
        ledger = LotLedger()
        ledger.receive("LOT-1", 20, 1000, "2026-01-01")
        ledger.receive("LOT-2", 30, 1500, "2026-02-01")
        result = ledger.consume(35, ValuationMethod.FIFO)
        # 20×1000 + 15×1500 = 42500, 42500//35 = 1214
        assert result.cost_per_unit == 42500 // 35


# ══════════════════════════════════════════════════════════════
# UNIT: LotStore (multi-item, multi-location)
# ══════════════════════════════════════════════════════════════

class TestLotStore:
    def test_auto_lot_id_generation(self):
        store = LotStore()
        lot1 = store.receive("ITEM-1", "WH-A", 10, 500, "2026-01-01")
        lot2 = store.receive("ITEM-1", "WH-A", 20, 600, "2026-01-15")
        assert lot1 == "LOT-ITEM-1-WH-A-0001"
        assert lot2 == "LOT-ITEM-1-WH-A-0002"

    def test_per_item_valuation_method(self):
        store = LotStore(default_method=ValuationMethod.FIFO)
        store.set_item_method("ITEM-X", ValuationMethod.LIFO)
        assert store.get_method("ITEM-X") == ValuationMethod.LIFO
        assert store.get_method("ITEM-Y") == ValuationMethod.FIFO

    def test_consume_uses_item_method(self):
        store = LotStore()
        store.set_item_method("ITEM-X", ValuationMethod.LIFO)
        store.receive("ITEM-X", "WH-A", 10, 1000, "2026-01-01")
        store.receive("ITEM-X", "WH-A", 10, 2000, "2026-02-01")
        result = store.consume("ITEM-X", "WH-A", 5)
        # LIFO: should consume from newest lot (2000 cost)
        assert result.consumed[0].unit_cost == 2000
        assert result.method == ValuationMethod.LIFO

    def test_stock_value_per_location(self):
        store = LotStore()
        store.receive("ITEM-1", "WH-A", 10, 1000, "2026-01-01")
        store.receive("ITEM-1", "WH-B", 20, 500, "2026-01-01")
        assert store.get_stock_value("ITEM-1", "WH-A") == 10000
        assert store.get_stock_value("ITEM-1", "WH-B") == 10000

    def test_total_inventory_value(self):
        store = LotStore()
        store.receive("ITEM-1", "WH-A", 10, 1000, "2026-01-01")
        store.receive("ITEM-2", "WH-A", 5, 2000, "2026-01-01")
        assert store.total_inventory_value() == 10 * 1000 + 5 * 2000


# ══════════════════════════════════════════════════════════════
# INTEGRATION: InventoryProjectionStore + LotStore
# ══════════════════════════════════════════════════════════════

class TestProjectionStoreLotIntegration:
    def test_stock_received_with_cost_creates_lot(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 50,
            "unit_cost": {"amount": 1500, "currency": "KES"},
            "reference_id": "PO-001",
        })
        assert ps.get_stock("ITM-1", "WH-A") == 50
        lots = ps.get_active_lots("ITM-1", "WH-A")
        assert len(lots) == 1
        assert lots[0].unit_cost == 1500
        assert lots[0].quantity_remaining == 50
        assert ps.get_stock_value("ITM-1", "WH-A") == 50 * 1500

    def test_stock_received_without_cost_no_lot(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 10,
        })
        assert ps.get_stock("ITM-1", "WH-A") == 10
        assert ps.get_active_lots("ITM-1", "WH-A") == []

    def test_stock_issued_consumes_fifo(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 20,
            "unit_cost": {"amount": 1000, "currency": "KES"},
        })
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 30,
            "unit_cost": {"amount": 2000, "currency": "KES"},
        })
        ps.apply("inventory.stock.issued.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 25,
        })
        assert ps.get_stock("ITM-1", "WH-A") == 25
        active = ps.get_active_lots("ITM-1", "WH-A")
        # FIFO: 20 from LOT-1 (exhausted), 5 from LOT-2 (25 remaining)
        assert len(active) == 1
        assert active[0].quantity_remaining == 25
        assert active[0].unit_cost == 2000

    def test_stock_issued_lifo_mode(self):
        ps = InventoryProjectionStore(default_valuation=ValuationMethod.LIFO)
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 20,
            "unit_cost": {"amount": 1000, "currency": "KES"},
        })
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 30,
            "unit_cost": {"amount": 2000, "currency": "KES"},
        })
        ps.apply("inventory.stock.issued.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 25,
        })
        active = ps.get_active_lots("ITM-1", "WH-A")
        # LIFO: 25 from LOT-2 (newest, 5 remaining), LOT-1 untouched
        assert len(active) == 2
        lot1 = [l for l in active if l.unit_cost == 1000][0]
        lot2 = [l for l in active if l.unit_cost == 2000][0]
        assert lot1.quantity_remaining == 20
        assert lot2.quantity_remaining == 5

    def test_stock_transferred_moves_cost(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 40,
            "unit_cost": {"amount": 1000, "currency": "KES"},
        })
        ps.apply("inventory.stock.transferred.v1", {
            "item_id": "ITM-1",
            "from_location_id": "WH-A", "to_location_id": "WH-B",
            "quantity": 15,
        })
        assert ps.get_stock("ITM-1", "WH-A") == 25
        assert ps.get_stock("ITM-1", "WH-B") == 15
        # Value should transfer at the consumed cost
        assert ps.get_stock_value("ITM-1", "WH-A") == 25 * 1000
        dest_lots = ps.get_active_lots("ITM-1", "WH-B")
        assert len(dest_lots) == 1
        assert dest_lots[0].quantity_remaining == 15
        assert dest_lots[0].unit_cost == 1000

    def test_stock_adjusted_plus_zero_cost(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.adjusted.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 5,
            "adjustment_type": "ADJUST_PLUS",
        })
        assert ps.get_stock("ITM-1", "WH-A") == 5
        lots = ps.get_active_lots("ITM-1", "WH-A")
        assert len(lots) == 1
        assert lots[0].unit_cost == 0  # found stock has zero cost

    def test_total_inventory_value(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "A", "location_id": "W1", "quantity": 10,
            "unit_cost": {"amount": 500, "currency": "KES"},
        })
        ps.apply("inventory.stock.received.v1", {
            "item_id": "B", "location_id": "W2", "quantity": 5,
            "unit_cost": {"amount": 3000, "currency": "KES"},
        })
        assert ps.total_inventory_value() == 10 * 500 + 5 * 3000

    def test_weighted_average_cost(self):
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 60,
            "unit_cost": {"amount": 1000, "currency": "KES"},
        })
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 40,
            "unit_cost": {"amount": 2000, "currency": "KES"},
        })
        # (60*1000 + 40*2000) / 100 = 1400
        assert ps.get_weighted_average_cost("ITM-1", "WH-A") == 1400

    def test_per_item_valuation_override(self):
        ps = InventoryProjectionStore()
        ps.set_item_valuation("ITM-LIFO", ValuationMethod.LIFO)
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-LIFO", "location_id": "WH-A", "quantity": 10,
            "unit_cost": {"amount": 100, "currency": "KES"},
        })
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-LIFO", "location_id": "WH-A", "quantity": 10,
            "unit_cost": {"amount": 200, "currency": "KES"},
        })
        ps.apply("inventory.stock.issued.v1", {
            "item_id": "ITM-LIFO", "location_id": "WH-A", "quantity": 5,
        })
        active = ps.get_active_lots("ITM-LIFO", "WH-A")
        lot_100 = [l for l in active if l.unit_cost == 100][0]
        lot_200 = [l for l in active if l.unit_cost == 200][0]
        assert lot_100.quantity_remaining == 10  # untouched
        assert lot_200.quantity_remaining == 5   # consumed 5 from newest

    def test_unit_cost_as_integer(self):
        """unit_cost can be plain int instead of dict."""
        ps = InventoryProjectionStore()
        ps.apply("inventory.stock.received.v1", {
            "item_id": "ITM-1", "location_id": "WH-A", "quantity": 10,
            "unit_cost": 750,
        })
        assert ps.get_stock_value("ITM-1", "WH-A") == 7500
