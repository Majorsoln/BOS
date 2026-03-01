"""
BOS Item Primitive — Catalog Item / Product / Service Definition
=================================================================
Engine: Core Primitives (Phase 4)
Authority: BOS Doctrine — Deterministic, Event-Sourced

The Item Primitive provides a universal product/service abstraction
used by: Retail Engine, Restaurant Engine, Workshop Engine,
         Inventory Engine, Procurement Engine.

RULES (NON-NEGOTIABLE):
- Items are immutable snapshots (versioned)
- Prices in integer minor units (no floats)
- SKU uniqueness scoped to business_id
- Unit of measure is explicit
- Tax category is a reference, not embedded logic
- No country-specific logic — tax rules are data-driven

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.primitives.ledger import Money


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ItemType(Enum):
    """Classification of catalog items."""
    PRODUCT = "PRODUCT"       # Physical goods
    SERVICE = "SERVICE"       # Intangible services
    MATERIAL = "MATERIAL"     # Raw materials / components
    COMPOSITE = "COMPOSITE"   # Bundle / kit of other items


class UnitOfMeasure(Enum):
    """Standard units of measure for items."""
    PIECE = "PIECE"
    KG = "KG"
    GRAM = "GRAM"
    LITER = "LITER"
    METER = "METER"
    SQ_METER = "SQ_METER"
    CUBIC_METER = "CUBIC_METER"
    HOUR = "HOUR"
    PACK = "PACK"
    BOX = "BOX"
    SHEET = "SHEET"
    LENGTH = "LENGTH"


class ItemStatus(Enum):
    """Item lifecycle status."""
    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"
    DRAFT = "DRAFT"


class PriceType(Enum):
    """Type of price entry."""
    SELLING = "SELLING"
    COST = "COST"
    WHOLESALE = "WHOLESALE"


# ══════════════════════════════════════════════════════════════
# PRICE ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PriceEntry:
    """
    A single price point for an item.

    Prices are versioned — when a price changes, a new PriceEntry
    is created (old one remains in event history).

    amount is in minor units (cents).
    """
    price_type: PriceType
    amount: Money
    effective_from: datetime
    effective_until: Optional[datetime] = None
    min_quantity: int = 1

    def __post_init__(self):
        if not isinstance(self.price_type, PriceType):
            raise ValueError("price_type must be PriceType enum.")
        if not isinstance(self.amount, Money):
            raise TypeError("amount must be Money.")
        if self.amount.amount < 0:
            raise ValueError("Price amount cannot be negative.")
        if self.min_quantity < 1:
            raise ValueError("min_quantity must be >= 1.")
        if (self.effective_until is not None
                and self.effective_until <= self.effective_from):
            raise ValueError("effective_until must be after effective_from.")

    def is_active_at(self, at: datetime) -> bool:
        """Check if this price is active at a given time."""
        if at < self.effective_from:
            return False
        if self.effective_until is not None and at >= self.effective_until:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "price_type": self.price_type.value,
            "amount": self.amount.to_dict(),
            "effective_from": self.effective_from.isoformat(),
            "effective_until": (
                self.effective_until.isoformat()
                if self.effective_until else None
            ),
            "min_quantity": self.min_quantity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PriceEntry:
        return cls(
            price_type=PriceType(data["price_type"]),
            amount=Money.from_dict(data["amount"]),
            effective_from=datetime.fromisoformat(data["effective_from"]),
            effective_until=(
                datetime.fromisoformat(data["effective_until"])
                if data.get("effective_until") else None
            ),
            min_quantity=data.get("min_quantity", 1),
        )


# ══════════════════════════════════════════════════════════════
# TAX CATEGORY REFERENCE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxCategoryRef:
    """
    Reference to a tax category (not the tax logic itself).

    Tax rules are resolved by the compliance/policy layer at
    transaction time — never hardcoded on the item.
    """
    category_code: str
    name: str

    def __post_init__(self):
        if not self.category_code or not isinstance(self.category_code, str):
            raise ValueError("category_code must be non-empty string.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be non-empty string.")

    def to_dict(self) -> dict:
        return {
            "category_code": self.category_code,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaxCategoryRef:
        return cls(
            category_code=data["category_code"],
            name=data["name"],
        )


# ══════════════════════════════════════════════════════════════
# ITEM DEFINITION (Immutable Snapshot)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ItemDefinition:
    """
    Canonical item definition — an immutable versioned snapshot.

    When an item changes, a new ItemDefinition is created with
    an incremented version. The old version lives in event history.

    Fields:
        item_id:        Unique identifier
        business_id:    Tenant boundary
        sku:            Stock Keeping Unit (unique per business)
        name:           Display name
        item_type:      PRODUCT | SERVICE | MATERIAL | COMPOSITE
        unit_of_measure: How the item is measured/sold
        tax_category:   Reference to tax category
        prices:         Tuple of price entries
        version:        Schema version (increments on change)
        status:         ACTIVE | DISCONTINUED | DRAFT
        attributes:     Extensible key-value attributes
    """
    item_id: uuid.UUID
    business_id: uuid.UUID
    sku: str
    name: str
    item_type: ItemType
    unit_of_measure: UnitOfMeasure
    version: int
    status: ItemStatus = ItemStatus.ACTIVE
    tax_category: Optional[TaxCategoryRef] = None
    prices: Tuple[PriceEntry, ...] = ()
    description: str = ""
    attributes: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.item_id, uuid.UUID):
            raise ValueError("item_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.sku or not isinstance(self.sku, str):
            raise ValueError("sku must be non-empty string.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be non-empty string.")
        if not isinstance(self.item_type, ItemType):
            raise ValueError("item_type must be ItemType enum.")
        if not isinstance(self.unit_of_measure, UnitOfMeasure):
            raise ValueError("unit_of_measure must be UnitOfMeasure enum.")
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be positive integer.")
        if not isinstance(self.prices, tuple):
            raise TypeError("prices must be a tuple of PriceEntry.")

    def get_active_price(
        self,
        price_type: PriceType,
        at: datetime,
        quantity: int = 1,
    ) -> Optional[PriceEntry]:
        """
        Resolve the active price for a given type, time, and quantity.
        Returns the most specific matching price (highest min_quantity
        that is <= quantity).
        """
        candidates = [
            p for p in self.prices
            if (p.price_type == price_type
                and p.is_active_at(at)
                and p.min_quantity <= quantity)
        ]
        if not candidates:
            return None
        # Most specific: highest min_quantity that qualifies
        return max(candidates, key=lambda p: p.min_quantity)

    def to_dict(self) -> dict:
        return {
            "item_id": str(self.item_id),
            "business_id": str(self.business_id),
            "sku": self.sku,
            "name": self.name,
            "item_type": self.item_type.value,
            "unit_of_measure": self.unit_of_measure.value,
            "version": self.version,
            "status": self.status.value,
            "tax_category": (
                self.tax_category.to_dict() if self.tax_category else None
            ),
            "prices": [p.to_dict() for p in self.prices],
            "description": self.description,
            "attributes": dict(self.attributes),
        }


# ══════════════════════════════════════════════════════════════
# ITEM CATALOG (In-Memory Projection)
# ══════════════════════════════════════════════════════════════

class ItemCatalog:
    """
    In-memory projection of item definitions.

    Read model — disposable, rebuildable from events.
    Provides lookup by item_id and sku.
    """

    def __init__(self, business_id: uuid.UUID):
        self._business_id = business_id
        # item_id → ItemDefinition
        self._items: Dict[uuid.UUID, ItemDefinition] = {}
        # sku → item_id
        self._sku_index: Dict[str, uuid.UUID] = {}

    @property
    def business_id(self) -> uuid.UUID:
        return self._business_id

    @property
    def item_count(self) -> int:
        return len(self._items)

    def apply_item(self, item: ItemDefinition) -> None:
        """Register or update an item in the catalog."""
        if item.business_id != self._business_id:
            raise ValueError(
                f"Tenant isolation violation: item business_id "
                f"{item.business_id} != catalog business_id "
                f"{self._business_id}."
            )

        # Check SKU uniqueness (different item_id with same SKU)
        existing_id = self._sku_index.get(item.sku)
        if existing_id is not None and existing_id != item.item_id:
            raise ValueError(
                f"SKU '{item.sku}' already assigned to item "
                f"{existing_id}. SKU must be unique per business."
            )

        self._items[item.item_id] = item
        self._sku_index[item.sku] = item.item_id

    def get_by_id(self, item_id: uuid.UUID) -> Optional[ItemDefinition]:
        return self._items.get(item_id)

    def get_by_sku(self, sku: str) -> Optional[ItemDefinition]:
        item_id = self._sku_index.get(sku)
        if item_id is None:
            return None
        return self._items.get(item_id)

    def list_active(self) -> List[ItemDefinition]:
        return [
            item for item in self._items.values()
            if item.status == ItemStatus.ACTIVE
        ]
