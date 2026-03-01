"""
BOS Workshop Engine — Phase 17 Tests
======================================
Covers:
  - ProjectItem construction and validation
  - LabeledPiece expansion (quantity -> individual pieces with ItemID)
  - BFD packing: correct bar allocation, ItemID labels, positions
  - BFD offcut: inter-cut waste (not piece dimension), capped at remaining
  - compute_project_pieces: multi-item labeling
  - generate_project_cutting_plan: BFD across whole project
  - compute_charge_rate_based: style rate x unit_qty per item
  - compute_charge_cost_based: bars x cost_per_bar + labor
  - ProjectQuoteRequest: command validation
  - FundiCuttingSheet: ordered cut instructions, exact dimensions
  - End-to-end project quote via WorkshopService
"""

import uuid
from datetime import datetime, timezone

import pytest

from engines.workshop.commands import (
    ProjectQuoteRequest,
    StyleRegisterRequest,
    WORKSHOP_PROJECT_QUOTE_REQUEST,
    VALID_CHARGE_METHODS,
)
from engines.workshop.events import WORKSHOP_PROJECT_QUOTE_GENERATED_V1
from engines.workshop.formula_engine import (
    ChargeMethod,
    CuttingPlan,
    EndpointType,
    FundiBarSheet,
    FundiCutStep,
    FundiCuttingSheet,
    LabeledPiece,
    Orientation,
    ProjectItem,
    ShapeType,
    StockBar,
    StyleComponent,
    StyleDefinition,
    _bfd_pack_1d,
    compute_charge_cost_based,
    compute_charge_rate_based,
    compute_project_pieces,
    format_cutting_sheet,
    generate_project_cutting_plan,
)
from engines.workshop.services import WorkshopService, WorkshopProjectionStore

BIZ = uuid.uuid4()
NOW = datetime(2026, 2, 28, 8, 0, 0, tzinfo=timezone.utc)


def kw(**extra):
    base = dict(
        business_id=BIZ, actor_type="HUMAN", actor_id="fundi-1",
        command_id=uuid.uuid4(), correlation_id=uuid.uuid4(), issued_at=NOW,
    )
    base.update(extra)
    return base


# ─── Stubs ────────────────────────────────────────────────────────────────────

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


def _make_service(persist=None):
    p = persist or StubPersist()
    svc = WorkshopService(
        business_context={"business_id": BIZ},
        command_bus=StubBus(),
        event_factory=StubFactory(),
        persist_event=p,
        event_type_registry=StubReg(),
    )
    return svc, p


# ─── Fixture: simple casement style ──────────────────────────────────────────

def _casement_style(style_id="CASEMENT_1LEAF"):
    """
    Single-leaf casement:
      2x HFrame (null -> W, offcut=5)
      2x VFrame (null -> H, offcut=5)
      1x Glass  (W-30 x H-30, FILL_AREA)
    """
    return StyleDefinition(
        style_id=style_id,
        name="Casement 1-Leaf",
        components=(
            StyleComponent(
                component_id="hframe", name="HFrame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60x40",
                quantity=2, formula_length=None,
                orientation=Orientation.HORIZONTAL, offcut_mm=5,
            ),
            StyleComponent(
                component_id="vframe", name="VFrame",
                shape_type=ShapeType.CUT_SHAPE, material_id="ALU_60x40",
                quantity=2, formula_length=None,
                orientation=Orientation.VERTICAL, offcut_mm=5,
            ),
            StyleComponent(
                component_id="glass", name="Glass",
                shape_type=ShapeType.FILL_AREA, material_id="GLASS_4MM",
                quantity=1, formula_length="W - 30", formula_width="H - 30",
            ),
        ),
    )


def _item(item_id, label, style, W, H, unit_quantity=1):
    return ProjectItem(
        item_id=item_id, item_label=label,
        style=style, dimensions={"W": W, "H": H},
        unit_quantity=unit_quantity,
    )


# ══════════════════════════════════════════════════════════════
# 1. ProjectItem
# ══════════════════════════════════════════════════════════════

class TestProjectItem:
    def test_basic_construction(self):
        style = _casement_style()
        it = ProjectItem(item_id=1, item_label="Dirisha #1",
                         style=style, dimensions={"W": 1200, "H": 900})
        assert it.item_id == 1
        assert it.unit_quantity == 1

    def test_item_id_zero_rejected(self):
        with pytest.raises(ValueError, match="item_id must be >= 1"):
            ProjectItem(item_id=0, item_label="X",
                        style=_casement_style(), dimensions={"W": 1000, "H": 800})

    def test_missing_W_rejected(self):
        with pytest.raises(ValueError, match="dimensions must include W and H"):
            ProjectItem(item_id=1, item_label="X",
                        style=_casement_style(), dimensions={"H": 800})

    def test_zero_unit_quantity_rejected(self):
        with pytest.raises(ValueError, match="unit_quantity must be >= 1"):
            ProjectItem(item_id=1, item_label="X",
                        style=_casement_style(),
                        dimensions={"W": 1000, "H": 800}, unit_quantity=0)

    def test_empty_label_rejected(self):
        with pytest.raises(ValueError, match="item_label must be non-empty"):
            ProjectItem(item_id=1, item_label="",
                        style=_casement_style(), dimensions={"W": 1000, "H": 800})


# ══════════════════════════════════════════════════════════════
# 2. compute_project_pieces — labeling and expansion
# ══════════════════════════════════════════════════════════════

class TestComputeProjectPieces:
    def test_single_item_produces_labeled_pieces(self):
        style = _casement_style()
        pieces = compute_project_pieces([_item(1, "D1", style, 1200, 900)])
        # 2 hframe + 2 vframe + 1 glass = 5
        assert len(pieces) == 5
        assert all(p.item_id == 1 for p in pieces)
        assert all(p.item_label == "D1" for p in pieces)

    def test_two_items_carry_different_ids(self):
        style = _casement_style()
        pieces = compute_project_pieces([
            _item(1, "D1", style, 1200, 900),
            _item(2, "D2", style, 800, 700),
        ])
        assert len(pieces) == 10
        item1_pieces = [p for p in pieces if p.item_id == 1]
        item2_pieces = [p for p in pieces if p.item_id == 2]
        assert len(item1_pieces) == 5
        assert len(item2_pieces) == 5

    def test_dimensions_correct_per_item(self):
        style = _casement_style()
        pieces = compute_project_pieces([_item(1, "X", style, 1200, 900)])
        hframes = [p for p in pieces if p.component_id == "hframe"]
        vframes = [p for p in pieces if p.component_id == "vframe"]
        glass = [p for p in pieces if p.component_id == "glass"]
        assert all(p.length_mm == 1200 for p in hframes)
        assert all(p.length_mm == 900 for p in vframes)
        assert glass[0].length_mm == 1170
        assert glass[0].width_mm == 870

    def test_offcut_carried_on_labeled_piece(self):
        style = _casement_style()
        pieces = compute_project_pieces([_item(1, "X", style, 1200, 900)])
        hframe = next(p for p in pieces if p.component_id == "hframe")
        assert hframe.offcut_mm == 5
        assert hframe.total_length_mm == 1205

    def test_unit_quantity_expanded(self):
        style = _casement_style()
        pieces = compute_project_pieces([_item(1, "X", style, 1200, 900, unit_quantity=3)])
        # 5 per unit x 3 = 15
        assert len(pieces) == 15

    def test_200_items_all_labeled(self):
        style = _casement_style()
        items = [_item(i, f"Item {i}", style, 1000 + i, 800) for i in range(1, 201)]
        pieces = compute_project_pieces(items)
        assert len(pieces) == 1000
        assert {p.item_id for p in pieces} == set(range(1, 201))


# ══════════════════════════════════════════════════════════════
# 3. BFD packing
# ══════════════════════════════════════════════════════════════

class TestBFDPacking:
    def _p(self, item_id, length_mm, offcut_mm=0):
        return LabeledPiece(
            item_id=item_id, item_label=f"Item {item_id}",
            component_id="comp", component_name="Frame",
            material_id="MAT", shape_type=ShapeType.CUT_SHAPE,
            length_mm=length_mm, width_mm=None, offcut_mm=offcut_mm,
        )

    def test_empty_returns_no_bars(self):
        bars, waste = _bfd_pack_1d([], 6000)
        assert bars == [] and waste == 0

    def test_single_piece(self):
        bars, waste = _bfd_pack_1d([self._p(1, 1500)], 6000)
        assert len(bars) == 1
        assert bars[0].waste_mm == 4500

    def test_pieces_fill_one_bar_exactly(self):
        pieces = [self._p(i, 1000) for i in range(1, 7)]  # 6 x 1000 = 6000
        bars, waste = _bfd_pack_1d(pieces, 6000)
        assert len(bars) == 1
        assert waste == 0

    def test_overflow_to_second_bar(self):
        pieces = [self._p(i, 1000) for i in range(1, 8)]  # 7 x 1000
        bars, waste = _bfd_pack_1d(pieces, 6000)
        assert len(bars) == 2

    def test_all_pieces_placed(self):
        pieces = [self._p(i, 1400) for i in range(1, 6)]  # 5 pieces
        bars, _ = _bfd_pack_1d(pieces, 6000)
        total = sum(len(b.allocations) for b in bars)
        assert total == 5

    def test_item_ids_in_allocations(self):
        pieces = [self._p(i, 1000) for i in [3, 7, 11]]
        bars, _ = _bfd_pack_1d(pieces, 6000)
        ids = {a.item_id for b in bars for a in b.allocations}
        assert ids == {3, 7, 11}

    def test_positions_non_overlapping_per_bar(self):
        pieces = [self._p(i, 1500) for i in range(1, 5)]
        bars, _ = _bfd_pack_1d(pieces, 6000)
        for bar in bars:
            allocs = sorted(bar.allocations, key=lambda a: a.position_mm)
            for j in range(len(allocs) - 1):
                end = allocs[j].position_mm + allocs[j].length_mm + allocs[j].offcut_mm
                assert end <= allocs[j + 1].position_mm

    def test_waste_equals_sum_of_bar_remainders(self):
        pieces = [self._p(i, 1400) for i in range(1, 6)]
        bars, total_waste = _bfd_pack_1d(pieces, 6000)
        assert total_waste == sum(b.waste_mm for b in bars)

    def test_oversized_piece_gets_own_bar(self):
        # piece length itself > stock → truly oversized
        bars, _ = _bfd_pack_1d([self._p(1, 7000)], 6000)
        assert len(bars) == 1
        assert bars[0].allocations[0].item_id == 1

    def test_bfd_best_fit_selection(self):
        """
        Verify BFD picks the bar with LEAST remaining space that still fits.
        Pieces (sorted desc): 3000, 2000, 1000   stock=6000
          Bar1 opens: 3000, rem=3000
          2000: fits Bar1 (rem=3000>=2000), rem becomes 1000
          1000: fits Bar1 (rem=1000 exactly), rem becomes 0
          -> 1 bar, 0 waste
        """
        pieces = [self._p(i, l) for i, l in [(1, 3000), (2, 2000), (3, 1000)]]
        bars, waste = _bfd_pack_1d(pieces, 6000)
        assert len(bars) == 1
        assert waste == 0

    # ─── Offcut semantics ──────────────────────────────────────

    def test_offcut_deducted_from_remaining_not_piece(self):
        """
        Offcut is inter-cut overhead on the bar, NOT added to the piece.
        Piece of 2400 + offcut 5 on bar 3600:
          remaining = 3600 - 2400 - 5(offcut) = 1195
          allocation.length_mm == 2400 (exact, not 2405)
        """
        bars, _ = _bfd_pack_1d([self._p(1, 2400, offcut_mm=5)], 3600)
        assert bars[0].allocations[0].length_mm == 2400
        assert bars[0].waste_mm == 1195   # 3600 - 2400 - 5

    def test_first_piece_starts_at_zero_no_precut(self):
        """First piece on a fresh bar starts at position 0 (bar is flat)."""
        bars, _ = _bfd_pack_1d([self._p(1, 1000, offcut_mm=10)], 6000)
        assert bars[0].allocations[0].position_mm == 0

    def test_second_piece_position_accounts_for_offcut(self):
        """
        Second piece starts after piece1.length + offcut1.
        Bar 6000, p1=2000+offcut=5 → p2 starts at 2005.
        """
        p1 = self._p(1, 2000, offcut_mm=5)
        p2 = self._p(2, 1000, offcut_mm=5)
        bars, _ = _bfd_pack_1d([p1, p2], 6000)
        assert len(bars) == 1
        allocs = sorted(bars[0].allocations, key=lambda a: a.position_mm)
        assert allocs[0].position_mm == 0
        assert allocs[0].length_mm == 2000
        assert allocs[1].position_mm == 2005  # 2000 + offcut 5

    def test_piece_fits_when_length_fits_but_full_offcut_does_not(self):
        """
        Key improvement: a piece fits if remaining >= length_mm, even if
        remaining < length_mm + offcut_mm.  The offcut is capped at
        whatever remains after the piece.

        Bar=3000, offcut=10, piece=2995:
          Old approach: 2995+10=3005>3000 → oversized (wrong!)
          New approach: 2995<3000 → fits. offcut=min(10,5)=5. waste=0.
        """
        bars, waste = _bfd_pack_1d([self._p(1, 2995, offcut_mm=10)], 3000)
        assert len(bars) == 1
        assert bars[0].allocations[0].length_mm == 2995
        assert bars[0].allocations[0].offcut_mm == 5   # capped at 3000-2995=5
        assert waste == 0  # 3000 - 2995 - 5(capped) = 0

    def test_offcut_capped_for_last_piece_on_bar(self):
        """
        Last piece on a bar: offcut capped at remaining after piece.
        Bar=6000, p1=5000+off=5(→rem=995), p2=990+off=5(→remaining=5→offcut=5→waste=0).
        """
        p1 = self._p(1, 5000, offcut_mm=5)
        p2 = self._p(2, 990, offcut_mm=5)
        bars, waste = _bfd_pack_1d([p1, p2], 6000)
        assert len(bars) == 1
        allocs = sorted(bars[0].allocations, key=lambda a: a.position_mm)
        # p1 at 0, rem after p1 = 6000-5000-5=995
        assert allocs[0].length_mm == 5000
        assert allocs[0].offcut_mm == 5
        # p2 at 5005, rem after p2 = 995-990-5=0
        assert allocs[1].length_mm == 990
        assert allocs[1].offcut_mm == 5
        assert waste == 0

    def test_single_piece_no_post_offcut_waste(self):
        """
        Single piece on a bar: the 'post-cut offcut' is consumed as
        inter-cut prep.  waste_mm = stock - length - offcut.
        """
        bars, waste = _bfd_pack_1d([self._p(1, 1000, offcut_mm=5)], 6000)
        assert waste == 4995  # 6000 - 1000 - 5

    def test_allocation_length_mm_is_always_exact_piece_dimension(self):
        """
        CutAllocation.length_mm must always equal the LabeledPiece.length_mm.
        Fundi reads this number and cuts exactly that dimension.
        """
        pieces = [self._p(i, 1200 + i * 100, offcut_mm=5) for i in range(1, 6)]
        bars, _ = _bfd_pack_1d(pieces, 6000)
        for bar in bars:
            for alloc in bar.allocations:
                # Find the original piece
                orig = next(p for p in pieces if p.item_id == alloc.item_id)
                assert alloc.length_mm == orig.length_mm  # exact, no offcut added

    def test_oversized_piece_length_only_not_total(self):
        """
        Oversized means piece.length_mm > stock_length.
        A piece with length=5998 + offcut=10 is NOT oversized for stock=6000
        (piece fits; only offcut doesn't fully fit → capped at 2).
        """
        bars, _ = _bfd_pack_1d([self._p(1, 5998, offcut_mm=10)], 6000)
        assert not bars[0].allocations[0].offcut_mm == 10  # capped at 2
        assert bars[0].allocations[0].length_mm == 5998     # exact


# ══════════════════════════════════════════════════════════════
# 3b. FundiCuttingSheet — ordered human-readable cut instructions
# ══════════════════════════════════════════════════════════════

class TestFundiCuttingSheet:
    def _plan(self, bars_data):
        """Build a CuttingPlan from [(item_id, label, length, offcut, pos), ...]"""
        from engines.workshop.formula_engine import CutAllocation
        bar_objs = []
        for idx, cuts in enumerate(bars_data):
            allocs = tuple(
                CutAllocation(
                    item_id=c[0], item_label=c[1], component_id="hf",
                    component_name="H-Frame", length_mm=c[2],
                    offcut_mm=c[3], position_mm=c[4],
                )
                for c in cuts
            )
            used = sum(c[2] + c[3] for c in cuts)
            waste = 6000 - used
            bar_objs.append(StockBar(
                bar_index=idx + 1,
                stock_length_mm=6000,
                allocations=allocs,
                waste_mm=waste,
            ))
        return CuttingPlan(
            material_id="ALU_60x40",
            shape_type=ShapeType.CUT_SHAPE,
            stock_length_mm=6000,
            bars=tuple(bar_objs),
            total_pieces=sum(len(d) for d in bars_data),
            total_waste_mm=sum(6000 - sum(c[2]+c[3] for c in d) for d in bars_data),
            waste_pct=5,
        )

    def test_returns_fundi_cutting_sheet(self):
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0), (7, "Part-A", 850, 5, 2405)],
        ])
        sheet = format_cutting_sheet(plan)
        assert isinstance(sheet, FundiCuttingSheet)

    def test_profile_and_stock_in_sheet(self):
        plan = self._plan([[(1, "Win-A", 1200, 5, 0)]])
        sheet = format_cutting_sheet(plan)
        assert sheet.profile_id == "ALU_60x40"
        assert sheet.stock_length_mm == 6000
        assert sheet.total_bars == 1

    def test_bars_ordered_by_bar_number(self):
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0)],
            [(2, "Win-B", 800, 5, 0)],
        ])
        sheet = format_cutting_sheet(plan)
        assert sheet.bars[0].bar_number == 1
        assert sheet.bars[1].bar_number == 2

    def test_cuts_sorted_by_position(self):
        """Fundi cuts left-to-right; cuts are ordered by position_mm."""
        plan = self._plan([
            [(3, "Item3", 260, 5, 2710), (1, "Item1", 2400, 5, 0), (7, "Item7", 850, 5, 2405)],
        ])
        sheet = format_cutting_sheet(plan)
        positions_in_order = [c.cut_mm for c in sheet.bars[0].cuts]
        # sorted by position: Item1(pos=0)=2400, Item7(pos=2405)=850, Item3(pos=2710)=260
        assert positions_in_order == [2400, 850, 260]

    def test_cut_mm_is_exact_piece_dimension(self):
        """FundiCutStep.cut_mm = exact length_mm (offcut not included)."""
        plan = self._plan([[(1, "Win-A", 2400, 5, 0)]])
        sheet = format_cutting_sheet(plan)
        assert sheet.bars[0].cuts[0].cut_mm == 2400   # 2400, never 2405

    def test_last_cut_has_zero_offcut(self):
        """Last step on a bar: offcut_mm=0 (no next cut to prepare for)."""
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0), (7, "Part-A", 850, 5, 2405)],
        ])
        sheet = format_cutting_sheet(plan)
        cuts = sheet.bars[0].cuts
        assert cuts[-1].offcut_mm == 0  # last cut, no inter-cut offcut shown

    def test_middle_cuts_show_offcut(self):
        """Middle cuts (not last) show the inter-cut offcut consumed after them."""
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0), (7, "Part-A", 850, 5, 2405), (12, "Fix", 260, 5, 3260)],
        ])
        sheet = format_cutting_sheet(plan)
        cuts = sheet.bars[0].cuts
        assert cuts[0].offcut_mm == 5   # inter-cut after first piece
        assert cuts[1].offcut_mm == 5   # inter-cut after second piece
        assert cuts[2].offcut_mm == 0   # last piece — no inter-cut

    def test_remaining_mm_shown_per_bar(self):
        """remaining_mm on each FundiBarSheet = waste at end of bar."""
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0), (7, "Part-A", 850, 5, 2405)],
        ])
        sheet = format_cutting_sheet(plan)
        bar = sheet.bars[0]
        # waste = 6000 - (2400+5) - (850+5) = 6000 - 3260 = 2740
        assert bar.remaining_mm == 2740

    def test_step_numbers_sequential_per_bar(self):
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0), (7, "Part-A", 850, 5, 2405), (12, "Fix", 260, 5, 3260)],
        ])
        sheet = format_cutting_sheet(plan)
        steps = [c.step for c in sheet.bars[0].cuts]
        assert steps == [1, 2, 3]

    def test_item_label_carried_to_cut_step(self):
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0), (7, "Part-A", 850, 5, 2405)],
        ])
        sheet = format_cutting_sheet(plan)
        labels = {c.item_label for c in sheet.bars[0].cuts}
        assert "Win-A" in labels
        assert "Part-A" in labels

    def test_multi_bar_sheet(self):
        plan = self._plan([
            [(1, "Win-A", 2400, 5, 0)],
            [(2, "Win-B", 800, 5, 0)],
            [(3, "Door-A", 900, 5, 0)],
        ])
        sheet = format_cutting_sheet(plan)
        assert sheet.total_bars == 3
        assert len(sheet.bars) == 3

    def test_end_to_end_fundi_sheet_from_real_plan(self):
        """
        Build a real CuttingPlan via generate_project_cutting_plan and
        format it into a FundiCuttingSheet.  Verify the sheet is sensible.
        """
        style = _casement_style()
        items = [
            _item(1, "Win-A", style, 1200, 900),
            _item(2, "Win-B", style, 800, 600),
        ]
        labeled = compute_project_pieces(items)
        alu_pieces = [p for p in labeled if p.material_id == "ALU_60x40"]
        plans = generate_project_cutting_plan(alu_pieces, {"ALU_60x40": 6000})
        plan = plans["ALU_60x40"]

        sheet = format_cutting_sheet(plan)
        assert sheet.profile_id == "ALU_60x40"
        assert sheet.total_pieces == len(alu_pieces)

        # Every cut has exact dimension matching source pieces
        all_cut_mms = {c.cut_mm for bar in sheet.bars for c in bar.cuts}
        assert 1200 in all_cut_mms  # Win-A hframe
        assert 800 in all_cut_mms   # Win-B hframe

        # Last cut on every bar has offcut=0
        for bar in sheet.bars:
            assert bar.cuts[-1].offcut_mm == 0


# ══════════════════════════════════════════════════════════════
# 4. generate_project_cutting_plan
# ══════════════════════════════════════════════════════════════

class TestProjectCuttingPlan:
    def _alu(self, item_id, length_mm):
        return LabeledPiece(
            item_id=item_id, item_label=f"Item {item_id}",
            component_id="hframe", component_name="HFrame",
            material_id="ALU_60x40", shape_type=ShapeType.CUT_SHAPE,
            length_mm=length_mm, width_mm=None, offcut_mm=5,
        )

    def test_returns_plan_keyed_by_material(self):
        pieces = [self._alu(i, 1200) for i in range(1, 4)]
        plans = generate_project_cutting_plan(pieces, {"ALU_60x40": 6000})
        assert "ALU_60x40" in plans

    def test_total_pieces_correct(self):
        pieces = [self._alu(i, 1200) for i in range(1, 6)]
        plan = generate_project_cutting_plan(pieces, {"ALU_60x40": 6000})["ALU_60x40"]
        assert plan.total_pieces == 5

    def test_all_item_ids_appear_in_bars(self):
        pieces = [self._alu(i, 1000) for i in [1, 2, 3, 4, 5]]
        plan = generate_project_cutting_plan(pieces, {"ALU_60x40": 6000})["ALU_60x40"]
        ids = {a.item_id for b in plan.bars for a in b.allocations}
        assert ids == {1, 2, 3, 4, 5}

    def test_multi_material_plans(self):
        alu = [self._alu(i, 1200) for i in [1, 2]]
        glass = [
            LabeledPiece(
                item_id=i, item_label=f"Item {i}",
                component_id="glass", component_name="Glass",
                material_id="GLASS_4MM", shape_type=ShapeType.FILL_AREA,
                length_mm=1170, width_mm=870, offcut_mm=0,
            )
            for i in [1, 2]
        ]
        plans = generate_project_cutting_plan(
            alu + glass, {"ALU_60x40": 6000, "GLASS_4MM": 2000}
        )
        assert "ALU_60x40" in plans
        assert "GLASS_4MM" in plans

    def test_waste_pct_in_range(self):
        pieces = [self._alu(i, 1500) for i in range(1, 5)]
        plan = generate_project_cutting_plan(pieces, {"ALU_60x40": 6000})["ALU_60x40"]
        assert 0 <= plan.waste_pct <= 100

    def test_full_project_two_items(self):
        style = _casement_style()
        items = [
            _item(1, "D1", style, 1200, 900),
            _item(2, "D2", style, 800, 700),
        ]
        labeled = compute_project_pieces(items)
        plans = generate_project_cutting_plan(
            labeled, {"ALU_60x40": 6000, "GLASS_4MM": 2000}
        )
        # 4 alu pieces per item x 2 items = 8
        assert plans["ALU_60x40"].total_pieces == 8
        alu_ids = {a.item_id for b in plans["ALU_60x40"].bars for a in b.allocations}
        assert 1 in alu_ids and 2 in alu_ids


# ══════════════════════════════════════════════════════════════
# 5. Charge methods
# ══════════════════════════════════════════════════════════════

class TestChargeRateBased:
    def test_single_item(self):
        style = _casement_style()
        total = compute_charge_rate_based(
            [_item(1, "X", style, 1200, 900)],
            {"CASEMENT_1LEAF": 150_000},
        )
        assert total == 150_000

    def test_two_items_summed(self):
        s1 = _casement_style("STYLE_A")
        s2 = _casement_style("STYLE_B")
        total = compute_charge_rate_based(
            [_item(1, "A", s1, 1200, 900), _item(2, "B", s2, 800, 700)],
            {"STYLE_A": 100_000, "STYLE_B": 80_000},
        )
        assert total == 180_000

    def test_unit_quantity_multiplied(self):
        style = _casement_style()
        total = compute_charge_rate_based(
            [_item(1, "X", style, 1200, 900, unit_quantity=5)],
            {"CASEMENT_1LEAF": 120_000},
        )
        assert total == 600_000

    def test_missing_style_rate_zero(self):
        style = _casement_style()
        total = compute_charge_rate_based(
            [_item(1, "X", style, 1200, 900)], {}
        )
        assert total == 0

    def test_empty_items(self):
        assert compute_charge_rate_based([], {}) == 0


class TestChargeCostBased:
    def _plan(self, mat_id, num_bars):
        bars = tuple(
            StockBar(bar_index=i + 1, stock_length_mm=6000,
                     allocations=(), waste_mm=0)
            for i in range(num_bars)
        )
        return CuttingPlan(
            material_id=mat_id, shape_type=ShapeType.CUT_SHAPE,
            stock_length_mm=6000, bars=bars,
            total_pieces=num_bars, total_waste_mm=0, waste_pct=0,
        )

    def test_single_material(self):
        plans = {"ALU": self._plan("ALU", 3)}
        assert compute_charge_cost_based(plans, {"ALU": 25_000}) == 75_000

    def test_two_materials(self):
        plans = {"ALU": self._plan("ALU", 2), "GLASS": self._plan("GLASS", 1)}
        total = compute_charge_cost_based(plans, {"ALU": 20_000, "GLASS": 50_000})
        assert total == 90_000

    def test_labor_added(self):
        plans = {"ALU": self._plan("ALU", 2)}
        total = compute_charge_cost_based(plans, {"ALU": 20_000}, labor_cost=30_000)
        assert total == 70_000

    def test_missing_rate_zero(self):
        plans = {"ALU": self._plan("ALU", 3)}
        assert compute_charge_cost_based(plans, {}) == 0

    def test_only_labor(self):
        assert compute_charge_cost_based({}, {}, labor_cost=15_000) == 15_000


# ══════════════════════════════════════════════════════════════
# 6. ProjectQuoteRequest command
# ══════════════════════════════════════════════════════════════

class TestProjectQuoteRequest:
    def _item(self):
        return {"style_id": "CASEMENT", "dimensions": {"W": 1200, "H": 900}}

    def test_valid_rate_based(self):
        req = ProjectQuoteRequest(
            project_quote_id="pq-1", job_id="j-1",
            items=(self._item(),), charge_method="RATE_BASED", currency="TZS",
        )
        assert req.charge_method == "RATE_BASED"

    def test_valid_cost_based(self):
        req = ProjectQuoteRequest(
            project_quote_id="pq-1", job_id="j-1",
            items=(self._item(),), charge_method="COST_BASED", currency="TZS",
        )
        assert req.charge_method == "COST_BASED"

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError, match="project_quote_id"):
            ProjectQuoteRequest(
                project_quote_id="", job_id="j-1",
                items=(self._item(),), charge_method="RATE_BASED", currency="TZS",
            )

    def test_empty_items_rejected(self):
        with pytest.raises(ValueError, match="items must be a non-empty list"):
            ProjectQuoteRequest(
                project_quote_id="pq-1", job_id="j-1",
                items=(), charge_method="RATE_BASED", currency="TZS",
            )

    def test_item_missing_W_rejected(self):
        with pytest.raises(ValueError, match="dimensions must be a dict with W and H"):
            ProjectQuoteRequest(
                project_quote_id="pq-1", job_id="j-1",
                items=({"style_id": "X", "dimensions": {"H": 900}},),
                charge_method="RATE_BASED", currency="TZS",
            )

    def test_invalid_charge_method_rejected(self):
        with pytest.raises(ValueError, match="charge_method must be one of"):
            ProjectQuoteRequest(
                project_quote_id="pq-1", job_id="j-1",
                items=(self._item(),), charge_method="GUESS", currency="TZS",
            )

    def test_bad_currency_rejected(self):
        with pytest.raises(ValueError, match="ISO 4217"):
            ProjectQuoteRequest(
                project_quote_id="pq-1", job_id="j-1",
                items=(self._item(),), charge_method="RATE_BASED", currency="TZ",
            )

    def test_to_command_type(self):
        req = ProjectQuoteRequest(
            project_quote_id="pq-1", job_id="j-1",
            items=(self._item(),), charge_method="RATE_BASED", currency="TZS",
        )
        cmd = req.to_command(**kw())
        assert cmd.command_type == WORKSHOP_PROJECT_QUOTE_REQUEST

    def test_valid_charge_methods_constants(self):
        assert "RATE_BASED" in VALID_CHARGE_METHODS
        assert "COST_BASED" in VALID_CHARGE_METHODS


# ══════════════════════════════════════════════════════════════
# 7. End-to-end: WorkshopService project quote
# ══════════════════════════════════════════════════════════════

class TestProjectQuoteEndToEnd:
    _STYLE_COMPONENTS = (
        {
            "component_id": "hframe", "name": "HFrame",
            "shape_type": "CUT_SHAPE", "material_id": "ALU_60x40",
            "quantity": 2, "formula_length": None,
            "orientation": "HORIZONTAL", "offcut_mm": 5,
        },
        {
            "component_id": "vframe", "name": "VFrame",
            "shape_type": "CUT_SHAPE", "material_id": "ALU_60x40",
            "quantity": 2, "formula_length": None,
            "orientation": "VERTICAL", "offcut_mm": 5,
        },
        {
            "component_id": "glass", "name": "Glass",
            "shape_type": "FILL_AREA", "material_id": "GLASS_4MM",
            "quantity": 1, "formula_length": "W - 30",
            "formula_width": "H - 30",
        },
    )

    def _register(self, svc, style_id="CASEMENT_1LEAF"):
        cmd = StyleRegisterRequest(
            style_id=style_id, name="Casement 1-Leaf",
            components=self._STYLE_COMPONENTS,
        ).to_command(**kw())
        svc._execute_command(cmd)

    def test_rate_based_quote(self):
        svc, _ = _make_service()
        self._register(svc)

        req = ProjectQuoteRequest(
            project_quote_id="pq-001", job_id="job-001",
            items=(
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1200, "H": 900}, "label": "D1"},
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 800, "H": 700}, "label": "D2"},
            ),
            charge_method="RATE_BASED",
            currency="TZS",
            stock_lengths={"ALU_60x40": 6000, "GLASS_4MM": 2000},
            rates={"CASEMENT_1LEAF": 250_000},
        )
        result = svc._execute_command(req.to_command(**kw()))

        assert result.event_type == WORKSHOP_PROJECT_QUOTE_GENERATED_V1
        assert result.projection_applied is True
        payload = result.event_data["payload"]
        # 2 items x 250,000 = 500,000
        assert payload["total_cost"] == 500_000
        assert payload["charge_method"] == "RATE_BASED"
        assert payload["currency"] == "TZS"

    def test_cost_based_quote(self):
        svc, _ = _make_service()
        self._register(svc)

        req = ProjectQuoteRequest(
            project_quote_id="pq-002", job_id="job-002",
            items=(
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1200, "H": 900}},
            ),
            charge_method="COST_BASED",
            currency="TZS",
            stock_lengths={"ALU_60x40": 6000, "GLASS_4MM": 2000},
            rates={"ALU_60x40": 30_000, "GLASS_4MM": 80_000, "LABOR": 50_000},
        )
        result = svc._execute_command(req.to_command(**kw()))

        assert result.event_type == WORKSHOP_PROJECT_QUOTE_GENERATED_V1
        payload = result.event_data["payload"]
        assert payload["total_cost"] >= 50_000  # at minimum the labor cost
        assert payload["charge_method"] == "COST_BASED"

    def test_labeled_pieces_in_event_payload(self):
        svc, _ = _make_service()
        self._register(svc)

        req = ProjectQuoteRequest(
            project_quote_id="pq-003", job_id="job-003",
            items=(
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1200, "H": 900}, "label": "WinA"},
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 800, "H": 700}, "label": "WinB"},
            ),
            charge_method="RATE_BASED", currency="TZS",
        )
        result = svc._execute_command(req.to_command(**kw()))
        payload = result.event_data["payload"]

        # 2 items x 5 pieces = 10 labeled pieces
        assert len(payload["labeled_pieces"]) == 10
        for lp in payload["labeled_pieces"]:
            assert "item_id" in lp
            assert "item_label" in lp
            assert lp["item_id"] in (1, 2)

    def test_cutting_plans_have_item_labels(self):
        svc, _ = _make_service()
        self._register(svc)

        req = ProjectQuoteRequest(
            project_quote_id="pq-004", job_id="job-004",
            items=(
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1200, "H": 900}},
            ),
            charge_method="RATE_BASED", currency="TZS",
            stock_lengths={"ALU_60x40": 6000, "GLASS_4MM": 2000},
        )
        result = svc._execute_command(req.to_command(**kw()))
        plans = result.event_data["payload"]["cutting_plans"]

        assert "ALU_60x40" in plans
        assert "GLASS_4MM" in plans

        for bar in plans["ALU_60x40"]["bars"]:
            for alloc in bar["allocations"]:
                assert "item_id" in alloc
                assert "item_label" in alloc

    def test_project_quote_stored_in_projection(self):
        svc, _ = _make_service()
        self._register(svc)

        req = ProjectQuoteRequest(
            project_quote_id="pq-005", job_id="job-005",
            items=(
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1200, "H": 900}},
            ),
            charge_method="RATE_BASED", currency="TZS",
        )
        svc._execute_command(req.to_command(**kw()))

        pq = svc.projection_store.get_project_quote("pq-005")
        assert pq is not None
        assert pq["charge_method"] == "RATE_BASED"
        assert pq["currency"] == "TZS"

    def test_unknown_style_raises(self):
        svc, _ = _make_service()
        req = ProjectQuoteRequest(
            project_quote_id="pq-006", job_id="job-006",
            items=({"style_id": "NO_SUCH_STYLE", "dimensions": {"W": 1000, "H": 800}},),
            charge_method="RATE_BASED", currency="TZS",
        )
        with pytest.raises(ValueError, match="not found or not active"):
            svc._execute_command(req.to_command(**kw()))

    def test_default_label_assigned(self):
        svc, _ = _make_service()
        self._register(svc)

        req = ProjectQuoteRequest(
            project_quote_id="pq-007", job_id="job-007",
            items=(
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1200, "H": 900}},
                {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 800, "H": 700}},
            ),
            charge_method="RATE_BASED", currency="TZS",
        )
        result = svc._execute_command(req.to_command(**kw()))
        labeled_pieces = result.event_data["payload"]["labeled_pieces"]
        labels = {lp["item_id"]: lp["item_label"] for lp in labeled_pieces}
        assert labels[1] == "Item 1"
        assert labels[2] == "Item 2"

    def test_20_items_smoke_test(self):
        svc, _ = _make_service()
        self._register(svc)

        items = tuple(
            {"style_id": "CASEMENT_1LEAF", "dimensions": {"W": 1000 + i * 50, "H": 800}}
            for i in range(20)
        )
        req = ProjectQuoteRequest(
            project_quote_id="pq-big", job_id="job-big",
            items=items, charge_method="RATE_BASED", currency="TZS",
        )
        result = svc._execute_command(req.to_command(**kw()))
        payload = result.event_data["payload"]
        # 20 items x 5 pieces = 100
        assert len(payload["labeled_pieces"]) == 100
        ids = {lp["item_id"] for lp in payload["labeled_pieces"]}
        assert ids == set(range(1, 21))

    def test_char_method_enum_values_match(self):
        assert ChargeMethod.RATE_BASED.value == "RATE_BASED"
        assert ChargeMethod.COST_BASED.value == "COST_BASED"
