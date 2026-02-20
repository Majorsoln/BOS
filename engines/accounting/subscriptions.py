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


ACCOUNTING_SUBSCRIPTIONS: Dict[str, str] = {
    "inventory.stock.received.v1": "handle_stock_received",
    "cash.payment.recorded.v1": "handle_payment_recorded",
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
