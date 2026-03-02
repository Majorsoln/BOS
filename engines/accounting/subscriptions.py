"""
BOS Accounting Engine — Event Subscriptions
==============================================
Accounting reacts to events from other engines.

Subscriptions:
- inventory.stock.received.v1 → post inventory asset journal (DR Inventory, CR AP)
- cash.payment.recorded.v1   → fulfill outstanding payment obligation

Doctrine: AGENTS.md Rule 4 — Engines communicate ONLY via events.
Account codes are configured per business. Default codes used as fallback.
Accounting is management-first (not statutory). Entries are reference-only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict

from engines.accounting.commands import JournalPostRequest, ObligationFulfillRequest


# Default chart of accounts codes (management reference)
DEFAULT_INVENTORY_ACCOUNT = "INVENTORY_ASSET"
DEFAULT_AP_ACCOUNT = "AP_TRADE"
DEFAULT_CASH_ACCOUNT = "CASH_ON_HAND"
DEFAULT_AR_ACCOUNT = "AR_TRADE"
DEFAULT_REVENUE_ACCOUNT = "REVENUE_SALES"
DEFAULT_WAGES_EXPENSE_ACCOUNT = "WAGES_EXPENSE"
DEFAULT_WAGES_PAYABLE_ACCOUNT = "WAGES_PAYABLE"
DEFAULT_TAX_PAYABLE_ACCOUNT = "TAX_PAYABLE"


ACCOUNTING_SUBSCRIPTIONS: Dict[str, str] = {
    "inventory.stock.received.v1": "handle_stock_received",
    "cash.payment.recorded.v1": "handle_payment_recorded",
    "hr.payroll.run.v1": "handle_payroll_run",
    "retail.sale.completed.v1": "handle_retail_sale",
    "restaurant.bill.settled.v1": "handle_restaurant_bill",
    "workshop.job.invoiced.v1": "handle_workshop_invoice",
}


class AccountingSubscriptionHandler:
    """
    Handles events from other engines.
    Posts management journal entries — NOT statutory entries.
    All posted amounts are for management reporting purposes.
    """

    def __init__(self, accounting_service=None):
        self._accounting_service = accounting_service

    def handle_stock_received(self, event_data: dict) -> None:
        """
        When Inventory receives stock from Procurement, post an inventory journal.

        Management entry (non-statutory):
          DEBIT  Inventory Asset account     (stock in)
          CREDIT Accounts Payable account    (liability created)

        Event source: inventory.stock.received.v1
        Payload fields used: business_id, item_id, quantity, unit_cost, reference_id
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        item_id = str(payload.get("item_id", ""))
        quantity = int(payload.get("quantity", 0))
        unit_cost_raw = payload.get("unit_cost")
        reference_id = str(payload.get("reference_id", ""))

        # Only post journal if we have cost information
        if not business_id_raw or not quantity or not unit_cost_raw:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        # Extract cost (unit_cost is a dict with amount + currency)
        if isinstance(unit_cost_raw, dict):
            unit_cost_amount = int(unit_cost_raw.get("amount", 0))
            currency = str(unit_cost_raw.get("currency", ""))
        elif isinstance(unit_cost_raw, (int, float)):
            unit_cost_amount = int(unit_cost_raw)
            currency = "USD"  # fallback
        else:
            return

        if not unit_cost_amount or not currency:
            return

        total_cost = quantity * unit_cost_amount

        try:
            request = JournalPostRequest(
                entry_id=f"auto:inv-recv:{item_id}:{uuid.uuid4().hex[:8]}",
                lines=tuple([
                    {
                        "account_code": DEFAULT_INVENTORY_ACCOUNT,
                        "side": "DEBIT",
                        "amount": total_cost,
                        "description": f"Inventory received: {item_id} x{quantity}",
                    },
                    {
                        "account_code": DEFAULT_AP_ACCOUNT,
                        "side": "CREDIT",
                        "amount": total_cost,
                        "description": f"Supplier payable: {reference_id or item_id}",
                    },
                ]),
                memo=f"Auto-journal: stock received {item_id} x{quantity} @ {unit_cost_amount} {currency}",
                currency=currency,
                reference_id=reference_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="System",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_payment_recorded(self, event_data: dict) -> None:
        """
        When Cash records a payment, fulfill the matching obligation.

        The event must carry obligation_id in its payload.
        If no obligation_id is present, no automatic fulfillment occurs
        (human must manually match in accounting review).

        Event source: cash.payment.recorded.v1
        Payload fields used: business_id, payment_id, amount, currency, payment_method,
                             reference_id (which may contain obligation_id)
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        payment_id = str(payload.get("payment_id", ""))
        amount = payload.get("amount", 0)
        currency = str(payload.get("currency", ""))
        payment_method = str(payload.get("payment_method", "CASH"))
        # obligation_id may be embedded in reference_id as "OBL:xxxx"
        reference_id = str(payload.get("reference_id", ""))

        if not business_id_raw or not amount or not currency:
            return

        # Try to extract obligation_id from reference
        obligation_id = None
        if reference_id.startswith("OBL:"):
            obligation_id = reference_id[4:]

        if not obligation_id:
            # No obligation to fulfill automatically — skip
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        # Map payment_method to fulfillment_type
        fulfillment_map = {
            "CASH": "PAYMENT_CASH",
            "CARD": "PAYMENT_CARD",
            "MOBILE": "PAYMENT_MOBILE",
            "BANK_TRANSFER": "PAYMENT_BANK",
            "CHEQUE": "PAYMENT_BANK",
        }
        fulfillment_type = fulfillment_map.get(payment_method, "PAYMENT_CASH")

        try:
            request = ObligationFulfillRequest(
                obligation_id=obligation_id,
                fulfillment_id=f"auto:pay:{payment_id}",
                fulfillment_type=fulfillment_type,
                amount=int(amount),
                currency=currency,
                reference_id=f"PAYMENT:{payment_id}",
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="System",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_payroll_run(self, event_data: dict) -> None:
        """
        When HR records a payroll run, post a wages journal entry.

        Management entry (non-statutory):
          DEBIT  Wages Expense    (gross_pay)
          CREDIT Wages Payable    (net_pay)
          CREDIT Tax Payable      (total_deductions)  — if deductions > 0

        Event source: hr.payroll.run.v1
        Payload fields used: business_id, employee_id, payroll_id,
                             gross_pay, net_pay, deductions, currency
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        employee_id = str(payload.get("employee_id", ""))
        payroll_id = str(payload.get("payroll_id", ""))
        gross_pay = int(payload.get("gross_pay", 0))
        net_pay = int(payload.get("net_pay", 0))
        currency = str(payload.get("currency", ""))
        period_start = str(payload.get("period_start", ""))
        period_end = str(payload.get("period_end", ""))

        if not business_id_raw or not gross_pay or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        total_deductions = gross_pay - net_pay

        lines = [
            {
                "account_code": DEFAULT_WAGES_EXPENSE_ACCOUNT,
                "side": "DEBIT",
                "amount": gross_pay,
                "description": f"Wages: {employee_id} ({period_start} to {period_end})",
            },
            {
                "account_code": DEFAULT_WAGES_PAYABLE_ACCOUNT,
                "side": "CREDIT",
                "amount": net_pay,
                "description": f"Net pay: {employee_id}",
            },
        ]
        if total_deductions > 0:
            lines.append({
                "account_code": DEFAULT_TAX_PAYABLE_ACCOUNT,
                "side": "CREDIT",
                "amount": total_deductions,
                "description": f"Payroll deductions: {employee_id}",
            })

        try:
            request = JournalPostRequest(
                entry_id=f"auto:payroll:{payroll_id}",
                lines=tuple(lines),
                memo=f"Auto-journal: payroll {payroll_id} for {employee_id} ({period_start}-{period_end})",
                currency=currency,
                reference_id=payroll_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="System",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_retail_sale(self, event_data: dict) -> None:
        """
        When Retail completes a sale, post a revenue journal entry.

        Management entry (non-statutory):
          DEBIT  Cash on Hand / AR Trade   (payment received or owed)
          CREDIT Revenue Sales             (revenue recognized at point of sale)

        Event source: retail.sale.completed.v1
        Payload fields used: business_id, sale_id, net_amount, currency, payment_method
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        sale_id = str(payload.get("sale_id", ""))
        net_amount = int(payload.get("net_amount", 0))
        currency = str(payload.get("currency", ""))
        payment_method = str(payload.get("payment_method", ""))

        if not business_id_raw or not net_amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        debit_account = DEFAULT_CASH_ACCOUNT if payment_method == "CASH" else DEFAULT_AR_ACCOUNT

        try:
            request = JournalPostRequest(
                entry_id=f"auto:retail-sale:{sale_id}",
                lines=tuple([
                    {
                        "account_code": debit_account,
                        "side": "DEBIT",
                        "amount": net_amount,
                        "description": f"Retail sale: {sale_id}",
                    },
                    {
                        "account_code": DEFAULT_REVENUE_ACCOUNT,
                        "side": "CREDIT",
                        "amount": net_amount,
                        "description": f"Sales revenue: {sale_id}",
                    },
                ]),
                memo=f"Auto-journal: retail sale {sale_id} via {payment_method}",
                currency=currency,
                reference_id=sale_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="System",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_restaurant_bill(self, event_data: dict) -> None:
        """
        When Restaurant settles a bill, post a revenue journal entry.

        Management entry (non-statutory):
          DEBIT  Cash on Hand / AR Trade   (payment received or owed)
          CREDIT Revenue Sales             (revenue recognized at settlement)

        Event source: restaurant.bill.settled.v1
        Payload fields used: business_id, bill_id, total_amount, currency, payment_method
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        bill_id = str(payload.get("bill_id", ""))
        total_amount = int(payload.get("total_amount", 0))
        currency = str(payload.get("currency", ""))
        payment_method = str(payload.get("payment_method", ""))

        if not business_id_raw or not total_amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        debit_account = DEFAULT_CASH_ACCOUNT if payment_method == "CASH" else DEFAULT_AR_ACCOUNT

        try:
            request = JournalPostRequest(
                entry_id=f"auto:restaurant-bill:{bill_id}",
                lines=tuple([
                    {
                        "account_code": debit_account,
                        "side": "DEBIT",
                        "amount": total_amount,
                        "description": f"Restaurant bill: {bill_id}",
                    },
                    {
                        "account_code": DEFAULT_REVENUE_ACCOUNT,
                        "side": "CREDIT",
                        "amount": total_amount,
                        "description": f"Restaurant revenue: {bill_id}",
                    },
                ]),
                memo=f"Auto-journal: restaurant bill {bill_id} via {payment_method}",
                currency=currency,
                reference_id=bill_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="System",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_workshop_invoice(self, event_data: dict) -> None:
        """
        When Workshop invoices a job, post an accounts-receivable journal entry.

        Management entry (non-statutory):
          DEBIT  AR Trade      (customer owes for the completed job)
          CREDIT Revenue Sales (revenue recognized at invoicing)

        Event source: workshop.job.invoiced.v1
        Payload fields used: business_id, invoice_id, job_id, amount, currency
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        invoice_id = str(payload.get("invoice_id", ""))
        job_id = str(payload.get("job_id", ""))
        amount = int(payload.get("amount", 0))
        currency = str(payload.get("currency", ""))

        if not business_id_raw or not amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        try:
            request = JournalPostRequest(
                entry_id=f"auto:workshop-invoice:{invoice_id}",
                lines=tuple([
                    {
                        "account_code": DEFAULT_AR_ACCOUNT,
                        "side": "DEBIT",
                        "amount": amount,
                        "description": f"Workshop invoice: {invoice_id} (job: {job_id})",
                    },
                    {
                        "account_code": DEFAULT_REVENUE_ACCOUNT,
                        "side": "CREDIT",
                        "amount": amount,
                        "description": f"Workshop service revenue: {job_id}",
                    },
                ]),
                memo=f"Auto-journal: workshop invoice {invoice_id} for job {job_id}",
                currency=currency,
                reference_id=invoice_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="System",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return
