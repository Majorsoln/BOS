"""
BOS Accounting Engine — Application Service
==============================================
Orchestrates accounting commands → events → projections.
Uses Ledger and Obligation primitives from Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.context.scope_guard import enforce_scope_guard
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.accounting.commands import ACCOUNTING_COMMAND_TYPES
from engines.accounting.events import (
    resolve_accounting_event_type,
    register_accounting_event_types,
    build_journal_posted_payload,
    build_journal_reversed_payload,
    build_account_created_payload,
    build_obligation_created_payload,
    build_obligation_fulfilled_payload,
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

class AccountingProjectionStore:
    """In-memory projection store for accounting state."""

    def __init__(self):
        self._events: List[dict] = []
        # account_code → {total_debits, total_credits}
        self._balances: Dict[str, Dict[str, int]] = {}
        # account_code → account data
        self._accounts: Dict[str, dict] = {}
        # obligation_id → {total_amount, fulfilled, status}
        self._obligations: Dict[str, dict] = {}

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("accounting.journal.posted"):
            for line in payload.get("lines", []):
                code = line["account_code"]
                if code not in self._balances:
                    self._balances[code] = {"total_debits": 0, "total_credits": 0}
                if line["side"] == "DEBIT":
                    self._balances[code]["total_debits"] += line["amount"]
                else:
                    self._balances[code]["total_credits"] += line["amount"]

        elif event_type.startswith("accounting.account.created"):
            self._accounts[payload["account_code"]] = payload

        elif event_type.startswith("accounting.obligation.created"):
            self._obligations[payload["obligation_id"]] = {
                "total_amount": payload["total_amount"],
                "fulfilled": 0,
                "status": "PENDING",
                "obligation_type": payload["obligation_type"],
                "currency": payload["currency"],
            }

        elif event_type.startswith("accounting.obligation.fulfilled"):
            obl_id = payload["obligation_id"]
            if obl_id in self._obligations:
                obl = self._obligations[obl_id]
                obl["fulfilled"] += payload["amount"]
                if obl["fulfilled"] >= obl["total_amount"]:
                    obl["status"] = "FULFILLED"
                else:
                    obl["status"] = "PARTIALLY_FULFILLED"

    def get_balance(self, account_code: str) -> Optional[Dict[str, int]]:
        return self._balances.get(account_code)

    def get_account(self, account_code: str) -> Optional[dict]:
        return self._accounts.get(account_code)

    def get_obligation(self, obligation_id: str) -> Optional[dict]:
        return self._obligations.get(obligation_id)

    def trial_balance(self) -> tuple:
        total_d = sum(b["total_debits"] for b in self._balances.values())
        total_c = sum(b["total_credits"] for b in self._balances.values())
        return total_d, total_c

    @property
    def event_count(self) -> int:
        return len(self._events)


# ══════════════════════════════════════════════════════════════
# PAYLOAD DISPATCHER
# ══════════════════════════════════════════════════════════════

PAYLOAD_BUILDERS = {
    "accounting.journal.post.request": build_journal_posted_payload,
    "accounting.journal.reverse.request": build_journal_reversed_payload,
    "accounting.account.create.request": build_account_created_payload,
    "accounting.obligation.create.request": build_obligation_created_payload,
    "accounting.obligation.fulfill.request": build_obligation_fulfilled_payload,
}


# ══════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AccountingExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLER
# ══════════════════════════════════════════════════════════════

class _AccountingCommandHandler:
    def __init__(self, service: "AccountingService"):
        self._service = service

    def execute(self, command: Command) -> AccountingExecutionResult:
        return self._service._execute_command(command)


# ══════════════════════════════════════════════════════════════
# APPLICATION SERVICE
# ══════════════════════════════════════════════════════════════

class AccountingService:
    """Accounting Engine application service."""

    def __init__(
        self,
        *,
        business_context,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: AccountingProjectionStore | None = None,
        feature_flag_provider=None,
    ):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or AccountingProjectionStore()
        self._feature_flag_provider = feature_flag_provider

        register_accounting_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _AccountingCommandHandler(self)
        for command_type in sorted(ACCOUNTING_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_command(self, command: Command) -> AccountingExecutionResult:
        enforce_scope_guard(command)
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_accounting_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported accounting command type: {command.command_type}"
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

        return AccountingExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> AccountingProjectionStore:
        return self._projection_store
