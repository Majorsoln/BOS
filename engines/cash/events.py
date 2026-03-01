"""
BOS Cash Engine — Event Types and Payload Builders
=====================================================
Engine: Cash Management
Authority: BOS Doctrine — Deterministic, Event-Sourced

Multi-drawer cash management with session tracking,
reconciliation, and denomination counting.
"""

from __future__ import annotations

from core.commands.base import Command


# ══════════════════════════════════════════════════════════════
# EVENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

CASH_SESSION_OPENED_V1 = "cash.session.opened.v1"
CASH_SESSION_CLOSED_V1 = "cash.session.closed.v1"
CASH_PAYMENT_RECORDED_V1 = "cash.payment.recorded.v1"
CASH_DEPOSIT_RECORDED_V1 = "cash.deposit.recorded.v1"
CASH_WITHDRAWAL_RECORDED_V1 = "cash.withdrawal.recorded.v1"

CASH_EVENT_TYPES = (
    CASH_SESSION_OPENED_V1,
    CASH_SESSION_CLOSED_V1,
    CASH_PAYMENT_RECORDED_V1,
    CASH_DEPOSIT_RECORDED_V1,
    CASH_WITHDRAWAL_RECORDED_V1,
)


# ══════════════════════════════════════════════════════════════
# COMMAND → EVENT MAPPING
# ══════════════════════════════════════════════════════════════

COMMAND_TO_EVENT_TYPE = {
    "cash.session.open.request": CASH_SESSION_OPENED_V1,
    "cash.session.close.request": CASH_SESSION_CLOSED_V1,
    "cash.payment.record.request": CASH_PAYMENT_RECORDED_V1,
    "cash.deposit.record.request": CASH_DEPOSIT_RECORDED_V1,
    "cash.withdrawal.record.request": CASH_WITHDRAWAL_RECORDED_V1,
}


def resolve_cash_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_cash_event_types(event_type_registry) -> None:
    for event_type in sorted(CASH_EVENT_TYPES):
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


def build_session_opened_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "session_id": command.payload["session_id"],
        "drawer_id": command.payload["drawer_id"],
        "opening_balance": command.payload["opening_balance"],
        "currency": command.payload["currency"],
        "opened_by": command.actor_id,
        "opened_at": command.issued_at,
    })
    return payload


def build_session_closed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "session_id": command.payload["session_id"],
        "drawer_id": command.payload["drawer_id"],
        "closing_balance": command.payload["closing_balance"],
        "expected_balance": command.payload.get("expected_balance"),
        "currency": command.payload["currency"],
        "difference": command.payload.get("difference", 0),
        "closed_by": command.actor_id,
        "closed_at": command.issued_at,
    })
    return payload


def build_payment_recorded_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "payment_id": command.payload["payment_id"],
        "session_id": command.payload["session_id"],
        "drawer_id": command.payload["drawer_id"],
        "amount": command.payload["amount"],
        "currency": command.payload["currency"],
        "payment_method": command.payload["payment_method"],
        "reference_id": command.payload.get("reference_id"),
        "recorded_at": command.issued_at,
    })
    return payload


def build_deposit_recorded_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "deposit_id": command.payload["deposit_id"],
        "session_id": command.payload["session_id"],
        "drawer_id": command.payload["drawer_id"],
        "amount": command.payload["amount"],
        "currency": command.payload["currency"],
        "reason": command.payload.get("reason", "FLOAT_ADD"),
        "recorded_at": command.issued_at,
    })
    return payload


def build_withdrawal_recorded_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "withdrawal_id": command.payload["withdrawal_id"],
        "session_id": command.payload["session_id"],
        "drawer_id": command.payload["drawer_id"],
        "amount": command.payload["amount"],
        "currency": command.payload["currency"],
        "reason": command.payload.get("reason", "BANK_DEPOSIT"),
        "recorded_at": command.issued_at,
    })
    return payload
