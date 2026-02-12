"""
BOS Engine Registry — Engine Contract Declaration
====================================================
Each engine must declare its identity, owned events, and subscriptions.
Contracts are frozen — once created, they cannot be altered.

Rules:
- engine_name must match the first segment of owned event types
- All event types must follow engine.domain.action format
- Subscribed events must belong to OTHER engines (no self-subscription)
- Contract is immutable after creation

This module ONLY declares structure. It does not enforce at runtime.
Enforcement is in enforcement.py.
"""

from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════
# VALIDATION HELPERS (used during contract construction only)
# ══════════════════════════════════════════════════════════════

def _validate_event_type_format(event_type: str) -> None:
    """
    Validate engine.domain.action format.
    Minimum three segments separated by dots.
    """
    if not event_type or not isinstance(event_type, str):
        raise ValueError(
            f"Event type must be a non-empty string, got: {event_type!r}"
        )

    parts = event_type.strip().split(".")
    if len(parts) < 3:
        raise ValueError(
            f"Event type '{event_type}' does not follow "
            f"engine.domain.action format (minimum 3 segments)."
        )

    for part in parts:
        if not part.strip():
            raise ValueError(
                f"Event type '{event_type}' contains empty segment."
            )


def _validate_namespace_ownership(
    event_type: str, engine_name: str
) -> None:
    """
    Verify first segment of event_type matches engine_name.
    inventory.stock.moved → engine_name must be 'inventory'.

    This is the namespace discipline rule. Non-negotiable.
    """
    first_segment = event_type.split(".")[0]
    if first_segment != engine_name:
        raise ValueError(
            f"Event type '{event_type}' namespace '{first_segment}' "
            f"does not match engine '{engine_name}'. "
            f"Engines can only own events in their own namespace."
        )


# ══════════════════════════════════════════════════════════════
# ENGINE CONTRACT (frozen declaration)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EngineContract:
    """
    Immutable declaration of an engine's identity and event boundaries.

    Fields:
        engine_name:            Unique engine identifier (e.g. 'inventory')
        owned_event_types:      Event types this engine may emit
        subscribed_event_types: Event types this engine listens to

    Validation (at creation time):
    - engine_name must be a simple identifier (no dots)
    - All owned event types must follow engine.domain.action format
    - First segment of owned types must match engine_name
    - Subscribed types must follow engine.domain.action format
    - Engine must not declare subscription to its own events

    Example:
        EngineContract(
            engine_name="inventory",
            owned_event_types=frozenset({
                "inventory.stock.moved",
                "inventory.stock.adjusted",
            }),
            subscribed_event_types=frozenset({
                "procurement.order.received",
                "retail.sale.completed",
            }),
        )
    """

    engine_name: str
    owned_event_types: frozenset[str]
    subscribed_event_types: frozenset[str]

    def __post_init__(self):
        # ── Validate engine_name ──────────────────────────────
        if not self.engine_name or not isinstance(self.engine_name, str):
            raise ValueError("engine_name must be a non-empty string.")

        name = self.engine_name.strip()
        if not name:
            raise ValueError("engine_name must not be blank.")

        if "." in self.engine_name:
            raise ValueError(
                f"engine_name '{self.engine_name}' must be a simple "
                f"identifier without dots."
            )

        # ── Validate owned_event_types ────────────────────────
        if not isinstance(self.owned_event_types, frozenset):
            raise TypeError("owned_event_types must be a frozenset.")

        for event_type in self.owned_event_types:
            _validate_event_type_format(event_type)
            _validate_namespace_ownership(event_type, self.engine_name)

        # ── Validate subscribed_event_types ───────────────────
        if not isinstance(self.subscribed_event_types, frozenset):
            raise TypeError("subscribed_event_types must be a frozenset.")

        for event_type in self.subscribed_event_types:
            _validate_event_type_format(event_type)

        # ── No self-subscription in contract ──────────────────
        own_subscriptions = (
            self.owned_event_types & self.subscribed_event_types
        )
        if own_subscriptions:
            raise ValueError(
                f"Engine '{self.engine_name}' declares subscription to "
                f"its own event types: {own_subscriptions}. "
                f"Self-subscription is a special case — use "
                f"allow_self_subscription at registration time."
            )
