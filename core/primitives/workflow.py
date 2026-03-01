"""
BOS Workflow Primitive — Generic State Machine
==============================================
Phase 4: Business Primitive Layer
Authority: BOS Core Technical Appendix — Command → Outcome → Event

The Workflow Primitive provides a generic, deterministic state machine
used by all engines that track lifecycle state.

Used by:
    Procurement Engine — PO states (DRAFT → APPROVED → RECEIVED → MATCHED)
    Workshop Engine    — Job states (CREATED → ASSIGNED → IN_PROGRESS → DONE → INVOICED)
    Restaurant Engine  — Order item states (CREATED → CONFIRMED → PREPARING → READY → SERVED)
    HR Engine          — Employee states (ACTIVE → TERMINATED), Leave states
    Retail Engine      — Sale states (OPEN → COMPLETED | VOIDED)

RULES (NON-NEGOTIABLE):
- State transitions are deterministic (same input → same output)
- Invalid transitions REJECTED — no silent state skips
- Every transition is logged with actor + timestamp
- State machine definition is immutable (frozen)
- Multi-tenant: workflow instance scoped to business_id

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from core.primitives.actor import Actor


# ══════════════════════════════════════════════════════════════
# TRANSITION RECORD
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StateTransition:
    """
    An immutable record of a single state transition.
    """
    transition_id: uuid.UUID
    from_state: str
    to_state: str
    actor: Actor
    transitioned_at: datetime
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.transition_id, uuid.UUID):
            raise ValueError("transition_id must be UUID.")
        if not self.from_state or not isinstance(self.from_state, str):
            raise ValueError("from_state must be non-empty string.")
        if not self.to_state or not isinstance(self.to_state, str):
            raise ValueError("to_state must be non-empty string.")
        if not isinstance(self.actor, Actor):
            raise TypeError("actor must be Actor.")

    def to_dict(self) -> dict:
        return {
            "transition_id": str(self.transition_id),
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor.to_dict(),
            "transitioned_at": self.transitioned_at.isoformat(),
            "reason": self.reason,
        }


# ══════════════════════════════════════════════════════════════
# WORKFLOW DEFINITION (state machine schema)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class WorkflowDefinition:
    """
    Defines the valid states and transitions for a workflow type.

    This is the STATE MACHINE SCHEMA — shared across all instances
    of a given workflow type (e.g. all PurchaseOrder workflows).

    Fields:
        name:           Identifier for this workflow type (e.g. "PurchaseOrder")
        initial_state:  Starting state for all new instances
        terminal_states: States from which no further transitions are allowed
        transitions:    Dict of {from_state → frozenset(allowed_to_states)}
    """
    name: str
    initial_state: str
    terminal_states: FrozenSet[str]
    transitions: Dict[str, FrozenSet[str]]

    def __post_init__(self):
        if not self.name:
            raise ValueError("Workflow name must be non-empty.")
        if not self.initial_state:
            raise ValueError("initial_state must be non-empty.")
        if self.initial_state not in self.transitions:
            raise ValueError(
                f"initial_state '{self.initial_state}' not in transitions."
            )

    def is_valid_transition(self, from_state: str, to_state: str) -> bool:
        """Check if a transition is allowed by this definition."""
        allowed = self.transitions.get(from_state, frozenset())
        return to_state in allowed

    def is_terminal(self, state: str) -> bool:
        return state in self.terminal_states

    def allowed_next_states(self, from_state: str) -> FrozenSet[str]:
        return self.transitions.get(from_state, frozenset())


# ══════════════════════════════════════════════════════════════
# WORKFLOW INSTANCE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class WorkflowInstance:
    """
    A running instance of a workflow (one per business object).

    Fields:
        instance_id:    Unique identifier for this instance
        business_id:    Tenant boundary
        workflow_name:  Name of the WorkflowDefinition this follows
        subject_id:     The business object this tracks (e.g. PO ID)
        subject_type:   The type of the business object (e.g. "PurchaseOrder")
        current_state:  Current state of this instance
        transitions:    Complete history of state transitions (immutable)
        created_at:     When the instance was created
        branch_id:      Optional branch scope
    """
    instance_id: uuid.UUID
    business_id: uuid.UUID
    workflow_name: str
    subject_id: str
    subject_type: str
    current_state: str
    created_at: datetime
    transitions: Tuple[StateTransition, ...] = ()
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.instance_id, uuid.UUID):
            raise ValueError("instance_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.workflow_name:
            raise ValueError("workflow_name must be non-empty.")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty.")
        if not self.current_state:
            raise ValueError("current_state must be non-empty.")

    def transition(
        self,
        definition: WorkflowDefinition,
        to_state: str,
        actor: Actor,
        at: datetime,
        reason: str = "",
    ) -> WorkflowInstance:
        """
        Return a new instance snapshot with the transition applied.
        Raises ValueError for invalid transitions.
        Original is unchanged (immutable).
        """
        if definition.name != self.workflow_name:
            raise ValueError(
                f"Definition '{definition.name}' does not match "
                f"instance workflow '{self.workflow_name}'."
            )
        if definition.is_terminal(self.current_state):
            raise ValueError(
                f"Cannot transition from terminal state '{self.current_state}'."
            )
        if not definition.is_valid_transition(self.current_state, to_state):
            allowed = sorted(definition.allowed_next_states(self.current_state))
            raise ValueError(
                f"Invalid transition: {self.current_state} → {to_state}. "
                f"Allowed: {allowed}."
            )

        record = StateTransition(
            transition_id=uuid.uuid4(),
            from_state=self.current_state,
            to_state=to_state,
            actor=actor,
            transitioned_at=at,
            reason=reason,
        )

        return WorkflowInstance(
            instance_id=self.instance_id,
            business_id=self.business_id,
            workflow_name=self.workflow_name,
            subject_id=self.subject_id,
            subject_type=self.subject_type,
            current_state=to_state,
            created_at=self.created_at,
            transitions=self.transitions + (record,),
            branch_id=self.branch_id,
        )

    def to_dict(self) -> dict:
        return {
            "instance_id": str(self.instance_id),
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "workflow_name": self.workflow_name,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "current_state": self.current_state,
            "created_at": self.created_at.isoformat(),
            "transitions": [t.to_dict() for t in self.transitions],
        }


# ══════════════════════════════════════════════════════════════
# COMMON WORKFLOW DEFINITIONS (BOS canonical state machines)
# ══════════════════════════════════════════════════════════════

PURCHASE_ORDER_WORKFLOW = WorkflowDefinition(
    name="PurchaseOrder",
    initial_state="DRAFT",
    terminal_states=frozenset({"CANCELLED", "FULLY_MATCHED"}),
    transitions={
        "DRAFT": frozenset({"APPROVED", "CANCELLED"}),
        "APPROVED": frozenset({"RECEIVED", "CANCELLED"}),
        "RECEIVED": frozenset({"INVOICE_MATCHED", "CANCELLED"}),
        "INVOICE_MATCHED": frozenset({"FULLY_MATCHED"}),
        "FULLY_MATCHED": frozenset(),
        "CANCELLED": frozenset(),
    },
)

WORKSHOP_JOB_WORKFLOW = WorkflowDefinition(
    name="WorkshopJob",
    initial_state="CREATED",
    terminal_states=frozenset({"INVOICED", "CANCELLED"}),
    transitions={
        "CREATED": frozenset({"ASSIGNED", "CANCELLED"}),
        "ASSIGNED": frozenset({"IN_PROGRESS", "CANCELLED"}),
        "IN_PROGRESS": frozenset({"COMPLETED", "CANCELLED"}),
        "COMPLETED": frozenset({"INVOICED"}),
        "INVOICED": frozenset(),
        "CANCELLED": frozenset(),
    },
)

RESTAURANT_ORDER_ITEM_WORKFLOW = WorkflowDefinition(
    name="RestaurantOrderItem",
    initial_state="CREATED",
    terminal_states=frozenset({"SERVED", "CANCELLED"}),
    transitions={
        "CREATED": frozenset({"CONFIRMED", "CANCELLED"}),
        "CONFIRMED": frozenset({"IN_PREPARATION", "CANCELLED"}),
        "IN_PREPARATION": frozenset({"READY"}),
        "READY": frozenset({"SERVED"}),
        "SERVED": frozenset(),
        "CANCELLED": frozenset(),
    },
)

LEAVE_REQUEST_WORKFLOW = WorkflowDefinition(
    name="LeaveRequest",
    initial_state="PENDING",
    terminal_states=frozenset({"APPROVED", "REJECTED", "CANCELLED"}),
    transitions={
        "PENDING": frozenset({"APPROVED", "REJECTED", "CANCELLED"}),
        "APPROVED": frozenset(),
        "REJECTED": frozenset(),
        "CANCELLED": frozenset(),
    },
)
