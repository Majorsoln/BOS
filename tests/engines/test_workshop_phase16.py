"""
BOS Workshop Engine — Phase 16 Tests
======================================
Covers:
  - Shared-name rule in formula engine
  - Style Registry commands (register, update, deactivate)
  - StyleCatalogProjection
  - Quote generation (end-to-end: style → formula → event)
  - Phase 16 policies
"""

import uuid
from datetime import datetime, timezone

import pytest

from engines.workshop.commands import (
    StyleRegisterRequest, StyleUpdateRequest, StyleDeactivateRequest,
    QuoteGenerateRequest,
    WORKSHOP_STYLE_REGISTER_REQUEST, WORKSHOP_STYLE_UPDATE_REQUEST,
    WORKSHOP_STYLE_DEACTIVATE_REQUEST, WORKSHOP_QUOTE_GENERATE_REQUEST,
)
from engines.workshop.events import (
    WORKSHOP_STYLE_REGISTERED_V1, WORKSHOP_STYLE_UPDATED_V1,
    WORKSHOP_STYLE_DEACTIVATED_V1, WORKSHOP_QUOTE_GENERATED_V1,
)
from engines.workshop.formula_engine import (
    StyleComponent, StyleDefinition, ShapeType, Orientation, EndpointType,
    compute_pieces,
)
from engines.workshop.policies import (
    style_must_exist_to_quote_policy,
    style_must_be_active_to_quote_policy,
    style_id_must_not_exist_to_register_policy,
)
from engines.workshop.services import WorkshopService, WorkshopProjectionStore
from projections.workshop.style_catalog import StyleCatalogProjection, StyleRecord

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 26, 9, 0, 0, tzinfo=timezone.utc)


def kw():
    return dict(
        business_id=BIZ, actor_type="HUMAN", actor_id="fundi-1",
        command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
    )


class StubReg:
    def __init__(self): self._t = set()
    def register(self, et): self._t.add(et)
    def is_registered(self, et): return et in self._t


class StubFactory:
    def __call__(self, *, command, event_type, payload):
        return {"event_type": event_type, "payload": payload,
                "business_id": command.business_id}


class StubPersist:
    def __init__(self): self.calls = []
    def __call__(self, *, event_data, context, registry, **k):
        self.calls.append(event_data)
        return {"accepted": True}


class StubBus:
    def __init__(self): self.handlers = {}
    def register_handler(self, ct, h): self.handlers[ct] = h


def _make_service(persist=None, style_catalog=None):
    p = persist or StubPersist()
    return WorkshopService(
        business_context={"business_id": BIZ},
        command_bus=StubBus(),
        event_factory=StubFactory(),
        persist_event=p,
        event_type_registry=StubReg(),
        style_catalog=style_catalog,
    ), p


# ═══════════════════════════════════════════════════════════════════
# 1. SHARED-NAME RULE
# ═══════════════════════════════════════════════════════════════════

class TestSharedNameRule:

    def _make_style(self):
        """
        Simulates a sliding window where both vertical frames share the name
        "Hframe".  The second "Hframe" component must reuse the computed value
        of the first instead of re-evaluating its own formula.
        """
        return StyleDefinition(
            style_id="sliding_test",
            name="Sliding Window Test",
            components=(
                StyleComponent(
                    component_id="hframe_left",
                    name="Hframe",
                    shape_type=ShapeType.CUT_SHAPE,
                    material_id="frame_mat",
                    formula_length=None,        # null = frame → uses H
                    orientation=Orientation.VERTICAL,
                    offcut_mm=5,
                ),
                StyleComponent(
                    component_id="hframe_right",
                    name="Hframe",               # same name as hframe_left
                    shape_type=ShapeType.CUT_SHAPE,
                    material_id="frame_mat",
                    formula_length=None,
                    orientation=Orientation.VERTICAL,
                    offcut_mm=5,
                ),
                StyleComponent(
                    component_id="wframe_top",
                    name="Wframe",
                    shape_type=ShapeType.CUT_SHAPE,
                    material_id="frame_mat",
                    formula_length=None,        # null = frame → uses W
                    orientation=Orientation.HORIZONTAL,
                    offcut_mm=5,
                ),
                StyleComponent(
                    component_id="hsash",
                    name="Hsash",
                    shape_type=ShapeType.CUT_SHAPE,
                    material_id="sash_mat",
                    formula_length="Hframe-(9+X)",   # references by name
                    orientation=Orientation.VERTICAL,
                    offcut_mm=3,
                ),
            ),
            variables={"X": "Sash height variable"},
        )

    def test_shared_name_produces_same_value(self):
        """Both Hframe components must have the same computed length."""
        style = self._make_style()
        pieces = compute_pieces(style, {"W": 170, "H": 250, "X": 59})
        hframe_pieces = [p for p in pieces if p.component_name == "Hframe"]
        assert len(hframe_pieces) == 2
        assert hframe_pieces[0].length_mm == hframe_pieces[1].length_mm == 250

    def test_formula_references_by_name(self):
        """Hsash formula 'Hframe-(9+X)' resolves using the name 'Hframe'."""
        style = self._make_style()
        pieces = compute_pieces(style, {"W": 170, "H": 250, "X": 59})
        hsash = next(p for p in pieces if p.component_name == "Hsash")
        # Hframe=250, X=59 → 250-(9+59) = 250-68 = 182
        assert hsash.length_mm == 182

    def test_shared_name_fill_area(self):
        """Two glass panels with same name share width/height values."""
        style = StyleDefinition(
            style_id="glass_test",
            name="Glass Test",
            components=(
                StyleComponent(
                    component_id="g1",
                    name="VentGlass",
                    shape_type=ShapeType.FILL_AREA,
                    material_id="glass",
                    formula_length="W-10",
                    formula_width="H-10",
                ),
                StyleComponent(
                    component_id="g2",
                    name="VentGlass",  # same name
                    shape_type=ShapeType.FILL_AREA,
                    material_id="glass",
                    formula_length="W-10",
                    formula_width="H-10",
                ),
            ),
        )
        pieces = compute_pieces(style, {"W": 100, "H": 80})
        glass = [p for p in pieces if p.component_name == "VentGlass"]
        assert glass[0].length_mm == glass[1].length_mm == 90
        assert glass[0].width_mm == glass[1].width_mm == 70


# ═══════════════════════════════════════════════════════════════════
# 2. StyleRegisterRequest
# ═══════════════════════════════════════════════════════════════════

_SAMPLE_COMPONENTS = [
    {"component_id": "hframe", "name": "Hframe", "shape_type": "CUT_SHAPE",
     "material_id": "upvc_115", "formula_length": None, "orientation": "VERTICAL",
     "offcut_mm": 5},
    {"component_id": "wframe", "name": "Wframe", "shape_type": "CUT_SHAPE",
     "material_id": "upvc_115", "formula_length": None, "orientation": "HORIZONTAL",
     "offcut_mm": 5},
]


class TestStyleRegisterRequest:

    def test_valid_register(self):
        req = StyleRegisterRequest(
            style_id="sliding_v1",
            name="Sliding Window",
            components=tuple(_SAMPLE_COMPONENTS),
            variables={"X": "Sash height"},
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == WORKSHOP_STYLE_REGISTER_REQUEST
        assert cmd.payload["style_id"] == "sliding_v1"
        assert len(cmd.payload["components"]) == 2
        assert cmd.payload["variables"] == {"X": "Sash height"}

    def test_empty_style_id_rejected(self):
        with pytest.raises(ValueError, match="style_id"):
            StyleRegisterRequest(style_id="", name="X", components=tuple(_SAMPLE_COMPONENTS))

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            StyleRegisterRequest(style_id="s1", name="", components=tuple(_SAMPLE_COMPONENTS))

    def test_empty_components_rejected(self):
        with pytest.raises(ValueError, match="components"):
            StyleRegisterRequest(style_id="s1", name="N", components=())

    def test_component_missing_required_key(self):
        bad = [{"component_id": "x", "name": "X", "shape_type": "CUT_SHAPE"}]  # no material_id
        with pytest.raises(ValueError, match="material_id"):
            StyleRegisterRequest(style_id="s1", name="N", components=tuple(bad))


# ═══════════════════════════════════════════════════════════════════
# 3. StyleUpdateRequest
# ═══════════════════════════════════════════════════════════════════

class TestStyleUpdateRequest:

    def test_valid_name_update(self):
        req = StyleUpdateRequest(style_id="s1", name="New Name")
        cmd = req.to_command(**kw())
        assert cmd.command_type == WORKSHOP_STYLE_UPDATE_REQUEST
        assert cmd.payload["name"] == "New Name"
        assert "components" not in cmd.payload

    def test_valid_components_update(self):
        req = StyleUpdateRequest(style_id="s1", components=tuple(_SAMPLE_COMPONENTS))
        cmd = req.to_command(**kw())
        assert "components" in cmd.payload

    def test_nothing_to_update_rejected(self):
        with pytest.raises(ValueError, match="At least one"):
            StyleUpdateRequest(style_id="s1")

    def test_empty_style_id_rejected(self):
        with pytest.raises(ValueError, match="style_id"):
            StyleUpdateRequest(style_id="", name="X")


# ═══════════════════════════════════════════════════════════════════
# 4. StyleDeactivateRequest
# ═══════════════════════════════════════════════════════════════════

class TestStyleDeactivateRequest:

    def test_valid_deactivate(self):
        req = StyleDeactivateRequest(style_id="s1", reason="Discontinued model")
        cmd = req.to_command(**kw())
        assert cmd.command_type == WORKSHOP_STYLE_DEACTIVATE_REQUEST
        assert cmd.payload["reason"] == "Discontinued model"

    def test_empty_reason_rejected(self):
        with pytest.raises(ValueError, match="reason"):
            StyleDeactivateRequest(style_id="s1", reason="")


# ═══════════════════════════════════════════════════════════════════
# 5. QuoteGenerateRequest
# ═══════════════════════════════════════════════════════════════════

class TestQuoteGenerateRequest:

    def test_valid_quote_request(self):
        req = QuoteGenerateRequest(
            quote_id="q-1", job_id="j-1", style_id="sliding_v1",
            dimensions={"W": 170, "H": 250, "X": 59},
            unit_quantity=2,
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == WORKSHOP_QUOTE_GENERATE_REQUEST
        assert cmd.payload["dimensions"] == {"W": 170, "H": 250, "X": 59}
        assert cmd.payload["unit_quantity"] == 2

    def test_missing_W_rejected(self):
        with pytest.raises(ValueError, match="W"):
            QuoteGenerateRequest(
                quote_id="q1", job_id="j1", style_id="s1",
                dimensions={"H": 250},
            )

    def test_zero_unit_quantity_rejected(self):
        with pytest.raises(ValueError, match="unit_quantity"):
            QuoteGenerateRequest(
                quote_id="q1", job_id="j1", style_id="s1",
                dimensions={"W": 100, "H": 200}, unit_quantity=0,
            )

    def test_empty_quote_id_rejected(self):
        with pytest.raises(ValueError, match="quote_id"):
            QuoteGenerateRequest(
                quote_id="", job_id="j1", style_id="s1",
                dimensions={"W": 100, "H": 200},
            )


# ═══════════════════════════════════════════════════════════════════
# 6. StyleCatalogProjection
# ═══════════════════════════════════════════════════════════════════

class TestStyleCatalogProjection:

    def _register_payload(self, style_id="s1", name="Test Style"):
        return {
            "business_id": str(BIZ),
            "style_id": style_id,
            "name": name,
            "components": list(_SAMPLE_COMPONENTS),
            "variables": {"X": "height var"},
            "registered_at": NOW.isoformat(),
        }

    def test_register_creates_active_record(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload())
        rec = cat.get_style("s1")
        assert rec is not None
        assert rec.status == "ACTIVE"
        assert rec.name == "Test Style"

    def test_get_active_style_returns_active(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload())
        assert cat.get_active_style("s1") is not None

    def test_update_changes_name(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload())
        cat.apply(WORKSHOP_STYLE_UPDATED_V1, {
            "business_id": str(BIZ), "style_id": "s1", "name": "Updated Name",
            "updated_at": NOW.isoformat(),
        })
        assert cat.get_style("s1").name == "Updated Name"

    def test_update_ignores_unknown_style(self):
        cat = StyleCatalogProjection()
        # Should not raise even if style doesn't exist
        cat.apply(WORKSHOP_STYLE_UPDATED_V1, {
            "business_id": str(BIZ), "style_id": "ghost", "name": "X",
            "updated_at": NOW.isoformat(),
        })

    def test_deactivate_sets_inactive(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload())
        cat.apply(WORKSHOP_STYLE_DEACTIVATED_V1, {
            "business_id": str(BIZ), "style_id": "s1", "reason": "discontinued",
            "deactivated_at": NOW.isoformat(),
        })
        assert cat.get_style("s1").status == "INACTIVE"
        assert cat.get_active_style("s1") is None

    def test_list_styles_returns_all(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s1", "Style A"))
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s2", "Style B"))
        styles = cat.list_styles(BIZ)
        assert len(styles) == 2

    def test_list_active_styles_excludes_inactive(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s1"))
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s2"))
        cat.apply(WORKSHOP_STYLE_DEACTIVATED_V1, {
            "business_id": str(BIZ), "style_id": "s2",
            "reason": "old", "deactivated_at": NOW.isoformat(),
        })
        active = cat.list_active_styles(BIZ)
        assert len(active) == 1
        assert active[0].style_id == "s1"

    def test_snapshot_counts(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s1"))
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s2"))
        cat.apply(WORKSHOP_STYLE_DEACTIVATED_V1, {
            "business_id": str(BIZ), "style_id": "s2",
            "reason": "old", "deactivated_at": NOW.isoformat(),
        })
        snap = cat.snapshot(BIZ)
        assert snap["total"] == 2
        assert snap["active"] == 1
        assert snap["inactive"] == 1

    def test_truncate_by_business(self):
        cat = StyleCatalogProjection()
        cat.apply(WORKSHOP_STYLE_REGISTERED_V1, self._register_payload("s1"))
        cat.truncate(BIZ)
        assert cat.get_style("s1") is None
        assert cat.list_styles(BIZ) == []


# ═══════════════════════════════════════════════════════════════════
# 7. SERVICE: style register/update/deactivate commands
# ═══════════════════════════════════════════════════════════════════

class TestWorkshopServiceStyleCommands:

    def _register_style(self, service, persist, style_id="sliding_v1"):
        req = StyleRegisterRequest(
            style_id=style_id,
            name="Sliding Window",
            components=tuple(_SAMPLE_COMPONENTS),
            variables={"X": "sash var"},
        )
        cmd = req.to_command(**kw())
        result = service._execute_command(cmd)
        return result

    def test_register_style_fires_event(self):
        svc, persist = _make_service()
        result = self._register_style(svc, persist)
        assert result.event_type == WORKSHOP_STYLE_REGISTERED_V1
        assert result.projection_applied

    def test_register_style_updates_catalog(self):
        svc, _ = _make_service()
        self._register_style(svc, _)
        rec = svc.style_catalog.get_active_style("sliding_v1")
        assert rec is not None
        assert rec.name == "Sliding Window"

    def test_update_style_fires_event(self):
        svc, persist = _make_service()
        self._register_style(svc, persist)
        req = StyleUpdateRequest(style_id="sliding_v1", name="Sliding Window v2")
        result = svc._execute_command(req.to_command(**kw()))
        assert result.event_type == WORKSHOP_STYLE_UPDATED_V1
        assert svc.style_catalog.get_style("sliding_v1").name == "Sliding Window v2"

    def test_deactivate_style_fires_event(self):
        svc, persist = _make_service()
        self._register_style(svc, persist)
        req = StyleDeactivateRequest(style_id="sliding_v1", reason="Old model")
        result = svc._execute_command(req.to_command(**kw()))
        assert result.event_type == WORKSHOP_STYLE_DEACTIVATED_V1
        assert svc.style_catalog.get_style("sliding_v1").status == "INACTIVE"

    def test_all_style_commands_registered_in_bus(self):
        bus = StubBus()
        WorkshopService(
            business_context={"business_id": BIZ},
            command_bus=bus,
            event_factory=StubFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
        )
        assert WORKSHOP_STYLE_REGISTER_REQUEST in bus.handlers
        assert WORKSHOP_STYLE_UPDATE_REQUEST in bus.handlers
        assert WORKSHOP_STYLE_DEACTIVATE_REQUEST in bus.handlers
        assert WORKSHOP_QUOTE_GENERATE_REQUEST in bus.handlers


# ═══════════════════════════════════════════════════════════════════
# 8. SERVICE: quote generation (end-to-end)
# ═══════════════════════════════════════════════════════════════════

_SLIDING_WINDOW_COMPONENTS = [
    {"component_id": "hframe", "name": "Hframe", "shape_type": "CUT_SHAPE",
     "material_id": "frame_mat", "formula_length": None, "orientation": "VERTICAL",
     "endpoint_type": "MM", "offcut_mm": 5, "quantity": 1},
    {"component_id": "wframe", "name": "Wframe", "shape_type": "CUT_SHAPE",
     "material_id": "frame_mat", "formula_length": None, "orientation": "HORIZONTAL",
     "endpoint_type": "MM", "offcut_mm": 5, "quantity": 1},
    {"component_id": "hsash", "name": "Hsash", "shape_type": "CUT_SHAPE",
     "material_id": "sash_mat", "formula_length": "Hframe-(9+X)", "orientation": "VERTICAL",
     "endpoint_type": "MS", "offcut_mm": 3, "quantity": 2},
    {"component_id": "wsash", "name": "Wsash", "shape_type": "CUT_SHAPE",
     "material_id": "sash_mat", "formula_length": "(Wframe+1)/2", "orientation": "HORIZONTAL",
     "endpoint_type": "SS", "offcut_mm": 3, "quantity": 2},
    {"component_id": "glass", "name": "VentGlass", "shape_type": "FILL_AREA",
     "material_id": "glass_mat", "formula_length": "Wframe-9", "formula_width": "X-9",
     "orientation": "HORIZONTAL", "endpoint_type": "MM", "offcut_mm": 0, "quantity": 1},
]


class TestQuoteGeneration:

    def _setup_service_with_style(self):
        svc, persist = _make_service()
        # Register the style first
        reg = StyleRegisterRequest(
            style_id="sliding_v1",
            name="Sliding Window 2-Panel",
            components=tuple(_SLIDING_WINDOW_COMPONENTS),
            variables={"X": "Sash/glass height variable"},
        )
        svc._execute_command(reg.to_command(**kw()))
        return svc, persist

    def test_quote_generated_event_fired(self):
        svc, persist = self._setup_service_with_style()
        req = QuoteGenerateRequest(
            quote_id="quote-001", job_id="job-001", style_id="sliding_v1",
            dimensions={"W": 170, "H": 250, "X": 59}, unit_quantity=1,
        )
        result = svc._execute_command(req.to_command(**kw()))
        assert result.event_type == WORKSHOP_QUOTE_GENERATED_V1
        assert result.projection_applied

    def test_quote_pieces_computed_correctly(self):
        svc, _ = self._setup_service_with_style()
        req = QuoteGenerateRequest(
            quote_id="quote-002", job_id="job-001", style_id="sliding_v1",
            dimensions={"W": 170, "H": 250, "X": 59}, unit_quantity=1,
        )
        result = svc._execute_command(req.to_command(**kw()))
        payload = result.event_data["payload"]
        pieces = payload["pieces"]

        # Verify computed values
        hframe = next(p for p in pieces if p["component_id"] == "hframe")
        assert hframe["length_mm"] == 250    # H

        wframe = next(p for p in pieces if p["component_id"] == "wframe")
        assert wframe["length_mm"] == 170    # W

        hsash = next(p for p in pieces if p["component_id"] == "hsash")
        assert hsash["length_mm"] == 182     # 250-(9+59)=182

        wsash = next(p for p in pieces if p["component_id"] == "wsash")
        assert wsash["length_mm"] == 85      # (170+1)/2=85

        glass = next(p for p in pieces if p["component_id"] == "glass")
        assert glass["length_mm"] == 161     # 170-9
        assert glass["width_mm"] == 50       # 59-9

    def test_quote_material_requirements_present(self):
        svc, _ = self._setup_service_with_style()
        req = QuoteGenerateRequest(
            quote_id="quote-003", job_id="job-001", style_id="sliding_v1",
            dimensions={"W": 170, "H": 250, "X": 59}, unit_quantity=1,
        )
        result = svc._execute_command(req.to_command(**kw()))
        reqs = result.event_data["payload"]["material_requirements"]
        assert "frame_mat" in reqs
        assert "sash_mat" in reqs
        assert "glass_mat" in reqs

    def test_quote_unit_quantity_multiplies_pieces(self):
        svc, _ = self._setup_service_with_style()
        req = QuoteGenerateRequest(
            quote_id="quote-004", job_id="job-001", style_id="sliding_v1",
            dimensions={"W": 170, "H": 250, "X": 59}, unit_quantity=3,
        )
        result = svc._execute_command(req.to_command(**kw()))
        pieces = result.event_data["payload"]["pieces"]
        # hsash has quantity=2 per unit; with 3 units → 6
        hsash = next(p for p in pieces if p["component_id"] == "hsash")
        assert hsash["quantity"] == 6

    def test_quote_stored_in_projection(self):
        svc, _ = self._setup_service_with_style()
        req = QuoteGenerateRequest(
            quote_id="quote-005", job_id="job-001", style_id="sliding_v1",
            dimensions={"W": 170, "H": 250, "X": 59},
        )
        svc._execute_command(req.to_command(**kw()))
        q = svc.projection_store.get_quote("quote-005")
        assert q is not None
        assert q["style_id"] == "sliding_v1"

    def test_quote_fails_for_unknown_style(self):
        svc, _ = _make_service()
        req = QuoteGenerateRequest(
            quote_id="q1", job_id="j1", style_id="no_such_style",
            dimensions={"W": 100, "H": 200},
        )
        with pytest.raises(ValueError, match="not found or not active"):
            svc._execute_command(req.to_command(**kw()))

    def test_quote_fails_for_inactive_style(self):
        svc, _ = self._setup_service_with_style()
        # Deactivate the style
        svc._execute_command(
            StyleDeactivateRequest(style_id="sliding_v1", reason="discontinued")
            .to_command(**kw())
        )
        req = QuoteGenerateRequest(
            quote_id="q2", job_id="j1", style_id="sliding_v1",
            dimensions={"W": 100, "H": 200, "X": 50},
        )
        with pytest.raises(ValueError, match="not found or not active"):
            svc._execute_command(req.to_command(**kw()))


# ═══════════════════════════════════════════════════════════════════
# 9. POLICIES
# ═══════════════════════════════════════════════════════════════════

class TestPhase16Policies:

    def _quote_cmd(self, style_id="s1"):
        req = QuoteGenerateRequest(
            quote_id="q1", job_id="j1", style_id=style_id,
            dimensions={"W": 100, "H": 200},
        )
        return req.to_command(**kw())

    def _register_cmd(self, style_id="s1"):
        req = StyleRegisterRequest(
            style_id=style_id, name="Test",
            components=tuple(_SAMPLE_COMPONENTS),
        )
        return req.to_command(**kw())

    def test_style_must_exist_passes_when_found(self):
        cmd = self._quote_cmd("s1")
        result = style_must_exist_to_quote_policy(cmd, style_lookup=lambda sid: {"style_id": sid})
        assert result is None

    def test_style_must_exist_fails_when_missing(self):
        cmd = self._quote_cmd("missing")
        result = style_must_exist_to_quote_policy(cmd, style_lookup=lambda sid: None)
        assert result is not None
        assert result.code == "STYLE_NOT_FOUND"

    def test_style_must_be_active_passes_for_active(self):
        cmd = self._quote_cmd("s1")
        active_style = StyleRecord(
            style_id="s1", name="X", components=[], variables={},
            status="ACTIVE", registered_at=NOW, business_id=str(BIZ)
        )
        result = style_must_be_active_to_quote_policy(cmd, style_lookup=lambda sid: active_style)
        assert result is None

    def test_style_must_be_active_fails_for_inactive(self):
        cmd = self._quote_cmd("s1")
        inactive = StyleRecord(
            style_id="s1", name="X", components=[], variables={},
            status="INACTIVE", registered_at=NOW, business_id=str(BIZ)
        )
        result = style_must_be_active_to_quote_policy(cmd, style_lookup=lambda sid: inactive)
        assert result is not None
        assert result.code == "STYLE_INACTIVE"

    def test_no_duplicate_register_fails(self):
        cmd = self._register_cmd("s1")
        existing = StyleRecord(
            style_id="s1", name="Existing", components=[], variables={},
            status="ACTIVE", registered_at=NOW, business_id=str(BIZ)
        )
        result = style_id_must_not_exist_to_register_policy(
            cmd, style_lookup=lambda sid: existing)
        assert result is not None
        assert result.code == "STYLE_ALREADY_EXISTS"

    def test_no_duplicate_register_passes_for_new(self):
        cmd = self._register_cmd("new_s")
        result = style_id_must_not_exist_to_register_policy(
            cmd, style_lookup=lambda sid: None)
        assert result is None

    def test_policies_skip_for_wrong_command_type(self):
        """Policies must return None for irrelevant command types."""
        from engines.workshop.commands import JobCreateRequest
        job_req = JobCreateRequest(
            job_id="j1", customer_id="c1", description="Fix window",
            currency="TZS",
        )
        cmd = job_req.to_command(**kw())
        assert style_must_exist_to_quote_policy(cmd, style_lookup=lambda sid: None) is None
        assert style_must_be_active_to_quote_policy(cmd, style_lookup=lambda sid: None) is None
