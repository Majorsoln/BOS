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
from core.context.scope import SCOPE_BUSINESS_ALLOWED, SCOPE_BRANCH_REQUIRED
from core.identity.requirements import ACTOR_REQUIRED


# ══════════════════════════════════════════════════════════════
# COMMAND TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

PROCUREMENT_ORDER_CREATE_REQUEST = "procurement.order.create.request"
PROCUREMENT_ORDER_APPROVE_REQUEST = "procurement.order.approve.request"
PROCUREMENT_ORDER_RECEIVE_REQUEST = "procurement.order.receive.request"
PROCUREMENT_ORDER_CANCEL_REQUEST = "procurement.order.cancel.request"
PROCUREMENT_INVOICE_MATCH_REQUEST = "procurement.invoice.match.request"
PROCUREMENT_REQUISITION_CREATE_REQUEST = "procurement.requisition.create.request"
PROCUREMENT_REQUISITION_APPROVE_REQUEST = "procurement.requisition.approve.request"
PROCUREMENT_PAYMENT_RELEASE_REQUEST = "procurement.payment.release.request"

PROCUREMENT_COMMAND_TYPES = frozenset({
    PROCUREMENT_ORDER_CREATE_REQUEST,
    PROCUREMENT_ORDER_APPROVE_REQUEST,
    PROCUREMENT_ORDER_RECEIVE_REQUEST,
    PROCUREMENT_ORDER_CANCEL_REQUEST,
    PROCUREMENT_INVOICE_MATCH_REQUEST,
    PROCUREMENT_REQUISITION_CREATE_REQUEST,
    PROCUREMENT_REQUISITION_APPROVE_REQUEST,
    PROCUREMENT_PAYMENT_RELEASE_REQUEST,
})

VALID_CANCEL_REASONS = frozenset({
    "SUPPLIER_UNAVAILABLE", "BUDGET_EXCEEDED", "DUPLICATE_ORDER",
    "BUSINESS_DECISION", "QUALITY_CONCERN",
})

VALID_PAYMENT_METHODS = frozenset({
    "CASH", "BANK_TRANSFER", "CHEQUE", "MOBILE",
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
            scope_requirement=SCOPE_BRANCH_REQUIRED,
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


@dataclass(frozen=True)
class RequisitionCreateRequest:
    """Request to create a purchase requisition."""
    requisition_id: str
    lines: tuple
    currency: str
    total_estimated: int = 0
    justification: str = ""
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.requisition_id:
            raise ValueError("requisition_id must be non-empty.")
        if not isinstance(self.lines, tuple) or not self.lines:
            raise ValueError("lines must be a non-empty tuple.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO code.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id, correlation_id, issued_at):
        return Command(
            command_id=command_id,
            command_type=PROCUREMENT_REQUISITION_CREATE_REQUEST,
            business_id=business_id, branch_id=self.branch_id,
            actor_type=actor_type, actor_id=actor_id,
            payload={
                "requisition_id": self.requisition_id,
                "lines": list(self.lines),
                "currency": self.currency,
                "total_estimated": self.total_estimated,
                "justification": self.justification,
            },
            issued_at=issued_at, correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class RequisitionApproveRequest:
    """Request to approve a purchase requisition."""
    requisition_id: str
    notes: str = ""
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.requisition_id:
            raise ValueError("requisition_id must be non-empty.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id, correlation_id, issued_at):
        return Command(
            command_id=command_id,
            command_type=PROCUREMENT_REQUISITION_APPROVE_REQUEST,
            business_id=business_id, branch_id=self.branch_id,
            actor_type=actor_type, actor_id=actor_id,
            payload={
                "requisition_id": self.requisition_id,
                "notes": self.notes,
            },
            issued_at=issued_at, correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class PaymentReleaseRequest:
    """Request to release payment for a received purchase order."""
    payment_id: str
    order_id: str
    amount: int
    currency: str
    payment_method: str
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.payment_id:
            raise ValueError("payment_id must be non-empty.")
        if not self.order_id:
            raise ValueError("order_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO code.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(VALID_PAYMENT_METHODS)}.")

    def to_command(self, *, business_id, actor_type, actor_id,
                   command_id, correlation_id, issued_at):
        return Command(
            command_id=command_id,
            command_type=PROCUREMENT_PAYMENT_RELEASE_REQUEST,
            business_id=business_id, branch_id=self.branch_id,
            actor_type=actor_type, actor_id=actor_id,
            payload={
                "payment_id": self.payment_id,
                "order_id": self.order_id,
                "amount": self.amount,
                "currency": self.currency,
                "payment_method": self.payment_method,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at, correlation_id=correlation_id,
            source_engine="procurement",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )
