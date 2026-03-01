"""
BOS Workshop Formula Engine + Cut List Tests
=============================================
GAP-02: Parametric geometry, formula evaluation, cut list generation,
        and the new workshop commands (GenerateCutList, MaterialConsume, OffcutRecord).
"""

import uuid
from datetime import datetime, timezone

import pytest

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)


def kw():
    return dict(
        business_id=BIZ, actor_type="HUMAN", actor_id="actor-1",
        command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
    )


class StubReg:
    def __init__(self):
        self._t = set()

    def register(self, et):
        self._t.add(et)

    def is_registered(self, et):
        return et in self._t


class StubFactory:
    def __call__(self, *, command, event_type, payload):
        return {"event_type": event_type, "payload": payload,
                "business_id": command.business_id, "source_engine": command.source_engine}


class StubPersist:
    def __init__(self):
        self.calls = []

    def __call__(self, *, event_data, context, registry, **k):
        self.calls.append(event_data)
        return {"accepted": True}


class StubBus:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, ct, h):
        self.handlers[ct] = h


# ══════════════════════════════════════════════════════════════
# FORMULA EVALUATOR UNIT TESTS
# ══════════════════════════════════════════════════════════════

class TestFormulaEvaluator:
    def _eval(self, formula, variables):
        from engines.workshop.formula_engine import evaluate_formula
        return evaluate_formula(formula, variables)

    def test_literal_number(self):
        assert self._eval("500", {}) == 500

    def test_variable_W(self):
        assert self._eval("W", {"W": 1200, "H": 900}) == 1200

    def test_variable_H(self):
        assert self._eval("H", {"W": 1200, "H": 900}) == 900

    def test_addition(self):
        assert self._eval("W + 100", {"W": 1200}) == 1300

    def test_subtraction(self):
        assert self._eval("W - 100", {"W": 1200}) == 1100

    def test_multiplication(self):
        assert self._eval("W * 2", {"W": 600}) == 1200

    def test_integer_division(self):
        assert self._eval("W / 2", {"W": 1200}) == 600

    def test_parentheses(self):
        assert self._eval("(W - 100) / 2", {"W": 1200}) == 550

    def test_component_reference(self):
        # Later component formula references earlier computed value
        assert self._eval("top_frame - 50", {"top_frame": 1200}) == 1150

    def test_complex_formula(self):
        # (W - 2 * frame) / 3 — three-pane division
        assert self._eval("(W - 2 * 40) / 3", {"W": 1200}) == 373  # floor div

    def test_user_variable_X(self):
        assert self._eval("X * 100", {"X": 3}) == 300

    def test_unknown_variable_raises(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            self._eval("UNKNOWN", {"W": 1200})

    def test_division_by_zero_raises(self):
        with pytest.raises(ValueError, match="Division by zero"):
            self._eval("W / 0", {"W": 1200})

    def test_negative_unary(self):
        # Negative results are clamped to 0 in compute_pieces, but formula can return negative
        assert self._eval("-100", {}) == -100

    def test_nested_parentheses(self):
        assert self._eval("((W + H) / 2)", {"W": 1000, "H": 800}) == 900


# ══════════════════════════════════════════════════════════════
# COMPUTE PIECES TESTS
# ══════════════════════════════════════════════════════════════

class TestComputePieces:
    def _make_style(self):
        from engines.workshop.formula_engine import (
            StyleDefinition, StyleComponent, ShapeType, Orientation, EndpointType,
        )
        # Simple casement window: top frame (H), bottom frame (H), left frame (W), right frame (W), glass
        components = (
            StyleComponent(
                component_id="top", name="Top Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.VERTICAL,
                endpoint_type=EndpointType.MM,
            ),
            StyleComponent(
                component_id="bottom", name="Bottom Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.VERTICAL,
                endpoint_type=EndpointType.MM,
            ),
            StyleComponent(
                component_id="left", name="Left Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.HORIZONTAL,
                endpoint_type=EndpointType.MM,
            ),
            StyleComponent(
                component_id="right", name="Right Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.HORIZONTAL,
                endpoint_type=EndpointType.MM,
            ),
            StyleComponent(
                component_id="glass", name="Glass Pane",
                shape_type=ShapeType.FILL_AREA, material_id="GLASS_4MM",
                formula_length="W - 40", formula_width="H - 40",
            ),
        )
        return StyleDefinition(style_id="s1", name="Simple Casement", components=components)

    def test_null_formula_horizontal_uses_W(self):
        from engines.workshop.formula_engine import compute_pieces
        style = self._make_style()
        pieces = compute_pieces(style, {"W": 1200, "H": 900})
        left = next(p for p in pieces if p.component_id == "left")
        assert left.length_mm == 1200

    def test_null_formula_vertical_uses_H(self):
        from engines.workshop.formula_engine import compute_pieces
        style = self._make_style()
        pieces = compute_pieces(style, {"W": 1200, "H": 900})
        top = next(p for p in pieces if p.component_id == "top")
        assert top.length_mm == 900

    def test_fill_area_formula_evaluated(self):
        from engines.workshop.formula_engine import compute_pieces
        style = self._make_style()
        pieces = compute_pieces(style, {"W": 1200, "H": 900})
        glass = next(p for p in pieces if p.component_id == "glass")
        assert glass.length_mm == 1160  # W - 40
        assert glass.width_mm == 860    # H - 40

    def test_unit_quantity_multiplied(self):
        from engines.workshop.formula_engine import compute_pieces
        style = self._make_style()
        pieces = compute_pieces(style, {"W": 1200, "H": 900}, unit_quantity=3)
        top = next(p for p in pieces if p.component_id == "top")
        assert top.quantity == 3  # 1 per unit × 3 units

    def test_missing_W_raises(self):
        from engines.workshop.formula_engine import compute_pieces
        style = self._make_style()
        with pytest.raises(ValueError, match="W"):
            compute_pieces(style, {"H": 900})

    def test_component_cross_reference(self):
        from engines.workshop.formula_engine import (
            StyleDefinition, StyleComponent, ShapeType, Orientation, compute_pieces,
        )
        components = (
            StyleComponent(
                component_id="frame", name="Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU",
                orientation=Orientation.HORIZONTAL,
            ),
            StyleComponent(
                component_id="sash", name="Sash",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU",
                formula_length="frame - 60",  # reference prior component
            ),
        )
        style = StyleDefinition(style_id="s2", name="Ref Test", components=components)
        pieces = compute_pieces(style, {"W": 1000, "H": 800})
        frame = next(p for p in pieces if p.component_id == "frame")
        sash = next(p for p in pieces if p.component_id == "sash")
        assert frame.length_mm == 1000
        assert sash.length_mm == 940  # 1000 - 60

    def test_negative_clamped_to_zero(self):
        from engines.workshop.formula_engine import (
            StyleDefinition, StyleComponent, ShapeType, Orientation, compute_pieces,
        )
        components = (
            StyleComponent(
                component_id="c", name="C",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU",
                formula_length="W - 5000",  # would be negative
            ),
        )
        style = StyleDefinition(style_id="s3", name="Neg Test", components=components)
        pieces = compute_pieces(style, {"W": 100, "H": 100})
        assert pieces[0].length_mm == 0


# ══════════════════════════════════════════════════════════════
# GENERATE CUT LIST TESTS
# ══════════════════════════════════════════════════════════════

class TestGenerateCutList:
    def _simple_cut_pieces(self):
        from engines.workshop.formula_engine import ComputedPiece, ShapeType
        # 4 frames of 1200mm from 6m stock → needs at least 1 stick (4800mm)
        return [
            ComputedPiece(
                component_id="top", component_name="Top Frame",
                material_id="ALU_60", shape_type=ShapeType.CUT_SHAPE,
                length_mm=1200, width_mm=None, quantity=4, offcut_mm=0,
            ),
        ]

    def test_cut_shape_sticks_estimated(self):
        from engines.workshop.formula_engine import generate_cut_list, ShapeType
        pieces = self._simple_cut_pieces()
        result = generate_cut_list(pieces, {"ALU_60": 6000})
        assert "ALU_60" in result
        mat = result["ALU_60"]
        assert mat.shape_type == ShapeType.CUT_SHAPE
        assert mat.pieces == 4
        assert mat.total_length_mm == 4800
        assert mat.estimated_sticks == 1  # 4 × 1200 = 4800 < 6000

    def test_cut_shape_needs_two_sticks(self):
        from engines.workshop.formula_engine import generate_cut_list, ComputedPiece, ShapeType
        pieces = [
            ComputedPiece(
                component_id="f", component_name="Frame",
                material_id="ALU", shape_type=ShapeType.CUT_SHAPE,
                length_mm=2000, width_mm=None, quantity=4, offcut_mm=0,
            ),
        ]
        result = generate_cut_list(pieces, {"ALU": 6000})
        mat = result["ALU"]
        # 4 × 2000 = 8000mm > 6000mm so needs at least 2 sticks
        assert mat.estimated_sticks >= 2

    def test_fill_area_sheets_estimated(self):
        from engines.workshop.formula_engine import generate_cut_list, ComputedPiece, ShapeType
        # 1 sheet of glass 1160 × 860 from 1200 stock
        pieces = [
            ComputedPiece(
                component_id="g", component_name="Glass",
                material_id="GLASS_4MM", shape_type=ShapeType.FILL_AREA,
                length_mm=1160, width_mm=860, quantity=1, offcut_mm=0,
            ),
        ]
        result = generate_cut_list(pieces, {"GLASS_4MM": 1200})
        mat = result["GLASS_4MM"]
        assert mat.estimated_sheets >= 1
        assert mat.total_area_mm2 == 1160 * 860

    def test_default_stock_length_used_when_not_supplied(self):
        from engines.workshop.formula_engine import generate_cut_list, ComputedPiece, ShapeType
        pieces = [
            ComputedPiece(
                component_id="p", component_name="P",
                material_id="MYSTERY_MAT", shape_type=ShapeType.CUT_SHAPE,
                length_mm=500, width_mm=None, quantity=1, offcut_mm=0,
            ),
        ]
        result = generate_cut_list(pieces, {})  # no stock lengths provided
        mat = result["MYSTERY_MAT"]
        assert mat.stock_length_mm == 6000  # default

    def test_waste_percentage_in_range(self):
        from engines.workshop.formula_engine import generate_cut_list, ComputedPiece, ShapeType
        pieces = [
            ComputedPiece(
                component_id="p", component_name="P",
                material_id="ALU", shape_type=ShapeType.CUT_SHAPE,
                length_mm=1000, width_mm=None, quantity=2, offcut_mm=0,
            ),
        ]
        result = generate_cut_list(pieces, {"ALU": 6000})
        mat = result["ALU"]
        assert 0 <= mat.waste_pct <= 100


# ══════════════════════════════════════════════════════════════
# NEW WORKSHOP COMMANDS
# ══════════════════════════════════════════════════════════════

class TestGenerateCutListRequest:
    def test_valid_request(self):
        from engines.workshop.commands import GenerateCutListRequest
        req = GenerateCutListRequest(
            cutlist_id="cl-1", job_id="j1", style_id="s1",
            dimensions={"W": 1200, "H": 900},
            pieces=[{"component_id": "top", "length_mm": 900}],
            material_requirements={"ALU_60": {"estimated_sticks": 1}},
            unit_quantity=1,
        )
        assert req.cutlist_id == "cl-1"

    def test_empty_cutlist_id_raises(self):
        from engines.workshop.commands import GenerateCutListRequest
        with pytest.raises(ValueError, match="cutlist_id"):
            GenerateCutListRequest(
                cutlist_id="", job_id="j1", style_id="s1",
                dimensions={"W": 1200, "H": 900},
                pieces=[], material_requirements={},
            )

    def test_empty_dimensions_raises(self):
        from engines.workshop.commands import GenerateCutListRequest
        with pytest.raises(ValueError, match="dimensions"):
            GenerateCutListRequest(
                cutlist_id="cl-1", job_id="j1", style_id="s1",
                dimensions={},
                pieces=[], material_requirements={},
            )

    def test_zero_unit_quantity_raises(self):
        from engines.workshop.commands import GenerateCutListRequest
        with pytest.raises(ValueError, match="unit_quantity"):
            GenerateCutListRequest(
                cutlist_id="cl-1", job_id="j1", style_id="s1",
                dimensions={"W": 1200, "H": 900},
                pieces=[], material_requirements={},
                unit_quantity=0,
            )

    def test_to_command(self):
        from engines.workshop.commands import GenerateCutListRequest
        req = GenerateCutListRequest(
            cutlist_id="cl-1", job_id="j1", style_id="s1",
            dimensions={"W": 1200, "H": 900},
            pieces=[],
            material_requirements={},
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == "workshop.cutlist.generate.request"
        assert cmd.payload["cutlist_id"] == "cl-1"
        assert cmd.payload["style_id"] == "s1"


class TestMaterialConsumeRequest:
    def test_valid_request(self):
        from engines.workshop.commands import MaterialConsumeRequest
        req = MaterialConsumeRequest(
            consumption_id="cons-1", job_id="j1",
            material_id="ALU_60", quantity_used=3, unit="PC",
        )
        assert req.quantity_used == 3

    def test_empty_consumption_id_raises(self):
        from engines.workshop.commands import MaterialConsumeRequest
        with pytest.raises(ValueError, match="consumption_id"):
            MaterialConsumeRequest(
                consumption_id="", job_id="j1",
                material_id="ALU_60", quantity_used=3, unit="PC",
            )

    def test_zero_quantity_raises(self):
        from engines.workshop.commands import MaterialConsumeRequest
        with pytest.raises(ValueError, match="quantity_used"):
            MaterialConsumeRequest(
                consumption_id="c1", job_id="j1",
                material_id="ALU_60", quantity_used=0, unit="PC",
            )

    def test_invalid_unit_raises(self):
        from engines.workshop.commands import MaterialConsumeRequest
        with pytest.raises(ValueError, match="unit"):
            MaterialConsumeRequest(
                consumption_id="c1", job_id="j1",
                material_id="ALU_60", quantity_used=1, unit="YARDS",
            )

    def test_to_command(self):
        from engines.workshop.commands import MaterialConsumeRequest
        req = MaterialConsumeRequest(
            consumption_id="cons-1", job_id="j1",
            material_id="ALU_60", quantity_used=2, unit="MM",
            cutlist_id="cl-1",
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == "workshop.material.consume.request"
        assert cmd.payload["material_id"] == "ALU_60"
        assert cmd.payload["unit"] == "MM"
        assert cmd.payload["cutlist_id"] == "cl-1"


class TestOffcutRecordRequest:
    def test_valid_request(self):
        from engines.workshop.commands import OffcutRecordRequest
        req = OffcutRecordRequest(
            offcut_id="oc-1", job_id="j1",
            material_id="ALU_60", length_mm=850,
        )
        assert req.length_mm == 850

    def test_empty_offcut_id_raises(self):
        from engines.workshop.commands import OffcutRecordRequest
        with pytest.raises(ValueError, match="offcut_id"):
            OffcutRecordRequest(
                offcut_id="", job_id="j1",
                material_id="ALU_60", length_mm=500,
            )

    def test_zero_length_raises(self):
        from engines.workshop.commands import OffcutRecordRequest
        with pytest.raises(ValueError, match="length_mm"):
            OffcutRecordRequest(
                offcut_id="oc-1", job_id="j1",
                material_id="ALU_60", length_mm=0,
            )

    def test_to_command(self):
        from engines.workshop.commands import OffcutRecordRequest
        req = OffcutRecordRequest(
            offcut_id="oc-1", job_id="j1",
            material_id="ALU_60", length_mm=850,
            location_id="store-A",
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == "workshop.offcut.record.request"
        assert cmd.payload["length_mm"] == 850
        assert cmd.payload["location_id"] == "store-A"


# ══════════════════════════════════════════════════════════════
# WORKSHOP SERVICE — NEW COMMAND DISPATCH
# ══════════════════════════════════════════════════════════════

class TestWorkshopServiceNewCommands:
    def _svc(self):
        from engines.workshop.services import WorkshopService
        return WorkshopService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg(),
        )

    def test_new_command_handlers_registered(self):
        from engines.workshop.commands import WORKSHOP_COMMAND_TYPES
        s = self._svc()
        assert "workshop.cutlist.generate.request" in s._command_bus.handlers
        assert "workshop.material.consume.request" in s._command_bus.handlers
        assert "workshop.offcut.record.request" in s._command_bus.handlers
        for ct in WORKSHOP_COMMAND_TYPES:
            assert ct in s._command_bus.handlers

    def test_cutlist_generate_dispatch(self):
        from engines.workshop.commands import GenerateCutListRequest
        s = self._svc()
        req = GenerateCutListRequest(
            cutlist_id="cl-1", job_id="j1", style_id="s1",
            dimensions={"W": 1200, "H": 900},
            pieces=[{"component_id": "top", "length_mm": 900}],
            material_requirements={"ALU_60": {"estimated_sticks": 1}},
        )
        result = s._execute_command(req.to_command(**kw()))
        assert result.event_type == "workshop.cutlist.generated.v1"
        assert result.projection_applied is True

    def test_cutlist_projection_stored(self):
        from engines.workshop.commands import GenerateCutListRequest, JobCreateRequest
        s = self._svc()
        # Create job first
        s._execute_command(JobCreateRequest(
            job_id="j1", customer_id="c1", description="Window",
            currency="KES",
        ).to_command(**kw()))
        # Generate cutlist
        req = GenerateCutListRequest(
            cutlist_id="cl-1", job_id="j1", style_id="s1",
            dimensions={"W": 1200, "H": 900},
            pieces=[],
            material_requirements={"ALU_60": {"estimated_sticks": 1}},
        )
        s._execute_command(req.to_command(**kw()))
        cl = s.projection_store.get_cutlist("cl-1")
        assert cl is not None
        assert cl["style_id"] == "s1"
        assert cl["dimensions"] == {"W": 1200, "H": 900}
        # cutlist_id should appear in job's cutlists list
        job = s.projection_store.get_job("j1")
        assert "cl-1" in job["cutlists"]

    def test_material_consume_dispatch(self):
        from engines.workshop.commands import MaterialConsumeRequest
        s = self._svc()
        req = MaterialConsumeRequest(
            consumption_id="cons-1", job_id="j1",
            material_id="ALU_60", quantity_used=2, unit="PC",
        )
        result = s._execute_command(req.to_command(**kw()))
        assert result.event_type == "workshop.material.consumed.v1"
        assert result.projection_applied is True

    def test_offcut_record_dispatch(self):
        from engines.workshop.commands import OffcutRecordRequest
        s = self._svc()
        req = OffcutRecordRequest(
            offcut_id="oc-1", job_id="j1",
            material_id="ALU_60", length_mm=850,
        )
        result = s._execute_command(req.to_command(**kw()))
        assert result.event_type == "workshop.offcut.recorded.v1"
        assert result.projection_applied is True

    def test_offcut_projection_stored(self):
        from engines.workshop.commands import OffcutRecordRequest
        s = self._svc()
        s._execute_command(OffcutRecordRequest(
            offcut_id="oc-1", job_id="j1",
            material_id="ALU_60", length_mm=850, location_id="storeroom-A",
        ).to_command(**kw()))
        offcut = s.projection_store.get_offcut("oc-1")
        assert offcut is not None
        assert offcut["length_mm"] == 850
        assert offcut["location_id"] == "storeroom-A"
        assert offcut["material_id"] == "ALU_60"

    def test_new_events_registered_in_type_registry(self):
        s = self._svc()
        assert s._event_type_registry.is_registered("workshop.cutlist.generated.v1")
        assert s._event_type_registry.is_registered("workshop.material.consumed.v1")
        assert s._event_type_registry.is_registered("workshop.offcut.recorded.v1")


# ══════════════════════════════════════════════════════════════
# FULL INTEGRATION: formula → cutlist → dispatch
# ══════════════════════════════════════════════════════════════

class TestFormulaToServiceIntegration:
    def test_end_to_end_formula_to_cutlist_command(self):
        from engines.workshop.formula_engine import (
            StyleDefinition, StyleComponent, ShapeType, Orientation,
            compute_pieces, generate_cut_list,
        )
        from engines.workshop.commands import GenerateCutListRequest
        from engines.workshop.services import WorkshopService

        # 1. Define style
        components = (
            StyleComponent(
                component_id="top", name="Top Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.VERTICAL,
            ),
            StyleComponent(
                component_id="bottom", name="Bottom Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.VERTICAL,
            ),
            StyleComponent(
                component_id="left", name="Left Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.HORIZONTAL,
            ),
            StyleComponent(
                component_id="right", name="Right Frame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60",
                orientation=Orientation.HORIZONTAL,
            ),
        )
        style = StyleDefinition(style_id="casement", name="Casement", components=components)

        # 2. Compute pieces for 1200×900 window × 2 units
        dimensions = {"W": 1200, "H": 900}
        pieces = compute_pieces(style, dimensions, unit_quantity=2)
        assert len(pieces) == 4  # 4 components

        # 3. Generate cut list
        mat_reqs = generate_cut_list(pieces, {"ALU_60": 6000})
        assert "ALU_60" in mat_reqs
        alu = mat_reqs["ALU_60"]
        # 2 horizontals × 1200 × 2 units + 2 verticals × 900 × 2 units = 8400mm
        assert alu.total_length_mm == (2 * 1200 + 2 * 900) * 2
        assert alu.estimated_sticks >= 2  # 8400mm needs ≥ 2 sticks of 6000mm

        # 4. Dispatch GenerateCutListRequest
        svc = WorkshopService(
            business_context={"business_id": BIZ}, command_bus=StubBus(),
            event_factory=StubFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg(),
        )
        req = GenerateCutListRequest(
            cutlist_id="cl-integration",
            job_id="job-win-001",
            style_id="casement",
            dimensions=dimensions,
            unit_quantity=2,
            pieces=[{"component_id": p.component_id, "length_mm": p.length_mm,
                      "quantity": p.quantity} for p in pieces],
            material_requirements={
                mid: {
                    "estimated_sticks": mr.estimated_sticks,
                    "total_length_mm": mr.total_length_mm,
                    "waste_pct": mr.waste_pct,
                }
                for mid, mr in mat_reqs.items()
            },
        )
        result = svc._execute_command(req.to_command(**kw()))
        assert result.event_type == "workshop.cutlist.generated.v1"
        assert result.projection_applied is True
        cl = svc.projection_store.get_cutlist("cl-integration")
        assert cl["style_id"] == "casement"
        assert cl["unit_quantity"] == 2
