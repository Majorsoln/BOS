"""
Tests — Cross-Engine Read Models
====================================
Retail, Finance, Inventory, Restaurant, Workshop read models.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pytest

from projections.retail import RetailReadModel
from projections.finance import FinanceReadModel
from projections.inventory import InventoryReadModel
from projections.restaurant import RestaurantReadModel
from projections.workshop import WorkshopReadModel
from projections.guards import FreshnessGuard, StalenessPolicy, FreshnessCheck


BIZ = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════
# RETAIL READ MODEL
# ══════════════════════════════════════════════════════════════


class TestRetailReadModel:
    def test_sale_completed_tracks_revenue(self):
        rm = RetailReadModel()
        rm.apply("retail.sale.completed.v1", {
            "sale_id": "S1", "business_id": str(BIZ),
            "total": "500.00", "currency": "USD", "line_count": 3,
        })
        assert rm.get_revenue(BIZ) == Decimal("500.00")
        assert rm.get_sale_count(BIZ) == 1

    def test_void_reverses_revenue(self):
        rm = RetailReadModel()
        rm.apply("retail.sale.completed.v1", {
            "sale_id": "S1", "business_id": str(BIZ), "total": "300",
        })
        rm.apply("retail.sale.voided.v1", {
            "sale_id": "S1", "business_id": str(BIZ),
        })
        assert rm.get_revenue(BIZ) == Decimal(0)
        assert rm.get_sale("S1").status == "VOIDED"

    def test_refund_tracked(self):
        rm = RetailReadModel()
        rm.apply("retail.sale.completed.v1", {
            "sale_id": "S1", "business_id": str(BIZ), "total": "1000",
        })
        rm.apply("retail.refund.recorded.v1", {
            "business_id": str(BIZ), "refund_amount": "200",
        })
        assert rm.get_net_revenue(BIZ) == Decimal("800")

    def test_truncate_business_scoped(self):
        rm = RetailReadModel()
        biz2 = uuid.uuid4()
        rm.apply("retail.sale.completed.v1", {"sale_id": "S1", "business_id": str(BIZ), "total": "100"})
        rm.apply("retail.sale.completed.v1", {"sale_id": "S2", "business_id": str(biz2), "total": "200"})
        rm.truncate(BIZ)
        assert rm.get_sale_count(BIZ) == 0
        assert rm.get_sale_count(biz2) == 1

    def test_snapshot(self):
        rm = RetailReadModel()
        rm.apply("retail.sale.completed.v1", {"sale_id": "S1", "business_id": str(BIZ), "total": "500"})
        snap = rm.snapshot(BIZ)
        assert snap["sale_count"] == 1
        assert snap["revenue"] == "500"


# ══════════════════════════════════════════════════════════════
# FINANCE READ MODEL
# ══════════════════════════════════════════════════════════════


class TestFinanceReadModel:
    def test_journal_posted_updates_balances(self):
        fm = FinanceReadModel()
        fm.apply("accounting.journal.posted.v1", {
            "business_id": str(BIZ),
            "lines": [
                {"account_code": "1000", "debit": "500", "credit": "0"},
                {"account_code": "4000", "debit": "0", "credit": "500"},
            ],
        })
        assert fm.get_journal_count(BIZ) == 1
        bal_1000 = fm.get_account_balance(BIZ, "1000")
        assert bal_1000.debit_total == Decimal("500")
        bal_4000 = fm.get_account_balance(BIZ, "4000")
        assert bal_4000.credit_total == Decimal("500")

    def test_cash_position(self):
        fm = FinanceReadModel()
        fm.apply("cash.session.closed.v1", {
            "business_id": str(BIZ), "closing_balance": "1234.56",
        })
        assert fm.get_cash_position(BIZ) == Decimal("1234.56")

    def test_trial_balance(self):
        fm = FinanceReadModel()
        fm.apply("accounting.journal.posted.v1", {
            "business_id": str(BIZ),
            "lines": [
                {"account_code": "1000", "debit": "100", "credit": "0"},
                {"account_code": "2000", "debit": "0", "credit": "100"},
            ],
        })
        tb = fm.get_trial_balance(BIZ)
        assert len(tb) == 2
        assert tb["1000"].balance == Decimal("100")
        assert tb["2000"].balance == Decimal("-100")

    def test_snapshot(self):
        fm = FinanceReadModel()
        fm.apply("accounting.journal.posted.v1", {
            "business_id": str(BIZ),
            "lines": [{"account_code": "1000", "debit": "100", "credit": "0"}],
        })
        snap = fm.snapshot(BIZ)
        assert snap["journal_count"] == 1
        assert snap["account_count"] == 1


# ══════════════════════════════════════════════════════════════
# INVENTORY READ MODEL
# ══════════════════════════════════════════════════════════════


class TestInventoryReadModel:
    def test_receive_increases_stock(self):
        im = InventoryReadModel()
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "50",
        })
        sl = im.get_stock(BIZ, "ITEM-1", "WH-1")
        assert sl.quantity == Decimal("50")
        assert sl.available == Decimal("50")

    def test_issue_decreases_stock(self):
        im = InventoryReadModel()
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "50",
        })
        im.apply("inventory.stock.issued.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "20",
        })
        sl = im.get_stock(BIZ, "ITEM-1", "WH-1")
        assert sl.quantity == Decimal("30")

    def test_transfer_moves_between_locations(self):
        im = InventoryReadModel()
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "100",
        })
        im.apply("inventory.stock.transferred.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "from_location_id": "WH-1", "to_location_id": "WH-2",
            "quantity": "30",
        })
        assert im.get_stock(BIZ, "ITEM-1", "WH-1").quantity == Decimal("70")
        assert im.get_stock(BIZ, "ITEM-1", "WH-2").quantity == Decimal("30")

    def test_reserved_reduces_available(self):
        im = InventoryReadModel()
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "100",
        })
        im.apply("inventory.stock.reserved.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "25",
        })
        sl = im.get_stock(BIZ, "ITEM-1", "WH-1")
        assert sl.quantity == Decimal("100")
        assert sl.reserved == Decimal("25")
        assert sl.available == Decimal("75")

    def test_total_stock_across_locations(self):
        im = InventoryReadModel()
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "50",
        })
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-2", "quantity": "30",
        })
        assert im.get_total_stock(BIZ, "ITEM-1") == Decimal("80")

    def test_snapshot(self):
        im = InventoryReadModel()
        im.apply("inventory.stock.received.v1", {
            "business_id": str(BIZ), "item_id": "ITEM-1",
            "location_id": "WH-1", "quantity": "100",
        })
        snap = im.snapshot(BIZ)
        assert snap["item_count"] == 1
        assert snap["movement_count"] == 1


# ══════════════════════════════════════════════════════════════
# RESTAURANT READ MODEL
# ══════════════════════════════════════════════════════════════


class TestRestaurantReadModel:
    def test_order_lifecycle(self):
        rm = RestaurantReadModel()
        rm.apply("restaurant.order.created.v1", {
            "business_id": str(BIZ), "order_id": "ORD-1", "item_count": 3,
        })
        rm.apply("restaurant.order.completed.v1", {
            "business_id": str(BIZ), "order_id": "ORD-1", "total": "75.50",
        })
        assert rm.get_order_count(BIZ) == 1
        assert rm.get_revenue(BIZ) == Decimal("75.50")

    def test_cancelled_order_no_revenue(self):
        rm = RestaurantReadModel()
        rm.apply("restaurant.order.created.v1", {
            "business_id": str(BIZ), "order_id": "ORD-1",
        })
        rm.apply("restaurant.order.cancelled.v1", {
            "business_id": str(BIZ), "order_id": "ORD-1",
        })
        assert rm.get_revenue(BIZ) == Decimal(0)

    def test_kitchen_tickets(self):
        rm = RestaurantReadModel()
        rm.apply("restaurant.kitchen.ticket.sent.v1", {"business_id": str(BIZ)})
        rm.apply("restaurant.kitchen.ticket.sent.v1", {"business_id": str(BIZ)})
        assert rm.get_tickets_sent(BIZ) == 2


# ══════════════════════════════════════════════════════════════
# WORKSHOP READ MODEL
# ══════════════════════════════════════════════════════════════


class TestWorkshopReadModel:
    def test_job_lifecycle(self):
        wm = WorkshopReadModel()
        wm.apply("workshop.job.created.v1", {
            "business_id": str(BIZ), "job_id": "J1",
        })
        wm.apply("workshop.job.completed.v1", {
            "business_id": str(BIZ), "job_id": "J1",
        })
        assert wm.get_job_count(BIZ) == 1

    def test_material_consumption(self):
        wm = WorkshopReadModel()
        wm.apply("workshop.job.created.v1", {
            "business_id": str(BIZ), "job_id": "J1",
        })
        wm.apply("workshop.material.consumed.v1", {
            "business_id": str(BIZ), "job_id": "J1", "cost": "250.00",
        })
        assert wm.get_material_consumed(BIZ) == Decimal("250.00")

    def test_offcut_tracking(self):
        wm = WorkshopReadModel()
        wm.apply("workshop.job.created.v1", {
            "business_id": str(BIZ), "job_id": "J1",
        })
        wm.apply("workshop.offcut.recorded.v1", {
            "business_id": str(BIZ), "job_id": "J1",
        })
        assert wm.get_offcut_count(BIZ) == 1

    def test_snapshot(self):
        wm = WorkshopReadModel()
        wm.apply("workshop.job.created.v1", {"business_id": str(BIZ), "job_id": "J1"})
        snap = wm.snapshot(BIZ)
        assert snap["job_count"] == 1


# ══════════════════════════════════════════════════════════════
# FRESHNESS GUARD
# ══════════════════════════════════════════════════════════════


class TestFreshnessGuard:
    def test_no_policy_always_fresh(self):
        fg = FreshnessGuard()
        check = fg.check("any_projection", T0)
        assert check.is_fresh is True

    def test_never_updated_is_stale(self):
        fg = FreshnessGuard()
        fg.set_policy(StalenessPolicy(
            projection_name="p1", max_staleness_seconds=60,
        ))
        check = fg.check("p1", T0)
        assert check.is_fresh is False

    def test_recently_updated_is_fresh(self):
        fg = FreshnessGuard()
        fg.set_policy(StalenessPolicy(
            projection_name="p1", max_staleness_seconds=60,
        ))
        fg.record_update("p1", T0)
        check = fg.check("p1", T0 + timedelta(seconds=30))
        assert check.is_fresh is True
        assert check.staleness_seconds == 30.0

    def test_old_update_is_stale(self):
        fg = FreshnessGuard()
        fg.set_policy(StalenessPolicy(
            projection_name="p1", max_staleness_seconds=60,
        ))
        fg.record_update("p1", T0)
        check = fg.check("p1", T0 + timedelta(seconds=120))
        assert check.is_fresh is False

    def test_check_all(self):
        fg = FreshnessGuard()
        fg.set_policy(StalenessPolicy(projection_name="p1", max_staleness_seconds=60))
        fg.set_policy(StalenessPolicy(projection_name="p2", max_staleness_seconds=60))
        fg.record_update("p1", T0)
        # p2 never updated
        results = fg.check_all(T0 + timedelta(seconds=30))
        assert results["p1"].is_fresh is True
        assert results["p2"].is_fresh is False
