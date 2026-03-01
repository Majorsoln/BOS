"""
BOS GAP-08 — HR Payroll + Ledger Integration Tests
=====================================================
Tests payroll command, event, projection, and accounting subscription.
"""

import uuid
from datetime import datetime, timezone

import pytest

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)


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
# PayrollRunRequest VALIDATION
# ══════════════════════════════════════════════════════════════

class TestPayrollRunRequestValidation:
    def test_valid_payroll_request(self):
        from engines.hr.commands import PayrollRunRequest
        req = PayrollRunRequest(
            payroll_id="PR-001", employee_id="EMP-1",
            period_start="2026-01-01", period_end="2026-01-31",
            gross_pay=100000, net_pay=75000, currency="KES",
            deductions={"PAYE": 20000, "NHIF": 3000, "NSSF": 2000},
        )
        assert req.total_deductions() == 25000
        cmd = req.to_command(**kw())
        assert cmd.command_type == "hr.payroll.run.request"

    def test_empty_payroll_id(self):
        from engines.hr.commands import PayrollRunRequest
        with pytest.raises(ValueError, match="payroll_id"):
            PayrollRunRequest(
                payroll_id="", employee_id="EMP-1",
                period_start="2026-01-01", period_end="2026-01-31",
                gross_pay=100000, net_pay=75000, currency="KES",
            )

    def test_empty_employee_id(self):
        from engines.hr.commands import PayrollRunRequest
        with pytest.raises(ValueError, match="employee_id"):
            PayrollRunRequest(
                payroll_id="PR-1", employee_id="",
                period_start="2026-01-01", period_end="2026-01-31",
                gross_pay=100000, net_pay=75000, currency="KES",
            )

    def test_zero_gross_pay(self):
        from engines.hr.commands import PayrollRunRequest
        with pytest.raises(ValueError, match="gross_pay"):
            PayrollRunRequest(
                payroll_id="PR-1", employee_id="EMP-1",
                period_start="2026-01-01", period_end="2026-01-31",
                gross_pay=0, net_pay=0, currency="KES",
            )

    def test_net_exceeds_gross(self):
        from engines.hr.commands import PayrollRunRequest
        with pytest.raises(ValueError, match="net_pay cannot exceed"):
            PayrollRunRequest(
                payroll_id="PR-1", employee_id="EMP-1",
                period_start="2026-01-01", period_end="2026-01-31",
                gross_pay=50000, net_pay=60000, currency="KES",
            )

    def test_invalid_currency(self):
        from engines.hr.commands import PayrollRunRequest
        with pytest.raises(ValueError, match="currency"):
            PayrollRunRequest(
                payroll_id="PR-1", employee_id="EMP-1",
                period_start="2026-01-01", period_end="2026-01-31",
                gross_pay=100000, net_pay=75000, currency="K",
            )

    def test_total_deductions_from_gross_net_diff(self):
        from engines.hr.commands import PayrollRunRequest
        req = PayrollRunRequest(
            payroll_id="PR-1", employee_id="EMP-1",
            period_start="2026-01-01", period_end="2026-01-31",
            gross_pay=100000, net_pay=70000, currency="KES",
        )
        # No deductions dict → inferred from gross - net
        assert req.total_deductions() == 30000


# ══════════════════════════════════════════════════════════════
# PAYROLL EVENT WIRING
# ══════════════════════════════════════════════════════════════

class TestPayrollEventWiring:
    def test_command_type_in_hr_command_types(self):
        from engines.hr.commands import HR_COMMAND_TYPES
        assert "hr.payroll.run.request" in HR_COMMAND_TYPES

    def test_event_type_mapping(self):
        from engines.hr.events import resolve_hr_event_type
        assert resolve_hr_event_type("hr.payroll.run.request") == "hr.payroll.run.v1"

    def test_event_registered(self):
        from engines.hr.events import HR_EVENT_TYPES
        assert "hr.payroll.run.v1" in HR_EVENT_TYPES

    def test_feature_flag_registered(self):
        from core.feature_flags.registry import COMMAND_FLAG_MAP
        assert "hr.payroll.run.request" in COMMAND_FLAG_MAP


# ══════════════════════════════════════════════════════════════
# HR SERVICE — PAYROLL END-TO-END
# ══════════════════════════════════════════════════════════════

class TestHRPayrollService:
    def _svc(self):
        from engines.hr.services import HRService
        return HRService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg())

    def test_payroll_handler_registered(self):
        s = self._svc()
        assert "hr.payroll.run.request" in s._command_bus.handlers

    def test_execute_payroll_run(self):
        from engines.hr.commands import PayrollRunRequest
        s = self._svc()

        # First onboard the employee
        from engines.hr.commands import EmployeeOnboardRequest
        s._execute_command(EmployeeOnboardRequest(
            employee_id="EMP-1", full_name="Jane Doe",
            role="Engineer", start_date="2026-01-01",
        ).to_command(**kw()))

        # Run payroll
        result = s._execute_command(PayrollRunRequest(
            payroll_id="PR-001", employee_id="EMP-1",
            period_start="2026-01-01", period_end="2026-01-31",
            gross_pay=100000, net_pay=75000, currency="KES",
            deductions={"PAYE": 20000, "NHIF": 3000, "NSSF": 2000},
        ).to_command(**kw()))

        assert result.event_type == "hr.payroll.run.v1"
        assert result.projection_applied is True

    def test_payroll_projection_store(self):
        from engines.hr.commands import EmployeeOnboardRequest, PayrollRunRequest
        s = self._svc()
        s._execute_command(EmployeeOnboardRequest(
            employee_id="EMP-1", full_name="Jane Doe",
            role="Engineer", start_date="2026-01-01",
        ).to_command(**kw()))

        s._execute_command(PayrollRunRequest(
            payroll_id="PR-001", employee_id="EMP-1",
            period_start="2026-01-01", period_end="2026-01-31",
            gross_pay=100000, net_pay=75000, currency="KES",
        ).to_command(**kw()))

        s._execute_command(PayrollRunRequest(
            payroll_id="PR-002", employee_id="EMP-1",
            period_start="2026-02-01", period_end="2026-02-28",
            gross_pay=100000, net_pay=75000, currency="KES",
        ).to_command(**kw()))

        assert s.projection_store.total_gross_pay == 200000
        assert s.projection_store.total_net_pay == 150000
        emp = s.projection_store.get_employee("EMP-1")
        assert "PR-001" in emp["payrolls"]
        assert "PR-002" in emp["payrolls"]
        pr = s.projection_store.get_payroll("PR-001")
        assert pr["gross_pay"] == 100000
        assert pr["net_pay"] == 75000


# ══════════════════════════════════════════════════════════════
# ACCOUNTING SUBSCRIPTION — PAYROLL JOURNAL
# ══════════════════════════════════════════════════════════════

class TestPayrollAccountingSubscription:
    def test_subscription_mapped(self):
        from engines.accounting.subscriptions import ACCOUNTING_SUBSCRIPTIONS
        assert "hr.payroll.run.v1" in ACCOUNTING_SUBSCRIPTIONS
        assert ACCOUNTING_SUBSCRIPTIONS["hr.payroll.run.v1"] == "handle_payroll_run"

    def test_handler_exists(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        handler = AccountingSubscriptionHandler()
        assert hasattr(handler, "handle_payroll_run")

    def test_handler_no_service_noop(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        handler = AccountingSubscriptionHandler(accounting_service=None)
        # Should not raise
        handler.handle_payroll_run({"payload": {
            "business_id": str(BIZ), "employee_id": "EMP-1",
            "payroll_id": "PR-1", "gross_pay": 100000,
            "net_pay": 75000, "currency": "KES",
        }})

    def test_handler_missing_data_noop(self):
        from engines.accounting.subscriptions import AccountingSubscriptionHandler
        handler = AccountingSubscriptionHandler(accounting_service=None)
        handler.handle_payroll_run({"payload": {}})  # no crash

    def test_default_accounts_defined(self):
        from engines.accounting.subscriptions import (
            DEFAULT_WAGES_EXPENSE_ACCOUNT,
            DEFAULT_WAGES_PAYABLE_ACCOUNT,
            DEFAULT_TAX_PAYABLE_ACCOUNT,
        )
        assert DEFAULT_WAGES_EXPENSE_ACCOUNT == "WAGES_EXPENSE"
        assert DEFAULT_WAGES_PAYABLE_ACCOUNT == "WAGES_PAYABLE"
        assert DEFAULT_TAX_PAYABLE_ACCOUNT == "TAX_PAYABLE"
