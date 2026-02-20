"""
BOS Restaurant Engine — Request Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED

RESTAURANT_TABLE_OPEN_REQUEST = "restaurant.table.open.request"
RESTAURANT_TABLE_CLOSE_REQUEST = "restaurant.table.close.request"
RESTAURANT_ORDER_PLACE_REQUEST = "restaurant.order.place.request"
RESTAURANT_ORDER_SERVE_ITEM_REQUEST = "restaurant.order.serve_item.request"
RESTAURANT_ORDER_CANCEL_REQUEST = "restaurant.order.cancel.request"
RESTAURANT_BILL_SETTLE_REQUEST = "restaurant.bill.settle.request"

RESTAURANT_COMMAND_TYPES = frozenset({
    RESTAURANT_TABLE_OPEN_REQUEST,
    RESTAURANT_TABLE_CLOSE_REQUEST,
    RESTAURANT_ORDER_PLACE_REQUEST,
    RESTAURANT_ORDER_SERVE_ITEM_REQUEST,
    RESTAURANT_ORDER_CANCEL_REQUEST,
    RESTAURANT_BILL_SETTLE_REQUEST,
})

VALID_PAYMENT_METHODS = frozenset({"CASH", "CARD", "MOBILE", "SPLIT"})
VALID_CANCEL_REASONS = frozenset({
    "CUSTOMER_REQUEST", "KITCHEN_UNAVAILABLE", "WRONG_ORDER", "LONG_WAIT",
})


def _cmd(command_type, payload, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None):
    return Command(
        command_id=command_id, command_type=command_type,
        business_id=business_id, branch_id=branch_id,
        actor_type=actor_type, actor_id=actor_id,
        payload=payload, issued_at=issued_at,
        correlation_id=correlation_id, source_engine="restaurant",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


@dataclass(frozen=True)
class TableOpenRequest:
    table_id: str
    table_name: str
    covers: int
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.table_id:
            raise ValueError("table_id must be non-empty.")
        if not self.table_name:
            raise ValueError("table_name must be non-empty.")
        if not isinstance(self.covers, int) or self.covers <= 0:
            raise ValueError("covers must be positive integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(RESTAURANT_TABLE_OPEN_REQUEST,
                     {"table_id": self.table_id, "table_name": self.table_name,
                      "covers": self.covers},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class TableCloseRequest:
    table_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.table_id:
            raise ValueError("table_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(RESTAURANT_TABLE_CLOSE_REQUEST,
                     {"table_id": self.table_id},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class OrderPlaceRequest:
    order_id: str
    table_id: str
    items: tuple
    currency: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if not self.table_id:
            raise ValueError("table_id must be non-empty.")
        if not isinstance(self.items, tuple) or len(self.items) == 0:
            raise ValueError("items must be non-empty tuple.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    def to_command(self, **kw) -> Command:
        return _cmd(RESTAURANT_ORDER_PLACE_REQUEST,
                     {"order_id": self.order_id, "table_id": self.table_id,
                      "items": list(self.items), "currency": self.currency},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class OrderServeItemRequest:
    order_id: str
    item_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(RESTAURANT_ORDER_SERVE_ITEM_REQUEST,
                     {"order_id": self.order_id, "item_id": self.item_id},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class OrderCancelRequest:
    order_id: str
    reason: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if self.reason not in VALID_CANCEL_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(self, **kw) -> Command:
        return _cmd(RESTAURANT_ORDER_CANCEL_REQUEST,
                     {"order_id": self.order_id, "reason": self.reason},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class BillSettleRequest:
    bill_id: str
    table_id: str
    total_amount: int
    currency: str
    payment_method: str
    tip_amount: int = 0
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.bill_id:
            raise ValueError("bill_id must be non-empty.")
        if not self.table_id:
            raise ValueError("table_id must be non-empty.")
        if not isinstance(self.total_amount, int) or self.total_amount <= 0:
            raise ValueError("total_amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method '{self.payment_method}' not valid.")
        if not isinstance(self.tip_amount, int) or self.tip_amount < 0:
            raise ValueError("tip_amount must be non-negative integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(RESTAURANT_BILL_SETTLE_REQUEST,
                     {"bill_id": self.bill_id, "table_id": self.table_id,
                      "total_amount": self.total_amount, "tip_amount": self.tip_amount,
                      "currency": self.currency, "payment_method": self.payment_method},
                     branch_id=self.branch_id, **kw)
