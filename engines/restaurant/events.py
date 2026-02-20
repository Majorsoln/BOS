"""
BOS Restaurant Engine — Event Types and Payload Builders
==========================================================
Engine: Restaurant (Table-service & Kitchen Management)
"""

from __future__ import annotations

from core.commands.base import Command

RESTAURANT_TABLE_OPENED_V1 = "restaurant.table.opened.v1"
RESTAURANT_TABLE_CLOSED_V1 = "restaurant.table.closed.v1"
RESTAURANT_ORDER_PLACED_V1 = "restaurant.order.placed.v1"
RESTAURANT_ORDER_ITEM_SERVED_V1 = "restaurant.order.item_served.v1"
RESTAURANT_ORDER_CANCELLED_V1 = "restaurant.order.cancelled.v1"
RESTAURANT_BILL_SETTLED_V1 = "restaurant.bill.settled.v1"

RESTAURANT_EVENT_TYPES = (
    RESTAURANT_TABLE_OPENED_V1,
    RESTAURANT_TABLE_CLOSED_V1,
    RESTAURANT_ORDER_PLACED_V1,
    RESTAURANT_ORDER_ITEM_SERVED_V1,
    RESTAURANT_ORDER_CANCELLED_V1,
    RESTAURANT_BILL_SETTLED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "restaurant.table.open.request": RESTAURANT_TABLE_OPENED_V1,
    "restaurant.table.close.request": RESTAURANT_TABLE_CLOSED_V1,
    "restaurant.order.place.request": RESTAURANT_ORDER_PLACED_V1,
    "restaurant.order.serve_item.request": RESTAURANT_ORDER_ITEM_SERVED_V1,
    "restaurant.order.cancel.request": RESTAURANT_ORDER_CANCELLED_V1,
    "restaurant.bill.settle.request": RESTAURANT_BILL_SETTLED_V1,
}


def resolve_restaurant_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_restaurant_event_types(event_type_registry) -> None:
    for event_type in sorted(RESTAURANT_EVENT_TYPES):
        event_type_registry.register(event_type)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "actor_id": command.actor_id,
        "actor_type": command.actor_type,
        "correlation_id": command.correlation_id,
        "command_id": command.command_id,
    }


def build_table_opened_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "table_id": command.payload["table_id"],
        "table_name": command.payload["table_name"],
        "covers": command.payload["covers"],
        "server_id": command.actor_id,
        "opened_at": command.issued_at,
    })
    return payload


def build_table_closed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "table_id": command.payload["table_id"],
        "closed_at": command.issued_at,
    })
    return payload


def build_order_placed_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "table_id": command.payload["table_id"],
        "items": command.payload["items"],
        "currency": command.payload["currency"],
        "placed_at": command.issued_at,
    })
    return payload


def build_order_item_served_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "item_id": command.payload["item_id"],
        "served_at": command.issued_at,
    })
    return payload


def build_order_cancelled_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "order_id": command.payload["order_id"],
        "reason": command.payload["reason"],
        "cancelled_at": command.issued_at,
    })
    return payload


def build_bill_settled_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update({
        "bill_id": command.payload["bill_id"],
        "table_id": command.payload["table_id"],
        "total_amount": command.payload["total_amount"],
        "tip_amount": command.payload.get("tip_amount", 0),
        "currency": command.payload["currency"],
        "payment_method": command.payload["payment_method"],
        "settled_at": command.issued_at,
    })
    return payload
