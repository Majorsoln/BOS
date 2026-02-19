"""
BOS Obligation Primitive — Payment / Delivery / Approval Tracking
===================================================================
Engine: Core Primitives (Phase 4)
Authority: BOS Doctrine — Deterministic, Event-Sourced

The Obligation Primitive tracks commitments between parties:
- Payment obligations (invoices, bills payable/receivable)
- Delivery obligations (shipments, fulfillment)
- Approval obligations (sign-offs, authorizations)

Used by: Accounting Engine, Cash Engine, Procurement Engine,
         Retail Engine, Restaurant Engine.

RULES (NON-NEGOTIABLE):
- Obligations are immutable snapshots (state changes via events)
- Amounts in integer minor units (no floats)
- Multi-tenant: scoped to business_id
- Every state transition emits an event
- Partial fulfillment is tracked explicitly
- State derived from events only (replayable)

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

class ObligationType(Enum):
    """Classification of obligation."""
    PAYABLE = "PAYABLE"         # We owe money (vendor invoice)
    RECEIVABLE = "RECEIVABLE"   # They owe us money (customer invoice)
    DELIVERY = "DELIVERY"       # Goods/services to deliver
    APPROVAL = "APPROVAL"       # Requires sign-off


class ObligationStatus(Enum):
    """Obligation lifecycle status."""
    PENDING = "PENDING"           # Created, not yet due
    DUE = "DUE"                   # Due date reached
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"       # Fully satisfied
    OVERDUE = "OVERDUE"           # Past due, not fulfilled
    CANCELLED = "CANCELLED"       # Voided
    DISPUTED = "DISPUTED"         # Under dispute


class FulfillmentType(Enum):
    """How the obligation was fulfilled."""
    PAYMENT_CASH = "PAYMENT_CASH"
    PAYMENT_CARD = "PAYMENT_CARD"
    PAYMENT_BANK = "PAYMENT_BANK"
    PAYMENT_MOBILE = "PAYMENT_MOBILE"
    DELIVERY_COMPLETE = "DELIVERY_COMPLETE"
    DELIVERY_PARTIAL = "DELIVERY_PARTIAL"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    CREDIT_NOTE = "CREDIT_NOTE"
    WRITE_OFF = "WRITE_OFF"


# ══════════════════════════════════════════════════════════════
# FULFILLMENT RECORD
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FulfillmentRecord:
    """
    Record of a single fulfillment action against an obligation.

    Supports partial fulfillment — multiple records can apply
    to a single obligation until it's fully satisfied.
    """
    fulfillment_id: uuid.UUID
    fulfillment_type: FulfillmentType
    amount: Money
    fulfilled_at: datetime
    reference_id: Optional[str] = None
    notes: str = ""

    def __post_init__(self):
        if not isinstance(self.fulfillment_id, uuid.UUID):
            raise ValueError("fulfillment_id must be UUID.")
        if not isinstance(self.fulfillment_type, FulfillmentType):
            raise ValueError("fulfillment_type must be FulfillmentType enum.")
        if not isinstance(self.amount, Money):
            raise TypeError("amount must be Money.")
        if self.amount.amount <= 0:
            raise ValueError("Fulfillment amount must be positive.")

    def to_dict(self) -> dict:
        return {
            "fulfillment_id": str(self.fulfillment_id),
            "fulfillment_type": self.fulfillment_type.value,
            "amount": self.amount.to_dict(),
            "fulfilled_at": self.fulfilled_at.isoformat(),
            "reference_id": self.reference_id,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FulfillmentRecord:
        return cls(
            fulfillment_id=uuid.UUID(data["fulfillment_id"]),
            fulfillment_type=FulfillmentType(data["fulfillment_type"]),
            amount=Money.from_dict(data["amount"]),
            fulfilled_at=datetime.fromisoformat(data["fulfilled_at"]),
            reference_id=data.get("reference_id"),
            notes=data.get("notes", ""),
        )


# ══════════════════════════════════════════════════════════════
# OBLIGATION DEFINITION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ObligationDefinition:
    """
    An obligation — a tracked commitment between parties.

    Fields:
        obligation_id:   Unique identifier
        business_id:     Tenant boundary
        obligation_type: PAYABLE | RECEIVABLE | DELIVERY | APPROVAL
        party_id:        The other party (customer, vendor)
        total_amount:    Total amount owed/expected
        currency:        ISO 4217 currency code
        due_date:        When the obligation is due
        created_at:      When the obligation was created
        status:          Current lifecycle status
        fulfillments:    History of fulfillment actions
        reference_id:    External reference (invoice#, PO#)
        branch_id:       Branch scope
        description:     What this obligation is for
    """
    obligation_id: uuid.UUID
    business_id: uuid.UUID
    obligation_type: ObligationType
    party_id: uuid.UUID
    total_amount: Money
    due_date: datetime
    created_at: datetime
    status: ObligationStatus = ObligationStatus.PENDING
    fulfillments: Tuple[FulfillmentRecord, ...] = ()
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None
    description: str = ""

    def __post_init__(self):
        if not isinstance(self.obligation_id, uuid.UUID):
            raise ValueError("obligation_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.obligation_type, ObligationType):
            raise ValueError("obligation_type must be ObligationType enum.")
        if not isinstance(self.party_id, uuid.UUID):
            raise ValueError("party_id must be UUID.")
        if not isinstance(self.total_amount, Money):
            raise TypeError("total_amount must be Money.")
        if self.total_amount.amount <= 0:
            raise ValueError("total_amount must be positive.")
        if not isinstance(self.fulfillments, tuple):
            raise TypeError("fulfillments must be a tuple.")

    @property
    def amount_fulfilled(self) -> Money:
        """Total amount fulfilled so far."""
        total = sum(f.amount.amount for f in self.fulfillments)
        return Money(amount=total, currency=self.total_amount.currency)

    @property
    def amount_remaining(self) -> Money:
        """Amount still outstanding."""
        remaining = self.total_amount.amount - self.amount_fulfilled.amount
        return Money(
            amount=max(0, remaining),
            currency=self.total_amount.currency,
        )

    @property
    def is_fully_fulfilled(self) -> bool:
        return self.amount_fulfilled.amount >= self.total_amount.amount

    @property
    def is_partially_fulfilled(self) -> bool:
        fulfilled = self.amount_fulfilled.amount
        return 0 < fulfilled < self.total_amount.amount

    @property
    def fulfillment_percentage(self) -> int:
        """Fulfillment percentage (0-100), integer only."""
        if self.total_amount.amount == 0:
            return 100
        return min(
            100,
            (self.amount_fulfilled.amount * 100) // self.total_amount.amount,
        )

    def is_overdue_at(self, at: datetime) -> bool:
        """Check if this obligation is overdue at a given time."""
        return (
            at > self.due_date
            and not self.is_fully_fulfilled
            and self.status not in (
                ObligationStatus.FULFILLED,
                ObligationStatus.CANCELLED,
            )
        )

    def with_fulfillment(
        self, record: FulfillmentRecord
    ) -> ObligationDefinition:
        """
        Create new obligation snapshot with added fulfillment.
        Returns new immutable instance — original unchanged.
        """
        new_fulfillments = self.fulfillments + (record,)
        total_fulfilled = sum(f.amount.amount for f in new_fulfillments)

        if total_fulfilled >= self.total_amount.amount:
            new_status = ObligationStatus.FULFILLED
        elif total_fulfilled > 0:
            new_status = ObligationStatus.PARTIALLY_FULFILLED
        else:
            new_status = self.status

        return ObligationDefinition(
            obligation_id=self.obligation_id,
            business_id=self.business_id,
            obligation_type=self.obligation_type,
            party_id=self.party_id,
            total_amount=self.total_amount,
            due_date=self.due_date,
            created_at=self.created_at,
            status=new_status,
            fulfillments=new_fulfillments,
            reference_id=self.reference_id,
            branch_id=self.branch_id,
            description=self.description,
        )

    def to_dict(self) -> dict:
        return {
            "obligation_id": str(self.obligation_id),
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "obligation_type": self.obligation_type.value,
            "party_id": str(self.party_id),
            "total_amount": self.total_amount.to_dict(),
            "due_date": self.due_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "fulfillments": [f.to_dict() for f in self.fulfillments],
            "reference_id": self.reference_id,
            "description": self.description,
            "amount_fulfilled": self.amount_fulfilled.to_dict(),
            "amount_remaining": self.amount_remaining.to_dict(),
            "fulfillment_percentage": self.fulfillment_percentage,
        }


# ══════════════════════════════════════════════════════════════
# OBLIGATION TRACKER (In-Memory Projection)
# ══════════════════════════════════════════════════════════════

class ObligationTracker:
    """
    In-memory projection tracking obligations and fulfillments.

    Read model — disposable, rebuildable from events.
    """

    def __init__(self, business_id: uuid.UUID):
        self._business_id = business_id
        self._obligations: Dict[uuid.UUID, ObligationDefinition] = {}

    @property
    def business_id(self) -> uuid.UUID:
        return self._business_id

    @property
    def obligation_count(self) -> int:
        return len(self._obligations)

    def apply_obligation(self, obligation: ObligationDefinition) -> None:
        """Register or update an obligation."""
        if obligation.business_id != self._business_id:
            raise ValueError(
                f"Tenant isolation violation: obligation business_id "
                f"{obligation.business_id} != tracker business_id "
                f"{self._business_id}."
            )
        self._obligations[obligation.obligation_id] = obligation

    def apply_fulfillment(
        self,
        obligation_id: uuid.UUID,
        record: FulfillmentRecord,
    ) -> ObligationDefinition:
        """
        Apply fulfillment to an existing obligation.
        Returns the new obligation snapshot.
        """
        existing = self._obligations.get(obligation_id)
        if existing is None:
            raise ValueError(
                f"Obligation {obligation_id} not found in tracker."
            )
        updated = existing.with_fulfillment(record)
        self._obligations[obligation_id] = updated
        return updated

    def get_by_id(
        self, obligation_id: uuid.UUID
    ) -> Optional[ObligationDefinition]:
        return self._obligations.get(obligation_id)

    def list_by_type(
        self, obligation_type: ObligationType
    ) -> List[ObligationDefinition]:
        return [
            o for o in self._obligations.values()
            if o.obligation_type == obligation_type
        ]

    def list_by_status(
        self, status: ObligationStatus
    ) -> List[ObligationDefinition]:
        return [
            o for o in self._obligations.values()
            if o.status == status
        ]

    def list_by_party(
        self, party_id: uuid.UUID
    ) -> List[ObligationDefinition]:
        return [
            o for o in self._obligations.values()
            if o.party_id == party_id
        ]

    def list_overdue_at(self, at: datetime) -> List[ObligationDefinition]:
        return [
            o for o in self._obligations.values()
            if o.is_overdue_at(at)
        ]

    def total_outstanding(
        self, obligation_type: ObligationType, currency: str
    ) -> Money:
        """Total outstanding amount for a given type and currency."""
        total = sum(
            o.amount_remaining.amount
            for o in self._obligations.values()
            if (o.obligation_type == obligation_type
                and o.total_amount.currency == currency
                and o.status not in (
                    ObligationStatus.FULFILLED,
                    ObligationStatus.CANCELLED,
                ))
        )
        return Money(amount=total, currency=currency)
