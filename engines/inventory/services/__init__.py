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
from engines.inventory.lot_engine import LotStore, ValuationMethod


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
    """
    In-memory projection store for inventory state.

    Tracks both simple quantity-level stock and lot-level FIFO/LIFO valuation.
    Lot tracking is activated when stock.received events include a unit_cost.
    """

    def __init__(self, default_valuation: ValuationMethod = ValuationMethod.FIFO):
        self._events: List[dict] = []
        self._stock: Dict[tuple, int] = {}          # (item_id, location_id) → qty
        self._items: Dict[str, dict] = {}
        self._lot_store: LotStore = LotStore(default_method=default_valuation)

    def set_item_valuation(self, item_id: str, method: ValuationMethod) -> None:
        """Override the valuation method for a specific item (FIFO / LIFO / WAC)."""
        self._lot_store.set_item_method(item_id, method)

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type.startswith("inventory.stock.received"):
            item_id = payload["item_id"]
            loc_id = payload["location_id"]
            qty = payload["quantity"]
            key = (item_id, loc_id)
            self._stock[key] = self._stock.get(key, 0) + qty

            # Lot tracking — only when unit_cost is present
            unit_cost_data = payload.get("unit_cost")
            if unit_cost_data is not None:
                unit_cost_int = (
                    unit_cost_data.get("amount", 0)
                    if isinstance(unit_cost_data, dict)
                    else int(unit_cost_data)
                )
                received_at = str(payload.get("received_at", ""))
                ref_id = payload.get("reference_id")
                self._lot_store.receive(
                    item_id=item_id,
                    location_id=loc_id,
                    quantity=qty,
                    unit_cost=unit_cost_int,
                    received_at=received_at,
                    reference_id=ref_id,
                )

        elif event_type.startswith("inventory.stock.issued"):
            item_id = payload["item_id"]
            loc_id = payload["location_id"]
            qty = payload["quantity"]
            key = (item_id, loc_id)
            self._stock[key] = self._stock.get(key, 0) - qty
            # Consume from lot store (uses item's configured method, default FIFO)
            self._lot_store.consume(item_id=item_id, location_id=loc_id, quantity=qty)

        elif event_type.startswith("inventory.stock.transferred"):
            item_id = payload["item_id"]
            from_key = (item_id, payload["from_location_id"])
            to_key = (item_id, payload["to_location_id"])
            qty = payload["quantity"]
            self._stock[from_key] = self._stock.get(from_key, 0) - qty
            self._stock[to_key] = self._stock.get(to_key, 0) + qty
            # Move cost from source lots to destination (FIFO consume + re-receive at WAC)
            result = self._lot_store.consume(
                item_id=item_id, location_id=payload["from_location_id"], quantity=qty
            )
            if result.quantity_consumed > 0:
                avg_cost = result.cost_per_unit
                self._lot_store.receive(
                    item_id=item_id,
                    location_id=payload["to_location_id"],
                    quantity=result.quantity_consumed,
                    unit_cost=avg_cost,
                    received_at=str(payload.get("transferred_at", "")),
                    reference_id=payload.get("reference_id"),
                )

        elif event_type.startswith("inventory.stock.adjusted"):
            item_id = payload["item_id"]
            loc_id = payload["location_id"]
            qty = payload["quantity"]
            key = (item_id, loc_id)
            if payload["adjustment_type"] == "ADJUST_PLUS":
                self._stock[key] = self._stock.get(key, 0) + qty
                # Adjustments in at zero cost (cannot determine true cost of found stock)
                self._lot_store.receive(
                    item_id=item_id, location_id=loc_id,
                    quantity=qty, unit_cost=0,
                    received_at=str(payload.get("adjusted_at", "")),
                    reference_id=payload.get("reference_id"),
                )
            else:
                self._stock[key] = self._stock.get(key, 0) - qty
                self._lot_store.consume(item_id=item_id, location_id=loc_id, quantity=qty)

        elif event_type.startswith("inventory.item.registered"):
            self._items[payload["item_id"]] = payload

        elif event_type.startswith("inventory.item.updated"):
            if payload["item_id"] in self._items:
                self._items[payload["item_id"]].update(payload.get("changes", {}))

    # ── Simple stock queries ───────────────────────────────────

    def get_stock(self, item_id: str, location_id: str) -> int:
        return self._stock.get((item_id, location_id), 0)

    def get_item(self, item_id: str) -> Optional[dict]:
        return self._items.get(item_id)

    # ── Lot-level valuation queries ───────────────────────────

    def get_stock_value(self, item_id: str, location_id: str) -> int:
        """Total value of stock on hand at this location (minor currency units)."""
        return self._lot_store.get_stock_value(item_id, location_id)

    def get_weighted_average_cost(self, item_id: str, location_id: str) -> int:
        """Weighted average cost per unit for this item/location."""
        return self._lot_store.get_weighted_average_cost(item_id, location_id)

    def get_lots(self, item_id: str, location_id: str):
        """All lots (including exhausted) for this item/location."""
        return self._lot_store.get_lots(item_id, location_id)

    def get_active_lots(self, item_id: str, location_id: str):
        """Only lots with remaining stock."""
        return self._lot_store.get_active_lots(item_id, location_id)

    def total_inventory_value(self) -> int:
        """Total value of all stock on hand across all items and locations."""
        return self._lot_store.total_inventory_value()

    @property
    def lot_store(self) -> LotStore:
        return self._lot_store

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
