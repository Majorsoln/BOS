"""
BOS Procurement Engine — Application Service
===============================================
Full purchase lifecycle: create PO → approve → receive → invoice match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from engines.procurement.commands import PROCUREMENT_COMMAND_TYPES
from engines.procurement.events import (
    resolve_procurement_event_type,
    register_procurement_event_types,
    build_order_created_payload,
    build_order_approved_payload,
    build_order_received_payload,
    build_order_cancelled_payload,
    build_invoice_matched_payload,
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

class ProcurementProjectionStore:
    """In-memory projection store for procurement state."""

    def __init__(self):
        self._events: List[dict] = []
        # order_id → order data
        self._orders: Dict[str, dict] = {}
        self._total_ordered: int = 0

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("procurement.order.created"):
            self._orders[payload["order_id"]] = {
                "status": "PENDING",
                "supplier_id": payload["supplier_id"],
                "supplier_name": payload["supplier_name"],
                "total_amount": payload["total_amount"],
                "currency": payload["currency"],
                "lines": payload["lines"],
                "received_lines": [],
            }
            self._total_ordered += payload["total_amount"]

        elif event_type.startswith("procurement.order.approved"):
            oid = payload["order_id"]
            if oid in self._orders:
                self._orders[oid]["status"] = "APPROVED"
                self._orders[oid]["approved_by"] = payload["approved_by"]

        elif event_type.startswith("procurement.order.received"):
            oid = payload["order_id"]
            if oid in self._orders:
                self._orders[oid]["status"] = "RECEIVED"
                self._orders[oid]["received_lines"] = payload["received_lines"]
                self._orders[oid]["location_id"] = payload["location_id"]

        elif event_type.startswith("procurement.order.cancelled"):
            oid = payload["order_id"]
            if oid in self._orders:
                prev = self._orders[oid]
                if prev["status"] in ("PENDING", "APPROVED"):
                    self._total_ordered -= prev["total_amount"]
                self._orders[oid]["status"] = "CANCELLED"

        elif event_type.startswith("procurement.invoice.matched"):
            oid = payload["order_id"]
            if oid in self._orders:
                self._orders[oid]["status"] = "INVOICED"
                self._orders[oid]["invoice_id"] = payload["invoice_id"]
                self._orders[oid]["invoice_amount"] = payload["invoice_amount"]

    def get_order(self, order_id: str) -> Optional[dict]:
        return self._orders.get(order_id)

    @property
    def total_ordered(self) -> int:
        return self._total_ordered

    @property
    def event_count(self) -> int:
        return len(self._events)


# ══════════════════════════════════════════════════════════════
# PAYLOAD DISPATCHER
# ══════════════════════════════════════════════════════════════

PAYLOAD_BUILDERS = {
    "procurement.order.create.request": build_order_created_payload,
    "procurement.order.approve.request": build_order_approved_payload,
    "procurement.order.receive.request": build_order_received_payload,
    "procurement.order.cancel.request": build_order_cancelled_payload,
    "procurement.invoice.match.request": build_invoice_matched_payload,
}


# ══════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProcurementExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLER
# ══════════════════════════════════════════════════════════════

class _ProcurementCommandHandler:
    def __init__(self, service: "ProcurementService"):
        self._service = service

    def execute(self, command: Command) -> ProcurementExecutionResult:
        return self._service._execute_command(command)


# ══════════════════════════════════════════════════════════════
# APPLICATION SERVICE
# ══════════════════════════════════════════════════════════════

class ProcurementService:
    """Procurement Engine application service — full purchase lifecycle."""

    def __init__(
        self,
        *,
        business_context,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: ProcurementProjectionStore | None = None,
    ):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or ProcurementProjectionStore()

        register_procurement_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _ProcurementCommandHandler(self)
        for command_type in sorted(PROCUREMENT_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_command(self, command: Command) -> ProcurementExecutionResult:
        event_type = resolve_procurement_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported procurement command type: {command.command_type}"
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

        return ProcurementExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> ProcurementProjectionStore:
        return self._projection_store
