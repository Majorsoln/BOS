"""
BOS Inventory Engine — Application Service
=============================================
Orchestrates inventory commands → events → projections.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.inventory.commands import INVENTORY_COMMAND_TYPES
from engines.inventory.events import (
    resolve_inventory_event_type,
    register_inventory_event_types,
    build_stock_received_payload,
    build_stock_issued_payload,
    build_stock_transferred_payload,
    build_stock_adjusted_payload,
    build_item_registered_payload,
    build_item_updated_payload,
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

class InventoryProjectionStore:
    """In-memory projection store for inventory state."""

    def __init__(self):
        self._events: List[dict] = []
        self._stock: Dict[tuple, int] = {}
        self._items: Dict[str, dict] = {}

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("inventory.stock.received"):
            key = (payload["item_id"], payload["location_id"])
            self._stock[key] = self._stock.get(key, 0) + payload["quantity"]

        elif event_type.startswith("inventory.stock.issued"):
            key = (payload["item_id"], payload["location_id"])
            self._stock[key] = self._stock.get(key, 0) - payload["quantity"]

        elif event_type.startswith("inventory.stock.transferred"):
            from_key = (payload["item_id"], payload["from_location_id"])
            to_key = (payload["item_id"], payload["to_location_id"])
            self._stock[from_key] = self._stock.get(from_key, 0) - payload["quantity"]
            self._stock[to_key] = self._stock.get(to_key, 0) + payload["quantity"]

        elif event_type.startswith("inventory.stock.adjusted"):
            key = (payload["item_id"], payload["location_id"])
            if payload["adjustment_type"] == "ADJUST_PLUS":
                self._stock[key] = self._stock.get(key, 0) + payload["quantity"]
            else:
                self._stock[key] = self._stock.get(key, 0) - payload["quantity"]

        elif event_type.startswith("inventory.item.registered"):
            self._items[payload["item_id"]] = payload

        elif event_type.startswith("inventory.item.updated"):
            if payload["item_id"] in self._items:
                self._items[payload["item_id"]].update(payload.get("changes", {}))

    def get_stock(self, item_id: str, location_id: str) -> int:
        return self._stock.get((item_id, location_id), 0)

    def get_item(self, item_id: str) -> Optional[dict]:
        return self._items.get(item_id)

    @property
    def event_count(self) -> int:
        return len(self._events)


# ══════════════════════════════════════════════════════════════
# PAYLOAD DISPATCHER
# ══════════════════════════════════════════════════════════════

PAYLOAD_BUILDERS = {
    "inventory.stock.receive.request": build_stock_received_payload,
    "inventory.stock.issue.request": build_stock_issued_payload,
    "inventory.stock.transfer.request": build_stock_transferred_payload,
    "inventory.stock.adjust.request": build_stock_adjusted_payload,
    "inventory.item.register.request": build_item_registered_payload,
    "inventory.item.update.request": build_item_updated_payload,
}


# ══════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class InventoryExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLER
# ══════════════════════════════════════════════════════════════

class _InventoryCommandHandler:
    def __init__(self, service: "InventoryService"):
        self._service = service

    def execute(self, command: Command) -> InventoryExecutionResult:
        return self._service._execute_command(command)


# ══════════════════════════════════════════════════════════════
# APPLICATION SERVICE
# ══════════════════════════════════════════════════════════════

class InventoryService:
    """
    Inventory Engine application service.

    Orchestrates:
    1. Command → Event type resolution
    2. Payload building
    3. Event persistence
    4. Projection updates
    """

    def __init__(
        self,
        *,
        business_context,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: InventoryProjectionStore | None = None,
        feature_flag_provider=None,
    ):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or InventoryProjectionStore()
        self._feature_flag_provider = feature_flag_provider

        register_inventory_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _InventoryCommandHandler(self)
        for command_type in sorted(INVENTORY_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_command(self, command: Command) -> InventoryExecutionResult:
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_inventory_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported inventory command type: {command.command_type}"
            )

        builder = PAYLOAD_BUILDERS.get(command.command_type)
        if builder is None:
            raise ValueError(
                f"No payload builder for: {command.command_type}"
            )

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

        return InventoryExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> InventoryProjectionStore:
        return self._projection_store
