"""
BOS Workshop Engine — Request Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED, SCOPE_BRANCH_REQUIRED
from core.identity.requirements import ACTOR_REQUIRED

WORKSHOP_JOB_CREATE_REQUEST = "workshop.job.create.request"
WORKSHOP_JOB_ASSIGN_REQUEST = "workshop.job.assign.request"
WORKSHOP_JOB_START_REQUEST = "workshop.job.start.request"
WORKSHOP_JOB_COMPLETE_REQUEST = "workshop.job.complete.request"
WORKSHOP_JOB_INVOICE_REQUEST = "workshop.job.invoice.request"
WORKSHOP_CUTLIST_GENERATE_REQUEST = "workshop.cutlist.generate.request"
WORKSHOP_MATERIAL_CONSUME_REQUEST = "workshop.material.consume.request"
WORKSHOP_OFFCUT_RECORD_REQUEST = "workshop.offcut.record.request"

WORKSHOP_COMMAND_TYPES = frozenset({
    WORKSHOP_JOB_CREATE_REQUEST,
    WORKSHOP_JOB_ASSIGN_REQUEST,
    WORKSHOP_JOB_START_REQUEST,
    WORKSHOP_JOB_COMPLETE_REQUEST,
    WORKSHOP_JOB_INVOICE_REQUEST,
    WORKSHOP_CUTLIST_GENERATE_REQUEST,
    WORKSHOP_MATERIAL_CONSUME_REQUEST,
    WORKSHOP_OFFCUT_RECORD_REQUEST,
})

VALID_MATERIAL_UNITS = frozenset({"MM", "M", "SQM", "SHT", "PC", "KG"})


def _cmd(ct, payload, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None,
         scope=SCOPE_BUSINESS_ALLOWED):
    return Command(
        command_id=command_id, command_type=ct,
        business_id=business_id, branch_id=branch_id,
        actor_type=actor_type, actor_id=actor_id,
        payload=payload, issued_at=issued_at,
        correlation_id=correlation_id, source_engine="workshop",
        scope_requirement=scope,
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
        }, branch_id=self.branch_id, scope=SCOPE_BRANCH_REQUIRED, **kw)


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
        }, branch_id=self.branch_id, scope=SCOPE_BRANCH_REQUIRED, **kw)


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


@dataclass(frozen=True)
class GenerateCutListRequest:
    """Generate a cut list from a style definition for a job."""
    cutlist_id: str
    job_id: str
    style_id: str
    dimensions: dict  # {"W": int, "H": int, ...}
    pieces: list      # computed piece list (from formula_engine.compute_pieces)
    material_requirements: dict  # from formula_engine.generate_cut_list
    unit_quantity: int = 1
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.cutlist_id:
            raise ValueError("cutlist_id must be non-empty.")
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not self.style_id:
            raise ValueError("style_id must be non-empty.")
        if not isinstance(self.dimensions, dict) or not self.dimensions:
            raise ValueError("dimensions must be a non-empty dict.")
        if not isinstance(self.unit_quantity, int) or self.unit_quantity <= 0:
            raise ValueError("unit_quantity must be a positive integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_CUTLIST_GENERATE_REQUEST, {
            "cutlist_id": self.cutlist_id,
            "job_id": self.job_id,
            "style_id": self.style_id,
            "dimensions": self.dimensions,
            "unit_quantity": self.unit_quantity,
            "pieces": self.pieces,
            "material_requirements": self.material_requirements,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class MaterialConsumeRequest:
    """Record consumption of material stock against a job."""
    consumption_id: str
    job_id: str
    material_id: str
    quantity_used: int
    unit: str
    cutlist_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.consumption_id:
            raise ValueError("consumption_id must be non-empty.")
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not self.material_id:
            raise ValueError("material_id must be non-empty.")
        if not isinstance(self.quantity_used, int) or self.quantity_used <= 0:
            raise ValueError("quantity_used must be a positive integer.")
        if self.unit not in VALID_MATERIAL_UNITS:
            raise ValueError(f"unit must be one of {sorted(VALID_MATERIAL_UNITS)}.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_MATERIAL_CONSUME_REQUEST, {
            "consumption_id": self.consumption_id,
            "job_id": self.job_id,
            "material_id": self.material_id,
            "quantity_used": self.quantity_used,
            "unit": self.unit,
            "cutlist_id": self.cutlist_id,
        }, branch_id=self.branch_id, scope=SCOPE_BRANCH_REQUIRED, **kw)


@dataclass(frozen=True)
class OffcutRecordRequest:
    """Record a usable offcut piece returned to stock after cutting."""
    offcut_id: str
    job_id: str
    material_id: str
    length_mm: int
    location_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.offcut_id:
            raise ValueError("offcut_id must be non-empty.")
        if not self.job_id:
            raise ValueError("job_id must be non-empty.")
        if not self.material_id:
            raise ValueError("material_id must be non-empty.")
        if not isinstance(self.length_mm, int) or self.length_mm <= 0:
            raise ValueError("length_mm must be a positive integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(WORKSHOP_OFFCUT_RECORD_REQUEST, {
            "offcut_id": self.offcut_id,
            "job_id": self.job_id,
            "material_id": self.material_id,
            "length_mm": self.length_mm,
            "location_id": self.location_id,
        }, branch_id=self.branch_id, scope=SCOPE_BRANCH_REQUIRED, **kw)
