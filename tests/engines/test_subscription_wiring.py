"""
BOS — Cross-Engine Subscription Wiring Tests
=============================================
Tests for:
- CashSubscriptionHandler  (event key fix + branch filtering)
- InventorySubscriptionHandler (retail_sale + restaurant_order handlers)
- AccountingSubscriptionHandler (retail_sale + restaurant_bill handlers)
- wire_all_subscriptions() bootstrap function
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

BIZ = uuid.uuid4()
BRANCH_A = uuid.uuid4()
BRANCH_B = uuid.uuid4()
NOW = datetime(2026, 3, 3, 10, 0, 0, tzinfo=timezone.utc)


# ── Shared stubs ───────────────────────────────────────────────

class StubReg:
    def __init__(self):
        self._types = set()
    def register(self, et):
        self._types.add(et)
    def is_registered(self, et):
        return et in self._types


class StubFactory:
    def __call__(self, *, command, event_type, payload):
        return {
            "event_type": event_type,
            "payload": payload,
            "business_id": command.business_id,
            "source_engine": command.source_engine,
        }


class StubPersist:
    def __init__(self):
        self.calls = []
    def __call__(self, *, event_data, context, registry, **k):
        self.calls.append(event_data)
        return {"accepted": True}


class StubBus:
    def __init__(self):
        self.handlers = {}
    def register_handler(self, ct, h):
        self.handlers[ct] = h


def _kw():
    return dict(
        business_id=BIZ,
        actor_type="HUMAN",
        actor_id="cashier-1",
        command_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        issued_at=NOW,
    )


def _cash_svc():
    from engines.cash.services import CashService
    return CashService(
        business_context={"business_id": BIZ},
        command_bus=StubBus(),
        event_factory=StubFactory(),
        persist_event=StubPersist(),
        event_type_registry=StubReg(),
    )


def _inv_svc():
    from engines.inventory.services import InventoryService
    return InventoryService(
        business_context={"business_id": BIZ},
        command_bus=StubBus(),
        event_factory=StubFactory(),
        persist_event=StubPersist(),
        event_type_registry=StubReg(),
    )


def _acct_svc():
    from engines.accounting.services import AccountingService
    return AccountingService(
        business_context={"business_id": BIZ},
        command_bus=StubBus(),
        event_factory=StubFactory(),
        persist_event=StubPersist(),
        event_type_registry=StubReg(),
    )


def _open_cash_session(svc, branch_id=None, session_id="sess-1", drawer_id="drawer-1"):
    """Helper: open a cash session in the given service."""
    from engines.cash.commands import SessionOpenRequest
    kw = dict(
        business_id=BIZ, actor_type="HUMAN", actor_id="cashier",
        command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
    )
    svc._execute_command(SessionOpenRequest(
        session_id=session_id,
        drawer_id=drawer_id,
        opening_balance=5000,
        currency="KES",
        branch_id=branch_id,
    ).to_command(**kw))


# ══════════════════════════════════════════════════════════════
# CASH SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════

class TestCashSubscriptionKeys:
    def test_keys_use_v1_suffix(self):
        from engines.cash.subscriptions import CASH_SUBSCRIPTIONS
        assert "retail.sale.completed.v1" in CASH_SUBSCRIPTIONS
        assert "restaurant.bill.settled.v1" in CASH_SUBSCRIPTIONS
        # old keys without .v1 must NOT exist
        assert "retail.sale.completed" not in CASH_SUBSCRIPTIONS
        assert "restaurant.bill.settled" not in CASH_SUBSCRIPTIONS

    def test_handler_methods_exist(self):
        from engines.cash.subscriptions import CashSubscriptionHandler
        h = CashSubscriptionHandler()
        assert callable(h.handle_retail_sale)
        assert callable(h.handle_restaurant_bill)


class TestCashBranchFiltering:
    """_get_open_session() must filter by branch_id."""

    def test_get_open_session_no_branch_returns_any(self):
        from engines.cash.subscriptions import CashSubscriptionHandler
        svc = _cash_svc()
        _open_cash_session(svc, branch_id=BRANCH_A)
        handler = CashSubscriptionHandler(cash_service=svc)
        result = handler._get_open_session(branch_id=None)
        assert result is not None
        assert result["session_id"] == "sess-1"

    def test_get_open_session_matching_branch(self):
        from engines.cash.subscriptions import CashSubscriptionHandler
        svc = _cash_svc()
        _open_cash_session(svc, branch_id=BRANCH_A)
        handler = CashSubscriptionHandler(cash_service=svc)
        result = handler._get_open_session(branch_id=BRANCH_A)
        assert result is not None

    def test_get_open_session_wrong_branch_returns_none(self):
        from engines.cash.subscriptions import CashSubscriptionHandler
        svc = _cash_svc()
        _open_cash_session(svc, branch_id=BRANCH_A)
        handler = CashSubscriptionHandler(cash_service=svc)
        # Branch B has no open session
        result = handler._get_open_session(branch_id=BRANCH_B)
        assert result is None

    def test_handle_retail_sale_skips_wrong_branch(self):
        """A retail sale on BRANCH_B should NOT record to BRANCH_A's session."""
        from engines.cash.subscriptions import CashSubscriptionHandler
        svc = _cash_svc()
        _open_cash_session(svc, branch_id=BRANCH_A)

        handler = CashSubscriptionHandler(cash_service=svc)
        event_data = {
            "payload": {
                "business_id": str(BIZ),
                "branch_id": str(BRANCH_B),  # different branch
                "sale_id": "sale-999",
                "net_amount": 5000,
                "currency": "KES",
                "payment_method": "CASH",
                "correlation_id": str(uuid.uuid4()),
            }
        }
        handler.handle_retail_sale(event_data)
        # Branch A session should still have 0 payments
        session = svc.projection_store.get_session("sess-1")
        assert session["total_payments"] == 0

    def test_handle_retail_sale_records_correct_branch(self):
        """A retail sale on BRANCH_A should record to BRANCH_A's session."""
        from engines.cash.subscriptions import CashSubscriptionHandler
        svc = _cash_svc()
        _open_cash_session(svc, branch_id=BRANCH_A)

        handler = CashSubscriptionHandler(cash_service=svc)
        event_data = {
            "payload": {
                "business_id": str(BIZ),
                "branch_id": str(BRANCH_A),  # correct branch
                "sale_id": "sale-001",
                "net_amount": 5000,
                "currency": "KES",
                "payment_method": "CASH",
                "correlation_id": str(uuid.uuid4()),
            }
        }
        handler.handle_retail_sale(event_data)
        session = svc.projection_store.get_session("sess-1")
        assert session["total_payments"] == 5000


class TestCashHandlerNoop:
    def test_no_service_noop(self):
        from engines.cash.subscriptions import CashSubscriptionHandler
        h = CashSubscriptionHandler(cash_service=None)
        h.handle_retail_sale({"payload": {"business_id": str(BIZ), "net_amount": 100}})

    def test_non_cash_payment_skipped(self):
        """CARD payment should not trigger a cash recording."""
        from engines.cash.subscriptions import CashSubscriptionHandler
        svc = _cash_svc()
        _open_cash_session(svc, branch_id=BRANCH_A)
        h = CashSubscriptionHandler(cash_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "branch_id": str(BRANCH_A),
            "sale_id": "card-sale",
            "payment_method": "CARD",
            "net_amount": 5000,
            "currency": "KES",
        }})
        session = svc.projection_store.get_session("sess-1")
        assert session["total_payments"] == 0


# ══════════════════════════════════════════════════════════════
# INVENTORY SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════

class TestInventorySubscriptionKeys:
    def test_keys_use_v1_suffix(self):
        from engines.inventory.subscriptions import INVENTORY_SUBSCRIPTIONS
        assert "procurement.order.received.v1" in INVENTORY_SUBSCRIPTIONS
        assert "retail.sale.completed.v1" in INVENTORY_SUBSCRIPTIONS
        assert "restaurant.order.placed.v1" in INVENTORY_SUBSCRIPTIONS
        # Old key without .v1 must NOT exist
        assert "procurement.order.received" not in INVENTORY_SUBSCRIPTIONS

    def test_all_methods_exist(self):
        from engines.inventory.subscriptions import (
            InventorySubscriptionHandler, INVENTORY_SUBSCRIPTIONS,
        )
        h = InventorySubscriptionHandler()
        for method_name in INVENTORY_SUBSCRIPTIONS.values():
            assert callable(getattr(h, method_name, None)), (
                f"InventorySubscriptionHandler.{method_name} does not exist"
            )


class TestInventoryRetailSaleHandler:
    def _receive_stock(self, svc, item_id, sku, qty):
        from engines.inventory.commands import StockReceiveRequest
        kw = dict(
            business_id=BIZ, actor_type="SYSTEM", actor_id="sys",
            command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
        )
        svc._execute_command(StockReceiveRequest(
            item_id=item_id, sku=sku, quantity=qty,
            location_id="DEFAULT", location_name="Default Store Location",
            branch_id=BRANCH_A,
        ).to_command(**kw))

    def test_handle_retail_sale_issues_stock_per_line(self):
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        svc = _inv_svc()
        self._receive_stock(svc, "item-1", "SKU-1", 100)
        self._receive_stock(svc, "item-2", "SKU-2", 50)

        handler = InventorySubscriptionHandler(inventory_service=svc)
        handler.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "branch_id": str(BRANCH_A),
            "sale_id": "sale-001",
            "currency": "KES",
            "correlation_id": str(uuid.uuid4()),
            "lines": [
                {"item_id": "item-1", "sku": "SKU-1", "quantity": 3},
                {"item_id": "item-2", "sku": "SKU-2", "quantity": 2},
            ],
        }})
        assert svc.projection_store.get_stock("item-1", "DEFAULT") == 97  # 100 - 3
        assert svc.projection_store.get_stock("item-2", "DEFAULT") == 48  # 50 - 2

    def test_handle_retail_sale_no_service_noop(self):
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        h = InventorySubscriptionHandler(inventory_service=None)
        h.handle_retail_sale({"payload": {"lines": [{"item_id": "x", "quantity": 1}]}})

    def test_handle_retail_sale_empty_lines_noop(self):
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        svc = _inv_svc()
        h = InventorySubscriptionHandler(inventory_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "lines": [],
        }})

    def test_handle_retail_sale_bad_line_skipped(self):
        """A bad line (missing item_id) should not crash the handler."""
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        svc = _inv_svc()
        h = InventorySubscriptionHandler(inventory_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "sale-bad",
            "correlation_id": str(uuid.uuid4()),
            "lines": [
                {"quantity": 5},  # missing item_id — should be skipped
            ],
        }})


class TestInventoryRestaurantOrderHandler:
    def test_handle_restaurant_order_issues_stock(self):
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        from engines.inventory.commands import StockReceiveRequest

        svc = _inv_svc()
        kw = dict(
            business_id=BIZ, actor_type="SYSTEM", actor_id="sys",
            command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
        )
        svc._execute_command(StockReceiveRequest(
            item_id="menu-1", sku="menu-1", quantity=20,
            location_id="DEFAULT", location_name="Default Store Location",
            branch_id=BRANCH_A,
        ).to_command(**kw))

        handler = InventorySubscriptionHandler(inventory_service=svc)
        handler.handle_restaurant_order({"payload": {
            "business_id": str(BIZ),
            "branch_id": str(BRANCH_A),
            "order_id": "order-101",
            "correlation_id": str(uuid.uuid4()),
            "items": [
                {"item_id": "menu-1", "name": "Pizza", "price": 1500},
            ],
        }})
        # Default quantity is 1
        assert svc.projection_store.get_stock("menu-1", "DEFAULT") == 19

    def test_handle_restaurant_order_respects_quantity_field(self):
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        from engines.inventory.commands import StockReceiveRequest

        svc = _inv_svc()
        kw = dict(
            business_id=BIZ, actor_type="SYSTEM", actor_id="sys",
            command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
        )
        svc._execute_command(StockReceiveRequest(
            item_id="ing-1", sku="ing-1", quantity=100,
            location_id="DEFAULT", location_name="Default Store Location",
            branch_id=BRANCH_A,
        ).to_command(**kw))

        handler = InventorySubscriptionHandler(inventory_service=svc)
        handler.handle_restaurant_order({"payload": {
            "business_id": str(BIZ),
            "branch_id": str(BRANCH_A),
            "order_id": "order-102",
            "correlation_id": str(uuid.uuid4()),
            "items": [{"item_id": "ing-1", "name": "Flour", "quantity": 3}],
        }})
        assert svc.projection_store.get_stock("ing-1", "DEFAULT") == 97  # 100 - 3

    def test_handle_restaurant_order_no_service_noop(self):
        from engines.inventory.subscriptions import InventorySubscriptionHandler
        h = InventorySubscriptionHandler(inventory_service=None)
        h.handle_restaurant_order({"payload": {"items": [{"item_id": "x"}]}})


# ══════════════════════════════════════════════════════════════
# ACCOUNTING SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════

class TestAccountingSubscriptionKeys:
    def test_retail_sale_key_present(self):
        from engines.accounting.subscriptions import ACCOUNTING_SUBSCRIPTIONS
        assert "retail.sale.completed.v1" in ACCOUNTING_SUBSCRIPTIONS
        assert ACCOUNTING_SUBSCRIPTIONS["retail.sale.completed.v1"] == "handle_retail_sale"

    def test_restaurant_bill_key_present(self):
        from engines.accounting.subscriptions import ACCOUNTING_SUBSCRIPTIONS
        assert "restaurant.bill.settled.v1" in ACCOUNTING_SUBSCRIPTIONS
        assert ACCOUNTING_SUBSCRIPTIONS["restaurant.bill.settled.v1"] == "handle_restaurant_bill"

    def test_existing_keys_still_present(self):
        from engines.accounting.subscriptions import ACCOUNTING_SUBSCRIPTIONS
        assert "inventory.stock.received.v1" in ACCOUNTING_SUBSCRIPTIONS
        assert "cash.payment.recorded.v1" in ACCOUNTING_SUBSCRIPTIONS
        assert "hr.payroll.run.v1" in ACCOUNTING_SUBSCRIPTIONS

    def test_all_methods_exist(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler, ACCOUNTING_SUBSCRIPTIONS,
        )
        h = AccountingSubscriptionHandler()
        for method_name in ACCOUNTING_SUBSCRIPTIONS.values():
            assert callable(getattr(h, method_name, None)), (
                f"AccountingSubscriptionHandler.{method_name} does not exist"
            )


class TestAccountingRetailSaleHandler:
    def test_cash_payment_debits_cash_account(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            DEFAULT_CASH_ACCOUNT,
            DEFAULT_REVENUE_ACCOUNT,
        )
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "sale-cash-1",
            "net_amount": 10000,
            "currency": "KES",
            "payment_method": "CASH",
            "correlation_id": str(uuid.uuid4()),
        }})
        cash_bal = svc.projection_store.get_balance(DEFAULT_CASH_ACCOUNT)
        revenue_bal = svc.projection_store.get_balance(DEFAULT_REVENUE_ACCOUNT)
        assert cash_bal is not None
        assert cash_bal["total_debits"] == 10000
        assert revenue_bal is not None
        assert revenue_bal["total_credits"] == 10000

    def test_card_payment_debits_card_clearing(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            DEFAULT_CARD_ACCOUNT,
            DEFAULT_REVENUE_ACCOUNT,
        )
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "sale-card-1",
            "net_amount": 8000,
            "currency": "KES",
            "payment_method": "CARD",
            "correlation_id": str(uuid.uuid4()),
        }})
        card_bal = svc.projection_store.get_balance(DEFAULT_CARD_ACCOUNT)
        assert card_bal is not None
        assert card_bal["total_debits"] == 8000

    def test_mobile_payment_debits_mobile_clearing(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            DEFAULT_MOBILE_ACCOUNT,
        )
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "sale-mobile-1",
            "net_amount": 3500,
            "currency": "KES",
            "payment_method": "MOBILE",
            "correlation_id": str(uuid.uuid4()),
        }})
        mob_bal = svc.projection_store.get_balance(DEFAULT_MOBILE_ACCOUNT)
        assert mob_bal is not None
        assert mob_bal["total_debits"] == 3500

    def test_credit_payment_debits_ar(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            DEFAULT_AR_ACCOUNT,
        )
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "sale-credit-1",
            "net_amount": 5000,
            "currency": "KES",
            "payment_method": "CREDIT",
            "correlation_id": str(uuid.uuid4()),
        }})
        ar_bal = svc.projection_store.get_balance(DEFAULT_AR_ACCOUNT)
        assert ar_bal is not None
        assert ar_bal["total_debits"] == 5000

    def test_trial_balance_stays_balanced_after_sale(self):
        """Posting a sale journal should keep trial balance balanced."""
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "sale-tb-1",
            "net_amount": 7000,
            "currency": "KES",
            "payment_method": "CASH",
            "correlation_id": str(uuid.uuid4()),
        }})
        total_debits, total_credits = svc.projection_store.trial_balance()
        assert total_debits == total_credits == 7000

    def test_no_service_noop(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        h = AccountingSubscriptionHandler(accounting_service=None)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "s1",
            "net_amount": 100,
            "currency": "KES",
        }})

    def test_missing_currency_noop(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_retail_sale({"payload": {
            "business_id": str(BIZ),
            "sale_id": "s-bad",
            "net_amount": 1000,
            # missing currency
        }})
        # No journal should have been posted — trial balance remains 0
        total_d, total_c = svc.projection_store.trial_balance()
        assert total_d == 0
        assert total_c == 0


class TestAccountingRestaurantBillHandler:
    def test_cash_bill_posts_revenue_journal(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            DEFAULT_CASH_ACCOUNT,
            DEFAULT_REVENUE_ACCOUNT,
        )
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_restaurant_bill({"payload": {
            "business_id": str(BIZ),
            "bill_id": "bill-001",
            "total_amount": 7500,
            "currency": "KES",
            "payment_method": "CASH",
            "correlation_id": str(uuid.uuid4()),
        }})
        cash_bal = svc.projection_store.get_balance(DEFAULT_CASH_ACCOUNT)
        revenue_bal = svc.projection_store.get_balance(DEFAULT_REVENUE_ACCOUNT)
        assert cash_bal["total_debits"] == 7500
        assert revenue_bal["total_credits"] == 7500

    def test_card_bill_debits_card_clearing(self):
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            DEFAULT_CARD_ACCOUNT,
        )
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_restaurant_bill({"payload": {
            "business_id": str(BIZ),
            "bill_id": "bill-002",
            "total_amount": 12000,
            "currency": "KES",
            "payment_method": "CARD",
            "correlation_id": str(uuid.uuid4()),
        }})
        card_bal = svc.projection_store.get_balance(DEFAULT_CARD_ACCOUNT)
        assert card_bal is not None
        assert card_bal["total_debits"] == 12000

    def test_bill_trial_balance_stays_balanced(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_restaurant_bill({"payload": {
            "business_id": str(BIZ),
            "bill_id": "bill-003",
            "total_amount": 9000,
            "currency": "KES",
            "payment_method": "MOBILE",
            "correlation_id": str(uuid.uuid4()),
        }})
        total_d, total_c = svc.projection_store.trial_balance()
        assert total_d == total_c == 9000

    def test_no_service_noop(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        h = AccountingSubscriptionHandler(accounting_service=None)
        h.handle_restaurant_bill({"payload": {
            "business_id": str(BIZ),
            "bill_id": "b1",
            "total_amount": 5000,
            "currency": "KES",
        }})

    def test_zero_amount_noop(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        svc = _acct_svc()
        h = AccountingSubscriptionHandler(accounting_service=svc)
        h.handle_restaurant_bill({"payload": {
            "business_id": str(BIZ),
            "bill_id": "b-zero",
            "total_amount": 0,
            "currency": "KES",
        }})
        total_d, total_c = svc.projection_store.trial_balance()
        assert total_d == 0
        assert total_c == 0


class TestPaymentDebitAccountMap:
    def test_all_payment_methods_mapped(self):
        from engines.accounting.subscriptions import PAYMENT_DEBIT_ACCOUNT_MAP
        for method in ("CASH", "CARD", "MOBILE", "BANK_TRANSFER", "CREDIT", "SPLIT"):
            assert method in PAYMENT_DEBIT_ACCOUNT_MAP, (
                f"PAYMENT_DEBIT_ACCOUNT_MAP missing key: {method}"
            )

    def test_card_does_not_use_ar(self):
        from engines.accounting.subscriptions import (
            PAYMENT_DEBIT_ACCOUNT_MAP,
            DEFAULT_AR_ACCOUNT,
        )
        assert PAYMENT_DEBIT_ACCOUNT_MAP["CARD"] != DEFAULT_AR_ACCOUNT

    def test_mobile_does_not_use_ar(self):
        from engines.accounting.subscriptions import (
            PAYMENT_DEBIT_ACCOUNT_MAP,
            DEFAULT_AR_ACCOUNT,
        )
        assert PAYMENT_DEBIT_ACCOUNT_MAP["MOBILE"] != DEFAULT_AR_ACCOUNT


# ══════════════════════════════════════════════════════════════
# BOOTSTRAP — wire_all_subscriptions()
# ══════════════════════════════════════════════════════════════

class TestWireAllSubscriptions:
    def _make_registry(self):
        from core.events.registry import SubscriberRegistry
        return SubscriberRegistry()

    def test_wire_cash_only(self):
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        registry = self._make_registry()
        result = wire_all_subscriptions(
            registry,
            cash_service=_cash_svc(),
        )
        assert "cash" in result
        assert result["cash"] == 5  # retail + restaurant + workshop + hotel + procurement
        assert registry.has_subscribers("retail.sale.completed.v1")
        assert registry.has_subscribers("restaurant.bill.settled.v1")

    def test_wire_inventory_only(self):
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        registry = self._make_registry()
        result = wire_all_subscriptions(
            registry,
            inventory_service=_inv_svc(),
        )
        assert "inventory" in result
        assert result["inventory"] == 3  # procurement + retail + restaurant
        assert registry.has_subscribers("procurement.order.received.v1")
        assert registry.has_subscribers("retail.sale.completed.v1")
        assert registry.has_subscribers("restaurant.order.placed.v1")

    def test_wire_accounting_only(self):
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        registry = self._make_registry()
        result = wire_all_subscriptions(
            registry,
            accounting_service=_acct_svc(),
        )
        assert "accounting" in result
        assert result["accounting"] == 10  # stock_received + payment + cash_session + payroll + retail + refund + restaurant + workshop + hotel + procurement
        assert registry.has_subscribers("inventory.stock.received.v1")
        assert registry.has_subscribers("cash.payment.recorded.v1")
        assert registry.has_subscribers("hr.payroll.run.v1")
        assert registry.has_subscribers("retail.sale.completed.v1")
        assert registry.has_subscribers("restaurant.bill.settled.v1")
        assert registry.has_subscribers("workshop.job.invoiced.v1")

    def test_wire_all_services(self):
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        registry = self._make_registry()
        result = wire_all_subscriptions(
            registry,
            cash_service=_cash_svc(),
            inventory_service=_inv_svc(),
            accounting_service=_acct_svc(),
        )
        assert "cash" in result
        assert "inventory" in result
        assert "accounting" in result
        assert sum(result.values()) > 0

    def test_wire_no_services_returns_empty(self):
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        registry = self._make_registry()
        result = wire_all_subscriptions(registry)
        assert result == {}

    def test_multiple_engines_same_event_type(self):
        """retail.sale.completed.v1 should have cash + inventory + accounting subscribers."""
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        registry = self._make_registry()
        wire_all_subscriptions(
            registry,
            cash_service=_cash_svc(),
            inventory_service=_inv_svc(),
            accounting_service=_acct_svc(),
        )
        count = registry.subscriber_count("retail.sale.completed.v1")
        assert count == 3

    def test_handler_callable_via_dispatcher(self):
        """Wired handlers should be invocable through the dispatcher.

        Handlers call event_data.get("payload", {}), so the event passed to
        dispatch must be a dict-like object. Use a dict subclass that also
        exposes .event_type and .event_id as attributes (what dispatcher reads).
        """
        from core.bootstrap.subscription_wiring import wire_all_subscriptions
        from core.events.dispatcher import dispatch

        class EventDict(dict):
            """Dict subclass that exposes event_type and event_id as attributes."""
            @property
            def event_type(self):
                return self["event_type"]
            @property
            def event_id(self):
                return self.get("event_id", "test-id")

        registry = self._make_registry()
        acct_svc = _acct_svc()
        wire_all_subscriptions(registry, accounting_service=acct_svc)

        fake_event = EventDict({
            "event_type": "retail.sale.completed.v1",
            "event_id": str(uuid.uuid4()),
            "payload": {
                "business_id": str(BIZ),
                "sale_id": "e2e-sale-1",
                "net_amount": 5000,
                "currency": "KES",
                "payment_method": "CASH",
                "correlation_id": str(uuid.uuid4()),
            },
        })
        result = dispatch(fake_event, registry)
        assert result["event_type"] == "retail.sale.completed.v1"
        assert result["subscribers_notified"] >= 1
        assert result["subscribers_failed"] == 0
        # Accounting journal should have been posted
        from engines.accounting.subscriptions import DEFAULT_CASH_ACCOUNT
        bal = acct_svc.projection_store.get_balance(DEFAULT_CASH_ACCOUNT)
        assert bal is not None
        assert bal["total_debits"] == 5000
