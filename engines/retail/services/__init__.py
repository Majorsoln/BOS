"""
BOS Retail Engine — Application Service
==========================================
Full sale lifecycle: open → add lines → discount → complete → void/refund.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from engines.retail.commands import RETAIL_COMMAND_TYPES
from engines.retail.events import (
    resolve_retail_event_type,
    register_retail_event_types,
    build_sale_opened_payload,
    build_sale_line_added_payload,
    build_sale_line_removed_payload,
    build_sale_discount_applied_payload,
    build_sale_completed_payload,
    build_sale_voided_payload,
    build_refund_issued_payload,
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

class RetailProjectionStore:
    """In-memory projection store for retail sale state."""

    def __init__(self):
        self._events: List[dict] = []
        # sale_id → sale data
        self._sales: Dict[str, dict] = {}
        # Aggregate metrics
        self._total_revenue: int = 0
        self._total_refunds: int = 0
        self._sale_count: int = 0

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("retail.sale.opened"):
            self._sales[payload["sale_id"]] = {
                "status": "OPEN",
                "currency": payload["currency"],
                "lines": {},
                "total_amount": 0,
                "discount_amount": 0,
                "customer_id": payload.get("customer_id"),
            }

        elif event_type.startswith("retail.sale.line_added"):
            sid = payload["sale_id"]
            if sid in self._sales:
                self._sales[sid]["lines"][payload["line_id"]] = {
                    "item_id": payload["item_id"],
                    "sku": payload["sku"],
                    "quantity": payload["quantity"],
                    "unit_price": payload["unit_price"],
                    "line_total": payload["line_total"],
                }
                self._sales[sid]["total_amount"] += payload["line_total"]

        elif event_type.startswith("retail.sale.line_removed"):
            sid = payload["sale_id"]
            if sid in self._sales:
                lid = payload["line_id"]
                if lid in self._sales[sid]["lines"]:
                    removed = self._sales[sid]["lines"].pop(lid)
                    self._sales[sid]["total_amount"] -= removed["line_total"]

        elif event_type.startswith("retail.sale.discount_applied"):
            sid = payload["sale_id"]
            if sid in self._sales:
                self._sales[sid]["discount_amount"] += payload["discount_value"]

        elif event_type.startswith("retail.sale.completed"):
            sid = payload["sale_id"]
            if sid in self._sales:
                self._sales[sid]["status"] = "COMPLETED"
                self._sales[sid]["net_amount"] = payload["net_amount"]
                self._sales[sid]["payment_method"] = payload["payment_method"]
                self._total_revenue += payload["net_amount"]
                self._sale_count += 1

        elif event_type.startswith("retail.sale.voided"):
            sid = payload["sale_id"]
            if sid in self._sales:
                prev_status = self._sales[sid]["status"]
                self._sales[sid]["status"] = "VOIDED"
                if prev_status == "COMPLETED":
                    self._total_revenue -= self._sales[sid].get("net_amount", 0)
                    self._sale_count -= 1

        elif event_type.startswith("retail.refund.issued"):
            self._total_refunds += payload["amount"]

    def get_sale(self, sale_id: str) -> Optional[dict]:
        return self._sales.get(sale_id)

    @property
    def total_revenue(self) -> int:
        return self._total_revenue

    @property
    def total_refunds(self) -> int:
        return self._total_refunds

    @property
    def sale_count(self) -> int:
        return self._sale_count

    @property
    def event_count(self) -> int:
        return len(self._events)


# ══════════════════════════════════════════════════════════════
# PAYLOAD DISPATCHER
# ══════════════════════════════════════════════════════════════

PAYLOAD_BUILDERS = {
    "retail.sale.open.request": build_sale_opened_payload,
    "retail.sale.add_line.request": build_sale_line_added_payload,
    "retail.sale.remove_line.request": build_sale_line_removed_payload,
    "retail.sale.apply_discount.request": build_sale_discount_applied_payload,
    "retail.sale.complete.request": build_sale_completed_payload,
    "retail.sale.void.request": build_sale_voided_payload,
    "retail.refund.issue.request": build_refund_issued_payload,
}


# ══════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RetailExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLER
# ══════════════════════════════════════════════════════════════

class _RetailCommandHandler:
    def __init__(self, service: "RetailService"):
        self._service = service

    def execute(self, command: Command) -> RetailExecutionResult:
        return self._service._execute_command(command)


# ══════════════════════════════════════════════════════════════
# APPLICATION SERVICE
# ══════════════════════════════════════════════════════════════

class RetailService:
    """Retail Engine application service — full POS lifecycle."""

    def __init__(
        self,
        *,
        business_context,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: RetailProjectionStore | None = None,
    ):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or RetailProjectionStore()

        register_retail_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _RetailCommandHandler(self)
        for command_type in sorted(RETAIL_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_command(self, command: Command) -> RetailExecutionResult:
        event_type = resolve_retail_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported retail command type: {command.command_type}"
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

        return RetailExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> RetailProjectionStore:
        return self._projection_store
