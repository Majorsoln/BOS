"""
BOS Inventory Engine — Request Commands
=========================================
Typed inventory requests that convert into canonical Command objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED, SCOPE_BRANCH_REQUIRED
from core.identity.requirements import ACTOR_REQUIRED


# ══════════════════════════════════════════════════════════════
# COMMAND TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

INVENTORY_STOCK_RECEIVE_REQUEST = "inventory.stock.receive.request"
INVENTORY_STOCK_ISSUE_REQUEST = "inventory.stock.issue.request"
INVENTORY_STOCK_TRANSFER_REQUEST = "inventory.stock.transfer.request"
INVENTORY_STOCK_ADJUST_REQUEST = "inventory.stock.adjust.request"
INVENTORY_ITEM_REGISTER_REQUEST = "inventory.item.register.request"
INVENTORY_ITEM_UPDATE_REQUEST = "inventory.item.update.request"

INVENTORY_COMMAND_TYPES = frozenset({
    INVENTORY_STOCK_RECEIVE_REQUEST,
    INVENTORY_STOCK_ISSUE_REQUEST,
    INVENTORY_STOCK_TRANSFER_REQUEST,
    INVENTORY_STOCK_ADJUST_REQUEST,
    INVENTORY_ITEM_REGISTER_REQUEST,
    INVENTORY_ITEM_UPDATE_REQUEST,
})

VALID_ADJUSTMENT_TYPES = frozenset({"ADJUST_PLUS", "ADJUST_MINUS"})
VALID_RECEIVE_REASONS = frozenset({
    "PURCHASE", "PRODUCTION", "CUSTOMER_RETURN", "INITIAL_STOCK",
})
VALID_ISSUE_REASONS = frozenset({
    "SALE", "CONSUMPTION", "INTERNAL_USE", "SUPPLIER_RETURN",
})
VALID_ADJUST_REASONS = frozenset({
    "PHYSICAL_COUNT", "DAMAGE", "EXPIRY", "THEFT",
})


# ══════════════════════════════════════════════════════════════
# REQUEST COMMANDS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StockReceiveRequest:
    """Request to receive stock into a location."""
    item_id: str
    sku: str
    quantity: int
    location_id: str
    location_name: str
    reason: str = "PURCHASE"
    unit_cost: Optional[dict] = None
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if not self.sku:
            raise ValueError("sku must be non-empty.")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be positive integer.")
        if not self.location_id:
            raise ValueError("location_id must be non-empty.")
        if self.reason not in VALID_RECEIVE_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=INVENTORY_STOCK_RECEIVE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "item_id": self.item_id,
                "sku": self.sku,
                "quantity": self.quantity,
                "location_id": self.location_id,
                "location_name": self.location_name,
                "reason": self.reason,
                "unit_cost": self.unit_cost,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="inventory",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class StockIssueRequest:
    """Request to issue stock from a location."""
    item_id: str
    sku: str
    quantity: int
    location_id: str
    location_name: str
    reason: str = "SALE"
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if not self.sku:
            raise ValueError("sku must be non-empty.")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be positive integer.")
        if not self.location_id:
            raise ValueError("location_id must be non-empty.")
        if self.reason not in VALID_ISSUE_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=INVENTORY_STOCK_ISSUE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "item_id": self.item_id,
                "sku": self.sku,
                "quantity": self.quantity,
                "location_id": self.location_id,
                "location_name": self.location_name,
                "reason": self.reason,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="inventory",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class StockTransferRequest:
    """Request to transfer stock between locations."""
    item_id: str
    sku: str
    quantity: int
    from_location_id: str
    from_location_name: str
    to_location_id: str
    to_location_name: str
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if not self.sku:
            raise ValueError("sku must be non-empty.")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be positive integer.")
        if not self.from_location_id:
            raise ValueError("from_location_id must be non-empty.")
        if not self.to_location_id:
            raise ValueError("to_location_id must be non-empty.")
        if self.from_location_id == self.to_location_id:
            raise ValueError("Cannot transfer to the same location.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=INVENTORY_STOCK_TRANSFER_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "item_id": self.item_id,
                "sku": self.sku,
                "quantity": self.quantity,
                "from_location_id": self.from_location_id,
                "from_location_name": self.from_location_name,
                "to_location_id": self.to_location_id,
                "to_location_name": self.to_location_name,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="inventory",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class StockAdjustRequest:
    """Request to adjust stock (physical count correction)."""
    item_id: str
    sku: str
    quantity: int
    adjustment_type: str
    location_id: str
    location_name: str
    reason: str
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if not self.sku:
            raise ValueError("sku must be non-empty.")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be positive integer.")
        if self.adjustment_type not in VALID_ADJUSTMENT_TYPES:
            raise ValueError(f"adjustment_type '{self.adjustment_type}' not valid.")
        if not self.location_id:
            raise ValueError("location_id must be non-empty.")
        if self.reason not in VALID_ADJUST_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=INVENTORY_STOCK_ADJUST_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "item_id": self.item_id,
                "sku": self.sku,
                "quantity": self.quantity,
                "adjustment_type": self.adjustment_type,
                "location_id": self.location_id,
                "location_name": self.location_name,
                "reason": self.reason,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="inventory",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class ItemRegisterRequest:
    """Request to register a new item in the catalog."""
    item_id: str
    sku: str
    name: str
    item_type: str
    unit_of_measure: str
    prices: tuple = ()
    tax_category: Optional[dict] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if not self.sku:
            raise ValueError("sku must be non-empty.")
        if not self.name:
            raise ValueError("name must be non-empty.")
        if not self.item_type:
            raise ValueError("item_type must be non-empty.")
        if not self.unit_of_measure:
            raise ValueError("unit_of_measure must be non-empty.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=INVENTORY_ITEM_REGISTER_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "item_id": self.item_id,
                "sku": self.sku,
                "name": self.name,
                "item_type": self.item_type,
                "unit_of_measure": self.unit_of_measure,
                "prices": list(self.prices),
                "tax_category": self.tax_category,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="inventory",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )
