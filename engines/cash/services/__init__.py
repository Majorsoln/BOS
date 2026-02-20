"""
BOS Cash Engine — Application Service
========================================
Multi-drawer cash management with session lifecycle tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.cash.commands import CASH_COMMAND_TYPES
from engines.cash.events import (
    resolve_cash_event_type,
    register_cash_event_types,
    build_session_opened_payload,
    build_session_closed_payload,
    build_payment_recorded_payload,
    build_deposit_recorded_payload,
    build_withdrawal_recorded_payload,
)


# ══════════════════════════════════════════════════════════════
# PROTOCOLS
# ══════════════════════════════════════════════════════════════

class EventFactoryProtocol(Protocol):
    def __call__(
        self, *, command: Command, event_type: str, payload: dict,
    ) -> dict:
        ...


class PersistEventProtocol(Protocol):
    def __call__(
        self, *, event_data: dict, context: Any, registry: Any, **kwargs,
    ) -> Any:
        ...


# ══════════════════════════════════════════════════════════════
# PROJECTION STORE
# ══════════════════════════════════════════════════════════════

class CashProjectionStore:
    """In-memory projection store for cash session state."""

    def __init__(self):
        self._events: List[dict] = []
        # session_id → session data
        self._sessions: Dict[str, dict] = {}
        # drawer_id → current balance
        self._drawer_balances: Dict[str, int] = {}

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("cash.session.opened"):
            self._sessions[payload["session_id"]] = {
                "drawer_id": payload["drawer_id"],
                "opening_balance": payload["opening_balance"],
                "currency": payload["currency"],
                "status": "OPEN",
                "total_payments": 0,
                "total_deposits": 0,
                "total_withdrawals": 0,
            }
            self._drawer_balances[payload["drawer_id"]] = payload["opening_balance"]

        elif event_type.startswith("cash.session.closed"):
            sid = payload["session_id"]
            if sid in self._sessions:
                self._sessions[sid]["status"] = "CLOSED"
                self._sessions[sid]["closing_balance"] = payload["closing_balance"]
                self._sessions[sid]["difference"] = payload.get("difference", 0)

        elif event_type.startswith("cash.payment.recorded"):
            sid = payload["session_id"]
            did = payload["drawer_id"]
            if sid in self._sessions:
                self._sessions[sid]["total_payments"] += payload["amount"]
            self._drawer_balances[did] = (
                self._drawer_balances.get(did, 0) + payload["amount"]
            )

        elif event_type.startswith("cash.deposit.recorded"):
            sid = payload["session_id"]
            did = payload["drawer_id"]
            if sid in self._sessions:
                self._sessions[sid]["total_deposits"] += payload["amount"]
            self._drawer_balances[did] = (
                self._drawer_balances.get(did, 0) + payload["amount"]
            )

        elif event_type.startswith("cash.withdrawal.recorded"):
            sid = payload["session_id"]
            did = payload["drawer_id"]
            if sid in self._sessions:
                self._sessions[sid]["total_withdrawals"] += payload["amount"]
            self._drawer_balances[did] = (
                self._drawer_balances.get(did, 0) - payload["amount"]
            )

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def get_drawer_balance(self, drawer_id: str) -> int:
        return self._drawer_balances.get(drawer_id, 0)

    @property
    def event_count(self) -> int:
        return len(self._events)


# ══════════════════════════════════════════════════════════════
# PAYLOAD DISPATCHER
# ══════════════════════════════════════════════════════════════

PAYLOAD_BUILDERS = {
    "cash.session.open.request": build_session_opened_payload,
    "cash.session.close.request": build_session_closed_payload,
    "cash.payment.record.request": build_payment_recorded_payload,
    "cash.deposit.record.request": build_deposit_recorded_payload,
    "cash.withdrawal.record.request": build_withdrawal_recorded_payload,
}


# ══════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CashExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLER
# ══════════════════════════════════════════════════════════════

class _CashCommandHandler:
    def __init__(self, service: "CashService"):
        self._service = service

    def execute(self, command: Command) -> CashExecutionResult:
        return self._service._execute_command(command)


# ══════════════════════════════════════════════════════════════
# APPLICATION SERVICE
# ══════════════════════════════════════════════════════════════

class CashService:
    """Cash Management Engine application service."""

    def __init__(
        self,
        *,
        business_context,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: CashProjectionStore | None = None,
        feature_flag_provider=None,
    ):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or CashProjectionStore()
        self._feature_flag_provider = feature_flag_provider

        register_cash_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _CashCommandHandler(self)
        for command_type in sorted(CASH_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_command(self, command: Command) -> CashExecutionResult:
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_cash_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported cash command type: {command.command_type}"
            )

        builder = PAYLOAD_BUILDERS.get(command.command_type)
        if builder is None:
            raise ValueError(f"No payload builder for: {command.command_type}")

        payload = builder(command)

        event_data = self._event_factory(
            command=command,
            event_type=event_type,
            payload=payload,
        )

        persist_result = self._persist_event(
            event_data=event_data,
            context=self._business_context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )

        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(
                event_type=event_type, payload=payload,
            )
            applied = True

        return CashExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> CashProjectionStore:
        return self._projection_store
