"""
BOS Accounting Engine — Event Subscriptions
==============================================
Accounting reacts to events from other engines.

Subscriptions:
- inventory.stock.received.v1         → post inventory asset journal (DR Inventory, CR AP)
- cash.payment.recorded.v1            → fulfill outstanding payment obligation
- cash.session.closed.v1             → post cash over/short reconciliation journal
- hr.payroll.run.v1                   → post wages journal (DR Wages Expense, CR Wages/Tax Payable)
- retail.sale.completed.v1            → post revenue journal with VAT split
- retail.refund.issued.v1             → post refund reversal journal
- restaurant.bill.settled.v1          → post F&B revenue journal with VAT split
- workshop.job.invoiced.v1            → post AR journal with VAT split for workshop invoices
- hotel.folio.settled.v1              → post hotel revenue journal with VAT split
- procurement.payment.released.v1     → post supplier payment journal (DR AP, CR Cash/Bank)

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
DEFAULT_TAX_PAYABLE_ACCOUNT = "TAX_PAYABLE"   # Payroll/income tax
DEFAULT_VAT_PAYABLE_ACCOUNT = "VAT_PAYABLE"   # Output VAT on sales
DEFAULT_CARD_ACCOUNT = "CARD_CLEARING"
DEFAULT_MOBILE_ACCOUNT = "MOBILE_CLEARING"
DEFAULT_BANK_ACCOUNT = "BANK_CLEARING"

# Map payment method → debit account for revenue journal entries.
# SPLIT has no breakdown available in the event payload; the cash account
# is used as a fallback and requires manual reconciliation.
PAYMENT_DEBIT_ACCOUNT_MAP = {
    "CASH": DEFAULT_CASH_ACCOUNT,
    "CARD": DEFAULT_CARD_ACCOUNT,
    "MOBILE": DEFAULT_MOBILE_ACCOUNT,
    "BANK_TRANSFER": DEFAULT_BANK_ACCOUNT,
    "CREDIT": DEFAULT_AR_ACCOUNT,
    "SPLIT": DEFAULT_CASH_ACCOUNT,
}


ACCOUNTING_SUBSCRIPTIONS: Dict[str, str] = {
    "inventory.stock.received.v1":         "handle_stock_received",
    "cash.payment.recorded.v1":            "handle_payment_recorded",
    "cash.session.closed.v1":             "handle_cash_session_closed",
    "hr.payroll.run.v1":                   "handle_payroll_run",
    "retail.sale.completed.v1":            "handle_retail_sale",
    "retail.refund.issued.v1":             "handle_retail_refund",
    "restaurant.bill.settled.v1":          "handle_restaurant_bill",
    "workshop.job.invoiced.v1":            "handle_workshop_invoice",
    "hotel.folio.settled.v1":              "handle_hotel_folio_settled",
    "procurement.payment.released.v1":     "handle_procurement_payment_released",
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
                actor_type="SYSTEM",
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
                actor_type="SYSTEM",
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
                actor_type="SYSTEM",
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
          DEBIT  <payment_account>   (cash/card/mobile/AR received)
          CREDIT Revenue Sales       (revenue earned)

        Payment account is selected by payment_method:
          CASH         → CASH_ON_HAND
          CARD         → CARD_CLEARING
          MOBILE       → MOBILE_CLEARING
          BANK_TRANSFER→ BANK_CLEARING
          CREDIT       → AR_TRADE
          SPLIT        → CASH_ON_HAND (fallback — requires manual reconciliation)

        Event source: retail.sale.completed.v1
        Payload fields used: business_id, branch_id, sale_id,
                             net_amount, currency, payment_method
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        sale_id = str(payload.get("sale_id", ""))
        total_amount = int(payload.get("total_amount", 0))
        tax_amount = int(payload.get("tax_amount", 0))
        net_amount = int(payload.get("net_amount", 0))
        currency = str(payload.get("currency", ""))
        payment_method = str(payload.get("payment_method", "CASH"))

        # Use total_amount (gross collected) as debit; fallback to net_amount
        debit_amount = total_amount or net_amount
        if not business_id_raw or not debit_amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        debit_account = PAYMENT_DEBIT_ACCOUNT_MAP.get(payment_method, DEFAULT_CASH_ACCOUNT)

        # Revenue amount is debit minus tax (net of VAT)
        revenue_amount = debit_amount - tax_amount if tax_amount else debit_amount

        lines = [
            {
                "account_code": debit_account,
                "side": "DEBIT",
                "amount": debit_amount,
                "description": f"Sale payment ({payment_method}): {sale_id}",
            },
            {
                "account_code": DEFAULT_REVENUE_ACCOUNT,
                "side": "CREDIT",
                "amount": revenue_amount,
                "description": f"Revenue: retail sale {sale_id}",
            },
        ]
        if tax_amount > 0:
            lines.append({
                "account_code": DEFAULT_VAT_PAYABLE_ACCOUNT,
                "side": "CREDIT",
                "amount": tax_amount,
                "description": f"Output VAT: retail sale {sale_id}",
            })

        try:
            request = JournalPostRequest(
                entry_id=f"auto:sale:{sale_id}",
                lines=tuple(lines),
                memo=f"Auto-journal: retail sale {sale_id} via {payment_method} — {debit_amount} {currency}",
                currency=currency,
                reference_id=sale_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
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
        When Workshop invoices a job, post an accounts-receivable journal entry
        with VAT split.

        Management entry (non-statutory):
          DEBIT  AR Trade      (total invoice amount — customer owes)
          CREDIT Revenue Sales (net revenue after VAT)
          CREDIT VAT Payable   (tax component, if tax_amount > 0)

        Event source: workshop.job.invoiced.v1
        Payload fields used: business_id, branch_id, invoice_id, job_id,
                             amount, tax_amount, currency
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        invoice_id = str(payload.get("invoice_id", ""))
        job_id = str(payload.get("job_id", ""))
        amount = int(payload.get("amount", 0))
        tax_amount = int(payload.get("tax_amount", 0))
        currency = str(payload.get("currency", ""))

        if not business_id_raw or not amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        revenue_amount = amount - tax_amount if tax_amount else amount

        lines = [
            {
                "account_code": DEFAULT_AR_ACCOUNT,
                "side": "DEBIT",
                "amount": amount,
                "description": f"Workshop invoice: {invoice_id} (job: {job_id})",
            },
            {
                "account_code": DEFAULT_REVENUE_ACCOUNT,
                "side": "CREDIT",
                "amount": revenue_amount,
                "description": f"Workshop service revenue: {job_id}",
            },
        ]
        if tax_amount > 0:
            lines.append({
                "account_code": DEFAULT_VAT_PAYABLE_ACCOUNT,
                "side": "CREDIT",
                "amount": tax_amount,
                "description": f"Output VAT: workshop invoice {invoice_id}",
            })

        try:
            request = JournalPostRequest(
                entry_id=f"auto:workshop-invoice:{invoice_id}",
                lines=tuple(lines),
                memo=f"Auto-journal: workshop invoice {invoice_id} for job {job_id} — {amount} {currency}",
                currency=currency,
                reference_id=invoice_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
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
          DEBIT  <payment_account>   (cash/card/mobile received)
          CREDIT Revenue Sales       (revenue earned)

        Event source: restaurant.bill.settled.v1
        Payload fields used: business_id, branch_id, bill_id,
                             total_amount, currency, payment_method
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        bill_id = str(payload.get("bill_id", ""))
        total_amount = int(payload.get("total_amount", 0))
        tax_amount = int(payload.get("tax_amount", 0))
        currency = str(payload.get("currency", ""))
        payment_method = str(payload.get("payment_method", "CASH"))

        if not business_id_raw or not total_amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        debit_account = PAYMENT_DEBIT_ACCOUNT_MAP.get(payment_method, DEFAULT_CASH_ACCOUNT)
        revenue_amount = total_amount - tax_amount if tax_amount else total_amount

        lines = [
            {
                "account_code": debit_account,
                "side": "DEBIT",
                "amount": total_amount,
                "description": f"Bill payment ({payment_method}): {bill_id}",
            },
            {
                "account_code": DEFAULT_REVENUE_ACCOUNT,
                "side": "CREDIT",
                "amount": revenue_amount,
                "description": f"Revenue: restaurant bill {bill_id}",
            },
        ]
        if tax_amount > 0:
            lines.append({
                "account_code": DEFAULT_VAT_PAYABLE_ACCOUNT,
                "side": "CREDIT",
                "amount": tax_amount,
                "description": f"Output VAT: restaurant bill {bill_id}",
            })

        try:
            request = JournalPostRequest(
                entry_id=f"auto:bill:{bill_id}",
                lines=tuple(lines),
                memo=f"Auto-journal: restaurant bill {bill_id} via {payment_method} — {total_amount} {currency}",
                currency=currency,
                reference_id=bill_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_retail_refund(self, event_data: dict) -> None:
        """
        When Retail issues a refund, post a reversal journal entry.

        Management entry (non-statutory):
          DEBIT  Revenue Sales       (revenue reversal)
          CREDIT <payment_account>   (cash/card refunded to customer)

        Event source: retail.refund.issued.v1
        Payload fields used: business_id, branch_id, refund_id, amount, currency
        Note: refund payload carries no payment_method — CASH_ON_HAND used as fallback.
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        refund_id = str(payload.get("refund_id", ""))
        original_sale_id = str(payload.get("original_sale_id", ""))
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
                entry_id=f"auto:refund:{refund_id}",
                lines=tuple([
                    {
                        "account_code": DEFAULT_REVENUE_ACCOUNT,
                        "side": "DEBIT",
                        "amount": amount,
                        "description": f"Refund reversal: {refund_id} (orig sale: {original_sale_id})",
                    },
                    {
                        "account_code": DEFAULT_CASH_ACCOUNT,
                        "side": "CREDIT",
                        "amount": amount,
                        "description": f"Refund payment out: {refund_id}",
                    },
                ]),
                memo=f"Auto-journal: retail refund {refund_id} — {amount} {currency}",
                currency=currency,
                reference_id=refund_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_hotel_folio_settled(self, event_data: dict) -> None:
        """
        When Hotel settles a folio, post a hotel revenue journal entry.

        Management entry (non-statutory):
          DEBIT  <payment_account>   (total charges collected)
          CREDIT VAT Payable         (tax component, if any)
          CREDIT Revenue Sales       (net hotel revenue)

        For company billing (is_company_billing=True):
          DEBIT  AR Trade            (invoice raised to company, not immediate cash)

        Event source: hotel.folio.settled.v1
        Payload fields used: business_id, branch_id, folio_id, total_charges,
                             tax_amount, payment_method, currency, is_company_billing
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        folio_id = str(payload.get("folio_id", ""))
        total_charges = int(payload.get("total_charges", 0))
        tax_amount = int(payload.get("tax_amount", 0))
        payment_method = str(payload.get("payment_method", "CARD"))
        currency = str(payload.get("currency", ""))
        is_company_billing = bool(payload.get("is_company_billing", False))

        if not business_id_raw or not total_charges or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        # Company billing → AR debit (invoice to company); else use payment account
        if is_company_billing:
            debit_account = DEFAULT_AR_ACCOUNT
        else:
            debit_account = PAYMENT_DEBIT_ACCOUNT_MAP.get(payment_method, DEFAULT_CARD_ACCOUNT)

        revenue_amount = total_charges - tax_amount if tax_amount else total_charges

        lines = [
            {
                "account_code": debit_account,
                "side": "DEBIT",
                "amount": total_charges,
                "description": f"Hotel folio settlement ({payment_method}): {folio_id}",
            },
            {
                "account_code": DEFAULT_REVENUE_ACCOUNT,
                "side": "CREDIT",
                "amount": revenue_amount,
                "description": f"Hotel revenue: folio {folio_id}",
            },
        ]
        if tax_amount > 0:
            lines.append({
                "account_code": DEFAULT_VAT_PAYABLE_ACCOUNT,
                "side": "CREDIT",
                "amount": tax_amount,
                "description": f"Output VAT: hotel folio {folio_id}",
            })

        try:
            request = JournalPostRequest(
                entry_id=f"auto:hotel-folio:{folio_id}",
                lines=tuple(lines),
                memo=f"Auto-journal: hotel folio {folio_id} settled — {total_charges} {currency}",
                currency=currency,
                reference_id=folio_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_procurement_payment_released(self, event_data: dict) -> None:
        """
        When Procurement releases a supplier payment, clear the AP obligation.

        Management entry (non-statutory):
          DEBIT  Accounts Payable    (clearing the liability to supplier)
          CREDIT <payment_account>   (cash/bank going out)

        Event source: procurement.payment.released.v1
        Payload fields used: business_id, branch_id, payment_id,
                             order_id, amount, currency, payment_method
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        payment_id = str(payload.get("payment_id", ""))
        order_id = str(payload.get("order_id", ""))
        amount = int(payload.get("amount", 0))
        currency = str(payload.get("currency", ""))
        payment_method = str(payload.get("payment_method", "BANK_TRANSFER"))

        if not business_id_raw or not amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        # Credit account: where cash is going out from (bank for most supplier payments)
        credit_account = PAYMENT_DEBIT_ACCOUNT_MAP.get(payment_method, DEFAULT_BANK_ACCOUNT)

        try:
            request = JournalPostRequest(
                entry_id=f"auto:proc-payment:{payment_id}",
                lines=tuple([
                    {
                        "account_code": DEFAULT_AP_ACCOUNT,
                        "side": "DEBIT",
                        "amount": amount,
                        "description": f"AP cleared: supplier payment {payment_id} (order: {order_id})",
                    },
                    {
                        "account_code": credit_account,
                        "side": "CREDIT",
                        "amount": amount,
                        "description": f"Supplier payment out ({payment_method}): {payment_id}",
                    },
                ]),
                memo=f"Auto-journal: procurement payment {payment_id} for order {order_id} — {amount} {currency}",
                currency=currency,
                reference_id=payment_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return

    def handle_cash_session_closed(self, event_data: dict) -> None:
        """
        When a cash drawer session is closed, post a reconciliation journal entry
        if there is a variance (over/short) between expected and closing balance.

        Management entry (non-statutory) — only when variance != 0:
          If cash OVER  (closing > expected):
            DEBIT  Cash on Hand          (extra cash found)
            CREDIT Cash Over/Short       (income — overage)
          If cash SHORT (closing < expected):
            DEBIT  Cash Over/Short       (expense — shortage)
            CREDIT Cash on Hand          (cash missing)

        Zero-variance closings produce no journal entry.

        Event source: cash.session.closed.v1
        Payload fields used: business_id, branch_id, session_id, drawer_id,
                             closing_balance, expected_balance, variance, currency
        """
        if self._accounting_service is None:
            return

        payload = event_data.get("payload", {})
        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        session_id = str(payload.get("session_id", ""))
        drawer_id = str(payload.get("drawer_id", ""))
        currency = str(payload.get("currency", ""))

        # variance = closing_balance - expected_balance
        variance = int(payload.get("variance", payload.get("difference", 0)))

        if not business_id_raw or not currency or variance == 0:
            return  # No variance — no journal needed

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        abs_variance = abs(variance)

        if variance > 0:
            # Cash OVER — more cash than expected
            lines = [
                {
                    "account_code": DEFAULT_CASH_ACCOUNT,
                    "side": "DEBIT",
                    "amount": abs_variance,
                    "description": f"Cash overage: session {session_id} drawer {drawer_id}",
                },
                {
                    "account_code": "CASH_OVER_SHORT",
                    "side": "CREDIT",
                    "amount": abs_variance,
                    "description": f"Cash over: session {session_id}",
                },
            ]
            memo = f"Auto-journal: cash session {session_id} closed OVER by {abs_variance} {currency}"
        else:
            # Cash SHORT — less cash than expected
            lines = [
                {
                    "account_code": "CASH_OVER_SHORT",
                    "side": "DEBIT",
                    "amount": abs_variance,
                    "description": f"Cash shortage: session {session_id} drawer {drawer_id}",
                },
                {
                    "account_code": DEFAULT_CASH_ACCOUNT,
                    "side": "CREDIT",
                    "amount": abs_variance,
                    "description": f"Cash short: session {session_id}",
                },
            ]
            memo = f"Auto-journal: cash session {session_id} closed SHORT by {abs_variance} {currency}"

        try:
            request = JournalPostRequest(
                entry_id=f"auto:cash-close:{session_id}",
                lines=tuple(lines),
                memo=memo,
                currency=currency,
                reference_id=session_id or None,
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:accounting.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._accounting_service._execute_command(command)
        except (KeyError, ValueError, TypeError):
            return
