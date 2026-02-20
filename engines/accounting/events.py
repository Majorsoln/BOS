"""
BOS Accounting Engine — Event Types and Payload Builders
==========================================================
Engine: Accounting
Authority: BOS Doctrine — Deterministic, Event-Sourced

Double-entry bookkeeping. Every transaction produces a balanced
journal entry. Uses the Ledger Primitive from Phase 4.
"""

from __future__ import annotations

from core.commands.base import Command


# ══════════════════════════════════════════════════════════════
# EVENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

ACCOUNTING_JOURNAL_POSTED_V1 = "accounting.journal.posted.v1"
ACCOUNTING_JOURNAL_REVERSED_V1 = "accounting.journal.reversed.v1"
ACCOUNTING_ACCOUNT_CREATED_V1 = "accounting.account.created.v1"
ACCOUNTING_OBLIGATION_CREATED_V1 = "accounting.obligation.created.v1"
ACCOUNTING_OBLIGATION_FULFILLED_V1 = "accounting.obligation.fulfilled.v1"

ACCOUNTING_EVENT_TYPES = (
    ACCOUNTING_JOURNAL_POSTED_V1,
    ACCOUNTING_JOURNAL_REVERSED_V1,
    ACCOUNTING_ACCOUNT_CREATED_V1,
    ACCOUNTING_OBLIGATION_CREATED_V1,
    ACCOUNTING_OBLIGATION_FULFILLED_V1,
)


# ══════════════════════════════════════════════════════════════
# COMMAND → EVENT MAPPING
# ══════════════════════════════════════════════════════════════

COMMAND_TO_EVENT_TYPE = {
    "accounting.journal.post.request": ACCOUNTING_JOURNAL_POSTED_V1,
    "accounting.journal.reverse.request": ACCOUNTING_JOURNAL_REVERSED_V1,
    "accounting.account.create.request": ACCOUNTING_ACCOUNT_CREATED_V1,
    "accounting.obligation.create.request": ACCOUNTING_OBLIGATION_CREATED_V1,
    "accounting.obligation.fulfill.request": ACCOUNTING_OBLIGATION_FULFILLED_V1,
}


def resolve_accounting_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_accounting_event_types(event_type_registry) -> None:
    for event_type in sorted(ACCOUNTING_EVENT_TYPES):
        event_type_registry.register(event_type)


# ══════════════════════════════════════════════════════════════
# PAYLOAD BUILDERS
# ══════════════════════════════════════════════════════════════

def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "actor_id": command.actor_id,
        "actor_type": command.actor_type,
        "correlation_id": command.correlation_id,
        "command_id": command.command_id,
    }


def build_journal_posted_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "entry_id": command.payload["entry_id"],
        "lines": command.payload["lines"],
        "memo": command.payload["memo"],
        "currency": command.payload["currency"],
        "reference_id": command.payload.get("reference_id"),
        "posted_at": command.issued_at,
    })
    return payload


def build_journal_reversed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "original_entry_id": command.payload["original_entry_id"],
        "reversal_entry_id": command.payload["reversal_entry_id"],
        "reason": command.payload["reason"],
        "reversed_at": command.issued_at,
    })
    return payload


def build_account_created_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "account_code": command.payload["account_code"],
        "account_type": command.payload["account_type"],
        "name": command.payload["name"],
        "parent_code": command.payload.get("parent_code"),
        "created_at": command.issued_at,
    })
    return payload


def build_obligation_created_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "obligation_id": command.payload["obligation_id"],
        "obligation_type": command.payload["obligation_type"],
        "party_id": command.payload["party_id"],
        "total_amount": command.payload["total_amount"],
        "currency": command.payload["currency"],
        "due_date": command.payload["due_date"],
        "reference_id": command.payload.get("reference_id"),
        "description": command.payload.get("description", ""),
        "created_at": command.issued_at,
    })
    return payload


def build_obligation_fulfilled_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "obligation_id": command.payload["obligation_id"],
        "fulfillment_id": command.payload["fulfillment_id"],
        "fulfillment_type": command.payload["fulfillment_type"],
        "amount": command.payload["amount"],
        "currency": command.payload["currency"],
        "reference_id": command.payload.get("reference_id"),
        "fulfilled_at": command.issued_at,
    })
    return payload
