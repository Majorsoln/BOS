"""
BOS Restaurant Engine — Event Type Declarations
================================================
Canonical event types emitted by the restaurant engine.

Format: engine.domain.action.version
All types must be registered via register_restaurant_event_types()
before any event of that type can be persisted.
"""

# ── Order lifecycle ────────────────────────────────────────────
RESTAURANT_ORDER_PLACED_V1 = "restaurant.order.placed.v1"
RESTAURANT_ORDER_CONFIRMED_V1 = "restaurant.order.confirmed.v1"
RESTAURANT_ORDER_CANCELLED_V1 = "restaurant.order.cancelled.v1"
RESTAURANT_ORDER_COMPLETED_V1 = "restaurant.order.completed.v1"

# ── Item lifecycle ─────────────────────────────────────────────
RESTAURANT_ORDER_ITEM_ADDED_V1 = "restaurant.order.item_added.v1"
RESTAURANT_ORDER_ITEM_VOIDED_V1 = "restaurant.order.item_voided.v1"

# ── Kitchen ────────────────────────────────────────────────────
RESTAURANT_KITCHEN_TICKET_SENT_V1 = "restaurant.kitchen.ticket_sent.v1"
RESTAURANT_KITCHEN_ITEM_READY_V1 = "restaurant.kitchen.item_ready.v1"

# ── Payment ────────────────────────────────────────────────────
RESTAURANT_ORDER_PAID_V1 = "restaurant.order.paid.v1"
RESTAURANT_ORDER_REFUNDED_V1 = "restaurant.order.refunded.v1"

RESTAURANT_EVENT_TYPES = (
    RESTAURANT_ORDER_PLACED_V1,
    RESTAURANT_ORDER_CONFIRMED_V1,
    RESTAURANT_ORDER_CANCELLED_V1,
    RESTAURANT_ORDER_COMPLETED_V1,
    RESTAURANT_ORDER_ITEM_ADDED_V1,
    RESTAURANT_ORDER_ITEM_VOIDED_V1,
    RESTAURANT_KITCHEN_TICKET_SENT_V1,
    RESTAURANT_KITCHEN_ITEM_READY_V1,
    RESTAURANT_ORDER_PAID_V1,
    RESTAURANT_ORDER_REFUNDED_V1,
)


def register_restaurant_event_types(event_type_registry) -> None:
    """Register all restaurant event types with the given EventTypeRegistry."""
    for event_type in sorted(RESTAURANT_EVENT_TYPES):
        event_type_registry.register(event_type)
