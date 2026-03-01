"""
BOS Approval Primitive — Approval Lifecycle Tracking
=====================================================
Phase 4: Business Primitive Layer
Authority: BOS Core Technical Appendix, Procurement HOW, HR HOW

The Approval Primitive tracks sign-off requirements for operations
that require human authorization before execution.

Used by:
    Procurement Engine — PO approval, invoice approval
    HR Engine          — Leave approval, payroll approval
    Workshop Engine    — Quote approval, material write-off
    Cash Engine        — Large adjustment approval
    Inventory Engine   — Stock adjustment approval

RULES (NON-NEGOTIABLE):
- Approvals are immutable (each state change = new snapshot)
- Multi-tenant: scoped to business_id
- AI actors cannot be approvers (NEVER)
- Approvals expire — expired approvals cannot be granted
- Rejected approvals cannot be re-approved (must create new)
- Every state transition is auditable

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

from core.primitives.actor import Actor


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ApprovalStatus(Enum):
    """Lifecycle status of an approval request."""
    PENDING = "PENDING"           # Awaiting review
    APPROVED = "APPROVED"         # Sign-off granted
    REJECTED = "REJECTED"         # Sign-off denied
    EXPIRED = "EXPIRED"           # Approval window closed
    CANCELLED = "CANCELLED"       # Withdrawn before decision


class ApprovalOutcome(Enum):
    """The decision made by an approver."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ══════════════════════════════════════════════════════════════
# APPROVAL DECISION RECORD
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ApprovalDecision:
    """
    A single decision record from one approver.

    An approval may require multiple approvers (multi-level).
    Each decision is recorded immutably.
    """
    decision_id: uuid.UUID
    approver: Actor
    outcome: ApprovalOutcome
    decided_at: datetime
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.decision_id, uuid.UUID):
            raise ValueError("decision_id must be UUID.")
        if not isinstance(self.approver, Actor):
            raise TypeError("approver must be Actor.")
        if self.approver.is_ai:
            raise ValueError("AI actors cannot be approvers.")
        if not isinstance(self.outcome, ApprovalOutcome):
            raise ValueError("outcome must be ApprovalOutcome enum.")
        if not isinstance(self.decided_at, datetime):
            raise TypeError("decided_at must be datetime.")

    def to_dict(self) -> dict:
        return {
            "decision_id": str(self.decision_id),
            "approver": self.approver.to_dict(),
            "outcome": self.outcome.value,
            "decided_at": self.decided_at.isoformat(),
            "reason": self.reason,
        }


# ══════════════════════════════════════════════════════════════
# APPROVAL REQUEST
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ApprovalRequest:
    """
    An approval request for a business operation.

    Fields:
        approval_id:        Unique identifier
        business_id:        Tenant boundary
        subject_type:       What type of thing needs approval (e.g. "PurchaseOrder")
        subject_id:         Identifier of the thing needing approval
        requested_by:       The actor who created the request
        requested_at:       When the request was created
        required_approvers: Set of approver IDs that must approve
        decisions:          History of decisions (immutable)
        status:             Current lifecycle status
        expires_at:         When this approval request expires (None = no expiry)
        branch_id:          Branch scope (optional)
        context:            Additional metadata for the approver's context
    """
    approval_id: uuid.UUID
    business_id: uuid.UUID
    subject_type: str
    subject_id: str
    requested_by: Actor
    requested_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    decisions: Tuple[ApprovalDecision, ...] = ()
    required_approvers: Tuple[str, ...] = ()
    expires_at: Optional[datetime] = None
    branch_id: Optional[uuid.UUID] = None
    context: Optional[dict] = None

    def __post_init__(self):
        if not isinstance(self.approval_id, uuid.UUID):
            raise ValueError("approval_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.subject_type or not isinstance(self.subject_type, str):
            raise ValueError("subject_type must be a non-empty string.")
        if not self.subject_id or not isinstance(self.subject_id, str):
            raise ValueError("subject_id must be a non-empty string.")
        if not isinstance(self.requested_by, Actor):
            raise TypeError("requested_by must be Actor.")
        if not isinstance(self.decisions, tuple):
            raise TypeError("decisions must be a tuple.")

    @property
    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == ApprovalStatus.REJECTED

    @property
    def approved_by(self) -> List[str]:
        return [
            d.approver.actor_id
            for d in self.decisions
            if d.outcome == ApprovalOutcome.APPROVED
        ]

    @property
    def all_required_approved(self) -> bool:
        if not self.required_approvers:
            return len(self.decisions) > 0
        return all(
            approver_id in self.approved_by
            for approver_id in self.required_approvers
        )

    def is_expired_at(self, at: datetime) -> bool:
        if self.expires_at is None:
            return False
        return at > self.expires_at and self.status == ApprovalStatus.PENDING

    def with_decision(self, decision: ApprovalDecision) -> ApprovalRequest:
        """
        Return new snapshot with decision applied.
        Original is unchanged (immutable).
        """
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Cannot add decision to approval in status {self.status.value}."
            )
        new_decisions = self.decisions + (decision,)

        # Determine new status
        if decision.outcome == ApprovalOutcome.REJECTED:
            new_status = ApprovalStatus.REJECTED
        elif self.all_required_approved or (
            not self.required_approvers and len(new_decisions) >= 1
        ):
            new_status = ApprovalStatus.APPROVED
        else:
            new_status = ApprovalStatus.PENDING

        return ApprovalRequest(
            approval_id=self.approval_id,
            business_id=self.business_id,
            subject_type=self.subject_type,
            subject_id=self.subject_id,
            requested_by=self.requested_by,
            requested_at=self.requested_at,
            status=new_status,
            decisions=new_decisions,
            required_approvers=self.required_approvers,
            expires_at=self.expires_at,
            branch_id=self.branch_id,
            context=self.context,
        )

    def to_dict(self) -> dict:
        return {
            "approval_id": str(self.approval_id),
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "requested_by": self.requested_by.to_dict(),
            "requested_at": self.requested_at.isoformat(),
            "status": self.status.value,
            "decisions": [d.to_dict() for d in self.decisions],
            "required_approvers": list(self.required_approvers),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "context": self.context,
        }


# ══════════════════════════════════════════════════════════════
# APPROVAL TRACKER (In-Memory Projection)
# ══════════════════════════════════════════════════════════════

class ApprovalTracker:
    """
    In-memory projection tracking all approval requests for a business.

    Read model — disposable, rebuildable from events.
    """

    def __init__(self, business_id: uuid.UUID):
        self._business_id = business_id
        self._approvals: dict[uuid.UUID, ApprovalRequest] = {}

    def register(self, approval: ApprovalRequest) -> None:
        """Register a new approval request."""
        if approval.business_id != self._business_id:
            raise ValueError("Tenant isolation: approval business_id mismatch.")
        self._approvals[approval.approval_id] = approval

    def apply_decision(
        self, approval_id: uuid.UUID, decision: ApprovalDecision
    ) -> ApprovalRequest:
        """Apply a decision to an existing approval. Returns updated snapshot."""
        existing = self._approvals.get(approval_id)
        if existing is None:
            raise ValueError(f"Approval {approval_id} not found.")
        updated = existing.with_decision(decision)
        self._approvals[approval_id] = updated
        return updated

    def get(self, approval_id: uuid.UUID) -> Optional[ApprovalRequest]:
        return self._approvals.get(approval_id)

    def list_pending(self) -> List[ApprovalRequest]:
        return [a for a in self._approvals.values() if a.is_pending]

    def list_for_subject(self, subject_id: str) -> List[ApprovalRequest]:
        return [a for a in self._approvals.values() if a.subject_id == subject_id]

    @property
    def count(self) -> int:
        return len(self._approvals)
