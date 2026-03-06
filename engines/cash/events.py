"""
BOS Cash Engine — Event Type Declarations
==========================================
Canonical event types emitted by the cash engine.

Format: engine.domain.action.version
All types must be registered via register_cash_event_types()
before any event of that type can be persisted.
"""

# ── Session lifecycle ──────────────────────────────────────────
CASH_SESSION_OPENED_V1 = "cash.session.opened.v1"
CASH_SESSION_CLOSED_V1 = "cash.session.closed.v1"
CASH_SESSION_RECONCILED_V1 = "cash.session.reconciled.v1"

# ── Drawer operations ─────────────────────────────────────────
CASH_DRAWER_COUNTED_V1 = "cash.drawer.counted.v1"
CASH_DRAWER_OPENED_V1 = "cash.drawer.opened.v1"

# ── Cash movements ────────────────────────────────────────────
CASH_FLOAT_ISSUED_V1 = "cash.float.issued.v1"
CASH_DROP_RECORDED_V1 = "cash.drop.recorded.v1"
CASH_SAFE_TRANSFER_V1 = "cash.safe.transferred.v1"

CASH_EVENT_TYPES = (
    CASH_SESSION_OPENED_V1,
    CASH_SESSION_CLOSED_V1,
    CASH_SESSION_RECONCILED_V1,
    CASH_DRAWER_COUNTED_V1,
    CASH_DRAWER_OPENED_V1,
    CASH_FLOAT_ISSUED_V1,
    CASH_DROP_RECORDED_V1,
    CASH_SAFE_TRANSFER_V1,
)


def register_cash_event_types(event_type_registry) -> None:
    """Register all cash event types with the given EventTypeRegistry."""
    for event_type in sorted(CASH_EVENT_TYPES):
        event_type_registry.register(event_type)
