"""
BOS Procurement Engine — Request Commands
============================================
Typed procurement requests that convert into canonical Command objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED


# ══════════════════════════════════════════════════════════════
# COMMAND TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

PROCUREMENT_ORDER_CREATE_REQUEST = "procurement.order.create.request"
PROCUREMENT_ORDER_APPROVE_REQUEST = "procurement.order.approve.request"
PROCUREMENT_ORDER_RECEIVE_REQUEST = "procurement.order.receive.request"
PROCUREMENT_ORDER_CANCEL_REQUEST = "procurement.order.cancel.request"
PROCUREMENT_INVOICE_MATCH_REQUEST = "procurement.invoice.match.request"

PROCUREMENT_COMMAND_TYPES = frozenset({
    PROCUREMENT_ORDER_CREATE_REQUEST,
    PROCUREMENT_ORDER_APPROVE_REQUEST,
    PROCUREMENT_ORDER_RECEIVE_REQUEST,
    PROCUREMENT_ORDER_CANCEL_REQUEST,
    PROCUREMENT_INVOICE_MATCH_REQUEST,
})

VALID_CANCEL_REASONS = frozenset({
    "SUPPLIER_UNAVAILABLE", "BUDGET_EXCEEDED", "DUPLICATE_ORDER",
    "BUSINESS_DECISION", "QUALITY_CONCERN",
})


# ══════════════════════════════════════════════════════════════
# REQUEST COMMANDS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OrderCreateRequest:
    """Create a new purchase order."""
    order_id: str
    supplier_id: str
    supplier_name: str
    lines: tuple
    total_amount: int
    currency: str
    expected_delivery: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if not self.supplier_id:
            raise ValueError("supplier_id must be non-empty.")
        if not self.supplier_name:
            raise ValueError("supplier_name must be non-empty.")
        if not isinstance(self.lines, tuple) or len(self.lines) == 0:
            raise ValueError("lines must be non-empty tuple.")
        if not isinstance(self.total_amount, int) or self.total_amount <= 0:
            raise ValueError("total_amount must be positive integer.")
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
            command_type=PROCUREMENT_ORDER_CREATE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "order_id": self.order_id,
                "supplier_id": self.supplier_id,
                "supplier_name": self.supplier_name,
                "lines": list(self.lines),
                "total_amount": self.total_amount,
                "currency": self.currency,
                "expected_delivery": self.expected_delivery,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class OrderApproveRequest:
    """Approve a pending purchase order."""
    order_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")

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
            command_type=PROCUREMENT_ORDER_APPROVE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"order_id": self.order_id},
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class OrderReceiveRequest:
    """Record goods receipt against an approved PO."""
    order_id: str
    received_lines: tuple
    location_id: str
    location_name: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if not isinstance(self.received_lines, tuple) or len(self.received_lines) == 0:
            raise ValueError("received_lines must be non-empty tuple.")
        if not self.location_id:
            raise ValueError("location_id must be non-empty.")

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
            command_type=PROCUREMENT_ORDER_RECEIVE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "order_id": self.order_id,
                "received_lines": list(self.received_lines),
                "location_id": self.location_id,
                "location_name": self.location_name,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class OrderCancelRequest:
    """Cancel a purchase order."""
    order_id: str
    reason: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if self.reason not in VALID_CANCEL_REASONS:
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
            command_type=PROCUREMENT_ORDER_CANCEL_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "order_id": self.order_id,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class InvoiceMatchRequest:
    """Match a supplier invoice to a received PO."""
    invoice_id: str
    order_id: str
    invoice_amount: int
    currency: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.invoice_id:
            raise ValueError("invoice_id must be non-empty.")
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if not isinstance(self.invoice_amount, int) or self.invoice_amount <= 0:
            raise ValueError("invoice_amount must be positive integer.")
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
            command_type=PROCUREMENT_INVOICE_MATCH_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "invoice_id": self.invoice_id,
                "order_id": self.order_id,
                "invoice_amount": self.invoice_amount,
                "currency": self.currency,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )
