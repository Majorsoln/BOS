"""
BOS Accounting Engine — Event Subscriptions
============================================
Handles events from other engines and posts the corresponding
accounting journal entries.

Subscription handlers are pure functions:
    handler(event) -> None

They NEVER write to the Event Store directly.
They maintain an in-memory journal ledger (read model) that can be
queried for reporting, audit, and downstream integration.

Registered via: register(subscriber_registry)

AC-11  restaurant.order.cancelled.v1  → revenue reversal (DR Revenue / CR AR)
AC-12  hr.payroll.run_completed.v1    → payroll journal with deduction splits
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger("bos.accounting")

# ── In-memory journal ledger ───────────────────────────────────
# Structure: { business_id: [{ source_event_id, description, entries }, ...] }
# Each entry: { account: str, debit: int, credit: int }
_JOURNAL_LEDGER: dict[str, list[dict[str, Any]]] = defaultdict(list)

# ── Deduction account routing for payroll (AC-12) ─────────────
_DEDUCTION_ACCOUNT_MAP: dict[str, str] = {
    "PAYE": "PAYE_PAYABLE",
    "NSSF": "NSSF_PAYABLE",
    "NHIF": "NHIF_PAYABLE",
    "SHIF": "NHIF_PAYABLE",  # SHIF is the successor to NHIF in Kenya
}


def _post_journal_entry(
    *,
    business_id: str,
    source_event_id: str,
    source_event_type: str,
    description: str,
    entries: list[dict[str, Any]],
) -> None:
    """
    Record a journal entry group in the in-memory ledger.

    Each call represents one accounting transaction (balanced set of lines).
    entries must be a list of dicts:  { account, debit, credit }
    """
    record: dict[str, Any] = {
        "source_event_id": source_event_id,
        "source_event_type": source_event_type,
        "description": description,
        "entries": entries,
    }
    _JOURNAL_LEDGER[business_id].append(record)
    logger.info(
        "[Accounting] Journal posted — business=%s event=%s: %s",
        business_id,
        source_event_id,
        description,
    )


# ══════════════════════════════════════════════════════════════
# AC-11 — Restaurant Order Cancellation
# ══════════════════════════════════════════════════════════════

def handle_restaurant_order_cancelled(event: Any) -> None:
    """
    AC-11: Handle restaurant.order.cancelled.v1

    Business rule:
    - If refund_amount > 0:  post revenue reversal (DR Revenue / CR AR)
    - If refund_amount == 0: pre-billing cancellation — no journal entry

    Expected payload keys:
        order_id        str   Identifier for log context
        refund_amount   int   Amount in minor units (e.g. cents). 0 = no charge.
    """
    payload: dict[str, Any] = event.payload or {}
    refund_amount = payload.get("refund_amount", 0)

    if not refund_amount or refund_amount <= 0:
        logger.debug(
            "[Accounting] AC-11 — order cancellation with no refund "
            "(event %s) — no journal entry.",
            event.event_id,
        )
        return

    business_id = str(event.business_id)
    source_event_id = str(event.event_id)
    order_id = payload.get("order_id", "unknown")

    _post_journal_entry(
        business_id=business_id,
        source_event_id=source_event_id,
        source_event_type=event.event_type,
        description=f"Revenue reversal — cancelled order {order_id}",
        entries=[
            {
                "account": "REVENUE",
                "debit": refund_amount,
                "credit": 0,
            },
            {
                "account": "ACCOUNTS_RECEIVABLE",
                "debit": 0,
                "credit": refund_amount,
            },
        ],
    )


# ══════════════════════════════════════════════════════════════
# AC-12 — Payroll Run
# ══════════════════════════════════════════════════════════════

def handle_payroll_run(event: Any) -> None:
    """
    AC-12: Handle hr.payroll.run_completed.v1

    Posts the payroll journal with deductions split by named key:
        PAYE          → PAYE_PAYABLE
        NSSF          → NSSF_PAYABLE
        NHIF / SHIF   → NHIF_PAYABLE
        unknown key   → OTHER_DEDUCTIONS_PAYABLE
        scalar total  → TAX_PAYABLE  (legacy fallback when deductions is a number)

    Expected payload keys:
        run_id          str              Payroll run identifier
        gross_pay       int              Total gross in minor units
        net_pay         int              Net pay payable in minor units
        deductions      dict | int | 0   Named deductions dict, or scalar total
    """
    payload: dict[str, Any] = event.payload or {}
    business_id = str(event.business_id)
    source_event_id = str(event.event_id)
    run_id = payload.get("run_id", "unknown")

    gross_pay = payload.get("gross_pay", 0)
    net_pay = payload.get("net_pay", 0)
    deductions = payload.get("deductions", {})

    entries: list[dict[str, Any]] = []

    # DR Salary Expense for gross payroll cost
    if gross_pay:
        entries.append(
            {"account": "SALARY_EXPENSE", "debit": gross_pay, "credit": 0}
        )

    # CR Net Pay Payable (what goes to employees)
    if net_pay:
        entries.append(
            {"account": "NET_PAY_PAYABLE", "debit": 0, "credit": net_pay}
        )

    # CR deduction liability accounts
    if isinstance(deductions, dict):
        for key, amount in deductions.items():
            if not amount:
                continue
            normalised_key = key.upper() if isinstance(key, str) else str(key)
            account = _DEDUCTION_ACCOUNT_MAP.get(
                normalised_key, "OTHER_DEDUCTIONS_PAYABLE"
            )
            entries.append({"account": account, "debit": 0, "credit": amount})
    elif deductions:
        # Legacy: scalar deduction total → TAX_PAYABLE
        entries.append(
            {"account": "TAX_PAYABLE", "debit": 0, "credit": deductions}
        )

    if not entries:
        logger.debug(
            "[Accounting] AC-12 — payroll run %s (event %s) has no postable amounts.",
            run_id,
            source_event_id,
        )
        return

    _post_journal_entry(
        business_id=business_id,
        source_event_id=source_event_id,
        source_event_type=event.event_type,
        description=f"Payroll journal — run {run_id}",
        entries=entries,
    )


# ══════════════════════════════════════════════════════════════
# Public read API
# ══════════════════════════════════════════════════════════════

def get_journal_entries(business_id: str) -> list[dict[str, Any]]:
    """
    Return all journal entries recorded for a given business.

    Read-only — never mutates the ledger.
    Returns a shallow copy of the entry list.
    """
    return list(_JOURNAL_LEDGER.get(str(business_id), []))


# ══════════════════════════════════════════════════════════════
# Registration
# ══════════════════════════════════════════════════════════════

def register(subscriber_registry) -> None:
    """
    Register accounting subscriptions with the given SubscriberRegistry.

    Call this once at wiring time, AFTER the registry is created.
    """
    from engines.restaurant.events import RESTAURANT_ORDER_CANCELLED_V1
    from engines.hr.events import HR_PAYROLL_RUN_COMPLETED_V1

    subscriber_registry.register_subscriber(
        event_type=RESTAURANT_ORDER_CANCELLED_V1,
        handler=handle_restaurant_order_cancelled,
        subscriber_engine="accounting",
    )
    subscriber_registry.register_subscriber(
        event_type=HR_PAYROLL_RUN_COMPLETED_V1,
        handler=handle_payroll_run,
        subscriber_engine="accounting",
    )
