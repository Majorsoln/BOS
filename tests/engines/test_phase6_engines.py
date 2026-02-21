"""
BOS Phase 6 — Retail & Procurement Engine Test Suite
=======================================================
Tests verify:
- Command creation and validation
- Event type resolution
- Payload building
- Service orchestration (command → event → projection)
- Policy enforcement
- Full lifecycle flows (sale open→line→complete, PO create→approve→receive)
- Projection correctness
- Determinism
"""

import uuid
from datetime import datetime, timezone

import pytest

BIZ_A = uuid.uuid4()
BRANCH = uuid.uuid4()
NOW = datetime(2026, 2, 19, 14, 0, 0, tzinfo=timezone.utc)


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
    def __init__(self):
        self._types = set()

    def register(self, event_type: str) -> None:
        self._types.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        return event_type in self._types


class StubEventFactory:
    def __call__(self, *, command, event_type, payload):
        return {
            "event_type": event_type,
            "payload": payload,
            "business_id": command.business_id,
            "source_engine": command.source_engine,
        }


class StubPersistEvent:
    def __init__(self):
        self.calls = []

    def __call__(self, *, event_data, context, registry, **kwargs):
        self.calls.append(event_data)
        return {"accepted": True}


class StubCommandBus:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, command_type, handler):
        self.handlers[command_type] = handler


# ══════════════════════════════════════════════════════════════
# RETAIL ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestRetailCommands:
    """Tests for retail command creation and validation."""

    def test_sale_open_request(self):
        from engines.retail.commands import SaleOpenRequest
        req = SaleOpenRequest(
            sale_id="sale-1", currency="KES",
            session_id="sess-1", drawer_id="d1",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "retail.sale.open.request"
        assert cmd.source_engine == "retail"

    def test_sale_add_line_request(self):
        from engines.retail.commands import SaleAddLineRequest
        req = SaleAddLineRequest(
            sale_id="sale-1", line_id="ln-1",
            item_id="item-1", sku="WIDGET-001",
            item_name="Widget", quantity=3, unit_price=1500,
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "retail.sale.add_line.request"
        assert cmd.payload["quantity"] == 3

    def test_sale_add_line_rejects_zero_quantity(self):
        from engines.retail.commands import SaleAddLineRequest
        with pytest.raises(ValueError, match="positive"):
            SaleAddLineRequest(
                sale_id="s1", line_id="l1",
                item_id="i1", sku="S", item_name="X",
                quantity=0, unit_price=100,
            )

    def test_sale_complete_request(self):
        from engines.retail.commands import SaleCompleteRequest
        req = SaleCompleteRequest(
            sale_id="sale-1",
            total_amount=4500, net_amount=4500,
            currency="KES", payment_method="CASH",
            lines=({"item_id": "i1", "quantity": 3, "unit_price": 1500},),
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "retail.sale.complete.request"

    def test_invalid_payment_method_rejected(self):
        from engines.retail.commands import SaleCompleteRequest
        with pytest.raises(ValueError, match="not valid"):
            SaleCompleteRequest(
                sale_id="s1",
                total_amount=100, net_amount=100,
                currency="KES", payment_method="CRYPTO",
                lines=({"item_id": "i1"},),
            )

    def test_sale_void_request(self):
        from engines.retail.commands import SaleVoidRequest
        req = SaleVoidRequest(sale_id="sale-1", reason="CASHIER_ERROR")
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "retail.sale.void.request"

    def test_invalid_void_reason_rejected(self):
        from engines.retail.commands import SaleVoidRequest
        with pytest.raises(ValueError, match="not valid"):
            SaleVoidRequest(sale_id="s1", reason="INVALID")

    def test_refund_issue_request(self):
        from engines.retail.commands import RefundIssueRequest
        req = RefundIssueRequest(
            refund_id="ref-1", original_sale_id="sale-1",
            amount=1500, currency="KES",
            reason="DEFECTIVE_PRODUCT",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "retail.refund.issue.request"

    def test_discount_request(self):
        from engines.retail.commands import SaleApplyDiscountRequest
        req = SaleApplyDiscountRequest(
            sale_id="sale-1",
            discount_type="PERCENTAGE",
            discount_value=10,
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "retail.sale.apply_discount.request"

    def test_invalid_discount_type_rejected(self):
        from engines.retail.commands import SaleApplyDiscountRequest
        with pytest.raises(ValueError, match="not valid"):
            SaleApplyDiscountRequest(
                sale_id="s1", discount_type="BOGO",
                discount_value=100,
            )


class TestRetailEvents:
    """Tests for retail event type resolution."""

    def test_event_type_resolution(self):
        from engines.retail.events import resolve_retail_event_type
        assert resolve_retail_event_type(
            "retail.sale.open.request"
        ) == "retail.sale.opened.v1"
        assert resolve_retail_event_type(
            "retail.sale.complete.request"
        ) == "retail.sale.completed.v1"
        assert resolve_retail_event_type(
            "retail.refund.issue.request"
        ) == "retail.refund.issued.v1"
        assert resolve_retail_event_type("unknown") is None

    def test_event_registration(self):
        from engines.retail.events import register_retail_event_types
        registry = StubEventTypeRegistry()
        register_retail_event_types(registry)
        assert registry.is_registered("retail.sale.opened.v1")
        assert registry.is_registered("retail.sale.completed.v1")
        assert registry.is_registered("retail.refund.issued.v1")

    def test_line_added_payload_computes_line_total(self):
        from engines.retail.commands import SaleAddLineRequest
        from engines.retail.events import build_sale_line_added_payload
        cmd = SaleAddLineRequest(
            sale_id="s1", line_id="l1",
            item_id="i1", sku="S", item_name="Widget",
            quantity=3, unit_price=1500,
        ).to_command(**make_command_args())
        payload = build_sale_line_added_payload(cmd)
        assert payload["line_total"] == 4500


class TestRetailService:
    """Tests for retail service — full sale lifecycle."""

    def _make_service(self):
        from engines.retail.services import RetailService
        return RetailService(
            business_context={"business_id": BIZ_A},
            command_bus=StubCommandBus(),
            event_factory=StubEventFactory(),
            persist_event=StubPersistEvent(),
            event_type_registry=StubEventTypeRegistry(),
        )

    def test_service_registers_all_handlers(self):
        from engines.retail.commands import RETAIL_COMMAND_TYPES
        service = self._make_service()
        for ct in RETAIL_COMMAND_TYPES:
            assert ct in service._command_bus.handlers

    def test_full_sale_lifecycle(self):
        from engines.retail.commands import (
            SaleOpenRequest, SaleAddLineRequest,
            SaleCompleteRequest,
        )
        service = self._make_service()

        # Open
        service._execute_command(
            SaleOpenRequest(
                sale_id="s1", currency="KES",
            ).to_command(**make_command_args())
        )
        sale = service.projection_store.get_sale("s1")
        assert sale["status"] == "OPEN"

        # Add line 1
        service._execute_command(
            SaleAddLineRequest(
                sale_id="s1", line_id="l1",
                item_id="i1", sku="SKU-1", item_name="Widget A",
                quantity=2, unit_price=1000,
            ).to_command(**make_command_args())
        )

        # Add line 2
        service._execute_command(
            SaleAddLineRequest(
                sale_id="s1", line_id="l2",
                item_id="i2", sku="SKU-2", item_name="Widget B",
                quantity=1, unit_price=3000,
            ).to_command(**make_command_args())
        )

        sale = service.projection_store.get_sale("s1")
        assert sale["total_amount"] == 5000
        assert len(sale["lines"]) == 2

        # Complete
        service._execute_command(
            SaleCompleteRequest(
                sale_id="s1",
                total_amount=5000, net_amount=5000,
                currency="KES", payment_method="CASH",
                lines=(
                    {"item_id": "i1", "quantity": 2, "unit_price": 1000},
                    {"item_id": "i2", "quantity": 1, "unit_price": 3000},
                ),
            ).to_command(**make_command_args())
        )

        sale = service.projection_store.get_sale("s1")
        assert sale["status"] == "COMPLETED"
        assert service.projection_store.total_revenue == 5000
        assert service.projection_store.sale_count == 1

    def test_remove_line_adjusts_total(self):
        from engines.retail.commands import (
            SaleOpenRequest, SaleAddLineRequest, SaleRemoveLineRequest,
        )
        service = self._make_service()

        service._execute_command(
            SaleOpenRequest(sale_id="s1", currency="KES").to_command(**make_command_args())
        )
        service._execute_command(
            SaleAddLineRequest(
                sale_id="s1", line_id="l1",
                item_id="i1", sku="S", item_name="A",
                quantity=5, unit_price=200,
            ).to_command(**make_command_args())
        )
        sale = service.projection_store.get_sale("s1")
        assert sale["total_amount"] == 1000

        service._execute_command(
            SaleRemoveLineRequest(
                sale_id="s1", line_id="l1",
            ).to_command(**make_command_args())
        )
        sale = service.projection_store.get_sale("s1")
        assert sale["total_amount"] == 0
        assert len(sale["lines"]) == 0

    def test_void_reverses_revenue(self):
        from engines.retail.commands import (
            SaleOpenRequest, SaleAddLineRequest,
            SaleCompleteRequest, SaleVoidRequest,
        )
        service = self._make_service()

        service._execute_command(
            SaleOpenRequest(sale_id="s1", currency="KES").to_command(**make_command_args())
        )
        service._execute_command(
            SaleAddLineRequest(
                sale_id="s1", line_id="l1",
                item_id="i1", sku="S", item_name="A",
                quantity=1, unit_price=5000,
            ).to_command(**make_command_args())
        )
        service._execute_command(
            SaleCompleteRequest(
                sale_id="s1", total_amount=5000, net_amount=5000,
                currency="KES", payment_method="CASH",
                lines=({"item_id": "i1", "quantity": 1, "unit_price": 5000},),
            ).to_command(**make_command_args())
        )
        assert service.projection_store.total_revenue == 5000

        service._execute_command(
            SaleVoidRequest(
                sale_id="s1", reason="CASHIER_ERROR",
            ).to_command(**make_command_args())
        )
        assert service.projection_store.total_revenue == 0
        assert service.projection_store.sale_count == 0

    def test_refund_tracked(self):
        from engines.retail.commands import RefundIssueRequest
        service = self._make_service()

        service._execute_command(
            RefundIssueRequest(
                refund_id="r1", original_sale_id="s1",
                amount=2000, currency="KES",
                reason="DEFECTIVE_PRODUCT",
            ).to_command(**make_command_args())
        )
        assert service.projection_store.total_refunds == 2000


class TestRetailPolicies:
    """Tests for retail engine policies."""

    def test_sale_must_be_open_rejects_completed(self):
        from engines.retail.policies import sale_must_be_open_policy
        from engines.retail.commands import SaleAddLineRequest
        cmd = SaleAddLineRequest(
            sale_id="s1", line_id="l1",
            item_id="i1", sku="S", item_name="A",
            quantity=1, unit_price=100,
        ).to_command(**make_command_args())

        result = sale_must_be_open_policy(
            cmd, sale_lookup=lambda s: {"status": "COMPLETED"},
        )
        assert result is not None
        assert result.code == "SALE_NOT_OPEN"

    def test_sale_must_be_open_passes(self):
        from engines.retail.policies import sale_must_be_open_policy
        from engines.retail.commands import SaleAddLineRequest
        cmd = SaleAddLineRequest(
            sale_id="s1", line_id="l1",
            item_id="i1", sku="S", item_name="A",
            quantity=1, unit_price=100,
        ).to_command(**make_command_args())

        result = sale_must_be_open_policy(
            cmd, sale_lookup=lambda s: {"status": "OPEN"},
        )
        assert result is None

    def test_void_requires_completed(self):
        from engines.retail.policies import void_requires_completed_policy
        from engines.retail.commands import SaleVoidRequest
        cmd = SaleVoidRequest(
            sale_id="s1", reason="CASHIER_ERROR",
        ).to_command(**make_command_args())

        result = void_requires_completed_policy(
            cmd, sale_lookup=lambda s: {"status": "OPEN"},
        )
        assert result is not None
        assert result.code == "SALE_NOT_COMPLETED"

    def test_refund_within_sale_amount(self):
        from engines.retail.policies import refund_within_sale_amount_policy
        from engines.retail.commands import RefundIssueRequest
        cmd = RefundIssueRequest(
            refund_id="r1", original_sale_id="s1",
            amount=10000, currency="KES",
            reason="DEFECTIVE_PRODUCT",
        ).to_command(**make_command_args())

        result = refund_within_sale_amount_policy(
            cmd, sale_lookup=lambda s: {"net_amount": 5000},
        )
        assert result is not None
        assert result.code == "REFUND_EXCEEDS_SALE"


# ══════════════════════════════════════════════════════════════
# PROCUREMENT ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestProcurementCommands:
    """Tests for procurement command creation and validation."""

    def test_order_create_request(self):
        from engines.procurement.commands import OrderCreateRequest
        req = OrderCreateRequest(
            order_id="po-1",
            supplier_id="sup-1", supplier_name="Acme Corp",
            lines=(
                {"item_id": "i1", "sku": "S1", "quantity": 100, "unit_cost": 50},
            ),
            total_amount=5000, currency="KES",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "procurement.order.create.request"
        assert cmd.source_engine == "procurement"

    def test_empty_lines_rejected(self):
        from engines.procurement.commands import OrderCreateRequest
        with pytest.raises(ValueError, match="non-empty"):
            OrderCreateRequest(
                order_id="po-1",
                supplier_id="sup-1", supplier_name="Acme",
                lines=(), total_amount=100, currency="KES",
            )

    def test_order_approve_request(self):
        from engines.procurement.commands import OrderApproveRequest
        req = OrderApproveRequest(order_id="po-1")
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "procurement.order.approve.request"

    def test_order_receive_request(self):
        from engines.procurement.commands import OrderReceiveRequest
        req = OrderReceiveRequest(
            order_id="po-1",
            received_lines=(
                {"item_id": "i1", "quantity_received": 100},
            ),
            location_id="loc-1", location_name="Main",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "procurement.order.receive.request"

    def test_order_cancel_request(self):
        from engines.procurement.commands import OrderCancelRequest
        req = OrderCancelRequest(
            order_id="po-1", reason="SUPPLIER_UNAVAILABLE",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "procurement.order.cancel.request"

    def test_invalid_cancel_reason_rejected(self):
        from engines.procurement.commands import OrderCancelRequest
        with pytest.raises(ValueError, match="not valid"):
            OrderCancelRequest(order_id="po-1", reason="DONT_WANT_IT")

    def test_invoice_match_request(self):
        from engines.procurement.commands import InvoiceMatchRequest
        req = InvoiceMatchRequest(
            invoice_id="inv-1", order_id="po-1",
            invoice_amount=5000, currency="KES",
        )
        cmd = req.to_command(**make_command_args())
        assert cmd.command_type == "procurement.invoice.match.request"


class TestProcurementEvents:
    """Tests for procurement event type resolution."""

    def test_event_type_resolution(self):
        from engines.procurement.events import resolve_procurement_event_type
        assert resolve_procurement_event_type(
            "procurement.order.create.request"
        ) == "procurement.order.created.v1"
        assert resolve_procurement_event_type(
            "procurement.order.receive.request"
        ) == "procurement.order.received.v1"
        assert resolve_procurement_event_type(
            "procurement.invoice.match.request"
        ) == "procurement.invoice.matched.v1"

    def test_event_registration(self):
        from engines.procurement.events import register_procurement_event_types
        registry = StubEventTypeRegistry()
        register_procurement_event_types(registry)
        assert registry.is_registered("procurement.order.created.v1")
        assert registry.is_registered("procurement.order.received.v1")
        assert registry.is_registered("procurement.invoice.matched.v1")


class TestProcurementService:
    """Tests for procurement service — full PO lifecycle."""

    def _make_service(self):
        from engines.procurement.services import ProcurementService
        return ProcurementService(
            business_context={"business_id": BIZ_A},
            command_bus=StubCommandBus(),
            event_factory=StubEventFactory(),
            persist_event=StubPersistEvent(),
            event_type_registry=StubEventTypeRegistry(),
        )

    def test_service_registers_all_handlers(self):
        from engines.procurement.commands import PROCUREMENT_COMMAND_TYPES
        service = self._make_service()
        for ct in PROCUREMENT_COMMAND_TYPES:
            assert ct in service._command_bus.handlers

    def test_full_po_lifecycle(self):
        from engines.procurement.commands import (
            OrderCreateRequest, OrderApproveRequest,
            OrderReceiveRequest, InvoiceMatchRequest,
        )
        service = self._make_service()

        # Create PO
        service._execute_command(
            OrderCreateRequest(
                order_id="po-1",
                supplier_id="sup-1", supplier_name="Acme",
                lines=({"item_id": "i1", "quantity": 100, "unit_cost": 50},),
                total_amount=5000, currency="KES",
            ).to_command(**make_command_args())
        )
        order = service.projection_store.get_order("po-1")
        assert order["status"] == "PENDING"

        # Approve
        service._execute_command(
            OrderApproveRequest(order_id="po-1").to_command(**make_command_args())
        )
        order = service.projection_store.get_order("po-1")
        assert order["status"] == "APPROVED"

        # Receive
        service._execute_command(
            OrderReceiveRequest(
                order_id="po-1",
                received_lines=({"item_id": "i1", "quantity_received": 100},),
                location_id="loc-1", location_name="Main",
            ).to_command(**make_command_args())
        )
        order = service.projection_store.get_order("po-1")
        assert order["status"] == "RECEIVED"

        # Invoice match
        service._execute_command(
            InvoiceMatchRequest(
                invoice_id="inv-1", order_id="po-1",
                invoice_amount=5000, currency="KES",
            ).to_command(**make_command_args())
        )
        order = service.projection_store.get_order("po-1")
        assert order["status"] == "INVOICED"

    def test_cancel_reverses_total_ordered(self):
        from engines.procurement.commands import (
            OrderCreateRequest, OrderCancelRequest,
        )
        service = self._make_service()

        service._execute_command(
            OrderCreateRequest(
                order_id="po-1",
                supplier_id="sup-1", supplier_name="Acme",
                lines=({"item_id": "i1", "quantity": 10, "unit_cost": 100},),
                total_amount=1000, currency="KES",
            ).to_command(**make_command_args())
        )
        assert service.projection_store.total_ordered == 1000

        service._execute_command(
            OrderCancelRequest(
                order_id="po-1", reason="BUSINESS_DECISION",
            ).to_command(**make_command_args())
        )
        order = service.projection_store.get_order("po-1")
        assert order["status"] == "CANCELLED"
        assert service.projection_store.total_ordered == 0


class TestProcurementPolicies:
    """Tests for procurement engine policies."""

    def test_approval_requires_pending(self):
        from engines.procurement.policies import order_must_be_pending_for_approval_policy
        from engines.procurement.commands import OrderApproveRequest
        cmd = OrderApproveRequest(
            order_id="po-1",
        ).to_command(**make_command_args())

        result = order_must_be_pending_for_approval_policy(
            cmd, order_lookup=lambda o: {"status": "APPROVED"},
        )
        assert result is not None
        assert result.code == "ORDER_NOT_PENDING"

    def test_approval_passes_for_pending(self):
        from engines.procurement.policies import order_must_be_pending_for_approval_policy
        from engines.procurement.commands import OrderApproveRequest
        cmd = OrderApproveRequest(
            order_id="po-1",
        ).to_command(**make_command_args())

        result = order_must_be_pending_for_approval_policy(
            cmd, order_lookup=lambda o: {"status": "PENDING"},
        )
        assert result is None

    def test_receipt_requires_approved(self):
        from engines.procurement.policies import order_must_be_approved_for_receipt_policy
        from engines.procurement.commands import OrderReceiveRequest
        cmd = OrderReceiveRequest(
            order_id="po-1",
            received_lines=({"item_id": "i1", "quantity_received": 10},),
            location_id="loc-1", location_name="Main",
        ).to_command(**make_command_args())

        result = order_must_be_approved_for_receipt_policy(
            cmd, order_lookup=lambda o: {"status": "PENDING"},
        )
        assert result is not None
        assert result.code == "ORDER_NOT_APPROVED"

    def test_invoice_tolerance_rejects(self):
        from engines.procurement.policies import invoice_amount_must_match_policy
        from engines.procurement.commands import InvoiceMatchRequest
        cmd = InvoiceMatchRequest(
            invoice_id="inv-1", order_id="po-1",
            invoice_amount=20000, currency="KES",
        ).to_command(**make_command_args())

        result = invoice_amount_must_match_policy(
            cmd,
            order_lookup=lambda o: {"total_amount": 10000},
            tolerance_percent=5,
        )
        assert result is not None
        assert result.code == "INVOICE_EXCEEDS_PO"

    def test_invoice_within_tolerance_passes(self):
        from engines.procurement.policies import invoice_amount_must_match_policy
        from engines.procurement.commands import InvoiceMatchRequest
        cmd = InvoiceMatchRequest(
            invoice_id="inv-1", order_id="po-1",
            invoice_amount=10400, currency="KES",
        ).to_command(**make_command_args())

        result = invoice_amount_must_match_policy(
            cmd,
            order_lookup=lambda o: {"total_amount": 10000},
            tolerance_percent=5,
        )
        assert result is None


# ══════════════════════════════════════════════════════════════
# CROSS-ENGINE DETERMINISM
# ══════════════════════════════════════════════════════════════

class TestPhase6Determinism:
    """Same operations → identical state."""

    def test_deterministic_retail(self):
        from engines.retail.services import RetailService
        from engines.retail.commands import (
            SaleOpenRequest, SaleAddLineRequest, SaleCompleteRequest,
        )

        def run():
            svc = RetailService(
                business_context={"business_id": BIZ_A},
                command_bus=StubCommandBus(),
                event_factory=StubEventFactory(),
                persist_event=StubPersistEvent(),
                event_type_registry=StubEventTypeRegistry(),
            )
            svc._execute_command(
                SaleOpenRequest(sale_id="s1", currency="KES")
                .to_command(**make_command_args())
            )
            svc._execute_command(
                SaleAddLineRequest(
                    sale_id="s1", line_id="l1",
                    item_id="i1", sku="S", item_name="A",
                    quantity=5, unit_price=200,
                ).to_command(**make_command_args())
            )
            svc._execute_command(
                SaleCompleteRequest(
                    sale_id="s1", total_amount=1000, net_amount=1000,
                    currency="KES", payment_method="CASH",
                    lines=({"item_id": "i1", "quantity": 5, "unit_price": 200},),
                ).to_command(**make_command_args())
            )
            return svc.projection_store.total_revenue

        assert run() == run() == 1000

    def test_deterministic_procurement(self):
        from engines.procurement.services import ProcurementService
        from engines.procurement.commands import (
            OrderCreateRequest, OrderApproveRequest,
        )

        def run():
            svc = ProcurementService(
                business_context={"business_id": BIZ_A},
                command_bus=StubCommandBus(),
                event_factory=StubEventFactory(),
                persist_event=StubPersistEvent(),
                event_type_registry=StubEventTypeRegistry(),
            )
            svc._execute_command(
                OrderCreateRequest(
                    order_id="po-1",
                    supplier_id="s1", supplier_name="Acme",
                    lines=({"item_id": "i1", "quantity": 50},),
                    total_amount=25000, currency="KES",
                ).to_command(**make_command_args())
            )
            svc._execute_command(
                OrderApproveRequest(order_id="po-1")
                .to_command(**make_command_args())
            )
            return (
                svc.projection_store.get_order("po-1")["status"],
                svc.projection_store.total_ordered,
            )

        assert run() == run() == ("APPROVED", 25000)
