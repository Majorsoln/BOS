"""
BOS Phase 5 — Business Engines Test Suite
============================================
Tests for: Inventory, Accounting, Cash engines.

Tests verify:
- Command creation and validation
- Event type resolution
- Payload building
- Service orchestration (command → event → projection)
- Policy enforcement
- Projection correctness
- Determinism
- Multi-tenant isolation
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest

BIZ_A = uuid.uuid4()
BIZ_B = uuid.uuid4()
BRANCH = uuid.uuid4()
NOW = datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════
# TEST HELPERS
# ══════════════════════════════════════════════════════════════

def make_command_args():
    return dict(
        business_id=BIZ_A,
        actor_type="HUMAN",
        actor_id="cashier-001",
        command_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        issued_at=NOW,
    )


class StubEventTypeRegistry:
    """Minimal event type registry for testing."""
    def __init__(self):
        self._types = set()

    def register(self, event_type: str) -> None:
        self._types.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        return event_type in self._types


class StubEventFactory:
    """Minimal event factory for testing."""
    def __call__(self, *, command, event_type, payload):
        return {
            "event_type": event_type,
            "payload": payload,
            "business_id": command.business_id,
            "source_engine": command.source_engine,
        }


class StubPersistEvent:
    """Minimal persist function that always succeeds."""
    def __init__(self):
        self.calls = []

    def __call__(self, *, event_data, context, registry, **kwargs):
        self.calls.append(event_data)
        return {"accepted": True}


class StubCommandBus:
    """Minimal command bus that records handler registrations."""
    def __init__(self):
        self.handlers = {}

    def register_handler(self, command_type, handler):
        self.handlers[command_type] = handler


# ══════════════════════════════════════════════════════════════
# INVENTORY ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestInventoryCommands:
    """Tests for inventory command creation and validation."""

    def test_stock_receive_request(self):
        from engines.inventory.commands import StockReceiveRequest
        req = StockReceiveRequest(
            item_id="item-1", sku="WIDGET-001",
            quantity=100, location_id="loc-1",
            location_name="Main Warehouse",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "inventory.stock.receive.request"
        assert cmd.source_engine == "inventory"
        assert cmd.payload["quantity"] == 100

    def test_stock_issue_request(self):
        from engines.inventory.commands import StockIssueRequest
        req = StockIssueRequest(
            item_id="item-1", sku="WIDGET-001",
            quantity=30, location_id="loc-1",
            location_name="Main Warehouse",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "inventory.stock.issue.request"
        assert cmd.payload["reason"] == "SALE"

    def test_stock_transfer_request(self):
        from engines.inventory.commands import StockTransferRequest
        req = StockTransferRequest(
            item_id="item-1", sku="WIDGET-001",
            quantity=20,
            from_location_id="loc-1", from_location_name="Warehouse A",
            to_location_id="loc-2", to_location_name="Warehouse B",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "inventory.stock.transfer.request"

    def test_transfer_same_location_rejected(self):
        from engines.inventory.commands import StockTransferRequest
        with pytest.raises(ValueError, match="same location"):
            StockTransferRequest(
                item_id="item-1", sku="WIDGET-001",
                quantity=10,
                from_location_id="loc-1", from_location_name="A",
                to_location_id="loc-1", to_location_name="A",
            )

    def test_stock_adjust_request(self):
        from engines.inventory.commands import StockAdjustRequest
        req = StockAdjustRequest(
            item_id="item-1", sku="WIDGET-001",
            quantity=5, adjustment_type="ADJUST_MINUS",
            location_id="loc-1", location_name="Main",
            reason="DAMAGE",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "inventory.stock.adjust.request"
        assert cmd.payload["adjustment_type"] == "ADJUST_MINUS"

    def test_quantity_must_be_positive(self):
        from engines.inventory.commands import StockReceiveRequest
        with pytest.raises(ValueError, match="positive"):
            StockReceiveRequest(
                item_id="item-1", sku="W", quantity=0,
                location_id="loc-1", location_name="Main",
            )

    def test_invalid_reason_rejected(self):
        from engines.inventory.commands import StockReceiveRequest
        with pytest.raises(ValueError, match="not valid"):
            StockReceiveRequest(
                item_id="item-1", sku="W", quantity=10,
                location_id="loc-1", location_name="Main",
                reason="INVALID_REASON",
            )

    def test_item_register_request(self):
        from engines.inventory.commands import ItemRegisterRequest
        req = ItemRegisterRequest(
            item_id="item-1", sku="LAPTOP-001",
            name="Laptop Pro", item_type="PRODUCT",
            unit_of_measure="PIECE",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "inventory.item.register.request"
        assert cmd.payload["name"] == "Laptop Pro"


class TestInventoryEvents:
    """Tests for inventory event type resolution and payloads."""

    def test_event_type_resolution(self):
        from engines.inventory.events import resolve_inventory_event_type
        assert resolve_inventory_event_type(
            "inventory.stock.receive.request"
        ) == "inventory.stock.received.v1"
        assert resolve_inventory_event_type(
            "inventory.stock.issue.request"
        ) == "inventory.stock.issued.v1"
        assert resolve_inventory_event_type("unknown") is None

    def test_event_type_registration(self):
        from engines.inventory.events import register_inventory_event_types
        registry = StubEventTypeRegistry()
        register_inventory_event_types(registry)
        assert registry.is_registered("inventory.stock.received.v1")
        assert registry.is_registered("inventory.stock.issued.v1")
        assert registry.is_registered("inventory.item.registered.v1")

    def test_stock_received_payload(self):
        from engines.inventory.commands import StockReceiveRequest
        from engines.inventory.events import build_stock_received_payload
        req = StockReceiveRequest(
            item_id="item-1", sku="W-001", quantity=50,
            location_id="loc-1", location_name="Main",
        )
        cmd = req.to_command(**make_command_args())
        payload = build_stock_received_payload(cmd)
        assert payload["item_id"] == "item-1"
        assert payload["quantity"] == 50
        assert payload["reason"] == "PURCHASE"


class TestInventoryService:
    """Tests for inventory service orchestration."""

    def _make_service(self):
        from engines.inventory.services import InventoryService
        return InventoryService(
            business_context={"business_id": BIZ_A},
            command_bus=StubCommandBus(),
            event_factory=StubEventFactory(),
            persist_event=StubPersistEvent(),
            event_type_registry=StubEventTypeRegistry(),
        )

    def test_service_registers_all_handlers(self):
        from engines.inventory.commands import INVENTORY_COMMAND_TYPES
        service = self._make_service()
        bus = service._command_bus
        for ct in INVENTORY_COMMAND_TYPES:
            assert ct in bus.handlers

    def test_service_execute_receive(self):
        from engines.inventory.commands import StockReceiveRequest
        service = self._make_service()
        req = StockReceiveRequest(
            item_id="item-1", sku="W-001", quantity=100,
            location_id="loc-1", location_name="Main",
            branch_id=BRANCH,
        )
        cmd = req.to_command(**make_command_args())
        result = service._execute_command(cmd)
        assert result.event_type == "inventory.stock.received.v1"
        assert result.projection_applied

    def test_projection_tracks_stock(self):
        from engines.inventory.commands import (
            StockReceiveRequest, StockIssueRequest,
        )
        service = self._make_service()

        # Receive 100
        req = StockReceiveRequest(
            item_id="item-1", sku="W-001", quantity=100,
            location_id="loc-1", location_name="Main",
            branch_id=BRANCH,
        )
        service._execute_command(req.to_command(**make_command_args()))

        # Issue 30
        req2 = StockIssueRequest(
            item_id="item-1", sku="W-001", quantity=30,
            location_id="loc-1", location_name="Main",
            branch_id=BRANCH,
        )
        service._execute_command(req2.to_command(**make_command_args()))

        assert service.projection_store.get_stock("item-1", "loc-1") == 70

    def test_projection_tracks_transfer(self):
        from engines.inventory.commands import (
            StockReceiveRequest, StockTransferRequest,
        )
        service = self._make_service()

        # Receive 50 at loc-1
        service._execute_command(
            StockReceiveRequest(
                item_id="i1", sku="S", quantity=50,
                location_id="loc-1", location_name="A",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )

        # Transfer 20 to loc-2
        service._execute_command(
            StockTransferRequest(
                item_id="i1", sku="S", quantity=20,
                from_location_id="loc-1", from_location_name="A",
                to_location_id="loc-2", to_location_name="B",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )

        assert service.projection_store.get_stock("i1", "loc-1") == 30
        assert service.projection_store.get_stock("i1", "loc-2") == 20


class TestInventoryPolicies:
    """Tests for inventory engine policies."""

    def test_negative_stock_policy_rejects(self):
        from engines.inventory.policies import negative_stock_policy
        from engines.inventory.commands import StockIssueRequest
        cmd = StockIssueRequest(
            item_id="item-1", sku="W", quantity=100,
            location_id="loc-1", location_name="Main",
        ).to_command(**make_command_args())

        # Stock lookup returns only 50
        result = negative_stock_policy(
            cmd, stock_lookup=lambda i, l: 50,
        )
        assert result is not None
        assert result.code == "INSUFFICIENT_STOCK"

    def test_negative_stock_policy_passes(self):
        from engines.inventory.policies import negative_stock_policy
        from engines.inventory.commands import StockIssueRequest
        cmd = StockIssueRequest(
            item_id="item-1", sku="W", quantity=30,
            location_id="loc-1", location_name="Main",
        ).to_command(**make_command_args())

        result = negative_stock_policy(
            cmd, stock_lookup=lambda i, l: 100,
        )
        assert result is None

    def test_negative_stock_passes_without_lookup(self):
        from engines.inventory.policies import negative_stock_policy
        from engines.inventory.commands import StockIssueRequest
        cmd = StockIssueRequest(
            item_id="item-1", sku="W", quantity=999,
            location_id="loc-1", location_name="Main",
        ).to_command(**make_command_args())

        result = negative_stock_policy(cmd, stock_lookup=None)
        assert result is None  # Optimistic mode

    def test_same_location_transfer_policy(self):
        from engines.inventory.policies import same_location_transfer_policy
        from core.commands.base import Command
        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.transfer.request",
            business_id=BIZ_A, branch_id=None,
            actor_type="HUMAN", actor_id="u1",
            payload={
                "from_location_id": "loc-1",
                "to_location_id": "loc-1",
            },
            issued_at=NOW, correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )
        result = same_location_transfer_policy(cmd)
        assert result is not None
        assert result.code == "SAME_LOCATION_TRANSFER"


# ══════════════════════════════════════════════════════════════
# ACCOUNTING ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestAccountingCommands:
    """Tests for accounting command creation and validation."""

    def test_journal_post_request(self):
        from engines.accounting.commands import JournalPostRequest
        req = JournalPostRequest(
            entry_id="entry-1",
            lines=(
                {"account_code": "1000", "side": "DEBIT", "amount": 5000},
                {"account_code": "4000", "side": "CREDIT", "amount": 5000},
            ),
            memo="Cash sale",
            currency="KES",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "accounting.journal.post.request"
        assert cmd.source_engine == "accounting"

    def test_unbalanced_journal_rejected(self):
        from engines.accounting.commands import JournalPostRequest
        with pytest.raises(ValueError, match="unbalanced"):
            JournalPostRequest(
                entry_id="entry-1",
                lines=(
                    {"account_code": "1000", "side": "DEBIT", "amount": 5000},
                    {"account_code": "4000", "side": "CREDIT", "amount": 3000},
                ),
                memo="Bad entry",
                currency="KES",
            )

    def test_single_line_rejected(self):
        from engines.accounting.commands import JournalPostRequest
        with pytest.raises(ValueError, match="at least 2"):
            JournalPostRequest(
                entry_id="entry-1",
                lines=(
                    {"account_code": "1000", "side": "DEBIT", "amount": 1000},
                ),
                memo="Single line",
                currency="KES",
            )

    def test_account_create_request(self):
        from engines.accounting.commands import AccountCreateRequest
        req = AccountCreateRequest(
            account_code="1000",
            account_type="ASSET",
            name="Cash",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "accounting.account.create.request"

    def test_invalid_account_type_rejected(self):
        from engines.accounting.commands import AccountCreateRequest
        with pytest.raises(ValueError, match="not valid"):
            AccountCreateRequest(
                account_code="1000",
                account_type="INVALID",
                name="Bad",
            )

    def test_obligation_create_request(self):
        from engines.accounting.commands import ObligationCreateRequest
        req = ObligationCreateRequest(
            obligation_id="obl-1",
            obligation_type="RECEIVABLE",
            party_id="party-1",
            total_amount=50000,
            currency="KES",
            due_date="2026-02-28",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "accounting.obligation.create.request"

    def test_obligation_fulfill_request(self):
        from engines.accounting.commands import ObligationFulfillRequest
        req = ObligationFulfillRequest(
            obligation_id="obl-1",
            fulfillment_id="ful-1",
            fulfillment_type="PAYMENT_CASH",
            amount=25000,
            currency="KES",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "accounting.obligation.fulfill.request"


class TestAccountingEvents:
    """Tests for accounting event resolution."""

    def test_event_type_resolution(self):
        from engines.accounting.events import resolve_accounting_event_type
        assert resolve_accounting_event_type(
            "accounting.journal.post.request"
        ) == "accounting.journal.posted.v1"
        assert resolve_accounting_event_type(
            "accounting.obligation.create.request"
        ) == "accounting.obligation.created.v1"

    def test_event_registration(self):
        from engines.accounting.events import register_accounting_event_types
        registry = StubEventTypeRegistry()
        register_accounting_event_types(registry)
        assert registry.is_registered("accounting.journal.posted.v1")
        assert registry.is_registered("accounting.obligation.fulfilled.v1")


class TestAccountingService:
    """Tests for accounting service orchestration."""

    def _make_service(self):
        from engines.accounting.services import AccountingService
        return AccountingService(
            business_context={"business_id": BIZ_A},
            command_bus=StubCommandBus(),
            event_factory=StubEventFactory(),
            persist_event=StubPersistEvent(),
            event_type_registry=StubEventTypeRegistry(),
        )

    def test_service_registers_all_handlers(self):
        from engines.accounting.commands import ACCOUNTING_COMMAND_TYPES
        service = self._make_service()
        for ct in ACCOUNTING_COMMAND_TYPES:
            assert ct in service._command_bus.handlers

    def test_journal_post_updates_projection(self):
        from engines.accounting.commands import JournalPostRequest
        service = self._make_service()
        req = JournalPostRequest(
            entry_id="e1",
            lines=(
                {"account_code": "1000", "side": "DEBIT", "amount": 10000},
                {"account_code": "4000", "side": "CREDIT", "amount": 10000},
            ),
            memo="Sale",
            currency="KES",
        )
        result = service._execute_command(req.to_command(**make_command_args()))
        assert result.event_type == "accounting.journal.posted.v1"
        assert result.projection_applied

        bal = service.projection_store.get_balance("1000")
        assert bal is not None
        assert bal["total_debits"] == 10000

    def test_trial_balance_stays_balanced(self):
        from engines.accounting.commands import JournalPostRequest
        service = self._make_service()

        for i in range(5):
            req = JournalPostRequest(
                entry_id=f"e{i}",
                lines=(
                    {"account_code": "1000", "side": "DEBIT", "amount": 1000 * (i+1)},
                    {"account_code": "4000", "side": "CREDIT", "amount": 1000 * (i+1)},
                ),
                memo=f"Entry {i}",
                currency="KES",
            )
            service._execute_command(req.to_command(**make_command_args()))

        d, c = service.projection_store.trial_balance()
        assert d == c == 15000

    def test_obligation_lifecycle(self):
        from engines.accounting.commands import (
            ObligationCreateRequest, ObligationFulfillRequest,
        )
        service = self._make_service()

        # Create obligation
        service._execute_command(
            ObligationCreateRequest(
                obligation_id="obl-1",
                obligation_type="RECEIVABLE",
                party_id="p1",
                total_amount=50000,
                currency="KES",
                due_date="2026-03-01",
            ).to_command(**make_command_args())
        )

        obl = service.projection_store.get_obligation("obl-1")
        assert obl["status"] == "PENDING"

        # Partial fulfillment
        service._execute_command(
            ObligationFulfillRequest(
                obligation_id="obl-1",
                fulfillment_id="f1",
                fulfillment_type="PAYMENT_CASH",
                amount=20000,
                currency="KES",
            ).to_command(**make_command_args())
        )
        obl = service.projection_store.get_obligation("obl-1")
        assert obl["status"] == "PARTIALLY_FULFILLED"

        # Full fulfillment
        service._execute_command(
            ObligationFulfillRequest(
                obligation_id="obl-1",
                fulfillment_id="f2",
                fulfillment_type="PAYMENT_MOBILE",
                amount=30000,
                currency="KES",
            ).to_command(**make_command_args())
        )
        obl = service.projection_store.get_obligation("obl-1")
        assert obl["status"] == "FULFILLED"


class TestAccountingPolicies:
    """Tests for accounting engine policies."""

    def test_balanced_entry_policy_passes(self):
        from engines.accounting.policies import balanced_entry_policy
        from engines.accounting.commands import JournalPostRequest
        cmd = JournalPostRequest(
            entry_id="e1",
            lines=(
                {"account_code": "1000", "side": "DEBIT", "amount": 5000},
                {"account_code": "4000", "side": "CREDIT", "amount": 5000},
            ),
            memo="OK",
            currency="KES",
        ).to_command(**make_command_args())
        assert balanced_entry_policy(cmd) is None

    def test_unbalanced_entry_policy_rejects(self):
        from engines.accounting.policies import balanced_entry_policy
        from core.commands.base import Command
        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="accounting.journal.post.request",
            business_id=BIZ_A, branch_id=None,
            actor_type="HUMAN", actor_id="u1",
            payload={
                "lines": [
                    {"account_code": "1000", "side": "DEBIT", "amount": 5000},
                    {"account_code": "4000", "side": "CREDIT", "amount": 3000},
                ],
            },
            issued_at=NOW, correlation_id=uuid.uuid4(),
            source_engine="accounting",
        )
        result = balanced_entry_policy(cmd)
        assert result is not None
        assert result.code == "UNBALANCED_ENTRY"


# ══════════════════════════════════════════════════════════════
# CASH ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestCashCommands:
    """Tests for cash command creation and validation."""

    def test_session_open_request(self):
        from engines.cash.commands import SessionOpenRequest
        req = SessionOpenRequest(
            session_id="sess-1", drawer_id="drawer-1",
            opening_balance=50000, currency="KES",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "cash.session.open.request"
        assert cmd.source_engine == "cash"

    def test_session_close_request(self):
        from engines.cash.commands import SessionCloseRequest
        req = SessionCloseRequest(
            session_id="sess-1", drawer_id="drawer-1",
            closing_balance=75000, currency="KES",
            expected_balance=74000,
        )
        assert req.difference == 1000  # Over by 1000
        cmd = req.to_command(**make_command_args())
        assert cmd.payload["difference"] == 1000

    def test_payment_record_request(self):
        from engines.cash.commands import PaymentRecordRequest
        req = PaymentRecordRequest(
            payment_id="pay-1", session_id="sess-1",
            drawer_id="drawer-1", amount=15000,
            currency="KES", payment_method="CASH",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "cash.payment.record.request"

    def test_invalid_payment_method_rejected(self):
        from engines.cash.commands import PaymentRecordRequest
        with pytest.raises(ValueError, match="not valid"):
            PaymentRecordRequest(
                payment_id="p1", session_id="s1",
                drawer_id="d1", amount=100,
                currency="KES", payment_method="CRYPTO",
            )

    def test_deposit_record_request(self):
        from engines.cash.commands import DepositRecordRequest
        req = DepositRecordRequest(
            deposit_id="dep-1", session_id="sess-1",
            drawer_id="drawer-1", amount=10000,
            currency="KES",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "cash.deposit.record.request"

    def test_withdrawal_record_request(self):
        from engines.cash.commands import WithdrawalRecordRequest
        req = WithdrawalRecordRequest(
            withdrawal_id="w-1", session_id="sess-1",
            drawer_id="drawer-1", amount=20000,
            currency="KES", reason="BANK_DEPOSIT",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "cash.withdrawal.record.request"

    def test_negative_opening_balance_rejected(self):
        from engines.cash.commands import SessionOpenRequest
        with pytest.raises(ValueError, match="non-negative"):
            SessionOpenRequest(
                session_id="s1", drawer_id="d1",
                opening_balance=-100, currency="KES",
            )


class TestCashEvents:
    """Tests for cash event resolution."""

    def test_event_type_resolution(self):
        from engines.cash.events import resolve_cash_event_type
        assert resolve_cash_event_type(
            "cash.session.open.request"
        ) == "cash.session.opened.v1"
        assert resolve_cash_event_type(
            "cash.payment.record.request"
        ) == "cash.payment.recorded.v1"

    def test_event_registration(self):
        from engines.cash.events import register_cash_event_types
        registry = StubEventTypeRegistry()
        register_cash_event_types(registry)
        assert registry.is_registered("cash.session.opened.v1")
        assert registry.is_registered("cash.payment.recorded.v1")


class TestCashService:
    """Tests for cash service orchestration."""

    def _make_service(self):
        from engines.cash.services import CashService
        return CashService(
            business_context={"business_id": BIZ_A},
            command_bus=StubCommandBus(),
            event_factory=StubEventFactory(),
            persist_event=StubPersistEvent(),
            event_type_registry=StubEventTypeRegistry(),
        )

    def test_service_registers_all_handlers(self):
        from engines.cash.commands import CASH_COMMAND_TYPES
        service = self._make_service()
        for ct in CASH_COMMAND_TYPES:
            assert ct in service._command_bus.handlers

    def test_session_lifecycle(self):
        from engines.cash.commands import (
            SessionOpenRequest, PaymentRecordRequest,
            SessionCloseRequest,
        )
        service = self._make_service()

        # Open session
        service._execute_command(
            SessionOpenRequest(
                session_id="s1", drawer_id="d1",
                opening_balance=50000, currency="KES",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )

        sess = service.projection_store.get_session("s1")
        assert sess["status"] == "OPEN"
        assert service.projection_store.get_drawer_balance("d1") == 50000

        # Record payment
        service._execute_command(
            PaymentRecordRequest(
                payment_id="p1", session_id="s1",
                drawer_id="d1", amount=15000,
                currency="KES", payment_method="CASH",
            ).to_command(**make_command_args())
        )

        assert service.projection_store.get_drawer_balance("d1") == 65000

        # Close session
        service._execute_command(
            SessionCloseRequest(
                session_id="s1", drawer_id="d1",
                closing_balance=65000, currency="KES",
                expected_balance=65000,
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )

        sess = service.projection_store.get_session("s1")
        assert sess["status"] == "CLOSED"

    def test_multiple_payments_accumulate(self):
        from engines.cash.commands import (
            SessionOpenRequest, PaymentRecordRequest,
        )
        service = self._make_service()

        service._execute_command(
            SessionOpenRequest(
                session_id="s1", drawer_id="d1",
                opening_balance=0, currency="KES",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )

        for i in range(5):
            service._execute_command(
                PaymentRecordRequest(
                    payment_id=f"p{i}", session_id="s1",
                    drawer_id="d1", amount=10000,
                    currency="KES", payment_method="CASH",
                ).to_command(**make_command_args())
            )

        assert service.projection_store.get_drawer_balance("d1") == 50000
        sess = service.projection_store.get_session("s1")
        assert sess["total_payments"] == 50000

    def test_deposit_and_withdrawal(self):
        from engines.cash.commands import (
            SessionOpenRequest, DepositRecordRequest,
            WithdrawalRecordRequest,
        )
        service = self._make_service()

        service._execute_command(
            SessionOpenRequest(
                session_id="s1", drawer_id="d1",
                opening_balance=10000, currency="KES",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )

        # Deposit 5000
        service._execute_command(
            DepositRecordRequest(
                deposit_id="dep-1", session_id="s1",
                drawer_id="d1", amount=5000, currency="KES",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )
        assert service.projection_store.get_drawer_balance("d1") == 15000

        # Withdraw 3000
        service._execute_command(
            WithdrawalRecordRequest(
                withdrawal_id="w-1", session_id="s1",
                drawer_id="d1", amount=3000, currency="KES",
                branch_id=BRANCH,
            ).to_command(**make_command_args())
        )
        assert service.projection_store.get_drawer_balance("d1") == 12000


class TestCashPolicies:
    """Tests for cash engine policies."""

    def test_session_must_be_open_rejects_closed(self):
        from engines.cash.policies import session_must_be_open_policy
        from engines.cash.commands import PaymentRecordRequest
        cmd = PaymentRecordRequest(
            payment_id="p1", session_id="s1",
            drawer_id="d1", amount=100,
            currency="KES", payment_method="CASH",
        ).to_command(**make_command_args())

        result = session_must_be_open_policy(
            cmd, session_lookup=lambda s: {"status": "CLOSED"},
        )
        assert result is not None
        assert result.code == "SESSION_NOT_OPEN"

    def test_session_must_be_open_passes(self):
        from engines.cash.policies import session_must_be_open_policy
        from engines.cash.commands import PaymentRecordRequest
        cmd = PaymentRecordRequest(
            payment_id="p1", session_id="s1",
            drawer_id="d1", amount=100,
            currency="KES", payment_method="CASH",
        ).to_command(**make_command_args())

        result = session_must_be_open_policy(
            cmd, session_lookup=lambda s: {"status": "OPEN"},
        )
        assert result is None

    def test_withdrawal_limit_rejects(self):
        from engines.cash.policies import withdrawal_limit_policy
        from engines.cash.commands import WithdrawalRecordRequest
        cmd = WithdrawalRecordRequest(
            withdrawal_id="w1", session_id="s1",
            drawer_id="d1", amount=50000,
            currency="KES",
        ).to_command(**make_command_args())

        result = withdrawal_limit_policy(
            cmd, drawer_balance_lookup=lambda d: 30000,
        )
        assert result is not None
        assert result.code == "INSUFFICIENT_DRAWER_BALANCE"

    def test_withdrawal_limit_passes(self):
        from engines.cash.policies import withdrawal_limit_policy
        from engines.cash.commands import WithdrawalRecordRequest
        cmd = WithdrawalRecordRequest(
            withdrawal_id="w1", session_id="s1",
            drawer_id="d1", amount=10000,
            currency="KES",
        ).to_command(**make_command_args())

        result = withdrawal_limit_policy(
            cmd, drawer_balance_lookup=lambda d: 50000,
        )
        assert result is None


# ══════════════════════════════════════════════════════════════
# CROSS-ENGINE DETERMINISM TEST
# ══════════════════════════════════════════════════════════════

class TestCrossEngineDeterminism:
    """Same operations in same order → identical state."""

    def test_deterministic_inventory_projection(self):
        from engines.inventory.services import InventoryService
        from engines.inventory.commands import (
            StockReceiveRequest, StockIssueRequest,
        )

        def run():
            svc = InventoryService(
                business_context={"business_id": BIZ_A},
                command_bus=StubCommandBus(),
                event_factory=StubEventFactory(),
                persist_event=StubPersistEvent(),
                event_type_registry=StubEventTypeRegistry(),
            )
            svc._execute_command(
                StockReceiveRequest(
                    item_id="i1", sku="S", quantity=100,
                    location_id="l1", location_name="Main",
                    branch_id=BRANCH,
                ).to_command(**make_command_args())
            )
            svc._execute_command(
                StockIssueRequest(
                    item_id="i1", sku="S", quantity=25,
                    location_id="l1", location_name="Main",
                    branch_id=BRANCH,
                ).to_command(**make_command_args())
            )
            return svc.projection_store.get_stock("i1", "l1")

        assert run() == run() == 75

    def test_deterministic_accounting_projection(self):
        from engines.accounting.services import AccountingService
        from engines.accounting.commands import JournalPostRequest

        def run():
            svc = AccountingService(
                business_context={"business_id": BIZ_A},
                command_bus=StubCommandBus(),
                event_factory=StubEventFactory(),
                persist_event=StubPersistEvent(),
                event_type_registry=StubEventTypeRegistry(),
            )
            svc._execute_command(
                JournalPostRequest(
                    entry_id="e1",
                    lines=(
                        {"account_code": "1000", "side": "DEBIT", "amount": 9999},
                        {"account_code": "4000", "side": "CREDIT", "amount": 9999},
                    ),
                    memo="Deterministic",
                    currency="KES",
                ).to_command(**make_command_args())
            )
            return svc.projection_store.trial_balance()

        assert run() == run() == (9999, 9999)
