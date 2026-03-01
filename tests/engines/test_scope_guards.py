"""
BOS GAP-10 — Scope Guard Enforcement Tests
==============================================
Verifies that branch-required operations reject branch_id=None
and business-allowed operations accept branch_id=None.

Doctrine: scope-policy.md §4, §5
"""

import uuid
from datetime import datetime, timezone

import pytest

from core.context.scope import SCOPE_BUSINESS_ALLOWED, SCOPE_BRANCH_REQUIRED
from core.context.scope_guard import enforce_scope_guard

BIZ = uuid.uuid4()
BRANCH = uuid.uuid4()
NOW = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)


def kw():
    """Standard command kwargs — branch_id is set on the request object, not here."""
    return dict(business_id=BIZ, actor_type="HUMAN", actor_id="actor-1",
                command_id=uuid.uuid4(), correlation_id=uuid.uuid4(),
                issued_at=NOW)


# ══════════════════════════════════════════════════════════════
# UNIT: enforce_scope_guard
# ══════════════════════════════════════════════════════════════

class TestScopeGuardFunction:
    def test_branch_required_with_branch_passes(self):
        from core.commands.base import Command
        cmd = Command(
            command_id=uuid.uuid4(), command_type="test.scope.guard.request",
            business_id=BIZ, branch_id=BRANCH,
            actor_type="HUMAN", actor_id="a",
            payload={}, issued_at=NOW,
            correlation_id=uuid.uuid4(), source_engine="test",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement="ACTOR_REQUIRED",
        )
        enforce_scope_guard(cmd)  # should not raise

    def test_branch_required_without_branch_rejects(self):
        from core.commands.base import Command
        cmd = Command(
            command_id=uuid.uuid4(), command_type="test.scope.guard.request",
            business_id=BIZ, branch_id=None,
            actor_type="HUMAN", actor_id="a",
            payload={}, issued_at=NOW,
            correlation_id=uuid.uuid4(), source_engine="test",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement="ACTOR_REQUIRED",
        )
        with pytest.raises(ValueError, match="BRANCH_REQUIRED"):
            enforce_scope_guard(cmd)

    def test_business_allowed_without_branch_passes(self):
        from core.commands.base import Command
        cmd = Command(
            command_id=uuid.uuid4(), command_type="test.scope.guard.request",
            business_id=BIZ, branch_id=None,
            actor_type="HUMAN", actor_id="a",
            payload={}, issued_at=NOW,
            correlation_id=uuid.uuid4(), source_engine="test",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement="ACTOR_REQUIRED",
        )
        enforce_scope_guard(cmd)  # should not raise


# ══════════════════════════════════════════════════════════════
# SCOPE REQUIREMENTS PER COMMAND (scope-policy.md §5)
# ══════════════════════════════════════════════════════════════

class TestScopeRequirementsPerCommand:
    """
    Verifies that each command emits the correct scope_requirement
    per the scope-policy.md matrix.
    """

    # ── Cash (§5.7) ───────────────────────────────────────────

    def test_cash_session_open_requires_branch(self):
        from engines.cash.commands import SessionOpenRequest
        cmd = SessionOpenRequest(
            session_id="S1", drawer_id="D1", opening_balance=10000,
            currency="KES", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_cash_session_close_requires_branch(self):
        from engines.cash.commands import SessionCloseRequest
        cmd = SessionCloseRequest(
            session_id="S1", drawer_id="D1", closing_balance=10000,
            currency="KES", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_cash_payment_allows_business(self):
        from engines.cash.commands import PaymentRecordRequest
        cmd = PaymentRecordRequest(
            payment_id="P1", session_id="S1", drawer_id="D1",
            amount=5000, currency="KES", payment_method="CASH",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BUSINESS_ALLOWED

    def test_cash_deposit_requires_branch(self):
        from engines.cash.commands import DepositRecordRequest
        cmd = DepositRecordRequest(
            deposit_id="DEP1", session_id="S1", drawer_id="D1",
            amount=5000, currency="KES", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_cash_withdrawal_requires_branch(self):
        from engines.cash.commands import WithdrawalRecordRequest
        cmd = WithdrawalRecordRequest(
            withdrawal_id="W1", session_id="S1", drawer_id="D1",
            amount=5000, currency="KES", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    # ── Inventory (§5.8) ──────────────────────────────────────

    def test_inventory_stock_receive_requires_branch(self):
        from engines.inventory.commands import StockReceiveRequest
        cmd = StockReceiveRequest(
            item_id="I1", sku="SK1", quantity=10,
            location_id="L1", location_name="Warehouse A",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_inventory_stock_issue_requires_branch(self):
        from engines.inventory.commands import StockIssueRequest
        cmd = StockIssueRequest(
            item_id="I1", sku="SK1", quantity=5,
            location_id="L1", location_name="Warehouse A",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_inventory_stock_transfer_requires_branch(self):
        from engines.inventory.commands import StockTransferRequest
        cmd = StockTransferRequest(
            item_id="I1", sku="SK1", quantity=5,
            from_location_id="L1", from_location_name="WH-A",
            to_location_id="L2", to_location_name="WH-B",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_inventory_stock_adjust_requires_branch(self):
        from engines.inventory.commands import StockAdjustRequest
        cmd = StockAdjustRequest(
            item_id="I1", sku="SK1", quantity=2,
            adjustment_type="ADJUST_PLUS", location_id="L1",
            location_name="WH-A", reason="PHYSICAL_COUNT",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_inventory_item_register_allows_business(self):
        from engines.inventory.commands import ItemRegisterRequest
        cmd = ItemRegisterRequest(
            item_id="I1", sku="SK1", name="Widget",
            item_type="PRODUCT", unit_of_measure="PCS",
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BUSINESS_ALLOWED

    # ── Retail (§5.10) ────────────────────────────────────────

    def test_retail_sale_open_requires_branch(self):
        from engines.retail.commands import SaleOpenRequest
        cmd = SaleOpenRequest(
            sale_id="S1", currency="KES", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_retail_sale_complete_requires_branch(self):
        from engines.retail.commands import SaleCompleteRequest
        cmd = SaleCompleteRequest(
            sale_id="S1", total_amount=10000, net_amount=10000,
            currency="KES", payment_method="CASH",
            lines=({"item_id": "I1", "qty": 1},),
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    # ── Restaurant (§5.10) ────────────────────────────────────

    def test_restaurant_table_open_requires_branch(self):
        from engines.restaurant.commands import TableOpenRequest
        cmd = TableOpenRequest(
            table_id="T1", table_name="Table 1", covers=4,
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_restaurant_bill_settle_requires_branch(self):
        from engines.restaurant.commands import BillSettleRequest
        cmd = BillSettleRequest(
            bill_id="B1", table_id="T1", total_amount=5000,
            currency="KES", payment_method="CASH",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    # ── Workshop (§5.11) ──────────────────────────────────────

    def test_workshop_job_create_allows_business(self):
        from engines.workshop.commands import JobCreateRequest
        cmd = JobCreateRequest(
            job_id="J1", customer_id="C1", description="Fix door",
            currency="KES",
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BUSINESS_ALLOWED

    def test_workshop_job_start_requires_branch(self):
        from engines.workshop.commands import JobStartRequest
        cmd = JobStartRequest(
            job_id="J1", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_workshop_material_consume_requires_branch(self):
        from engines.workshop.commands import MaterialConsumeRequest
        cmd = MaterialConsumeRequest(
            consumption_id="MC1", job_id="J1", material_id="M1",
            quantity_used=5, unit="MM", branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    def test_workshop_offcut_record_requires_branch(self):
        from engines.workshop.commands import OffcutRecordRequest
        cmd = OffcutRecordRequest(
            offcut_id="OC1", job_id="J1", material_id="M1",
            length_mm=500, branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED

    # ── Procurement (§5.9) ────────────────────────────────────

    def test_procurement_order_create_allows_business(self):
        from engines.procurement.commands import OrderCreateRequest
        cmd = OrderCreateRequest(
            order_id="PO1", supplier_id="S1", supplier_name="Acme",
            lines=({"item": "I1"},), total_amount=50000, currency="KES",
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BUSINESS_ALLOWED

    def test_procurement_order_receive_requires_branch(self):
        from engines.procurement.commands import OrderReceiveRequest
        cmd = OrderReceiveRequest(
            order_id="PO1", received_lines=({"item": "I1", "qty": 10},),
            location_id="WH-A", location_name="Warehouse A",
            branch_id=BRANCH,
        ).to_command(**kw())
        assert cmd.scope_requirement == SCOPE_BRANCH_REQUIRED


# ══════════════════════════════════════════════════════════════
# INTEGRATION: Scope Guard Blocks Engine Execution
# ══════════════════════════════════════════════════════════════

class StubReg:
    def __init__(self):
        self._t = set()
    def register(self, et):
        self._t.add(et)
    def is_registered(self, et):
        return et in self._t


class StubFactory:
    def __call__(self, *, command, event_type, payload):
        return {"event_type": event_type, "payload": payload,
                "business_id": command.business_id}


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


class TestScopeGuardBlocksExecution:
    def test_inventory_stock_receive_without_branch_blocked(self):
        from engines.inventory.services import InventoryService
        from engines.inventory.commands import StockReceiveRequest
        svc = InventoryService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())
        cmd = StockReceiveRequest(
            item_id="I1", sku="SK1", quantity=10,
            location_id="L1", location_name="WH-A",
        ).to_command(**kw())
        with pytest.raises(ValueError, match="BRANCH_REQUIRED"):
            svc._execute_command(cmd)

    def test_inventory_item_register_without_branch_allowed(self):
        from engines.inventory.services import InventoryService
        from engines.inventory.commands import ItemRegisterRequest
        svc = InventoryService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())
        cmd = ItemRegisterRequest(
            item_id="I1", sku="SK1", name="Widget",
            item_type="PRODUCT", unit_of_measure="PCS",
        ).to_command(**kw())
        result = svc._execute_command(cmd)
        assert result.projection_applied

    def test_retail_sale_without_branch_blocked(self):
        from engines.retail.services import RetailService
        from engines.retail.commands import SaleOpenRequest
        svc = RetailService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())
        cmd = SaleOpenRequest(
            sale_id="S1", currency="KES",
        ).to_command(**kw())
        with pytest.raises(ValueError, match="BRANCH_REQUIRED"):
            svc._execute_command(cmd)

    def test_restaurant_table_without_branch_blocked(self):
        from engines.restaurant.services import RestaurantService
        from engines.restaurant.commands import TableOpenRequest
        svc = RestaurantService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())
        cmd = TableOpenRequest(
            table_id="T1", table_name="Table 1", covers=4,
        ).to_command(**kw())
        with pytest.raises(ValueError, match="BRANCH_REQUIRED"):
            svc._execute_command(cmd)
