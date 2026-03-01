"""
BOS Retail Engine — Request Commands
=======================================
Typed retail requests that convert into canonical Command objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BRANCH_REQUIRED
from core.identity.requirements import ACTOR_REQUIRED


# ══════════════════════════════════════════════════════════════
# COMMAND TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

RETAIL_SALE_OPEN_REQUEST = "retail.sale.open.request"
RETAIL_SALE_ADD_LINE_REQUEST = "retail.sale.add_line.request"
RETAIL_SALE_REMOVE_LINE_REQUEST = "retail.sale.remove_line.request"
RETAIL_SALE_APPLY_DISCOUNT_REQUEST = "retail.sale.apply_discount.request"
RETAIL_SALE_COMPLETE_REQUEST = "retail.sale.complete.request"
RETAIL_SALE_VOID_REQUEST = "retail.sale.void.request"
RETAIL_REFUND_ISSUE_REQUEST = "retail.refund.issue.request"

RETAIL_COMMAND_TYPES = frozenset({
    RETAIL_SALE_OPEN_REQUEST,
    RETAIL_SALE_ADD_LINE_REQUEST,
    RETAIL_SALE_REMOVE_LINE_REQUEST,
    RETAIL_SALE_APPLY_DISCOUNT_REQUEST,
    RETAIL_SALE_COMPLETE_REQUEST,
    RETAIL_SALE_VOID_REQUEST,
    RETAIL_REFUND_ISSUE_REQUEST,
})

VALID_DISCOUNT_TYPES = frozenset({"PERCENTAGE", "FIXED_AMOUNT"})
VALID_PAYMENT_METHODS = frozenset({
    "CASH", "CARD", "MOBILE", "BANK_TRANSFER", "CREDIT", "SPLIT",
})
VALID_VOID_REASONS = frozenset({
    "CUSTOMER_REQUEST", "CASHIER_ERROR", "SYSTEM_ERROR", "FRAUD_SUSPECT",
})
VALID_REFUND_REASONS = frozenset({
    "DEFECTIVE_PRODUCT", "CUSTOMER_DISSATISFIED", "WRONG_ITEM",
    "OVERCHARGE", "POLICY_RETURN",
})


# ══════════════════════════════════════════════════════════════
# REQUEST COMMANDS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SaleOpenRequest:
    """Open a new sale transaction."""
    sale_id: str
    currency: str
    session_id: Optional[str] = None
    drawer_id: Optional[str] = None
    customer_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

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
            command_type=RETAIL_SALE_OPEN_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "sale_id": self.sale_id,
                "session_id": self.session_id,
                "drawer_id": self.drawer_id,
                "customer_id": self.customer_id,
                "currency": self.currency,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class SaleAddLineRequest:
    """Add a line item to an open sale."""
    sale_id: str
    line_id: str
    item_id: str
    sku: str
    item_name: str
    quantity: int
    unit_price: int
    tax_rate: int = 0
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if not self.line_id:
            raise ValueError("line_id must be non-empty.")
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be positive integer.")
        if not isinstance(self.unit_price, int) or self.unit_price <= 0:
            raise ValueError("unit_price must be positive integer.")

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
            command_type=RETAIL_SALE_ADD_LINE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "sale_id": self.sale_id,
                "line_id": self.line_id,
                "item_id": self.item_id,
                "sku": self.sku,
                "item_name": self.item_name,
                "quantity": self.quantity,
                "unit_price": self.unit_price,
                "tax_rate": self.tax_rate,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class SaleRemoveLineRequest:
    """Remove a line item from an open sale."""
    sale_id: str
    line_id: str
    reason: str = "CUSTOMER_REQUEST"
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if not self.line_id:
            raise ValueError("line_id must be non-empty.")

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
            command_type=RETAIL_SALE_REMOVE_LINE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "sale_id": self.sale_id,
                "line_id": self.line_id,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class SaleApplyDiscountRequest:
    """Apply a discount to an open sale."""
    sale_id: str
    discount_type: str
    discount_value: int
    reason: str = ""
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if self.discount_type not in VALID_DISCOUNT_TYPES:
            raise ValueError(f"discount_type '{self.discount_type}' not valid.")
        if not isinstance(self.discount_value, int) or self.discount_value <= 0:
            raise ValueError("discount_value must be positive integer.")

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
            command_type=RETAIL_SALE_APPLY_DISCOUNT_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "sale_id": self.sale_id,
                "discount_type": self.discount_type,
                "discount_value": self.discount_value,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class SaleCompleteRequest:
    """Complete a sale — triggers stock issue, payment record, journal post."""
    sale_id: str
    total_amount: int
    net_amount: int
    currency: str
    payment_method: str
    lines: tuple
    tax_amount: int = 0
    discount_amount: int = 0
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if not isinstance(self.total_amount, int) or self.total_amount <= 0:
            raise ValueError("total_amount must be positive integer.")
        if not isinstance(self.net_amount, int) or self.net_amount <= 0:
            raise ValueError("net_amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method '{self.payment_method}' not valid.")
        if not isinstance(self.lines, tuple) or len(self.lines) == 0:
            raise ValueError("lines must be non-empty tuple.")

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
            command_type=RETAIL_SALE_COMPLETE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "sale_id": self.sale_id,
                "total_amount": self.total_amount,
                "tax_amount": self.tax_amount,
                "discount_amount": self.discount_amount,
                "net_amount": self.net_amount,
                "currency": self.currency,
                "payment_method": self.payment_method,
                "lines": list(self.lines),
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class SaleVoidRequest:
    """Void a completed sale before end-of-day."""
    sale_id: str
    reason: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if self.reason not in VALID_VOID_REASONS:
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
            command_type=RETAIL_SALE_VOID_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "sale_id": self.sale_id,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class RefundIssueRequest:
    """Issue a refund against a completed sale."""
    refund_id: str
    original_sale_id: str
    amount: int
    currency: str
    reason: str
    lines: tuple = ()
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.refund_id:
            raise ValueError("refund_id must be non-empty.")
        if not self.original_sale_id:
            raise ValueError("original_sale_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if self.reason not in VALID_REFUND_REASONS:
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
            command_type=RETAIL_REFUND_ISSUE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "refund_id": self.refund_id,
                "original_sale_id": self.original_sale_id,
                "amount": self.amount,
                "currency": self.currency,
                "reason": self.reason,
                "lines": list(self.lines),
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="retail",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
            actor_requirement=ACTOR_REQUIRED,
        )
