"""
BOS Cash Engine — Event Subscriptions
========================================
Cash reacts to events from other engines (read-only).

Subscriptions:
- retail.sale.completed → auto-record cash payment to active session
- restaurant.bill.settled → auto-record cash payment to active session

Doctrine: AGENTS.md Rule 4 — Engines communicate ONLY via events.
Only CASH payment_method triggers recording. Card/Mobile handled elsewhere.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from engines.cash.commands import PaymentRecordRequest


CASH_SUBSCRIPTIONS: Dict[str, str] = {
    "retail.sale.completed": "handle_retail_sale",
    "restaurant.bill.settled": "handle_restaurant_bill",
}


class CashSubscriptionHandler:
    """
    Handles events from other engines.
    Triggers Cash commands for cash-method payments only.
    """

    def __init__(self, cash_service=None):
        self._cash_service = cash_service

    def _get_open_session(self) -> Optional[dict]:
        """Look up any open cash session from the projection store."""
        if self._cash_service is None:
            return None
        store = getattr(self._cash_service, "projection_store", None)
        if store is None:
            return None
        for session_id, session in store._sessions.items():
            if session.get("status") == "OPEN":
                return {"session_id": session_id, **session}
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

        if not business_id_raw or not amount or not currency:
            return

        try:
            business_id = uuid.UUID(str(business_id_raw))
            branch_id = uuid.UUID(str(branch_id_raw)) if branch_id_raw else None
        except (ValueError, AttributeError):
            return

        session_info = self._get_open_session()
        if session_info is None:
            return

        try:
            request = PaymentRecordRequest(
                payment_id=f"auto:{subject_id}",
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
                actor_type="System",
                actor_id="system:cash.subscription",
                command_id=uuid.uuid4(),
                correlation_id=uuid.UUID(str(payload.get("correlation_id", uuid.uuid4()))),
                issued_at=datetime.now(tz=timezone.utc),
            )
            self._cash_service._execute_command(command)
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
