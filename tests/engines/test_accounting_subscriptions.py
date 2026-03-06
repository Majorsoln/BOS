"""
Tests for engines/accounting/subscriptions.py

Covers:
  AC-11  handle_restaurant_order_cancelled
  AC-12  handle_payroll_run
"""

import types
import uuid

import pytest

from engines.accounting.subscriptions import (
    _JOURNAL_LEDGER,
    get_journal_entries,
    handle_payroll_run,
    handle_restaurant_order_cancelled,
)


# ── Helpers ────────────────────────────────────────────────────

def _make_event(*, event_type: str, payload: dict, business_id=None):
    """Build a minimal fake event object (no DB required)."""
    ev = types.SimpleNamespace()
    ev.event_id = uuid.uuid4()
    ev.event_type = event_type
    ev.business_id = business_id or uuid.uuid4()
    ev.payload = payload
    return ev


@pytest.fixture(autouse=True)
def clear_ledger():
    """Ensure ledger is empty before and after each test."""
    _JOURNAL_LEDGER.clear()
    yield
    _JOURNAL_LEDGER.clear()


# ══════════════════════════════════════════════════════════════
# AC-11 — handle_restaurant_order_cancelled
# ══════════════════════════════════════════════════════════════

class TestHandleRestaurantOrderCancelled:
    def test_posts_reversal_when_refund_amount_positive(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="restaurant.order.cancelled.v1",
            payload={"order_id": "ORD-001", "refund_amount": 2500},
            business_id=biz_id,
        )

        handle_restaurant_order_cancelled(event)

        entries = get_journal_entries(str(biz_id))
        assert len(entries) == 1
        journal = entries[0]
        assert "cancelled order ORD-001" in journal["description"]
        lines = journal["entries"]
        assert len(lines) == 2

        revenue_line = next(l for l in lines if l["account"] == "REVENUE")
        ar_line = next(l for l in lines if l["account"] == "ACCOUNTS_RECEIVABLE")

        assert revenue_line["debit"] == 2500
        assert revenue_line["credit"] == 0
        assert ar_line["debit"] == 0
        assert ar_line["credit"] == 2500

    def test_no_entry_when_refund_amount_zero(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="restaurant.order.cancelled.v1",
            payload={"order_id": "ORD-002", "refund_amount": 0},
            business_id=biz_id,
        )

        handle_restaurant_order_cancelled(event)

        assert get_journal_entries(str(biz_id)) == []

    def test_no_entry_when_refund_amount_absent(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="restaurant.order.cancelled.v1",
            payload={"order_id": "ORD-003"},
            business_id=biz_id,
        )

        handle_restaurant_order_cancelled(event)

        assert get_journal_entries(str(biz_id)) == []

    def test_no_entry_when_refund_amount_negative(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="restaurant.order.cancelled.v1",
            payload={"order_id": "ORD-004", "refund_amount": -100},
            business_id=biz_id,
        )

        handle_restaurant_order_cancelled(event)

        assert get_journal_entries(str(biz_id)) == []

    def test_source_event_id_recorded(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="restaurant.order.cancelled.v1",
            payload={"order_id": "ORD-005", "refund_amount": 500},
            business_id=biz_id,
        )

        handle_restaurant_order_cancelled(event)

        entries = get_journal_entries(str(biz_id))
        assert entries[0]["source_event_id"] == str(event.event_id)

    def test_multiple_cancellations_accumulate(self):
        biz_id = uuid.uuid4()
        for i in range(3):
            event = _make_event(
                event_type="restaurant.order.cancelled.v1",
                payload={"order_id": f"ORD-{i}", "refund_amount": 1000},
                business_id=biz_id,
            )
            handle_restaurant_order_cancelled(event)

        assert len(get_journal_entries(str(biz_id))) == 3

    def test_different_businesses_isolated(self):
        biz_a = uuid.uuid4()
        biz_b = uuid.uuid4()

        handle_restaurant_order_cancelled(
            _make_event(
                event_type="restaurant.order.cancelled.v1",
                payload={"refund_amount": 100},
                business_id=biz_a,
            )
        )

        assert get_journal_entries(str(biz_a)) != []
        assert get_journal_entries(str(biz_b)) == []


# ══════════════════════════════════════════════════════════════
# AC-12 — handle_payroll_run
# ══════════════════════════════════════════════════════════════

class TestHandlePayrollRun:
    def test_named_deductions_routed_correctly(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={
                "run_id": "PR-2026-03",
                "gross_pay": 100_000,
                "net_pay": 72_000,
                "deductions": {
                    "PAYE": 15_000,
                    "NSSF": 6_000,
                    "NHIF": 7_000,
                },
            },
            business_id=biz_id,
        )

        handle_payroll_run(event)

        entries = get_journal_entries(str(biz_id))
        assert len(entries) == 1
        lines = {l["account"]: l for l in entries[0]["entries"]}

        assert lines["SALARY_EXPENSE"]["debit"] == 100_000
        assert lines["NET_PAY_PAYABLE"]["credit"] == 72_000
        assert lines["PAYE_PAYABLE"]["credit"] == 15_000
        assert lines["NSSF_PAYABLE"]["credit"] == 6_000
        assert lines["NHIF_PAYABLE"]["credit"] == 7_000

    def test_shif_maps_to_nhif_payable(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={
                "run_id": "PR-SHIF",
                "gross_pay": 50_000,
                "net_pay": 44_000,
                "deductions": {"SHIF": 6_000},
            },
            business_id=biz_id,
        )

        handle_payroll_run(event)

        lines = {
            l["account"]: l
            for l in get_journal_entries(str(biz_id))[0]["entries"]
        }
        assert lines["NHIF_PAYABLE"]["credit"] == 6_000

    def test_unknown_deduction_key_maps_to_other_deductions(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={
                "run_id": "PR-UNION",
                "gross_pay": 80_000,
                "net_pay": 70_000,
                "deductions": {"UNION_DUES": 10_000},
            },
            business_id=biz_id,
        )

        handle_payroll_run(event)

        lines = {
            l["account"]: l
            for l in get_journal_entries(str(biz_id))[0]["entries"]
        }
        assert lines["OTHER_DEDUCTIONS_PAYABLE"]["credit"] == 10_000

    def test_scalar_deductions_legacy_fallback_to_tax_payable(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={
                "run_id": "PR-LEGACY",
                "gross_pay": 60_000,
                "net_pay": 50_000,
                "deductions": 10_000,
            },
            business_id=biz_id,
        )

        handle_payroll_run(event)

        lines = {
            l["account"]: l
            for l in get_journal_entries(str(biz_id))[0]["entries"]
        }
        assert lines["TAX_PAYABLE"]["credit"] == 10_000

    def test_no_entry_when_no_amounts(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={"run_id": "PR-EMPTY"},
            business_id=biz_id,
        )

        handle_payroll_run(event)

        assert get_journal_entries(str(biz_id)) == []

    def test_zero_deduction_value_skipped(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={
                "run_id": "PR-ZERO",
                "gross_pay": 40_000,
                "net_pay": 40_000,
                "deductions": {"PAYE": 0},
            },
            business_id=biz_id,
        )

        handle_payroll_run(event)

        lines = {
            l["account"]: l
            for l in get_journal_entries(str(biz_id))[0]["entries"]
        }
        assert "PAYE_PAYABLE" not in lines

    def test_case_insensitive_deduction_keys(self):
        biz_id = uuid.uuid4()
        event = _make_event(
            event_type="hr.payroll.run_completed.v1",
            payload={
                "run_id": "PR-CASE",
                "gross_pay": 50_000,
                "net_pay": 40_000,
                "deductions": {"paye": 10_000},
            },
            business_id=biz_id,
        )

        handle_payroll_run(event)

        lines = {
            l["account"]: l
            for l in get_journal_entries(str(biz_id))[0]["entries"]
        }
        assert lines["PAYE_PAYABLE"]["credit"] == 10_000
