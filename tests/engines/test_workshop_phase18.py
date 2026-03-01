"""
BOS Workshop Engine — Phase 18 Tests
======================================
Covers:
  - GlassPlacement construction and field semantics
  - GlassCutLine: orientation, position, primary vs secondary
  - GlassSheetLayout: placements, primary V-cuts, secondary H-cuts, waste
  - GlassCuttingPlan: aggregate totals across sheets
  - _guillotine_strip_pack: Column Strip Packing + BFD behaviour
      - Single piece → 1 sheet, 0 cuts
      - Two pieces same width → 1 strip, 1 H-cut
      - Two pieces different widths → 2 strips, 1 primary V-cut
      - BFD: piece goes to strip with min remaining height
      - Rotation: rotated 90° when it improves fit
      - Kerf consumed between strips (V) and between rows (H)
      - Overflow to second sheet when full
      - Oversized pieces are silently skipped
  - generate_glass_cutting_plan: public API
      - Filters out CUT_SHAPE pieces
      - Groups by material_id
      - Skips materials not in stock_sizes
      - Correct total/waste tallies
      - allow_rotation=False disables rotation
"""

import pytest

from engines.workshop.formula_engine import (
    GlassCutLine,
    GlassCuttingPlan,
    GlassPlacement,
    GlassSheetLayout,
    LabeledPiece,
    ShapeType,
    _build_glass_sheet_layout,
    _guillotine_strip_pack,
    generate_glass_cutting_plan,
)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _make_glass(
    item_id: int,
    label: str,
    w_mm: int,
    h_mm: int,
    material_id: str = "GLASS_4MM",
    comp_id: str = "g1",
    comp_name: str = "Glass Pane",
) -> LabeledPiece:
    """Create a FILL_AREA LabeledPiece (glass/panel piece)."""
    return LabeledPiece(
        item_id=item_id,
        item_label=label,
        component_id=comp_id,
        component_name=comp_name,
        material_id=material_id,
        shape_type=ShapeType.FILL_AREA,
        length_mm=w_mm,    # width stored in length_mm
        width_mm=h_mm,     # height stored in width_mm
        offcut_mm=0,
    )


def _make_alu(
    item_id: int,
    label: str,
    length_mm: int,
    material_id: str = "ALU_60x40",
) -> LabeledPiece:
    """Create a CUT_SHAPE LabeledPiece (aluminum bar piece)."""
    return LabeledPiece(
        item_id=item_id,
        item_label=label,
        component_id="a1",
        component_name="Top Frame",
        material_id=material_id,
        shape_type=ShapeType.CUT_SHAPE,
        length_mm=length_mm,
        width_mm=None,
        offcut_mm=5,
    )


# ══════════════════════════════════════════════════════════════
# GlassPlacement — dataclass field semantics
# ══════════════════════════════════════════════════════════════

class TestGlassPlacement:
    def test_fields_stored_correctly(self):
        gp = GlassPlacement(
            item_id=1, item_label="Win #1", component_id="g1",
            component_name="Glass Pane",
            x_mm=0, y_mm=0, w_mm=600, h_mm=400,
            original_w_mm=600, original_h_mm=400, rotated=False,
        )
        assert gp.item_id == 1
        assert gp.item_label == "Win #1"
        assert gp.x_mm == 0
        assert gp.y_mm == 0
        assert gp.w_mm == 600
        assert gp.h_mm == 400
        assert gp.original_w_mm == 600
        assert gp.original_h_mm == 400
        assert gp.rotated is False

    def test_rotated_flag(self):
        gp = GlassPlacement(
            item_id=2, item_label="Win #2", component_id="g1",
            component_name="Glass Pane",
            x_mm=10, y_mm=20, w_mm=400, h_mm=600,
            original_w_mm=600, original_h_mm=400, rotated=True,
        )
        assert gp.rotated is True
        assert gp.w_mm == 400   # swapped
        assert gp.h_mm == 600   # swapped
        assert gp.original_w_mm == 600  # unchanged
        assert gp.original_h_mm == 400  # unchanged

    def test_frozen_immutable(self):
        gp = GlassPlacement(
            item_id=1, item_label="L", component_id="g1",
            component_name="G", x_mm=0, y_mm=0, w_mm=100, h_mm=200,
            original_w_mm=100, original_h_mm=200, rotated=False,
        )
        with pytest.raises(Exception):
            gp.x_mm = 50  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════
# GlassCutLine — field semantics
# ══════════════════════════════════════════════════════════════

class TestGlassCutLine:
    def test_primary_v_cut_fields(self):
        cl = GlassCutLine(
            step=1, orientation="V", position_mm=600,
            from_mm=0, to_mm=1200, is_primary=True,
            strip_index=0, description="Primary V-cut: separate strip 1 | strip 2",
        )
        assert cl.orientation == "V"
        assert cl.is_primary is True
        assert cl.strip_index == 0
        assert cl.from_mm == 0
        assert cl.to_mm == 1200

    def test_secondary_h_cut_fields(self):
        cl = GlassCutLine(
            step=2, orientation="H", position_mm=500,
            from_mm=0, to_mm=600, is_primary=False,
            strip_index=1, description="Strip 1 H-cut after piece 1",
        )
        assert cl.orientation == "H"
        assert cl.is_primary is False
        assert cl.strip_index == 1

    def test_frozen_immutable(self):
        cl = GlassCutLine(
            step=1, orientation="V", position_mm=100,
            from_mm=0, to_mm=500, is_primary=True,
            strip_index=0, description="",
        )
        with pytest.raises(Exception):
            cl.step = 99  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — single piece
# ══════════════════════════════════════════════════════════════

class TestSinglePiece:
    """One piece → 1 sheet, 1 placement, no cuts."""

    def setup_method(self):
        self.piece = _make_glass(1, "Win #1", w_mm=600, h_mm=400)
        self.layouts = _guillotine_strip_pack(
            [self.piece], sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )

    def test_one_sheet_used(self):
        assert len(self.layouts) == 1

    def test_one_placement(self):
        layout = self.layouts[0]
        assert layout.piece_count == 1

    def test_placement_position_is_top_left(self):
        p = self.layouts[0].placements[0]
        assert p.x_mm == 0
        assert p.y_mm == 0

    def test_placement_dimensions_match_piece(self):
        p = self.layouts[0].placements[0]
        assert p.w_mm == 600
        assert p.h_mm == 400

    def test_no_primary_cuts_for_single_strip(self):
        assert len(self.layouts[0].primary_cuts) == 0

    def test_no_secondary_cuts_for_single_piece(self):
        assert len(self.layouts[0].secondary_cuts) == 0

    def test_piece_area_correct(self):
        assert self.layouts[0].piece_area_mm2 == 600 * 400

    def test_waste_mm2_correct(self):
        sheet_area = 2000 * 1200
        piece_area = 600 * 400
        assert self.layouts[0].waste_mm2 == sheet_area - piece_area


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — two pieces, same width → 1 strip
# ══════════════════════════════════════════════════════════════

class TestTwoPiecesSameWidth:
    """Two same-width pieces stack in one strip with an H-cut between them."""

    def setup_method(self):
        self.p1 = _make_glass(1, "Win #1", w_mm=600, h_mm=400)
        self.p2 = _make_glass(2, "Win #2", w_mm=600, h_mm=300)
        # Sheet: 2000×1200, kerf=5
        self.layouts = _guillotine_strip_pack(
            [self.p1, self.p2], sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )

    def test_one_sheet(self):
        assert len(self.layouts) == 1

    def test_one_strip_no_primary_cut(self):
        assert len(self.layouts[0].primary_cuts) == 0

    def test_two_placements(self):
        assert self.layouts[0].piece_count == 2

    def test_first_piece_at_top(self):
        # BFD sorts by width desc; both 600mm → input order preserved
        # p1 placed first (y=0), p2 placed after (y=400+5=405)
        ys = sorted(p.y_mm for p in self.layouts[0].placements)
        assert ys[0] == 0

    def test_second_piece_y_includes_kerf(self):
        ys = sorted(p.y_mm for p in self.layouts[0].placements)
        # p1 height=400, kerf=5 → p2 y = 400+5 = 405
        assert ys[1] == 405

    def test_one_h_cut_between_pieces(self):
        assert len(self.layouts[0].secondary_cuts) == 1

    def test_h_cut_position(self):
        cut = self.layouts[0].secondary_cuts[0]
        assert cut.orientation == "H"
        assert cut.position_mm == 400  # after p1 height

    def test_h_cut_is_not_primary(self):
        cut = self.layouts[0].secondary_cuts[0]
        assert cut.is_primary is False

    def test_h_cut_strip_index_is_1(self):
        cut = self.layouts[0].secondary_cuts[0]
        assert cut.strip_index == 1

    def test_h_cut_spans_strip_width(self):
        cut = self.layouts[0].secondary_cuts[0]
        assert cut.from_mm == 0
        assert cut.to_mm == 600  # strip width


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — two different-width pieces → 2 strips
# ══════════════════════════════════════════════════════════════

class TestTwoPiecesDifferentWidth:
    """Two pieces of different widths → separate strips, one primary V-cut."""

    def setup_method(self):
        self.p1 = _make_glass(1, "Win #1", w_mm=800, h_mm=500)
        self.p2 = _make_glass(2, "Win #2", w_mm=600, h_mm=500)
        # p1 (800mm) opens strip 0; p2 (600mm) can't fit (600 > 800 is False,
        # BUT 800 > 600 so strip has w=800, p2.w=600 ≤ 800 → p2 DOES fit in strip 0.
        # Wait — p2 must use BFD. Strip 0 w=800, used_h=500.
        # p2: pw=600 ≤ strip_w=800 ✓, pre_kerf=5, 500+5+500=1005 ≤ 1200 ✓ → fits!
        # So p2 goes into strip 0 (same strip), NOT a new strip.
        # Let me adjust: make p2 too tall to fit in remaining strip height.
        # Sheet h=1200. Strip 0 used_h=500. p2 h=800: 500+5+800=1305 > 1200 → no fit.
        # So p2 opens strip 1.
        self.p2_tall = _make_glass(2, "Win #2", w_mm=600, h_mm=800)
        self.layouts = _guillotine_strip_pack(
            [self.p1, self.p2_tall], sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )

    def test_one_sheet(self):
        assert len(self.layouts) == 1

    def test_two_placements(self):
        assert self.layouts[0].piece_count == 2

    def test_one_primary_v_cut(self):
        assert len(self.layouts[0].primary_cuts) == 1

    def test_primary_cut_is_vertical(self):
        cut = self.layouts[0].primary_cuts[0]
        assert cut.orientation == "V"

    def test_primary_cut_is_full_height(self):
        cut = self.layouts[0].primary_cuts[0]
        assert cut.from_mm == 0
        assert cut.to_mm == 1200  # full sheet height

    def test_primary_cut_position_after_strip_0(self):
        cut = self.layouts[0].primary_cuts[0]
        # Strip 0 starts at x=0, width=800 → cut at x=800
        assert cut.position_mm == 800

    def test_primary_cut_is_flagged_primary(self):
        assert self.layouts[0].primary_cuts[0].is_primary is True

    def test_strip_1_starts_after_kerf(self):
        # Strip 1 x = 800 + kerf(5) = 805
        p2_placement = next(
            p for p in self.layouts[0].placements if p.item_id == 2
        )
        assert p2_placement.x_mm == 805

    def test_no_secondary_cuts_for_single_piece_per_strip(self):
        assert len(self.layouts[0].secondary_cuts) == 0

    def test_primary_cut_step_is_1(self):
        assert self.layouts[0].primary_cuts[0].step == 1


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — BFD behaviour
# ══════════════════════════════════════════════════════════════

class TestBFDGlassBehavior:
    """BFD: piece goes to the strip with MINIMUM remaining height that fits."""

    def test_bfd_picks_tighter_strip(self):
        """
        Sheet 2000×1200, kerf=5.
        Strip 0: w=700, first piece h=900 → remaining=300
        Strip 1: w=600, first piece h=200 → remaining=1000

        New piece: 600×250 — fits both strips (300 ≥ 250 with kerf: 300-5=295 ≥ 250? No).
        Actually 300-5=295 < 250 → doesn't fit strip 0.
        Fits strip 1: 200+5+250=455 ≤ 1200.
        So it goes to strip 1.

        Let's use a case where it clearly fits both and BFD picks strip 0 (tighter).
        Strip 0: used_h=900, remaining=300
        Strip 1: used_h=100, remaining=1100
        New piece: pw=600 ≤ both strips' widths.
        Piece h=200: strip 0: 900+5+200=1105 ≤ 1200 ✓ remaining=95
                      strip 1: 100+5+200=305 ≤ 1200 ✓ remaining=895
        BFD picks strip 0 (remaining=95 < 895).
        """
        p_anchor0 = _make_glass(1, "A", w_mm=700, h_mm=900)
        p_anchor1 = _make_glass(2, "B", w_mm=600, h_mm=100)
        p_target  = _make_glass(3, "C", w_mm=600, h_mm=200)
        # Feed in sorted order so anchors land in correct strips
        # p_anchor0 wider → opens strip 0; p_anchor1 narrower → can fit strip 0?
        # strip 0: w=700, used_h=900. p_anchor1: pw=600≤700, 900+5+100=1005≤1200.
        # BFD: strip 0 remaining after = 1200-1005=195. Only strip.
        # So p_anchor1 lands in strip 0! Let's force 2 strips with heights.
        # Better: make p_anchor1 too tall to fit strip 0.
        p_anchor1_tall = _make_glass(2, "B", w_mm=600, h_mm=400)
        # strip 0: w=700, used_h=900. p_anchor1_tall: 900+5+400=1305 > 1200 → no fit.
        # Opens strip 1: x=705, w=600, used_h=400.
        # Now p_target (600×200): strip0 remaining=300, strip1 remaining=800
        #   strip0: 900+5+200=1105≤1200 ✓ remaining=95
        #   strip1: 400+5+200=605≤1200 ✓ remaining=595
        # BFD picks strip0 (min remaining=95 < 595).

        layouts = _guillotine_strip_pack(
            [p_anchor0, p_anchor1_tall, p_target],
            sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        # p_target (item_id=3) should be in strip 0 (x=0)
        target_placement = next(
            p for p in layouts[0].placements if p.item_id == 3
        )
        assert target_placement.x_mm == 0   # strip 0

    def test_bfd_does_not_pick_strip_that_wont_fit(self):
        """Piece must NOT go to a strip where it doesn't fit by height."""
        # Strip 0: w=800, used_h=1100. Remaining=100 (after kerf=5: 1100+5+new_h ≤ 1200)
        # Piece 800×200: needs 1100+5+200=1305 > 1200 → doesn't fit strip 0.
        p_anchor = _make_glass(1, "A", w_mm=800, h_mm=1100)
        p_big    = _make_glass(2, "B", w_mm=800, h_mm=200)

        layouts = _guillotine_strip_pack(
            [p_anchor, p_big], sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        # p_big can't fit strip 0 → opens strip 1 (x=805) OR goes to sheet 2.
        # Sheet is wide enough (2000) so strip 1 at x=805 can fit p_big (800mm wide → 805+800=1605 ≤ 2000).
        p_big_pl = next(p for p in layouts[0].placements if p.item_id == 2)
        assert p_big_pl.x_mm == 805  # strip 1

    def test_bfd_all_pieces_placed(self):
        """All pieces must appear in the output."""
        pieces = [
            _make_glass(i, f"W{i}", w_mm=400, h_mm=300)
            for i in range(1, 6)
        ]
        layouts = _guillotine_strip_pack(
            pieces, sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        total_placed = sum(l.piece_count for l in layouts)
        assert total_placed == 5


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — kerf consumption
# ══════════════════════════════════════════════════════════════

class TestKerfConsumption:
    def test_kerf_between_piece_rows(self):
        """H-cut position = first_piece_h (no kerf before first piece)."""
        p1 = _make_glass(1, "A", w_mm=500, h_mm=400)
        p2 = _make_glass(2, "B", w_mm=500, h_mm=300)
        layouts = _guillotine_strip_pack(
            [p1, p2], sheet_w=1000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        cut = layouts[0].secondary_cuts[0]
        # H-cut at y=400 (bottom of p1)
        assert cut.position_mm == 400

    def test_kerf_added_to_second_piece_y(self):
        """Second piece y = first_piece_h + kerf."""
        p1 = _make_glass(1, "A", w_mm=500, h_mm=400)
        p2 = _make_glass(2, "B", w_mm=500, h_mm=300)
        layouts = _guillotine_strip_pack(
            [p1, p2], sheet_w=1000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        p2_pl = next(p for p in layouts[0].placements if p.item_id == 2)
        assert p2_pl.y_mm == 405  # 400 + 5 kerf

    def test_kerf_between_strips(self):
        """Strip 1 x = strip 0 right_edge + kerf."""
        p1 = _make_glass(1, "A", w_mm=700, h_mm=1100)  # fills strip 0
        p2 = _make_glass(2, "B", w_mm=600, h_mm=500)   # goes to strip 1
        # p2 can't fit strip 0 (1100+5+500=1605 > 1200)
        layouts = _guillotine_strip_pack(
            [p1, p2], sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        p2_pl = next(p for p in layouts[0].placements if p.item_id == 2)
        # strip 0: x=0, w=700 → strip 1: x=700+5=705
        assert p2_pl.x_mm == 705

    def test_kerf_0_means_no_gap(self):
        """With kerf=0, pieces and strips are adjacent with no gap."""
        p1 = _make_glass(1, "A", w_mm=500, h_mm=400)
        p2 = _make_glass(2, "B", w_mm=500, h_mm=300)
        layouts = _guillotine_strip_pack(
            [p1, p2], sheet_w=1000, sheet_h=1200, kerf=0,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        p2_pl = next(p for p in layouts[0].placements if p.item_id == 2)
        assert p2_pl.y_mm == 400  # no kerf gap


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — rotation
# ══════════════════════════════════════════════════════════════

class TestRotation:
    def test_rotation_enabled_swaps_dimensions(self):
        """
        Piece 1200×400, sheet 1000×1500, kerf=5.
        Normal orientation (1200×400): 1200 > sheet_w(1000) → can't fit normal.
        Rotated (400×1200): 400 ≤ 1000, 1200 ≤ 1500 → fits rotated.
        """
        p = _make_glass(1, "Win", w_mm=1200, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1500, kerf=5,
            material_id="GLASS_4MM", allow_rotation=True,
        )
        assert len(layouts) == 1
        pl = layouts[0].placements[0]
        assert pl.rotated is True
        assert pl.w_mm == 400   # rotated width
        assert pl.h_mm == 1200  # rotated height

    def test_rotation_records_original_dimensions(self):
        """original_w_mm / original_h_mm always match the LabeledPiece."""
        p = _make_glass(1, "Win", w_mm=1200, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1500, kerf=5,
            material_id="GLASS_4MM", allow_rotation=True,
        )
        pl = layouts[0].placements[0]
        assert pl.original_w_mm == 1200
        assert pl.original_h_mm == 400

    def test_rotation_disabled_skips_oversized(self):
        """With allow_rotation=False, oversized pieces are skipped."""
        p = _make_glass(1, "Win", w_mm=1200, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1500, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        assert len(layouts) == 0  # piece can't fit → no layouts

    def test_no_rotation_when_square(self):
        """Square piece is never marked rotated (both orientations identical)."""
        p = _make_glass(1, "Win", w_mm=500, h_mm=500)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=True,
        )
        assert layouts[0].placements[0].rotated is False

    def test_rotation_not_applied_when_piece_fits_normal(self):
        """If piece fits in normal orientation, it should NOT be rotated."""
        p = _make_glass(1, "Win", w_mm=600, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=True,
        )
        assert layouts[0].placements[0].rotated is False


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — overflow to second sheet
# ══════════════════════════════════════════════════════════════

class TestMultipleSheets:
    def test_overflow_creates_second_sheet(self):
        """When sheet is full, remaining pieces go to a second sheet."""
        # Sheet 1000×800, kerf=5. One piece 1000×800 fills entire sheet.
        p1 = _make_glass(1, "A", w_mm=1000, h_mm=800)
        p2 = _make_glass(2, "B", w_mm=500, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p1, p2], sheet_w=1000, sheet_h=800, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        assert len(layouts) == 2

    def test_second_sheet_index_is_2(self):
        p1 = _make_glass(1, "A", w_mm=1000, h_mm=800)
        p2 = _make_glass(2, "B", w_mm=500, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p1, p2], sheet_w=1000, sheet_h=800, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        assert layouts[1].sheet_index == 2

    def test_all_pieces_placed_across_sheets(self):
        """Total placed pieces across all sheets equals input count."""
        pieces = [
            _make_glass(i, f"W{i}", w_mm=800, h_mm=600)
            for i in range(1, 5)
        ]
        layouts = _guillotine_strip_pack(
            pieces, sheet_w=1000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        total = sum(l.piece_count for l in layouts)
        assert total == 4

    def test_sheet_material_id_propagated(self):
        p = _make_glass(1, "A", w_mm=500, h_mm=400, material_id="TEMPER_6MM")
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1200, kerf=5,
            material_id="TEMPER_6MM", allow_rotation=False,
        )
        assert layouts[0].material_id == "TEMPER_6MM"


# ══════════════════════════════════════════════════════════════
# _guillotine_strip_pack — waste calculation
# ══════════════════════════════════════════════════════════════

class TestWasteCalculation:
    def test_waste_mm2_is_sheet_minus_piece_area(self):
        p = _make_glass(1, "A", w_mm=600, h_mm=400)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=2000, sheet_h=1200, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        layout = layouts[0]
        expected_waste = 2000 * 1200 - 600 * 400
        assert layout.waste_mm2 == expected_waste

    def test_waste_pct_single_small_piece(self):
        """
        Sheet 1000×1000 = 1_000_000 mm².
        Piece 100×100 = 10_000 mm².
        waste = 990_000 → 99%.
        """
        p = _make_glass(1, "A", w_mm=100, h_mm=100)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1000, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        assert layouts[0].waste_pct == 99

    def test_waste_pct_zero_when_perfectly_full(self):
        """
        Sheet 1000×1000. Piece 1000×1000.
        Waste = 0, waste_pct = 0.
        """
        p = _make_glass(1, "A", w_mm=1000, h_mm=1000)
        layouts = _guillotine_strip_pack(
            [p], sheet_w=1000, sheet_h=1000, kerf=5,
            material_id="GLASS_4MM", allow_rotation=False,
        )
        assert layouts[0].waste_pct == 0
        assert layouts[0].waste_mm2 == 0


# ══════════════════════════════════════════════════════════════
# _build_glass_sheet_layout — cut sequencing
# ══════════════════════════════════════════════════════════════

class TestCutSequencing:
    def test_primary_cuts_have_lower_step_numbers_than_secondary(self):
        """Primary V-cuts must come before secondary H-cuts in step order."""
        # Two strips, each with 2 pieces → 1 primary cut + 2 secondary cuts
        strips = [
            {
                "x": 0, "w": 600, "used_h": 900,
                "pieces": [
                    {"piece": _make_glass(1, "A", 600, 400), "y": 0, "pw": 600, "ph": 400, "rotated": False},
                    {"piece": _make_glass(2, "B", 600, 300), "y": 405, "pw": 600, "ph": 300, "rotated": False},
                ],
            },
            {
                "x": 605, "w": 500, "used_h": 500,
                "pieces": [
                    {"piece": _make_glass(3, "C", 500, 500), "y": 0, "pw": 500, "ph": 500, "rotated": False},
                ],
            },
        ]
        layout = _build_glass_sheet_layout(
            strips, sheet_idx=1, material_id="GLASS_4MM",
            sheet_w=1200, sheet_h=1200, kerf=5,
        )
        primary_steps = [c.step for c in layout.primary_cuts]
        secondary_steps = [c.step for c in layout.secondary_cuts]
        assert max(primary_steps) < min(secondary_steps)

    def test_primary_cut_steps_start_at_1(self):
        strips = [
            {"x": 0, "w": 600, "used_h": 400,
             "pieces": [{"piece": _make_glass(1, "A", 600, 400), "y": 0, "pw": 600, "ph": 400, "rotated": False}]},
            {"x": 605, "w": 500, "used_h": 400,
             "pieces": [{"piece": _make_glass(2, "B", 500, 400), "y": 0, "pw": 500, "ph": 400, "rotated": False}]},
        ]
        layout = _build_glass_sheet_layout(
            strips, sheet_idx=1, material_id="G", sheet_w=1200, sheet_h=1200, kerf=5,
        )
        assert layout.primary_cuts[0].step == 1

    def test_n_strips_minus_1_primary_cuts(self):
        """N strips → N-1 primary V-cuts."""
        strips = [
            {"x": x, "w": 300, "used_h": 300,
             "pieces": [{"piece": _make_glass(i + 1, f"P{i}", 300, 300), "y": 0, "pw": 300, "ph": 300, "rotated": False}]}
            for i, x in enumerate([0, 305, 610])
        ]
        layout = _build_glass_sheet_layout(
            strips, sheet_idx=1, material_id="G", sheet_w=1000, sheet_h=1000, kerf=5,
        )
        assert len(layout.primary_cuts) == 2  # 3 strips → 2 cuts

    def test_secondary_cut_count(self):
        """Each strip with N pieces has N-1 secondary H-cuts."""
        # 1 strip with 3 pieces → 2 H-cuts
        strips = [
            {
                "x": 0, "w": 600, "used_h": 910,
                "pieces": [
                    {"piece": _make_glass(1, "A", 600, 300), "y": 0, "pw": 600, "ph": 300, "rotated": False},
                    {"piece": _make_glass(2, "B", 600, 300), "y": 305, "pw": 600, "ph": 300, "rotated": False},
                    {"piece": _make_glass(3, "C", 600, 300), "y": 610, "pw": 600, "ph": 300, "rotated": False},
                ],
            }
        ]
        layout = _build_glass_sheet_layout(
            strips, sheet_idx=1, material_id="G", sheet_w=1000, sheet_h=1000, kerf=5,
        )
        assert len(layout.secondary_cuts) == 2

    def test_primary_cuts_span_full_sheet_height(self):
        """Primary V-cuts run from y=0 to y=sheet_h."""
        strips = [
            {"x": 0, "w": 400, "used_h": 400,
             "pieces": [{"piece": _make_glass(1, "A", 400, 400), "y": 0, "pw": 400, "ph": 400, "rotated": False}]},
            {"x": 405, "w": 400, "used_h": 400,
             "pieces": [{"piece": _make_glass(2, "B", 400, 400), "y": 0, "pw": 400, "ph": 400, "rotated": False}]},
        ]
        layout = _build_glass_sheet_layout(
            strips, sheet_idx=1, material_id="G", sheet_w=900, sheet_h=800, kerf=5,
        )
        cut = layout.primary_cuts[0]
        assert cut.from_mm == 0
        assert cut.to_mm == 800  # = sheet_h


# ══════════════════════════════════════════════════════════════
# generate_glass_cutting_plan — public API
# ══════════════════════════════════════════════════════════════

class TestGenerateGlassCuttingPlan:

    def _glass_pieces(self):
        return [
            _make_glass(1, "Win #1", w_mm=600, h_mm=400, material_id="GLASS_4MM"),
            _make_glass(2, "Win #2", w_mm=500, h_mm=350, material_id="GLASS_4MM"),
            _make_glass(3, "Door #1", w_mm=800, h_mm=600, material_id="TEMPER_6MM"),
        ]

    def test_returns_dict_keyed_by_material(self):
        pieces = self._glass_pieces()
        plans = generate_glass_cutting_plan(
            pieces,
            stock_sizes={"GLASS_4MM": (2000, 1200), "TEMPER_6MM": (2000, 1200)},
        )
        assert "GLASS_4MM" in plans
        assert "TEMPER_6MM" in plans

    def test_filters_out_cut_shape_pieces(self):
        """CUT_SHAPE pieces must be ignored."""
        mixed = [
            _make_glass(1, "Win #1", w_mm=600, h_mm=400, material_id="GLASS_4MM"),
            _make_alu(2, "Bar #1", length_mm=3000, material_id="GLASS_4MM"),  # CUT_SHAPE with same mat_id
        ]
        plans = generate_glass_cutting_plan(
            mixed,
            stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        # Only 1 glass piece placed, not the bar
        assert plans["GLASS_4MM"].total_pieces == 1

    def test_skip_material_without_stock_size(self):
        """Materials absent from stock_sizes are silently skipped."""
        pieces = [_make_glass(1, "Win", w_mm=600, h_mm=400, material_id="UNKNOWN_GLASS")]
        plans = generate_glass_cutting_plan(
            pieces,
            stock_sizes={"GLASS_4MM": (2000, 1200)},  # UNKNOWN_GLASS not listed
        )
        assert "UNKNOWN_GLASS" not in plans

    def test_empty_pieces_list(self):
        plans = generate_glass_cutting_plan([], stock_sizes={"GLASS_4MM": (2000, 1200)})
        assert plans == {}

    def test_total_pieces_count(self):
        pieces = [
            _make_glass(i, f"W{i}", w_mm=400, h_mm=300, material_id="GLASS_4MM")
            for i in range(1, 4)
        ]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        assert plans["GLASS_4MM"].total_pieces == 3

    def test_total_piece_area(self):
        pieces = [
            _make_glass(1, "A", w_mm=600, h_mm=400, material_id="GLASS_4MM"),
            _make_glass(2, "B", w_mm=500, h_mm=300, material_id="GLASS_4MM"),
        ]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        expected = 600 * 400 + 500 * 300
        assert plans["GLASS_4MM"].total_piece_area_mm2 == expected

    def test_total_waste_mm2_non_negative(self):
        pieces = [_make_glass(1, "A", w_mm=600, h_mm=400, material_id="GLASS_4MM")]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        assert plans["GLASS_4MM"].total_waste_mm2 >= 0

    def test_waste_pct_between_0_and_100(self):
        pieces = [_make_glass(1, "A", w_mm=600, h_mm=400, material_id="GLASS_4MM")]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        pct = plans["GLASS_4MM"].waste_pct
        assert 0 <= pct <= 100

    def test_allow_rotation_false_disables_rotation(self):
        """
        Piece 1500×600, sheet 1000×2000.
        Normal (1500×600): 1500 > 1000 → can't fit.
        Rotated (600×1500): 600 ≤ 1000, 1500 ≤ 2000 → fits.
        With allow_rotation=False: no placement, 0 sheets.
        """
        p = _make_glass(1, "Big", w_mm=1500, h_mm=600, material_id="GLASS_4MM")
        plans_no_rot = generate_glass_cutting_plan(
            [p], stock_sizes={"GLASS_4MM": (1000, 2000)},
            allow_rotation=False,
        )
        plans_rot = generate_glass_cutting_plan(
            [p], stock_sizes={"GLASS_4MM": (1000, 2000)},
            allow_rotation=True,
        )
        # No rotation: piece can't fit → no sheets
        assert plans_no_rot.get("GLASS_4MM") is None or \
               plans_no_rot["GLASS_4MM"].total_sheets == 0
        # With rotation: piece fits
        assert plans_rot["GLASS_4MM"].total_sheets == 1
        assert plans_rot["GLASS_4MM"].total_pieces == 1

    def test_plan_sheet_dimensions_match_stock_sizes(self):
        pieces = [_make_glass(1, "A", w_mm=400, h_mm=300, material_id="GLASS_4MM")]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2440, 1220)},
        )
        plan = plans["GLASS_4MM"]
        assert plan.sheet_w_mm == 2440
        assert plan.sheet_h_mm == 1220

    def test_plan_kerf_propagated(self):
        pieces = [_make_glass(1, "A", w_mm=400, h_mm=300, material_id="GLASS_4MM")]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
            kerf_mm=3,
        )
        assert plans["GLASS_4MM"].kerf_mm == 3

    def test_multi_material_separate_plans(self):
        """Each material gets its own independent GlassCuttingPlan."""
        pieces = [
            _make_glass(1, "Win", w_mm=600, h_mm=400, material_id="GLASS_4MM"),
            _make_glass(2, "Door", w_mm=800, h_mm=700, material_id="TEMPER_6MM"),
        ]
        plans = generate_glass_cutting_plan(
            pieces,
            stock_sizes={"GLASS_4MM": (2000, 1200), "TEMPER_6MM": (2000, 1200)},
        )
        assert plans["GLASS_4MM"].material_id == "GLASS_4MM"
        assert plans["TEMPER_6MM"].material_id == "TEMPER_6MM"
        assert plans["GLASS_4MM"].total_pieces == 1
        assert plans["TEMPER_6MM"].total_pieces == 1

    def test_returned_type_is_glass_cutting_plan(self):
        pieces = [_make_glass(1, "A", w_mm=400, h_mm=300, material_id="GLASS_4MM")]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        assert isinstance(plans["GLASS_4MM"], GlassCuttingPlan)

    def test_sheets_are_glass_sheet_layout_instances(self):
        pieces = [_make_glass(1, "A", w_mm=400, h_mm=300, material_id="GLASS_4MM")]
        plans = generate_glass_cutting_plan(
            pieces, stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        for sheet in plans["GLASS_4MM"].sheets:
            assert isinstance(sheet, GlassSheetLayout)

    def test_item_label_carried_to_placement(self):
        """The item_label must appear in placements for traceability."""
        p = _make_glass(1, "Dirisha #7", w_mm=500, h_mm=400, material_id="GLASS_4MM")
        plans = generate_glass_cutting_plan(
            [p], stock_sizes={"GLASS_4MM": (2000, 1200)},
        )
        pl = plans["GLASS_4MM"].sheets[0].placements[0]
        assert pl.item_label == "Dirisha #7"
        assert pl.item_id == 1
