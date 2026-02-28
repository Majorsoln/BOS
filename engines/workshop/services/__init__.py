"""
BOS Workshop Engine — Application Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.context.scope_guard import enforce_scope_guard
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.workshop.commands import (
    WORKSHOP_COMMAND_TYPES,
    WORKSHOP_QUOTE_GENERATE_REQUEST,
)
from engines.workshop.events import (
    resolve_workshop_event_type, register_workshop_event_types,
    build_job_created_payload, build_job_assigned_payload,
    build_job_started_payload, build_job_completed_payload,
    build_job_invoiced_payload,
    build_cutlist_generated_payload, build_material_consumed_payload,
    build_offcut_recorded_payload,
    build_style_registered_payload, build_style_updated_payload,
    build_style_deactivated_payload, build_quote_generated_payload,
    WORKSHOP_STYLE_REGISTERED_V1, WORKSHOP_STYLE_UPDATED_V1,
    WORKSHOP_STYLE_DEACTIVATED_V1, WORKSHOP_QUOTE_GENERATED_V1,
)
from engines.workshop.formula_engine import (
    StyleDefinition, StyleComponent, ShapeType, Orientation, EndpointType,
    compute_pieces, generate_cut_list,
)
from projections.workshop.style_catalog import StyleCatalogProjection


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
        self._quotes: Dict[str, dict] = {}
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
        elif event_type == WORKSHOP_QUOTE_GENERATED_V1:
            qid = payload["quote_id"]
            self._quotes[qid] = {
                "job_id": payload["job_id"],
                "style_id": payload["style_id"],
                "dimensions": payload["dimensions"],
                "unit_quantity": payload.get("unit_quantity", 1),
                "pieces": payload.get("pieces", []),
                "material_requirements": payload.get("material_requirements", {}),
            }
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid].setdefault("quotes", []).append(qid)

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def get_cutlist(self, cutlist_id: str) -> Optional[dict]:
        return self._cutlists.get(cutlist_id)

    def get_offcut(self, offcut_id: str) -> Optional[dict]:
        return self._offcuts.get(offcut_id)

    def get_quote(self, quote_id: str) -> Optional[dict]:
        return self._quotes.get(quote_id)

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
    "workshop.style.register.request": build_style_registered_payload,
    "workshop.style.update.request": build_style_updated_payload,
    "workshop.style.deactivate.request": build_style_deactivated_payload,
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


def _rebuild_style_definition(record) -> StyleDefinition:
    """Rebuild a StyleDefinition dataclass from a stored StyleRecord."""
    components = []
    for c in record.components:
        components.append(StyleComponent(
            component_id=c["component_id"],
            name=c["name"],
            shape_type=ShapeType(c["shape_type"]),
            material_id=c["material_id"],
            quantity=int(c.get("quantity", 1)),
            formula_length=c.get("formula_length"),
            formula_width=c.get("formula_width"),
            orientation=Orientation(c.get("orientation", "HORIZONTAL")),
            endpoint_type=EndpointType(c.get("endpoint_type", "MM")),
            offcut_mm=int(c.get("offcut_mm", 0)),
        ))
    return StyleDefinition(
        style_id=record.style_id,
        name=record.name,
        components=tuple(components),
        variables=dict(record.variables) if record.variables else None,
    )


def _serialize_pieces(pieces) -> list:
    return [
        {
            "component_id": p.component_id,
            "component_name": p.component_name,
            "material_id": p.material_id,
            "shape_type": p.shape_type.value,
            "length_mm": p.length_mm,
            "width_mm": p.width_mm,
            "quantity": p.quantity,
            "offcut_mm": p.offcut_mm,
        }
        for p in pieces
    ]


def _serialize_material_requirements(reqs: dict) -> dict:
    return {
        mat_id: {
            "material_id": req.material_id,
            "shape_type": req.shape_type.value,
            "total_length_mm": req.total_length_mm,
            "total_area_mm2": req.total_area_mm2,
            "pieces": req.pieces,
            "stock_length_mm": req.stock_length_mm,
            "estimated_sticks": req.estimated_sticks,
            "estimated_sheets": req.estimated_sheets,
            "waste_pct": req.waste_pct,
        }
        for mat_id, req in reqs.items()
    }


class WorkshopService:
    def __init__(self, *, business_context, command_bus,
                 event_factory: EventFactoryProtocol,
                 persist_event: PersistEventProtocol,
                 event_type_registry,
                 projection_store: WorkshopProjectionStore | None = None,
                 style_catalog: StyleCatalogProjection | None = None,
                 feature_flag_provider=None):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or WorkshopProjectionStore()
        self._style_catalog = style_catalog or StyleCatalogProjection()
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
        enforce_scope_guard(command)
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        # Quote generation requires formula computation — handled separately
        if command.command_type == WORKSHOP_QUOTE_GENERATE_REQUEST:
            return self._execute_quote_generation(command)

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
            # Style events are also applied to the style catalog
            if event_type in (WORKSHOP_STYLE_REGISTERED_V1,
                              WORKSHOP_STYLE_UPDATED_V1,
                              WORKSHOP_STYLE_DEACTIVATED_V1):
                self._style_catalog.apply(event_type=event_type, payload=payload)
            applied = True
        return WorkshopExecutionResult(
            event_type=event_type, event_data=event_data,
            persist_result=persist_result, projection_applied=applied)

    def _execute_quote_generation(self, command: Command) -> WorkshopExecutionResult:
        """
        Quote generation path:
        1. Look up the style from the catalog (must be ACTIVE).
        2. Rebuild StyleDefinition from stored component dicts.
        3. Run compute_pieces() + generate_cut_list() via formula engine.
        4. Build the quote event payload with the computed results.
        5. Persist and apply to projection store.
        """
        style_id = command.payload["style_id"]
        style_record = self._style_catalog.get_active_style(style_id)
        if style_record is None:
            raise ValueError(
                f"Style '{style_id}' not found or not active. "
                "Register the style before generating a quote."
            )

        style = _rebuild_style_definition(style_record)
        dimensions = command.payload["dimensions"]
        unit_quantity = int(command.payload.get("unit_quantity", 1))
        stock_lengths = dict(command.payload.get("stock_lengths") or {})

        pieces = compute_pieces(style, dimensions, unit_quantity)
        material_reqs = generate_cut_list(pieces, stock_lengths)

        pieces_data = _serialize_pieces(pieces)
        reqs_data = _serialize_material_requirements(material_reqs)

        payload = build_quote_generated_payload(command, pieces_data, reqs_data)
        event_data = self._event_factory(
            command=command, event_type=WORKSHOP_QUOTE_GENERATED_V1, payload=payload)
        persist_result = self._persist_event(
            event_data=event_data, context=self._business_context,
            registry=self._event_type_registry, scope_requirement=command.scope_requirement)
        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=WORKSHOP_QUOTE_GENERATED_V1, payload=payload)
            applied = True
        return WorkshopExecutionResult(
            event_type=WORKSHOP_QUOTE_GENERATED_V1, event_data=event_data,
            persist_result=persist_result, projection_applied=applied)

    @property
    def projection_store(self) -> WorkshopProjectionStore:
        return self._projection_store

    @property
    def style_catalog(self) -> StyleCatalogProjection:
        return self._style_catalog
