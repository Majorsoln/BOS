"""
BOS Workshop Engine — Application Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.workshop.commands import WORKSHOP_COMMAND_TYPES
from engines.workshop.events import (
    resolve_workshop_event_type, register_workshop_event_types,
    build_job_created_payload, build_job_assigned_payload,
    build_job_started_payload, build_job_completed_payload,
    build_job_invoiced_payload,
    build_cutlist_generated_payload, build_material_consumed_payload,
    build_offcut_recorded_payload,
)


class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...

class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


class WorkshopProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._jobs: Dict[str, dict] = {}
        self._cutlists: Dict[str, dict] = {}
        self._offcuts: Dict[str, dict] = {}
        self._total_revenue: int = 0

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})
        if event_type.startswith("workshop.job.created"):
            self._jobs[payload["job_id"]] = {
                "status": "CREATED", "customer_id": payload["customer_id"],
                "estimated_cost": payload.get("estimated_cost", 0),
                "currency": payload["currency"],
            }
        elif event_type.startswith("workshop.job.assigned"):
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid]["status"] = "ASSIGNED"
                self._jobs[jid]["technician_id"] = payload["technician_id"]
        elif event_type.startswith("workshop.job.started"):
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid]["status"] = "IN_PROGRESS"
        elif event_type.startswith("workshop.job.completed"):
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid]["status"] = "COMPLETED"
                self._jobs[jid]["final_cost"] = payload["final_cost"]
        elif event_type.startswith("workshop.job.invoiced"):
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid]["status"] = "INVOICED"
                self._total_revenue += payload["amount"]
        elif event_type.startswith("workshop.cutlist.generated"):
            clid = payload["cutlist_id"]
            self._cutlists[clid] = {
                "job_id": payload["job_id"],
                "style_id": payload["style_id"],
                "dimensions": payload["dimensions"],
                "unit_quantity": payload.get("unit_quantity", 1),
                "material_requirements": payload["material_requirements"],
            }
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid].setdefault("cutlists", []).append(clid)
        elif event_type.startswith("workshop.material.consumed"):
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid].setdefault("consumed_materials", []).append({
                    "consumption_id": payload["consumption_id"],
                    "material_id": payload["material_id"],
                    "quantity_used": payload["quantity_used"],
                    "unit": payload["unit"],
                })
        elif event_type.startswith("workshop.offcut.recorded"):
            self._offcuts[payload["offcut_id"]] = {
                "job_id": payload["job_id"],
                "material_id": payload["material_id"],
                "length_mm": payload["length_mm"],
                "location_id": payload.get("location_id"),
            }

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def get_cutlist(self, cutlist_id: str) -> Optional[dict]:
        return self._cutlists.get(cutlist_id)

    def get_offcut(self, offcut_id: str) -> Optional[dict]:
        return self._offcuts.get(offcut_id)

    @property
    def total_revenue(self) -> int:
        return self._total_revenue

    @property
    def event_count(self) -> int:
        return len(self._events)


PAYLOAD_BUILDERS = {
    "workshop.job.create.request": build_job_created_payload,
    "workshop.job.assign.request": build_job_assigned_payload,
    "workshop.job.start.request": build_job_started_payload,
    "workshop.job.complete.request": build_job_completed_payload,
    "workshop.job.invoice.request": build_job_invoiced_payload,
    "workshop.cutlist.generate.request": build_cutlist_generated_payload,
    "workshop.material.consume.request": build_material_consumed_payload,
    "workshop.offcut.record.request": build_offcut_recorded_payload,
}


@dataclass(frozen=True)
class WorkshopExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _WorkshopCommandHandler:
    def __init__(self, service: "WorkshopService"):
        self._service = service
    def execute(self, command: Command) -> WorkshopExecutionResult:
        return self._service._execute_command(command)


class WorkshopService:
    def __init__(self, *, business_context, command_bus,
                 event_factory: EventFactoryProtocol,
                 persist_event: PersistEventProtocol,
                 event_type_registry,
                 projection_store: WorkshopProjectionStore | None = None,
                 feature_flag_provider=None):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or WorkshopProjectionStore()
        self._feature_flag_provider = feature_flag_provider
        register_workshop_event_types(self._event_type_registry)
        handler = _WorkshopCommandHandler(self)
        for ct in sorted(WORKSHOP_COMMAND_TYPES):
            self._command_bus.register_handler(ct, handler)

    def _is_persist_accepted(self, r: Any) -> bool:
        if hasattr(r, "accepted"):
            return bool(r.accepted)
        if isinstance(r, dict):
            return bool(r.get("accepted"))
        return bool(r)

    def _execute_command(self, command: Command) -> WorkshopExecutionResult:
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_workshop_event_type(command.command_type)
        if event_type is None:
            raise ValueError(f"Unsupported: {command.command_type}")
        builder = PAYLOAD_BUILDERS[command.command_type]
        payload = builder(command)
        event_data = self._event_factory(command=command, event_type=event_type, payload=payload)
        persist_result = self._persist_event(
            event_data=event_data, context=self._business_context,
            registry=self._event_type_registry, scope_requirement=command.scope_requirement)
        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            applied = True
        return WorkshopExecutionResult(
            event_type=event_type, event_data=event_data,
            persist_result=persist_result, projection_applied=applied)

    @property
    def projection_store(self) -> WorkshopProjectionStore:
        return self._projection_store
