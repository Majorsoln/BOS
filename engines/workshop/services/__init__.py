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
    WORKSHOP_PROJECT_QUOTE_REQUEST,
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
    build_project_quote_payload,
    WORKSHOP_STYLE_REGISTERED_V1, WORKSHOP_STYLE_UPDATED_V1,
    WORKSHOP_STYLE_DEACTIVATED_V1, WORKSHOP_QUOTE_GENERATED_V1,
    WORKSHOP_PROJECT_QUOTE_GENERATED_V1,
)
from engines.workshop.formula_engine import (
    StyleDefinition, StyleComponent, ShapeType, Orientation, EndpointType,
    compute_pieces, generate_cut_list,
    # Phase 17
    ProjectItem, LabeledPiece, CuttingPlan,
    compute_project_pieces, generate_project_cutting_plan,
    compute_charge_rate_based, compute_charge_cost_based,
    ChargeMethod,
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
        self._project_quotes: Dict[str, dict] = {}
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
        elif event_type == WORKSHOP_PROJECT_QUOTE_GENERATED_V1:
            pqid = payload["project_quote_id"]
            self._project_quotes[pqid] = {
                "job_id": payload["job_id"],
                "items": payload["items"],
                "charge_method": payload["charge_method"],
                "currency": payload["currency"],
                "total_cost": payload["total_cost"],
                "cutting_plans": payload.get("cutting_plans", {}),
                "labeled_pieces": payload.get("labeled_pieces", []),
            }
            jid = payload["job_id"]
            if jid in self._jobs:
                self._jobs[jid].setdefault("project_quotes", []).append(pqid)

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def get_cutlist(self, cutlist_id: str) -> Optional[dict]:
        return self._cutlists.get(cutlist_id)

    def get_offcut(self, offcut_id: str) -> Optional[dict]:
        return self._offcuts.get(offcut_id)

    def get_quote(self, quote_id: str) -> Optional[dict]:
        return self._quotes.get(quote_id)

    def get_project_quote(self, project_quote_id: str) -> Optional[dict]:
        return self._project_quotes.get(project_quote_id)

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


def _serialize_labeled_pieces(pieces: List[LabeledPiece]) -> list:
    return [
        {
            "item_id": p.item_id,
            "item_label": p.item_label,
            "component_id": p.component_id,
            "component_name": p.component_name,
            "material_id": p.material_id,
            "shape_type": p.shape_type.value,
            "length_mm": p.length_mm,
            "width_mm": p.width_mm,
            "offcut_mm": p.offcut_mm,
        }
        for p in pieces
    ]


def _serialize_cutting_plans(plans: Dict[str, CuttingPlan]) -> dict:
    result = {}
    for mat_id, plan in plans.items():
        bars_data = []
        for bar in plan.bars:
            allocs_data = [
                {
                    "item_id": a.item_id,
                    "item_label": a.item_label,
                    "component_id": a.component_id,
                    "component_name": a.component_name,
                    "length_mm": a.length_mm,
                    "offcut_mm": a.offcut_mm,
                    "position_mm": a.position_mm,
                }
                for a in bar.allocations
            ]
            bars_data.append({
                "bar_index": bar.bar_index,
                "stock_length_mm": bar.stock_length_mm,
                "allocations": allocs_data,
                "waste_mm": bar.waste_mm,
            })
        result[mat_id] = {
            "material_id": plan.material_id,
            "shape_type": plan.shape_type.value,
            "stock_length_mm": plan.stock_length_mm,
            "bars": bars_data,
            "total_pieces": plan.total_pieces,
            "total_waste_mm": plan.total_waste_mm,
            "waste_pct": plan.waste_pct,
        }
    return result


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

        # Quote generation and project quotes require formula computation
        if command.command_type == WORKSHOP_QUOTE_GENERATE_REQUEST:
            return self._execute_quote_generation(command)
        if command.command_type == WORKSHOP_PROJECT_QUOTE_REQUEST:
            return self._execute_project_quote(command)

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

    def _execute_project_quote(self, command: Command) -> "WorkshopExecutionResult":
        """
        Project quote generation path (Phase 17):

        1. For each item (in order), look up its style from the catalog
           (must be ACTIVE). Assign ItemID = 1..N from input order.
        2. Build List[ProjectItem].
        3. compute_project_pieces() → List[LabeledPiece] (one per physical cut).
        4. generate_project_cutting_plan() → BFD cutting plans per material.
        5. Compute total charge (RATE_BASED or COST_BASED).
        6. Build WORKSHOP_PROJECT_QUOTE_GENERATED_V1 event, persist, apply.
        """
        raw_items = command.payload["items"]
        charge_method = command.payload["charge_method"]
        stock_lengths = dict(command.payload.get("stock_lengths") or {})
        rates = dict(command.payload.get("rates") or {})

        # Build ProjectItem list, resolving each style from catalog
        project_items: List[ProjectItem] = []
        for seq, raw in enumerate(raw_items, start=1):
            style_id = raw["style_id"]
            style_record = self._style_catalog.get_active_style(style_id)
            if style_record is None:
                raise ValueError(
                    f"Item {seq}: Style '{style_id}' not found or not active. "
                    "Register and activate the style before generating a project quote."
                )
            style = _rebuild_style_definition(style_record)
            label = raw.get("label") or f"Item {seq}"
            project_items.append(ProjectItem(
                item_id=seq,
                item_label=label,
                style=style,
                dimensions=dict(raw["dimensions"]),
                unit_quantity=int(raw.get("unit_quantity", 1)),
            ))

        # Expand all items into individual labeled pieces (one per physical cut)
        labeled_pieces = compute_project_pieces(project_items)

        # Run BFD cutting plan across the whole project
        cutting_plans = generate_project_cutting_plan(labeled_pieces, stock_lengths)

        # Compute charge
        if charge_method == ChargeMethod.RATE_BASED.value:
            total_cost = compute_charge_rate_based(project_items, rates)
        else:
            # COST_BASED: "LABOR" is a special key for flat labor cost
            labor_cost = int(rates.get("LABOR", 0))
            material_rates = {k: v for k, v in rates.items() if k != "LABOR"}
            total_cost = compute_charge_cost_based(cutting_plans, material_rates, labor_cost)

        # Serialize for event payload
        pieces_data = _serialize_labeled_pieces(labeled_pieces)
        plans_data = _serialize_cutting_plans(cutting_plans)

        payload = build_project_quote_payload(command, pieces_data, plans_data, total_cost)
        event_data = self._event_factory(
            command=command,
            event_type=WORKSHOP_PROJECT_QUOTE_GENERATED_V1,
            payload=payload,
        )
        persist_result = self._persist_event(
            event_data=event_data,
            context=self._business_context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )
        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(
                event_type=WORKSHOP_PROJECT_QUOTE_GENERATED_V1, payload=payload
            )
            applied = True
        return WorkshopExecutionResult(
            event_type=WORKSHOP_PROJECT_QUOTE_GENERATED_V1,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    @property
    def projection_store(self) -> WorkshopProjectionStore:
        return self._projection_store

    @property
    def style_catalog(self) -> StyleCatalogProjection:
        return self._style_catalog
