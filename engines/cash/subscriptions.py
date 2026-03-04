"""
BOS Cash Engine — Event Subscriptions
========================================
Cash reacts to events from other engines (read-only).

Subscriptions:
- retail.sale.completed.v1         → auto-record cash payment to active session
- restaurant.bill.settled.v1       → auto-record cash payment to active session
- workshop.job.invoiced.v1         → auto-record cash payment to active session
- hotel.folio.settled.v1           → auto-record cash payment to active session
- procurement.payment.released.v1  → auto-record outgoing cash payment (cash disbursement)

Doctrine: AGENTS.md Rule 4 — Engines communicate ONLY via events.
Only CASH payment_method triggers recording. Card/Mobile handled elsewhere.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from engines.cash.commands import PaymentRecordRequest, WithdrawalRecordRequest


CASH_SUBSCRIPTIONS: Dict[str, str] = {
    "retail.sale.completed.v1":        "handle_retail_sale",
    "restaurant.bill.settled.v1":      "handle_restaurant_bill",
    "workshop.job.invoiced.v1":        "handle_workshop_invoice",
    "hotel.folio.settled.v1":          "handle_hotel_folio",
    "procurement.payment.released.v1": "handle_procurement_payment",
}


class CashSubscriptionHandler:
    """
    Handles events from other engines.
    Triggers Cash commands for cash-method payments only.
    """

    def __init__(self, cash_service=None):
        self._cash_service = cash_service
        self._processed_payment_ids: Set[str] = set()

    def _get_open_session(self, branch_id=None) -> Optional[dict]:
        """Look up an open cash session, filtered by branch_id when provided.

        For multi-branch businesses, always pass branch_id to avoid recording
        a payment to the wrong branch's session.
        """
        if self._cash_service is None:
            return None
        store = getattr(self._cash_service, "projection_store", None)
        if store is None:
            return None
        for session_id, session in store._sessions.items():
            if session.get("status") != "OPEN":
                continue
            if branch_id is not None:
                session_branch = session.get("branch_id")
                if str(session_branch) != str(branch_id):
                    continue
            return {"session_id": session_id, **session}
        # No open session — cash recording silently skipped.
        # Cashier must open a session before processing payments.
        return None

    def _record_cash_payment(
        self,
        event_data: dict,
        amount_key: str,
        ref_prefix: str,
        id_key: str,
    ) -> None:
        """Shared logic: record a cash payment triggered by an event."""
        if self._cash_service is None:
            return

        payload = event_data.get("payload", {})
        payment_method = str(payload.get("payment_method", ""))
        if payment_method != "CASH":
            return

        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        subject_id = str(payload.get(id_key, ""))
        amount = payload.get(amount_key, 0)
        currency = str(payload.get("currency", ""))

        # Idempotency guard: skip if this payment was already recorded in this session.
        payment_id = f"auto:{subject_id}"
        if payment_id in self._processed_payment_ids:
            return

        if not business_id_raw or not amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        session_info = self._get_open_session(branch_id=branch_id)
        if session_info is None:
            return

        try:
            request = PaymentRecordRequest(
                payment_id=payment_id,
                session_id=session_info["session_id"],
                drawer_id=session_info["drawer_id"],
                amount=int(amount),
                currency=currency,
                payment_method="CASH",
                reference_id=f"{ref_prefix}:{subject_id}",
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:cash.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._cash_service._execute_command(command)
            self._processed_payment_ids.add(payment_id)
        except (KeyError, ValueError, TypeError):
            return

    def handle_retail_sale(self, event_data: dict) -> None:
        """
        When Retail records a completed sale, auto-record cash payment.
        Only triggers for payment_method == "CASH".
        Event source: retail.sale.completed.v1
        """
        self._record_cash_payment(
            event_data, amount_key="net_amount",
            ref_prefix="SALE", id_key="sale_id",
        )

    def handle_restaurant_bill(self, event_data: dict) -> None:
        """
        When Restaurant settles a bill, auto-record cash payment.
        Only triggers for payment_method == "CASH".
        Event source: restaurant.bill.settled.v1
        """
        self._record_cash_payment(
            event_data, amount_key="total_amount",
            ref_prefix="BILL", id_key="bill_id",
        )

    def handle_workshop_invoice(self, event_data: dict) -> None:
        """
        When Workshop invoices a job paid in cash, auto-record cash payment.
        Only triggers for payment_method == "CASH".
        Event source: workshop.job.invoiced.v1
        """
        self._record_cash_payment(
            event_data, amount_key="amount",
            ref_prefix="WSINV", id_key="invoice_id",
        )

    def handle_hotel_folio(self, event_data: dict) -> None:
        """
        When Hotel settles a folio paid in cash, auto-record cash payment.
        Only triggers for payment_method == "CASH".
        Event source: hotel.folio.settled.v1
        """
        self._record_cash_payment(
            event_data, amount_key="total_charges",
            ref_prefix="FOLIO", id_key="folio_id",
        )

    def handle_procurement_payment(self, event_data: dict) -> None:
        """
        When Procurement releases a cash payment to a supplier, record cash going out.
        Only triggers for payment_method == "CASH".
        Unlike inbound payments, this is an outgoing disbursement — uses withdrawal logic.
        Event source: procurement.payment.released.v1
        """
        if self._cash_service is None:
            return

        payload = event_data.get("payload", {})
        payment_method = str(payload.get("payment_method", ""))
        if payment_method != "CASH":
            return

        business_id_raw = payload.get("business_id")
        branch_id_raw = payload.get("branch_id")
        payment_id = str(payload.get("payment_id", ""))
        order_id = str(payload.get("order_id", ""))
        amount = payload.get("amount", 0)
        currency = str(payload.get("currency", ""))

        withdrawal_id = f"auto:{payment_id}"
        if withdrawal_id in self._processed_payment_ids:
            return

        if not business_id_raw or not amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        session_info = self._get_open_session(branch_id=branch_id)
        if session_info is None:
            return

        try:
            request = WithdrawalRecordRequest(
                withdrawal_id=withdrawal_id,
                session_id=session_info["session_id"],
                drawer_id=session_info["drawer_id"],
                amount=int(amount),
                currency=currency,
                reason="EXPENSE_PAYOUT",
                branch_id=branch_id,
            )
            command = request.to_command(
                business_id=business_id,
                actor_type="SYSTEM",
                actor_id="system:cash.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._cash_service._execute_command(command)
            self._processed_payment_ids.add(withdrawal_id)
        except (KeyError, ValueError, TypeError):
            return
