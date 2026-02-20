"""
BOS Workshop Engine — Request Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED

WORKSHOP_JOB_CREATE_REQUEST = "workshop.job.create.request"
WORKSHOP_JOB_ASSIGN_REQUEST = "workshop.job.assign.request"
WORKSHOP_JOB_START_REQUEST = "workshop.job.start.request"
WORKSHOP_JOB_COMPLETE_REQUEST = "workshop.job.complete.request"
WORKSHOP_JOB_INVOICE_REQUEST = "workshop.job.invoice.request"

WORKSHOP_COMMAND_TYPES = frozenset({
    WORKSHOP_JOB_CREATE_REQUEST,
    WORKSHOP_JOB_ASSIGN_REQUEST,
    WORKSHOP_JOB_START_REQUEST,
    WORKSHOP_JOB_COMPLETE_REQUEST,
    WORKSHOP_JOB_INVOICE_REQUEST,
})


def _cmd(ct, payload, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None):
    return Command(
        command_id=command_id, command_type=ct,
        business_id=business_id, branch_id=branch_id,
        actor_type=actor_type, actor_id=actor_id,
        payload=payload, issued_at=issued_at,
        correlation_id=correlation_id, source_engine="workshop",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


@dataclass(frozen=True)
class JobCreateRequest:
    job_id: str
    customer_id: str
    description: str
    currency: str
    estimated_cost: int = 0
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not self.customer_id:
            raise ValueError("customer_id must be non-empty.")
        if not self.description:
            raise ValueError("description must be non-empty.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_JOB_CREATE_REQUEST, {
            "job_id": self.job_id, "customer_id": self.customer_id,
            "description": self.description, "estimated_cost": self.estimated_cost,
            "currency": self.currency,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class JobAssignRequest:
    job_id: str
    technician_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not self.technician_id:
            raise ValueError("technician_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_JOB_ASSIGN_REQUEST, {
            "job_id": self.job_id, "technician_id": self.technician_id,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class JobStartRequest:
    job_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_JOB_START_REQUEST, {
            "job_id": self.job_id,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class JobCompleteRequest:
    job_id: str
    final_cost: int
    currency: str
    parts_used: tuple = ()
    labor_hours: int = 0
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not isinstance(self.final_cost, int) or self.final_cost <= 0:
            raise ValueError("final_cost must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_JOB_COMPLETE_REQUEST, {
            "job_id": self.job_id, "final_cost": self.final_cost,
            "currency": self.currency, "parts_used": list(self.parts_used),
            "labor_hours": self.labor_hours,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class JobInvoiceRequest:
    job_id: str
    invoice_id: str
    amount: int
    currency: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not self.invoice_id:
            raise ValueError("invoice_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_JOB_INVOICE_REQUEST, {
            "job_id": self.job_id, "invoice_id": self.invoice_id,
            "amount": self.amount, "currency": self.currency,
        }, branch_id=self.branch_id, **kw)
