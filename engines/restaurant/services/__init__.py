"""
BOS Restaurant Engine — Application Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from engines.restaurant.commands import RESTAURANT_COMMAND_TYPES
from engines.restaurant.events import (
    resolve_restaurant_event_type, register_restaurant_event_types,
    build_table_opened_payload, build_table_closed_payload,
    build_order_placed_payload, build_order_item_served_payload,
    build_order_cancelled_payload, build_bill_settled_payload,
)


class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...


class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


class RestaurantProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._tables: Dict[str, dict] = {}
        self._orders: Dict[str, dict] = {}
        self._total_revenue: int = 0
        self._total_tips: int = 0

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})
        if event_type.startswith("restaurant.table.opened"):
            self._tables[payload["table_id"]] = {
                "status": "OPEN", "covers": payload["covers"],
                "orders": [], "table_name": payload["table_name"],
            }
        elif event_type.startswith("restaurant.table.closed"):
            tid = payload["table_id"]
            if tid in self._tables:
                self._tables[tid]["status"] = "CLOSED"
        elif event_type.startswith("restaurant.order.placed"):
            oid = payload["order_id"]
            self._orders[oid] = {
                "table_id": payload["table_id"], "status": "PLACED",
                "items": {it["item_id"]: "PENDING" for it in payload["items"]},
            }
            tid = payload["table_id"]
            if tid in self._tables:
                self._tables[tid]["orders"].append(oid)
        elif event_type.startswith("restaurant.order.item_served"):
            oid = payload["order_id"]
            if oid in self._orders:
                self._orders[oid]["items"][payload["item_id"]] = "SERVED"
                if all(s == "SERVED" for s in self._orders[oid]["items"].values()):
                    self._orders[oid]["status"] = "FULLY_SERVED"
        elif event_type.startswith("restaurant.order.cancelled"):
            oid = payload["order_id"]
            if oid in self._orders:
                self._orders[oid]["status"] = "CANCELLED"
        elif event_type.startswith("restaurant.bill.settled"):
            self._total_revenue += payload["total_amount"]
            self._total_tips += payload.get("tip_amount", 0)

    def get_table(self, table_id: str) -> Optional[dict]:
        return self._tables.get(table_id)

    def get_order(self, order_id: str) -> Optional[dict]:
        return self._orders.get(order_id)

    @property
    def total_revenue(self) -> int:
        return self._total_revenue

    @property
    def total_tips(self) -> int:
        return self._total_tips

    @property
    def event_count(self) -> int:
        return len(self._events)


PAYLOAD_BUILDERS = {
    "restaurant.table.open.request": build_table_opened_payload,
    "restaurant.table.close.request": build_table_closed_payload,
    "restaurant.order.place.request": build_order_placed_payload,
    "restaurant.order.serve_item.request": build_order_item_served_payload,
    "restaurant.order.cancel.request": build_order_cancelled_payload,
    "restaurant.bill.settle.request": build_bill_settled_payload,
}


@dataclass(frozen=True)
class RestaurantExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _RestaurantCommandHandler:
    def __init__(self, service: "RestaurantService"):
        self._service = service

    def execute(self, command: Command) -> RestaurantExecutionResult:
        return self._service._execute_command(command)


class RestaurantService:
    def __init__(self, *, business_context, command_bus,
                 event_factory: EventFactoryProtocol,
                 persist_event: PersistEventProtocol,
                 event_type_registry,
                 projection_store: RestaurantProjectionStore | None = None):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or RestaurantProjectionStore()
        register_restaurant_event_types(self._event_type_registry)
        handler = _RestaurantCommandHandler(self)
        for ct in sorted(RESTAURANT_COMMAND_TYPES):
            self._command_bus.register_handler(ct, handler)

    def _is_persist_accepted(self, r: Any) -> bool:
        if hasattr(r, "accepted"):
            return bool(r.accepted)
        if isinstance(r, dict):
            return bool(r.get("accepted"))
        return bool(r)

    def _execute_command(self, command: Command) -> RestaurantExecutionResult:
        event_type = resolve_restaurant_event_type(command.command_type)
        if event_type is None:
            raise ValueError(f"Unsupported: {command.command_type}")
        builder = PAYLOAD_BUILDERS[command.command_type]
        payload = builder(command)
        event_data = self._event_factory(command=command, event_type=event_type, payload=payload)
        persist_result = self._persist_event(
            event_data=event_data, context=self._business_context,
            registry=self._event_type_registry, scope_requirement=command.scope_requirement)
        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            applied = True
        return RestaurantExecutionResult(
            event_type=event_type, event_data=event_data,
            persist_result=persist_result, projection_applied=applied)

    @property
    def projection_store(self) -> RestaurantProjectionStore:
        return self._projection_store
