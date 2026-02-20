"""
BOS Workshop Engine — Event Types and Payload Builders
========================================================
Engine: Workshop (Job/Repair/Service Management)
"""

from __future__ import annotations

from core.commands.base import Command

WORKSHOP_JOB_CREATED_V1 = "workshop.job.created.v1"
WORKSHOP_JOB_ASSIGNED_V1 = "workshop.job.assigned.v1"
WORKSHOP_JOB_STARTED_V1 = "workshop.job.started.v1"
WORKSHOP_JOB_COMPLETED_V1 = "workshop.job.completed.v1"
WORKSHOP_JOB_INVOICED_V1 = "workshop.job.invoiced.v1"
WORKSHOP_CUTLIST_GENERATED_V1 = "workshop.cutlist.generated.v1"
WORKSHOP_MATERIAL_CONSUMED_V1 = "workshop.material.consumed.v1"
WORKSHOP_OFFCUT_RECORDED_V1 = "workshop.offcut.recorded.v1"

WORKSHOP_EVENT_TYPES = (
    WORKSHOP_JOB_CREATED_V1,
    WORKSHOP_JOB_ASSIGNED_V1,
    WORKSHOP_JOB_STARTED_V1,
    WORKSHOP_JOB_COMPLETED_V1,
    WORKSHOP_JOB_INVOICED_V1,
    WORKSHOP_CUTLIST_GENERATED_V1,
    WORKSHOP_MATERIAL_CONSUMED_V1,
    WORKSHOP_OFFCUT_RECORDED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "workshop.job.create.request": WORKSHOP_JOB_CREATED_V1,
    "workshop.job.assign.request": WORKSHOP_JOB_ASSIGNED_V1,
    "workshop.job.start.request": WORKSHOP_JOB_STARTED_V1,
    "workshop.job.complete.request": WORKSHOP_JOB_COMPLETED_V1,
    "workshop.job.invoice.request": WORKSHOP_JOB_INVOICED_V1,
    "workshop.cutlist.generate.request": WORKSHOP_CUTLIST_GENERATED_V1,
    "workshop.material.consume.request": WORKSHOP_MATERIAL_CONSUMED_V1,
    "workshop.offcut.record.request": WORKSHOP_OFFCUT_RECORDED_V1,
}


def resolve_workshop_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_workshop_event_types(event_type_registry) -> None:
    for et in sorted(WORKSHOP_EVENT_TYPES):
        event_type_registry.register(et)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id, "branch_id": command.branch_id,
        "actor_id": command.actor_id, "actor_type": command.actor_type,
        "correlation_id": command.correlation_id, "command_id": command.command_id,
    }


def build_job_created_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "job_id": command.payload["job_id"],
        "customer_id": command.payload["customer_id"],
        "description": command.payload["description"],
        "estimated_cost": command.payload.get("estimated_cost", 0),
        "currency": command.payload["currency"],
        "created_at": command.issued_at,
    })
    return p


def build_job_assigned_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "job_id": command.payload["job_id"],
        "technician_id": command.payload["technician_id"],
        "assigned_at": command.issued_at,
    })
    return p


def build_job_started_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "job_id": command.payload["job_id"],
        "started_at": command.issued_at,
    })
    return p


def build_job_completed_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "job_id": command.payload["job_id"],
        "parts_used": command.payload.get("parts_used", []),
        "labor_hours": command.payload.get("labor_hours", 0),
        "final_cost": command.payload["final_cost"],
        "currency": command.payload["currency"],
        "completed_at": command.issued_at,
    })
    return p


def build_job_invoiced_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "job_id": command.payload["job_id"],
        "invoice_id": command.payload["invoice_id"],
        "amount": command.payload["amount"],
        "currency": command.payload["currency"],
        "invoiced_at": command.issued_at,
    })
    return p


def build_cutlist_generated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "cutlist_id": command.payload["cutlist_id"],
        "job_id": command.payload["job_id"],
        "style_id": command.payload["style_id"],
        "dimensions": command.payload["dimensions"],
        "unit_quantity": command.payload.get("unit_quantity", 1),
        "pieces": command.payload["pieces"],
        "material_requirements": command.payload["material_requirements"],
        "generated_at": command.issued_at,
    })
    return p


def build_material_consumed_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "consumption_id": command.payload["consumption_id"],
        "job_id": command.payload["job_id"],
        "cutlist_id": command.payload.get("cutlist_id"),
        "material_id": command.payload["material_id"],
        "quantity_used": command.payload["quantity_used"],
        "unit": command.payload["unit"],
        "consumed_at": command.issued_at,
    })
    return p


def build_offcut_recorded_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "offcut_id": command.payload["offcut_id"],
        "job_id": command.payload["job_id"],
        "material_id": command.payload["material_id"],
        "length_mm": command.payload["length_mm"],
        "location_id": command.payload.get("location_id"),
        "recorded_at": command.issued_at,
    })
    return p
