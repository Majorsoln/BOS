"""
BOS Inventory Engine — Event Types and Payload Builders
=========================================================
Engine: Inventory
Authority: BOS Doctrine — Deterministic, Event-Sourced

Inventory builds payload only. Envelope/hash-chain remain external.
"""

from __future__ import annotations

from core.commands.base import Command


# ══════════════════════════════════════════════════════════════
# EVENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

INVENTORY_STOCK_RECEIVED_V1 = "inventory.stock.received.v1"
INVENTORY_STOCK_ISSUED_V1 = "inventory.stock.issued.v1"
INVENTORY_STOCK_TRANSFERRED_V1 = "inventory.stock.transferred.v1"
INVENTORY_STOCK_ADJUSTED_V1 = "inventory.stock.adjusted.v1"
INVENTORY_ITEM_REGISTERED_V1 = "inventory.item.registered.v1"
INVENTORY_ITEM_UPDATED_V1 = "inventory.item.updated.v1"

INVENTORY_EVENT_TYPES = (
    INVENTORY_STOCK_RECEIVED_V1,
    INVENTORY_STOCK_ISSUED_V1,
    INVENTORY_STOCK_TRANSFERRED_V1,
    INVENTORY_STOCK_ADJUSTED_V1,
    INVENTORY_ITEM_REGISTERED_V1,
    INVENTORY_ITEM_UPDATED_V1,
)


# ══════════════════════════════════════════════════════════════
# COMMAND → EVENT MAPPING
# ══════════════════════════════════════════════════════════════

COMMAND_TO_EVENT_TYPE = {
    "inventory.stock.receive.request": INVENTORY_STOCK_RECEIVED_V1,
    "inventory.stock.issue.request": INVENTORY_STOCK_ISSUED_V1,
    "inventory.stock.transfer.request": INVENTORY_STOCK_TRANSFERRED_V1,
    "inventory.stock.adjust.request": INVENTORY_STOCK_ADJUSTED_V1,
    "inventory.item.register.request": INVENTORY_ITEM_REGISTERED_V1,
    "inventory.item.update.request": INVENTORY_ITEM_UPDATED_V1,
}


def resolve_inventory_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_inventory_event_types(event_type_registry) -> None:
    for event_type in sorted(INVENTORY_EVENT_TYPES):
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


def build_stock_received_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "quantity": command.payload["quantity"],
        "location_id": command.payload["location_id"],
        "location_name": command.payload["location_name"],
        "reason": command.payload.get("reason", "PURCHASE"),
        "unit_cost": command.payload.get("unit_cost"),
        "reference_id": command.payload.get("reference_id"),
        "received_at": command.issued_at,
    })
    return payload


def build_stock_issued_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "quantity": command.payload["quantity"],
        "location_id": command.payload["location_id"],
        "location_name": command.payload["location_name"],
        "reason": command.payload.get("reason", "SALE"),
        "reference_id": command.payload.get("reference_id"),
        "issued_at": command.issued_at,
    })
    return payload


def build_stock_transferred_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "quantity": command.payload["quantity"],
        "from_location_id": command.payload["from_location_id"],
        "from_location_name": command.payload["from_location_name"],
        "to_location_id": command.payload["to_location_id"],
        "to_location_name": command.payload["to_location_name"],
        "reference_id": command.payload.get("reference_id"),
        "transferred_at": command.issued_at,
    })
    return payload


def build_stock_adjusted_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "quantity": command.payload["quantity"],
        "adjustment_type": command.payload["adjustment_type"],
        "location_id": command.payload["location_id"],
        "location_name": command.payload["location_name"],
        "reason": command.payload["reason"],
        "reference_id": command.payload.get("reference_id"),
        "adjusted_at": command.issued_at,
    })
    return payload


def build_item_registered_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "name": command.payload["name"],
        "item_type": command.payload["item_type"],
        "unit_of_measure": command.payload["unit_of_measure"],
        "prices": command.payload.get("prices", []),
        "tax_category": command.payload.get("tax_category"),
        "registered_at": command.issued_at,
    })
    return payload


def build_item_updated_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "item_id": command.payload["item_id"],
        "sku": command.payload["sku"],
        "changes": command.payload["changes"],
        "version": command.payload["version"],
        "updated_at": command.issued_at,
    })
    return payload
