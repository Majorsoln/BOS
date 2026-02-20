"""
BOS Inventory Movement Primitive — Stock Movement Abstraction
===============================================================
Engine: Core Primitives (Phase 4)
Authority: BOS Doctrine — Deterministic, Event-Sourced

The Inventory Movement Primitive provides the universal stock
movement abstraction used by: Inventory Engine, Retail Engine,
Workshop Engine, Procurement Engine, Restaurant Engine.

RULES (NON-NEGOTIABLE):
- Every stock change is a StockMovement (no hidden mutations)
- Quantities are integers (minor units for fractional items)
- Movement types are explicit (IN, OUT, TRANSFER, ADJUST)
- Location-aware (warehouse, shelf, branch)
- Multi-tenant: scoped to business_id
- State derived from events only (replayable)
- FIFO/LIFO costing is a policy, not embedded in the primitive

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.primitives.ledger import Money


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class MovementType(Enum):
    """Type of inventory movement."""
    RECEIVE = "RECEIVE"         # Stock received (purchase, production)
    ISSUE = "ISSUE"             # Stock issued (sale, consumption)
    TRANSFER = "TRANSFER"       # Between locations
    ADJUST_PLUS = "ADJUST_PLUS"   # Positive adjustment (count correction)
    ADJUST_MINUS = "ADJUST_MINUS" # Negative adjustment (shrinkage, damage)
    RETURN_IN = "RETURN_IN"     # Customer return (stock back in)
    RETURN_OUT = "RETURN_OUT"   # Return to supplier


class MovementReason(Enum):
    """Why the movement happened — for audit trail."""
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    PRODUCTION = "PRODUCTION"
    CONSUMPTION = "CONSUMPTION"
    PHYSICAL_COUNT = "PHYSICAL_COUNT"
    DAMAGE = "DAMAGE"
    EXPIRY = "EXPIRY"
    THEFT = "THEFT"
    INTERNAL_USE = "INTERNAL_USE"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    SUPPLIER_RETURN = "SUPPLIER_RETURN"
    BRANCH_TRANSFER = "BRANCH_TRANSFER"
    INITIAL_STOCK = "INITIAL_STOCK"


# ══════════════════════════════════════════════════════════════
# LOCATION REFERENCE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LocationRef:
    """
    Reference to a stock location.

    Locations are hierarchical: branch → warehouse → zone → bin.
    Only location_id and name are required.
    """
    location_id: uuid.UUID
    name: str
    location_type: str = "WAREHOUSE"

    def __post_init__(self):
        if not isinstance(self.location_id, uuid.UUID):
            raise ValueError("location_id must be UUID.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be non-empty string.")

    def to_dict(self) -> dict:
        return {
            "location_id": str(self.location_id),
            "name": self.name,
            "location_type": self.location_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LocationRef:
        return cls(
            location_id=uuid.UUID(data["location_id"]),
            name=data["name"],
            location_type=data.get("location_type", "WAREHOUSE"),
        )


# ══════════════════════════════════════════════════════════════
# STOCK MOVEMENT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StockMovement:
    """
    Single stock movement record — the atomic unit of inventory change.

    Every change to stock levels is expressed as a StockMovement.
    No hidden mutations — all changes auditable.

    Fields:
        movement_id:    Unique identifier
        business_id:    Tenant boundary
        item_id:        Reference to item
        sku:            SKU for quick reference
        movement_type:  RECEIVE | ISSUE | TRANSFER | ADJUST_*
        reason:         Why this movement happened
        quantity:       Amount moved (always positive)
        unit_cost:      Cost per unit at time of movement (optional)
        location_from:  Source location (required for ISSUE, TRANSFER)
        location_to:    Destination location (required for RECEIVE, TRANSFER)
        occurred_at:    When the movement happened
        reference_id:   External reference (PO number, sale ID, etc.)
        branch_id:      Branch scope
    """
    movement_id: uuid.UUID
    business_id: uuid.UUID
    item_id: uuid.UUID
    sku: str
    movement_type: MovementType
    reason: MovementReason
    quantity: int
    occurred_at: datetime
    unit_cost: Optional[Money] = None
    location_from: Optional[LocationRef] = None
    location_to: Optional[LocationRef] = None
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.movement_id, uuid.UUID):
            raise ValueError("movement_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.item_id, uuid.UUID):
            raise ValueError("item_id must be UUID.")
        if not self.sku or not isinstance(self.sku, str):
            raise ValueError("sku must be non-empty string.")
        if not isinstance(self.movement_type, MovementType):
            raise ValueError("movement_type must be MovementType enum.")
        if not isinstance(self.reason, MovementReason):
            raise ValueError("reason must be MovementReason enum.")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be positive integer.")

        # Validate location requirements per movement type
        if self.movement_type == MovementType.TRANSFER:
            if self.location_from is None or self.location_to is None:
                raise ValueError(
                    "TRANSFER movements require both "
                    "location_from and location_to."
                )
        if self.movement_type in (MovementType.ISSUE,
                                   MovementType.ADJUST_MINUS,
                                   MovementType.RETURN_OUT):
            if self.location_from is None:
                raise ValueError(
                    f"{self.movement_type.value} movements require "
                    f"location_from."
                )
        if self.movement_type in (MovementType.RECEIVE,
                                   MovementType.ADJUST_PLUS,
                                   MovementType.RETURN_IN):
            if self.location_to is None:
                raise ValueError(
                    f"{self.movement_type.value} movements require "
                    f"location_to."
                )

    @property
    def net_quantity_change(self) -> int:
        """
        Net effect on total stock.
        Positive = stock increased, Negative = stock decreased.
        TRANSFER = 0 (moves between locations, net unchanged).
        """
        if self.movement_type in (MovementType.RECEIVE,
                                   MovementType.ADJUST_PLUS,
                                   MovementType.RETURN_IN):
            return self.quantity
        if self.movement_type in (MovementType.ISSUE,
                                   MovementType.ADJUST_MINUS,
                                   MovementType.RETURN_OUT):
            return -self.quantity
        # TRANSFER: net zero at business level
        return 0

    def to_dict(self) -> dict:
        return {
            "movement_id": str(self.movement_id),
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "item_id": str(self.item_id),
            "sku": self.sku,
            "movement_type": self.movement_type.value,
            "reason": self.reason.value,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost.to_dict() if self.unit_cost else None,
            "location_from": (
                self.location_from.to_dict() if self.location_from else None
            ),
            "location_to": (
                self.location_to.to_dict() if self.location_to else None
            ),
            "occurred_at": self.occurred_at.isoformat(),
            "reference_id": self.reference_id,
        }


# ══════════════════════════════════════════════════════════════
# STOCK LEVEL (Projection Primitive)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StockLevel:
    """
    Computed stock level for an item at a location.
    Projection — disposable, rebuildable from movement events.
    """
    item_id: uuid.UUID
    sku: str
    location_id: uuid.UUID
    business_id: uuid.UUID
    quantity_on_hand: int
    total_received: int
    total_issued: int

    @property
    def is_in_stock(self) -> bool:
        return self.quantity_on_hand > 0

    def to_dict(self) -> dict:
        return {
            "item_id": str(self.item_id),
            "sku": self.sku,
            "location_id": str(self.location_id),
            "business_id": str(self.business_id),
            "quantity_on_hand": self.quantity_on_hand,
            "total_received": self.total_received,
            "total_issued": self.total_issued,
        }


# ══════════════════════════════════════════════════════════════
# INVENTORY PROJECTION (In-Memory, Replayable)
# ══════════════════════════════════════════════════════════════

class InventoryProjection:
    """
    In-memory projection that computes stock levels from movements.

    Read model — disposable, rebuildable from events.
    Tracks per-item, per-location quantities.
    """

    def __init__(self, business_id: uuid.UUID):
        self._business_id = business_id
        self._movements: List[StockMovement] = []
        # (item_id, location_id) → {"received": int, "issued": int}
        self._levels: Dict[Tuple[uuid.UUID, uuid.UUID], Dict[str, int]] = {}
        # item_id → sku (for lookup)
        self._sku_map: Dict[uuid.UUID, str] = {}

    @property
    def business_id(self) -> uuid.UUID:
        return self._business_id

    @property
    def movement_count(self) -> int:
        return len(self._movements)

    def apply_movement(self, movement: StockMovement) -> None:
        """Apply a stock movement to update levels."""
        if movement.business_id != self._business_id:
            raise ValueError(
                f"Tenant isolation violation: movement business_id "
                f"{movement.business_id} != projection business_id "
                f"{self._business_id}."
            )

        self._sku_map[movement.item_id] = movement.sku

        # Process outbound (from location)
        if movement.location_from is not None:
            key = (movement.item_id, movement.location_from.location_id)
            if key not in self._levels:
                self._levels[key] = {"received": 0, "issued": 0}
            self._levels[key]["issued"] += movement.quantity

        # Process inbound (to location)
        if movement.location_to is not None:
            key = (movement.item_id, movement.location_to.location_id)
            if key not in self._levels:
                self._levels[key] = {"received": 0, "issued": 0}
            self._levels[key]["received"] += movement.quantity

        self._movements.append(movement)

    def get_stock_level(
        self, item_id: uuid.UUID, location_id: uuid.UUID
    ) -> Optional[StockLevel]:
        """Get stock level for an item at a specific location."""
        key = (item_id, location_id)
        if key not in self._levels:
            return None
        data = self._levels[key]
        return StockLevel(
            item_id=item_id,
            sku=self._sku_map.get(item_id, ""),
            location_id=location_id,
            business_id=self._business_id,
            quantity_on_hand=data["received"] - data["issued"],
            total_received=data["received"],
            total_issued=data["issued"],
        )

    def get_total_stock(self, item_id: uuid.UUID) -> int:
        """Get total stock for an item across all locations."""
        total = 0
        for (iid, _), data in self._levels.items():
            if iid == item_id:
                total += data["received"] - data["issued"]
        return total

    def get_all_levels(self) -> List[StockLevel]:
        """Get all stock levels."""
        result = []
        for (item_id, location_id), data in sorted(self._levels.items()):
            result.append(StockLevel(
                item_id=item_id,
                sku=self._sku_map.get(item_id, ""),
                location_id=location_id,
                business_id=self._business_id,
                quantity_on_hand=data["received"] - data["issued"],
                total_received=data["received"],
                total_issued=data["issued"],
            ))
        return result
