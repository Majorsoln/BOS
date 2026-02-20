"""
BOS Phase 7 — Restaurant, Workshop, Promotion, HR Engine Tests
================================================================
All 9 engine skeletons now fully implemented.
"""

import uuid
from datetime import datetime, timezone

import pytest

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 19, 16, 0, 0, tzinfo=timezone.utc)


def kw():
    return dict(business_id=BIZ, actor_type="HUMAN", actor_id="actor-1",
                command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW)


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
                "business_id": command.business_id, "source_engine": command.source_engine}


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


# ══════════════════════════════════════════════════════════════
# RESTAURANT
# ══════════════════════════════════════════════════════════════

class TestRestaurant:
    def _svc(self):
        from engines.restaurant.services import RestaurantService
        return RestaurantService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())

    def test_handlers_registered(self):
        from engines.restaurant.commands import RESTAURANT_COMMAND_TYPES
        s = self._svc()
        for ct in RESTAURANT_COMMAND_TYPES:
            assert ct in s._command_bus.handlers

    def test_full_lifecycle(self):
        from engines.restaurant.commands import (
            TableOpenRequest, OrderPlaceRequest,
            OrderServeItemRequest, BillSettleRequest, TableCloseRequest,
        )
        s = self._svc()
        s._execute_command(TableOpenRequest(
            table_id="t1", table_name="Table 1", covers=4,
        ).to_command(**kw()))
        assert s.projection_store.get_table("t1")["status"] == "OPEN"

        s._execute_command(OrderPlaceRequest(
            order_id="o1", table_id="t1",
            items=({"item_id": "m1", "name": "Pizza", "price": 1500},),
            currency="KES",
        ).to_command(**kw()))
        assert s.projection_store.get_order("o1")["status"] == "PLACED"

        s._execute_command(OrderServeItemRequest(
            order_id="o1", item_id="m1",
        ).to_command(**kw()))
        assert s.projection_store.get_order("o1")["status"] == "FULLY_SERVED"

        s._execute_command(BillSettleRequest(
            bill_id="b1", table_id="t1",
            total_amount=1500, currency="KES",
            payment_method="CASH", tip_amount=200,
        ).to_command(**kw()))
        assert s.projection_store.total_revenue == 1500
        assert s.projection_store.total_tips == 200

        s._execute_command(TableCloseRequest(table_id="t1").to_command(**kw()))
        assert s.projection_store.get_table("t1")["status"] == "CLOSED"

    def test_order_cancel(self):
        from engines.restaurant.commands import (
            TableOpenRequest, OrderPlaceRequest, OrderCancelRequest,
        )
        s = self._svc()
        s._execute_command(TableOpenRequest(
            table_id="t1", table_name="T1", covers=2).to_command(**kw()))
        s._execute_command(OrderPlaceRequest(
            order_id="o1", table_id="t1",
            items=({"item_id": "m1", "name": "Soup", "price": 500},),
            currency="KES",
        ).to_command(**kw()))
        s._execute_command(OrderCancelRequest(
            order_id="o1", reason="CUSTOMER_REQUEST",
        ).to_command(**kw()))
        assert s.projection_store.get_order("o1")["status"] == "CANCELLED"

    def test_invalid_cancel_reason(self):
        from engines.restaurant.commands import OrderCancelRequest
        with pytest.raises(ValueError, match="not valid"):
            OrderCancelRequest(order_id="o1", reason="BAD")

    def test_table_policy(self):
        from engines.restaurant.policies import table_must_be_open_policy
        from engines.restaurant.commands import OrderPlaceRequest
        cmd = OrderPlaceRequest(
            order_id="o1", table_id="t1",
            items=({"item_id": "m1"},), currency="KES",
        ).to_command(**kw())
        r = table_must_be_open_policy(cmd, table_lookup=lambda t: {"status": "CLOSED"})
        assert r is not None
        assert r.code == "TABLE_NOT_OPEN"


# ══════════════════════════════════════════════════════════════
# WORKSHOP
# ══════════════════════════════════════════════════════════════

class TestWorkshop:
    def _svc(self):
        from engines.workshop.services import WorkshopService
        return WorkshopService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())

    def test_handlers_registered(self):
        from engines.workshop.commands import WORKSHOP_COMMAND_TYPES
        s = self._svc()
        for ct in WORKSHOP_COMMAND_TYPES:
            assert ct in s._command_bus.handlers

    def test_full_job_lifecycle(self):
        from engines.workshop.commands import (
            JobCreateRequest, JobAssignRequest,
            JobStartRequest, JobCompleteRequest, JobInvoiceRequest,
        )
        s = self._svc()

        s._execute_command(JobCreateRequest(
            job_id="j1", customer_id="c1",
            description="Laptop screen repair", currency="KES",
            estimated_cost=5000,
        ).to_command(**kw()))
        assert s.projection_store.get_job("j1")["status"] == "CREATED"

        s._execute_command(JobAssignRequest(
            job_id="j1", technician_id="tech-1",
        ).to_command(**kw()))
        assert s.projection_store.get_job("j1")["status"] == "ASSIGNED"

        s._execute_command(JobStartRequest(job_id="j1").to_command(**kw()))
        assert s.projection_store.get_job("j1")["status"] == "IN_PROGRESS"

        s._execute_command(JobCompleteRequest(
            job_id="j1", final_cost=4500, currency="KES",
            labor_hours=3,
        ).to_command(**kw()))
        assert s.projection_store.get_job("j1")["status"] == "COMPLETED"

        s._execute_command(JobInvoiceRequest(
            job_id="j1", invoice_id="inv-1",
            amount=4500, currency="KES",
        ).to_command(**kw()))
        assert s.projection_store.get_job("j1")["status"] == "INVOICED"
        assert s.projection_store.total_revenue == 4500

    def test_job_must_be_assigned_to_start(self):
        from engines.workshop.policies import job_must_be_assigned_to_start_policy
        from engines.workshop.commands import JobStartRequest
        cmd = JobStartRequest(job_id="j1").to_command(**kw())
        r = job_must_be_assigned_to_start_policy(
            cmd, job_lookup=lambda j: {"status": "CREATED"})
        assert r is not None
        assert r.code == "JOB_NOT_ASSIGNED"


# ══════════════════════════════════════════════════════════════
# PROMOTION
# ══════════════════════════════════════════════════════════════

class TestPromotion:
    def _svc(self):
        from engines.promotion.services import PromotionService
        return PromotionService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())

    def test_handlers_registered(self):
        from engines.promotion.commands import PROMOTION_COMMAND_TYPES
        s = self._svc()
        for ct in PROMOTION_COMMAND_TYPES:
            assert ct in s._command_bus.handlers

    def test_campaign_lifecycle(self):
        from engines.promotion.commands import (
            CampaignCreateRequest, CampaignActivateRequest,
            CouponIssueRequest, CouponRedeemRequest,
            CampaignDeactivateRequest,
        )
        s = self._svc()

        s._execute_command(CampaignCreateRequest(
            campaign_id="camp-1", name="Summer Sale",
            campaign_type="SEASONAL", discount_type="PERCENTAGE",
            discount_value=15, start_date="2026-06-01", end_date="2026-08-31",
        ).to_command(**kw()))
        assert s.projection_store.get_campaign("camp-1")["status"] == "DRAFT"

        s._execute_command(CampaignActivateRequest(
            campaign_id="camp-1",
        ).to_command(**kw()))
        assert s.projection_store.get_campaign("camp-1")["status"] == "ACTIVE"

        s._execute_command(CouponIssueRequest(
            coupon_id="cpn-1", campaign_id="camp-1",
        ).to_command(**kw()))
        assert s.projection_store.get_coupon("cpn-1")["status"] == "ISSUED"

        s._execute_command(CouponRedeemRequest(
            coupon_id="cpn-1", sale_id="sale-1", discount_applied=750,
        ).to_command(**kw()))
        assert s.projection_store.get_coupon("cpn-1")["status"] == "REDEEMED"
        assert s.projection_store.total_discounts == 750

        s._execute_command(CampaignDeactivateRequest(
            campaign_id="camp-1", reason="Season ended",
        ).to_command(**kw()))
        assert s.projection_store.get_campaign("camp-1")["status"] == "INACTIVE"

    def test_invalid_campaign_type(self):
        from engines.promotion.commands import CampaignCreateRequest
        with pytest.raises(ValueError, match="not valid"):
            CampaignCreateRequest(
                campaign_id="c1", name="X", campaign_type="INVALID",
                discount_type="PERCENTAGE", discount_value=10,
                start_date="2026-01-01", end_date="2026-12-31")

    def test_campaign_must_be_active_for_coupon(self):
        from engines.promotion.policies import campaign_must_be_active_for_coupon_policy
        from engines.promotion.commands import CouponIssueRequest
        cmd = CouponIssueRequest(
            coupon_id="cpn-1", campaign_id="camp-1",
        ).to_command(**kw())
        r = campaign_must_be_active_for_coupon_policy(
            cmd, campaign_lookup=lambda c: {"status": "DRAFT"})
        assert r is not None
        assert r.code == "CAMPAIGN_NOT_ACTIVE"

    def test_coupon_must_be_issued_for_redeem(self):
        from engines.promotion.policies import coupon_must_be_issued_for_redeem_policy
        from engines.promotion.commands import CouponRedeemRequest
        cmd = CouponRedeemRequest(
            coupon_id="cpn-1", sale_id="s1", discount_applied=100,
        ).to_command(**kw())
        r = coupon_must_be_issued_for_redeem_policy(
            cmd, coupon_lookup=lambda c: {"status": "REDEEMED"})
        assert r is not None
        assert r.code == "COUPON_NOT_ISSUED"


# ══════════════════════════════════════════════════════════════
# HR
# ══════════════════════════════════════════════════════════════

class TestHR:
    def _svc(self):
        from engines.hr.services import HRService
        return HRService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())

    def test_handlers_registered(self):
        from engines.hr.commands import HR_COMMAND_TYPES
        s = self._svc()
        for ct in HR_COMMAND_TYPES:
            assert ct in s._command_bus.handlers

    def test_employee_lifecycle(self):
        from engines.hr.commands import (
            EmployeeOnboardRequest, ShiftStartRequest,
            ShiftEndRequest, LeaveRequestRequest,
            EmployeeTerminateRequest,
        )
        s = self._svc()

        s._execute_command(EmployeeOnboardRequest(
            employee_id="emp-1", full_name="Jane Doe",
            role="Cashier", start_date="2026-02-01",
        ).to_command(**kw()))
        assert s.projection_store.get_employee("emp-1")["status"] == "ACTIVE"

        s._execute_command(ShiftStartRequest(
            shift_id="sh-1", employee_id="emp-1",
        ).to_command(**kw()))

        s._execute_command(ShiftEndRequest(
            shift_id="sh-1", employee_id="emp-1", hours_worked=8,
        ).to_command(**kw()))
        assert s.projection_store.total_hours == 8

        s._execute_command(LeaveRequestRequest(
            leave_id="lv-1", employee_id="emp-1",
            leave_type="ANNUAL", start_date="2026-03-01", end_date="2026-03-05",
        ).to_command(**kw()))
        emp = s.projection_store.get_employee("emp-1")
        assert "lv-1" in emp["leaves"]

        s._execute_command(EmployeeTerminateRequest(
            employee_id="emp-1", reason="RESIGNATION",
            effective_date="2026-04-01",
        ).to_command(**kw()))
        assert s.projection_store.get_employee("emp-1")["status"] == "TERMINATED"

    def test_invalid_leave_type(self):
        from engines.hr.commands import LeaveRequestRequest
        with pytest.raises(ValueError, match="not valid"):
            LeaveRequestRequest(
                leave_id="l1", employee_id="e1",
                leave_type="HOLIDAY", start_date="2026-01-01", end_date="2026-01-02")

    def test_invalid_terminate_reason(self):
        from engines.hr.commands import EmployeeTerminateRequest
        with pytest.raises(ValueError, match="not valid"):
            EmployeeTerminateRequest(
                employee_id="e1", reason="FIRED", effective_date="2026-01-01")

    def test_employee_must_be_active_policy(self):
        from engines.hr.policies import employee_must_be_active_policy
        from engines.hr.commands import ShiftStartRequest
        cmd = ShiftStartRequest(
            shift_id="sh-1", employee_id="emp-1",
        ).to_command(**kw())
        r = employee_must_be_active_policy(
            cmd, employee_lookup=lambda e: {"status": "TERMINATED"})
        assert r is not None
        assert r.code == "EMPLOYEE_NOT_ACTIVE"


# ══════════════════════════════════════════════════════════════
# CROSS-ENGINE DETERMINISM
# ══════════════════════════════════════════════════════════════

class TestPhase7Determinism:
    def test_all_four_engines_deterministic(self):
        from engines.restaurant.services import RestaurantService
        from engines.restaurant.commands import TableOpenRequest, BillSettleRequest
        from engines.workshop.services import WorkshopService
        from engines.workshop.commands import JobCreateRequest, JobInvoiceRequest, JobAssignRequest, JobStartRequest, JobCompleteRequest
        from engines.promotion.services import PromotionService
        from engines.promotion.commands import CampaignCreateRequest, CampaignActivateRequest
        from engines.hr.services import HRService
        from engines.hr.commands import EmployeeOnboardRequest, ShiftEndRequest, ShiftStartRequest

        def run():
            results = {}

            # Restaurant
            rs = RestaurantService(
                business_context={"business_id": BIZ}, command_bus=StubBus(),
                event_factory=StubFactory(), persist_event=StubPersist(),
                event_type_registry=StubReg())
            rs._execute_command(TableOpenRequest(
                table_id="t1", table_name="T1", covers=2).to_command(**kw()))
            rs._execute_command(BillSettleRequest(
                bill_id="b1", table_id="t1", total_amount=3000,
                currency="KES", payment_method="CASH").to_command(**kw()))
            results["restaurant_revenue"] = rs.projection_store.total_revenue

            # Workshop
            ws = WorkshopService(
                business_context={"business_id": BIZ}, command_bus=StubBus(),
                event_factory=StubFactory(), persist_event=StubPersist(),
                event_type_registry=StubReg())
            ws._execute_command(JobCreateRequest(
                job_id="j1", customer_id="c1", description="Fix",
                currency="KES").to_command(**kw()))
            ws._execute_command(JobAssignRequest(
                job_id="j1", technician_id="t1").to_command(**kw()))
            ws._execute_command(JobStartRequest(job_id="j1").to_command(**kw()))
            ws._execute_command(JobCompleteRequest(
                job_id="j1", final_cost=2000, currency="KES").to_command(**kw()))
            ws._execute_command(JobInvoiceRequest(
                job_id="j1", invoice_id="i1", amount=2000,
                currency="KES").to_command(**kw()))
            results["workshop_revenue"] = ws.projection_store.total_revenue

            # Promotion
            ps = PromotionService(
                business_context={"business_id": BIZ}, command_bus=StubBus(),
                event_factory=StubFactory(), persist_event=StubPersist(),
                event_type_registry=StubReg())
            ps._execute_command(CampaignCreateRequest(
                campaign_id="c1", name="Sale", campaign_type="SEASONAL",
                discount_type="PERCENTAGE", discount_value=10,
                start_date="2026-01-01", end_date="2026-12-31").to_command(**kw()))
            ps._execute_command(CampaignActivateRequest(
                campaign_id="c1").to_command(**kw()))
            results["promo_status"] = ps.projection_store.get_campaign("c1")["status"]

            # HR
            hs = HRService(
                business_context={"business_id": BIZ}, command_bus=StubBus(),
                event_factory=StubFactory(), persist_event=StubPersist(),
                event_type_registry=StubReg())
            hs._execute_command(EmployeeOnboardRequest(
                employee_id="e1", full_name="Jane", role="Dev",
                start_date="2026-01-01").to_command(**kw()))
            hs._execute_command(ShiftStartRequest(
                shift_id="s1", employee_id="e1").to_command(**kw()))
            hs._execute_command(ShiftEndRequest(
                shift_id="s1", employee_id="e1", hours_worked=8).to_command(**kw()))
            results["hr_hours"] = hs.projection_store.total_hours

            return results

        r1 = run()
        r2 = run()
        assert r1 == r2
        assert r1["restaurant_revenue"] == 3000
        assert r1["workshop_revenue"] == 2000
        assert r1["promo_status"] == "ACTIVE"
        assert r1["hr_hours"] == 8
