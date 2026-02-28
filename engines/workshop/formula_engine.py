"""
BOS Workshop Formula Engine — Parametric Geometry Evaluator
============================================================
Authority: BOS_Workshop_HOW_Official.pdf + BOS_Workshop_Style_Examples.pdf

RULES (NON-NEGOTIABLE):
- Deterministic: same input → same output always
- No random() or datetime.now() inside engine logic
- null formula = frame-level component (takes W if horizontal, H if vertical)
- Non-null formulas reference variables or other component IDs
- Dependency chain must be acyclic (validated at style definition time)
- Material quantities derived ONLY from cut list (not raw formula totals)
- AI cannot modify styles or formula definitions

Shape Types:
    CUT_SHAPE  — Linear/1D: frames, sashes, mullions (produces lengths)
    FILL_AREA  — Area/2D: glass, panels, boards (produces width × height)
    FILL_CUT   — Area but cut linearly: mosquito nets, mesh

Endpoint Types (for CUT_SHAPE only):
    MM — Mater-Mater: frame-to-frame (both pieces full length)
    MS — Mater-Square: frame continues, inner piece fits between
    SS — Square-Square: both inner pieces fit between frames

Formula Language:
    null          → frame component (position-derived)
    W, H          → unit width and height
    X, Y, Z       → user-defined variables (entered at quote time)
    <comp_id>     → computed value of another component
    Operators: +, -, *, /  (integer arithmetic, always integer result)
    Parentheses: ( ... )
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ShapeType(Enum):
    CUT_SHAPE = "CUT_SHAPE"    # Linear/1D — frames, sashes, mullions
    FILL_AREA = "FILL_AREA"    # Area/2D — glass, panels
    FILL_CUT = "FILL_CUT"      # Area but cut linearly — nets, mesh


class Orientation(Enum):
    HORIZONTAL = "HORIZONTAL"  # Takes W for null formula
    VERTICAL = "VERTICAL"      # Takes H for null formula


class EndpointType(Enum):
    MM = "MM"  # Mater-Mater (frame-to-frame)
    MS = "MS"  # Mater-Square (frame continues, inner fits between)
    SS = "SS"  # Square-Square (both inner, fit between frames)


# ══════════════════════════════════════════════════════════════
# FORMULA TOKENIZER
# ══════════════════════════════════════════════════════════════

def _tokenize(formula: str) -> List[str]:
    """Split formula string into tokens."""
    tokens = []
    i = 0
    s = formula.strip()
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(s[i:j])
            i = j
        elif c.isalpha() or c == '_':
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == '_' or s[j] == '.'):
                j += 1
            tokens.append(s[i:j])
            i = j
        elif c in '()+-*/':
            tokens.append(c)
            i += 1
        else:
            raise ValueError(f"Unexpected character in formula: '{c}' in '{formula}'")
    return tokens


# ══════════════════════════════════════════════════════════════
# FORMULA EVALUATOR (Recursive Descent Parser)
# ══════════════════════════════════════════════════════════════

class _FormulaParser:
    """
    Deterministic recursive descent parser for BOS workshop formulas.
    Evaluates arithmetic expressions with variable references.
    No eval() — fully safe and auditable.
    """

    def __init__(self, tokens: List[str], variables: Dict[str, int]):
        self._tokens = tokens
        self._pos = 0
        self._variables = variables  # variable name → integer value

    def _peek(self) -> Optional[str]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self) -> str:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> int:
        result = self._parse_expr()
        if self._peek() is not None:
            raise ValueError(f"Unexpected token: {self._peek()}")
        return result

    def _parse_expr(self) -> int:
        """Expression: term ((+|-) term)*"""
        left = self._parse_term()
        while self._peek() in ('+', '-'):
            op = self._consume()
            right = self._parse_term()
            if op == '+':
                left = left + right
            else:
                left = left - right
        return left

    def _parse_term(self) -> int:
        """Term: factor ((*|/) factor)*"""
        left = self._parse_factor()
        while self._peek() in ('*', '/'):
            op = self._consume()
            right = self._parse_factor()
            if op == '*':
                left = left * right
            else:
                if right == 0:
                    raise ValueError("Division by zero in formula.")
                left = left // right
        return left

    def _parse_factor(self) -> int:
        """Factor: number | variable | (expr)"""
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of formula.")

        if tok == '(':
            self._consume()
            val = self._parse_expr()
            closing = self._consume()
            if closing != ')':
                raise ValueError("Expected ')' in formula.")
            return val

        if tok == '-':
            self._consume()
            return -self._parse_factor()

        if tok.isdigit() or (len(tok) > 1 and tok[0].isdigit()):
            self._consume()
            return int(tok)

        # Variable or component reference
        self._consume()
        if tok not in self._variables:
            raise ValueError(
                f"Unknown variable or component reference: '{tok}'. "
                f"Available: {sorted(self._variables.keys())}"
            )
        return self._variables[tok]

    raise_error = ValueError


def evaluate_formula(formula: str, variables: Dict[str, int]) -> int:
    """
    Evaluate a single formula string given variable bindings.
    Returns integer result (all BOS dimensions are integer mm or minor units).

    Variables dict should include:
        W, H — unit dimensions
        X, Y, Z — user-defined inputs
        <comp_id> — computed values of prior components
    """
    tokens = _tokenize(formula)
    parser = _FormulaParser(tokens, variables)
    return parser.parse()


# ══════════════════════════════════════════════════════════════
# STYLE COMPONENT DEFINITION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StyleComponent:
    """
    Defines one component (piece) in a window/door style.

    Fields:
        component_id:   Unique ID within the style (used in formula refs)
        name:           Human-readable label (e.g. "Top Frame", "Glass Pane")
        shape_type:     CUT_SHAPE | FILL_AREA | FILL_CUT
        material_id:    Which material stock this cuts from
        quantity:       How many of this piece per unit (default 1)
        formula_length: Length formula (or null for frame-derived)
        formula_width:  Width formula for FILL_AREA/FILL_CUT (or null)
        orientation:    HORIZONTAL | VERTICAL (for null frame derivation)
        endpoint_type:  MM | MS | SS (for CUT_SHAPE endpoint treatment)
        offcut_mm:      Kerf/offcut to add after formula evaluation
    """
    component_id: str
    name: str
    shape_type: ShapeType
    material_id: str
    quantity: int = 1
    formula_length: Optional[str] = None   # null = frame (derived from orientation)
    formula_width: Optional[str] = None    # for FILL_AREA: the other dimension
    orientation: Orientation = Orientation.HORIZONTAL
    endpoint_type: EndpointType = EndpointType.MM
    offcut_mm: int = 0

    def __post_init__(self):
        if not self.component_id:
            raise ValueError("component_id must be non-empty.")
        if not self.name:
            raise ValueError("name must be non-empty.")
        if not isinstance(self.shape_type, ShapeType):
            raise ValueError("shape_type must be ShapeType enum.")
        if not self.material_id:
            raise ValueError("material_id must be non-empty.")
        if self.quantity < 1:
            raise ValueError("quantity must be >= 1.")
        if self.shape_type == ShapeType.FILL_AREA and self.formula_width is None and self.formula_length is not None:
            raise ValueError("FILL_AREA components need formula_width when formula_length is set.")


# ══════════════════════════════════════════════════════════════
# STYLE DEFINITION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StyleDefinition:
    """
    A window/door style — the template for parametric production.

    Fields:
        style_id:    Unique identifier
        name:        Human label (e.g. "Casement 2-Leaf", "Sliding 3-Panel")
        components:  Ordered tuple of StyleComponent (dependency order matters!)
        variables:   Variable names and their descriptions (X, Y, Z meanings)
                     e.g. {"X": "Number of panes", "Y": "Number of rows"}
    """
    style_id: str
    name: str
    components: Tuple[StyleComponent, ...]
    variables: Dict[str, str] = None  # variable name → description

    def __post_init__(self):
        if not self.style_id:
            raise ValueError("style_id must be non-empty.")
        if not self.name:
            raise ValueError("name must be non-empty.")
        if not self.components:
            raise ValueError("components must not be empty.")
        # Check for duplicate component IDs
        ids = [c.component_id for c in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate component_id in style components.")

    def get_component(self, component_id: str) -> Optional[StyleComponent]:
        for c in self.components:
            if c.component_id == component_id:
                return c
        return None


# ══════════════════════════════════════════════════════════════
# CUT LIST GENERATION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ComputedPiece:
    """A single computed piece for one unit."""
    component_id: str
    component_name: str
    material_id: str
    shape_type: ShapeType
    length_mm: int           # length for CUT_SHAPE; width for FILL_*
    width_mm: Optional[int]  # None for CUT_SHAPE; height for FILL_*
    quantity: int
    offcut_mm: int

    @property
    def total_length_mm(self) -> int:
        """Length including offcut."""
        return self.length_mm + self.offcut_mm

    @property
    def area_mm2(self) -> Optional[int]:
        """Area for FILL shapes."""
        if self.width_mm is not None:
            return self.length_mm * self.width_mm
        return None


@dataclass(frozen=True)
class MaterialRequirement:
    """Total material needed for a job (across all units)."""
    material_id: str
    shape_type: ShapeType
    total_length_mm: int    # For CUT_SHAPE: total linear mm needed
    total_area_mm2: int     # For FILL_*: total area in mm²
    pieces: int             # Number of pieces
    stock_length_mm: int    # Standard stock length (for estimating sticks/sheets)
    estimated_sticks: int   # For CUT_SHAPE: estimated sticks/profiles needed
    estimated_sheets: int   # For FILL_*: estimated sheets needed
    waste_pct: int          # Estimated waste percentage (0-100)


def compute_pieces(
    style: StyleDefinition,
    dimensions: Dict[str, int],
    unit_quantity: int = 1,
) -> List[ComputedPiece]:
    """
    Evaluate all component formulas for a given style and dimensions.

    Args:
        style: The StyleDefinition to use
        dimensions: Dict with W, H, and optional X, Y, Z values
        unit_quantity: How many units of this style (multiplies piece quantities)

    Returns:
        List of ComputedPiece objects in component dependency order.

    Raises:
        ValueError if formula evaluation fails or dimensions missing.

    Shared-Name Rule:
        Components sharing the same `name` share the same computed value.
        The first component with a given name is evaluated normally; subsequent
        components with the same name reuse that result without re-evaluating.
        Formulas may also reference components by name (not just component_id).
    """
    if "W" not in dimensions or "H" not in dimensions:
        raise ValueError("dimensions must include W (width) and H (height).")

    # Build the variable scope, starting with W, H, X, Y, Z
    scope: Dict[str, int] = {k: v for k, v in dimensions.items()}

    # Shared-name tracking: name → first computed length/width for that name
    name_length_map: Dict[str, int] = {}
    name_width_map: Dict[str, Optional[int]] = {}

    pieces: List[ComputedPiece] = []

    for component in style.components:
        if component.name in name_length_map:
            # Shared-name rule: reuse the value computed by the first
            # component with this name (e.g. two "Hframe" pieces share H).
            length_mm = name_length_map[component.name]
            width_mm = name_width_map.get(component.name)
        else:
            # Evaluate length formula
            if component.formula_length is None:
                # null formula — frame component
                if component.orientation == Orientation.HORIZONTAL:
                    length_mm = dimensions["W"]
                else:
                    length_mm = dimensions["H"]
            else:
                length_mm = evaluate_formula(component.formula_length, scope)

            # Evaluate width formula (for FILL shapes)
            width_mm = None
            if component.shape_type in (ShapeType.FILL_AREA, ShapeType.FILL_CUT):
                if component.formula_width is not None:
                    width_mm = evaluate_formula(component.formula_width, scope)
                else:
                    width_mm = dimensions["H"]

            # Clamp to non-negative
            length_mm = max(0, length_mm)
            if width_mm is not None:
                width_mm = max(0, width_mm)

            # Cache by name (shared-name rule) and expose name in scope
            # so that subsequent formulas can reference by name as well as
            # component_id (e.g. "Hframe-(9+X)" works when name="Hframe").
            name_length_map[component.name] = length_mm
            name_width_map[component.name] = width_mm
            scope[component.name] = length_mm

        # Always register by component_id for formula cross-references
        scope[component.component_id] = length_mm

        pieces.append(ComputedPiece(
            component_id=component.component_id,
            component_name=component.name,
            material_id=component.material_id,
            shape_type=component.shape_type,
            length_mm=length_mm,
            width_mm=width_mm,
            quantity=component.quantity * unit_quantity,
            offcut_mm=component.offcut_mm,
        ))

    return pieces


def generate_cut_list(
    pieces: List[ComputedPiece],
    stock_lengths: Dict[str, int],
) -> Dict[str, MaterialRequirement]:
    """
    Generate material requirements from computed pieces.

    Uses "fundi-first" logic (largest pieces first) for 1D optimization.
    Uses area-sum approach for 2D optimization.

    Args:
        pieces: Output of compute_pieces()
        stock_lengths: Dict of material_id → standard stock length in mm
                       (e.g. {"ALUMINUM_60x40": 6000, "GLASS_4MM": 2400*1200})
                       For FILL_AREA: value should be sheet_width (area assumed square-ish)

    Returns:
        Dict of material_id → MaterialRequirement
    """
    # Group pieces by material
    by_material: Dict[str, List[ComputedPiece]] = {}
    for piece in pieces:
        by_material.setdefault(piece.material_id, []).append(piece)

    requirements: Dict[str, MaterialRequirement] = {}

    for mat_id, mat_pieces in by_material.items():
        # All pieces for this material should be same shape_type
        # (a material can only be CUT_SHAPE or FILL_*)
        shape_type = mat_pieces[0].shape_type
        stock_len = stock_lengths.get(mat_id, 6000)  # default 6m profiles

        total_length = 0
        total_area = 0
        total_pieces = 0
        all_lengths: List[int] = []

        for piece in mat_pieces:
            for _ in range(piece.quantity):
                if shape_type == ShapeType.CUT_SHAPE:
                    piece_length = piece.total_length_mm
                    total_length += piece_length
                    all_lengths.append(piece_length)
                else:
                    # FILL_AREA or FILL_CUT
                    if piece.width_mm is not None:
                        area = piece.length_mm * piece.width_mm
                    else:
                        area = piece.length_mm * piece.length_mm
                    total_area += area
                total_pieces += 1

        if shape_type == ShapeType.CUT_SHAPE:
            # 1D fundi-first: sort largest first, pack into sticks
            all_lengths.sort(reverse=True)
            sticks_needed, waste = _pack_1d(all_lengths, stock_len)
            waste_pct = int((waste * 100) // (sticks_needed * stock_len)) if sticks_needed > 0 else 0

            requirements[mat_id] = MaterialRequirement(
                material_id=mat_id,
                shape_type=shape_type,
                total_length_mm=total_length,
                total_area_mm2=0,
                pieces=total_pieces,
                stock_length_mm=stock_len,
                estimated_sticks=sticks_needed,
                estimated_sheets=0,
                waste_pct=waste_pct,
            )
        else:
            # 2D: estimate sheets from total area
            # stock_len for FILL = width of sheet (assume square sheet for simplicity)
            sheet_area = stock_len * stock_len
            # Add 15% waste factor for 2D cutting
            adjusted_area = int(total_area * 115 // 100)
            sheets_needed = max(1, (adjusted_area + sheet_area - 1) // sheet_area)
            waste_pct = max(0, 100 - (total_area * 100 // (sheets_needed * sheet_area)))

            requirements[mat_id] = MaterialRequirement(
                material_id=mat_id,
                shape_type=shape_type,
                total_length_mm=0,
                total_area_mm2=total_area,
                pieces=total_pieces,
                stock_length_mm=stock_len,
                estimated_sticks=0,
                estimated_sheets=sheets_needed,
                waste_pct=waste_pct,
            )

    return requirements


def _pack_1d(lengths: List[int], stock_length: int) -> Tuple[int, int]:
    """
    Greedy 1D bin-packing (First-Fit Decreasing).
    Used by generate_cut_list() for single-item cut lists.
    Returns (sticks_needed, total_waste_mm).
    """
    if not lengths:
        return 0, 0

    # Each "bin" is one stick
    sticks: List[int] = []  # remaining space in each stick

    for piece_len in lengths:
        if piece_len > stock_length:
            # Piece longer than stock — needs its own stick (or error)
            # BOS handles this as a multi-piece join (flagged for fundi decision)
            sticks.append(stock_length - piece_len % stock_length if piece_len % stock_length != 0 else 0)
            continue

        # Find first stick with enough space (first-fit decreasing)
        placed = False
        for i, remaining in enumerate(sticks):
            if remaining >= piece_len:
                sticks[i] -= piece_len
                placed = True
                break

        if not placed:
            # Open a new stick
            sticks.append(stock_length - piece_len)

    total_waste = sum(sticks)
    return len(sticks), total_waste


# ══════════════════════════════════════════════════════════════
# PHASE 17: MULTI-ITEM PROJECT — STRUCTURES
# ══════════════════════════════════════════════════════════════
#
# A Project contains N Items (e.g. 200 windows/doors).
# Each Item has a Style + dimensions → produces cut pieces.
# ItemID = 1..N from input order.
#
# The cutting plan labels every cut with its ItemID so the fundi
# knows: "this 1,150mm piece on Bar 3 is for Dirisha #7".
#
# Cutting Optimization:
#   Single-item cut list → FFD (existing generate_cut_list)
#   Multi-item project   → BFD (Best-Fit Decreasing, this phase)
#   BFD difference from FFD: for each piece, instead of placing it
#   in the FIRST bin that fits, we find the bin with the LEAST
#   remaining space that still fits (minimising fragmentation).
#
# Charge Methods:
#   RATE_BASED — price = sum(style_rate × unit_qty) per item
#   COST_BASED — price = sum(bars_used × cost_per_bar) per material
#                        + flat labor_cost


class ChargeMethod(Enum):
    RATE_BASED = "RATE_BASED"   # charge by style rate × unit_quantity per item
    COST_BASED = "COST_BASED"   # charge by actual bars/sheets consumed + labor


@dataclass
class ProjectItem:
    """
    One item in a multi-item project quote.

    Fields:
        item_id:       1..N — position in project (from input order)
        item_label:    Human label e.g. "Dirisha #1", "Door A"
        style:         The StyleDefinition for this item
        dimensions:    {"W": int, "H": int} + optional X/Y/Z
        unit_quantity: How many identical units of this item (default 1)
    """
    item_id: int
    item_label: str
    style: StyleDefinition
    dimensions: Dict[str, int]
    unit_quantity: int = 1

    def __post_init__(self):
        if self.item_id < 1:
            raise ValueError("item_id must be >= 1.")
        if not self.item_label:
            raise ValueError("item_label must be non-empty.")
        if not self.style:
            raise ValueError("style must be provided.")
        if "W" not in self.dimensions or "H" not in self.dimensions:
            raise ValueError("dimensions must include W and H.")
        if self.unit_quantity < 1:
            raise ValueError("unit_quantity must be >= 1.")


@dataclass(frozen=True)
class LabeledPiece:
    """
    A single physical piece (quantity=1) tagged with the ItemID of the
    project item it belongs to.

    Produced by expanding ComputedPiece.quantity into one LabeledPiece per
    physical cut, so that the cutting plan can assign each piece to a bar and
    label it with its ItemID.
    """
    item_id: int
    item_label: str
    component_id: str
    component_name: str
    material_id: str
    shape_type: ShapeType
    length_mm: int
    width_mm: Optional[int]
    offcut_mm: int

    @property
    def total_length_mm(self) -> int:
        """Cut length including offcut/kerf allowance."""
        return self.length_mm + self.offcut_mm


# ══════════════════════════════════════════════════════════════
# CUTTING PLAN STRUCTURES
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CutAllocation:
    """
    One cut assigned to a stock bar or sheet, labeled with its ItemID.
    Used in the Cutting Plan so the fundi knows which window/door
    each cut piece belongs to.
    """
    item_id: int           # which project item owns this piece
    item_label: str        # e.g. "Dirisha #3"
    component_id: str
    component_name: str    # e.g. "Top Frame", "Glass Pane"
    length_mm: int         # piece cut length (not including offcut)
    offcut_mm: int         # kerf/end allowance after this piece
    position_mm: int       # start position from bar/sheet origin


@dataclass(frozen=True)
class StockBar:
    """
    One physical bar (for CUT_SHAPE) or sheet (for FILL_AREA) of stock
    material, with all cut allocations assigned to it.
    """
    bar_index: int                          # 1-based
    stock_length_mm: int                    # total bar/sheet length
    allocations: Tuple[CutAllocation, ...]  # cuts in position order
    waste_mm: int                           # unused material at end


@dataclass(frozen=True)
class CuttingPlan:
    """
    Complete cutting plan for one material across the entire project.
    Shows which pieces (with ItemID labels) go on which bar or sheet.
    """
    material_id: str
    shape_type: ShapeType
    stock_length_mm: int
    bars: Tuple[StockBar, ...]
    total_pieces: int
    total_waste_mm: int
    waste_pct: int          # 0-100


# ══════════════════════════════════════════════════════════════
# BFD — BEST-FIT DECREASING (for project-level cutting plans)
# ══════════════════════════════════════════════════════════════

def _bfd_pack_1d(
    labeled_pieces: List[LabeledPiece],
    stock_length: int,
) -> Tuple[List[StockBar], int]:
    """
    Best-Fit Decreasing (BFD) 1D bin-packing for project cutting plans.

    Algorithm:
        1. Sort pieces by total_length_mm descending (decreasing).
        2. For each piece, find the open bar with the LEAST remaining space
           that still fits the piece (best-fit minimises fragmentation).
        3. If no bar fits, open a new bar.

    Difference from FFD (_pack_1d):
        FFD: first bar that fits.
        BFD: bar with minimum remaining space that still fits.
        BFD wastes less material when piece sizes vary.

    Oversized pieces (> stock_length) are assigned to a dedicated bar and
    flagged — the fundi decides whether to join or special-order stock.

    Returns: (list of StockBar, total_waste_mm)
    """
    if not labeled_pieces:
        return [], 0

    # Sort largest-first (Decreasing part of BFD)
    sorted_pieces = sorted(
        labeled_pieces, key=lambda p: p.total_length_mm, reverse=True
    )

    # Each slot represents an open bar.
    # remaining: space left; position_used: next cut starts here; allocations: cuts so far
    slots: List[Dict] = []

    for piece in sorted_pieces:
        piece_len = piece.total_length_mm

        if piece_len > stock_length:
            # Oversized: own bar, flagged for fundi decision
            alloc = CutAllocation(
                item_id=piece.item_id, item_label=piece.item_label,
                component_id=piece.component_id, component_name=piece.component_name,
                length_mm=piece.length_mm, offcut_mm=piece.offcut_mm,
                position_mm=0,
            )
            slots.append({
                "remaining": 0, "position_used": piece_len,
                "allocations": [alloc], "oversized": True,
            })
            continue

        # Best-Fit: find bar with minimum remaining space >= piece_len
        best_idx = -1
        best_remaining = stock_length + 1  # sentinel

        for i, slot in enumerate(slots):
            if slot.get("oversized"):
                continue
            r = slot["remaining"]
            if r >= piece_len and r < best_remaining:
                best_remaining = r
                best_idx = i

        if best_idx == -1:
            # No bar fits — open a new bar
            alloc = CutAllocation(
                item_id=piece.item_id, item_label=piece.item_label,
                component_id=piece.component_id, component_name=piece.component_name,
                length_mm=piece.length_mm, offcut_mm=piece.offcut_mm,
                position_mm=0,
            )
            slots.append({
                "remaining": stock_length - piece_len,
                "position_used": piece_len,
                "allocations": [alloc],
            })
        else:
            pos = slots[best_idx]["position_used"]
            alloc = CutAllocation(
                item_id=piece.item_id, item_label=piece.item_label,
                component_id=piece.component_id, component_name=piece.component_name,
                length_mm=piece.length_mm, offcut_mm=piece.offcut_mm,
                position_mm=pos,
            )
            slots[best_idx]["remaining"] -= piece_len
            slots[best_idx]["position_used"] += piece_len
            slots[best_idx]["allocations"].append(alloc)

    # Convert to StockBar objects
    bars = [
        StockBar(
            bar_index=i + 1,
            stock_length_mm=stock_length,
            allocations=tuple(slot["allocations"]),
            waste_mm=slot["remaining"],
        )
        for i, slot in enumerate(slots)
    ]
    total_waste = sum(s["remaining"] for s in slots)
    return bars, total_waste


def _pack_2d_labeled(
    pieces: List[LabeledPiece],
    sheet_area: int,
    sheet_width: int,
) -> List[StockBar]:
    """
    Simple area-based 2D sheet packing for FILL_AREA/FILL_CUT materials.
    Groups pieces into sheets (largest-first) by cumulative area.
    Each allocation carries its ItemID for traceability.

    position_mm is cumulative area used on the sheet (proxy for position).
    """
    sorted_pieces = sorted(
        pieces,
        key=lambda p: p.length_mm * (p.width_mm or p.length_mm),
        reverse=True,
    )

    sheets: List[StockBar] = []
    current_allocs: List[CutAllocation] = []
    current_area = 0
    sheet_idx = 0

    for piece in sorted_pieces:
        piece_area = piece.length_mm * (piece.width_mm or piece.length_mm)

        if piece_area > sheet_area:
            # Oversized: own sheet
            alloc = CutAllocation(
                item_id=piece.item_id, item_label=piece.item_label,
                component_id=piece.component_id, component_name=piece.component_name,
                length_mm=piece.length_mm, offcut_mm=0, position_mm=0,
            )
            sheet_idx += 1
            sheets.append(StockBar(
                bar_index=sheet_idx,
                stock_length_mm=sheet_width,
                allocations=(alloc,),
                waste_mm=max(0, sheet_area - piece_area),
            ))
            continue

        if current_area + piece_area > sheet_area and current_allocs:
            # Close current sheet
            sheet_idx += 1
            sheets.append(StockBar(
                bar_index=sheet_idx,
                stock_length_mm=sheet_width,
                allocations=tuple(current_allocs),
                waste_mm=sheet_area - current_area,
            ))
            current_allocs = []
            current_area = 0

        alloc = CutAllocation(
            item_id=piece.item_id, item_label=piece.item_label,
            component_id=piece.component_id, component_name=piece.component_name,
            length_mm=piece.length_mm, offcut_mm=0,
            position_mm=current_area,
        )
        current_allocs.append(alloc)
        current_area += piece_area

    if current_allocs:
        sheet_idx += 1
        sheets.append(StockBar(
            bar_index=sheet_idx,
            stock_length_mm=sheet_width,
            allocations=tuple(current_allocs),
            waste_mm=sheet_area - current_area,
        ))

    return sheets


# ══════════════════════════════════════════════════════════════
# PROJECT PIECE COMPUTATION
# ══════════════════════════════════════════════════════════════

def compute_project_pieces(items: List[ProjectItem]) -> List[LabeledPiece]:
    """
    Expand all project items into individual LabeledPiece records.

    For each item: runs compute_pieces() and expands each ComputedPiece by
    its quantity into separate LabeledPiece records (one per physical piece),
    each tagged with the item's ItemID and label.

    Args:
        items: Project items in input order (item_id must be 1..N)

    Returns:
        Flat list of LabeledPiece — one record per physical cut piece.
    """
    result: List[LabeledPiece] = []
    for item in items:
        computed = compute_pieces(item.style, item.dimensions, item.unit_quantity)
        for piece in computed:
            for _ in range(piece.quantity):
                result.append(LabeledPiece(
                    item_id=item.item_id,
                    item_label=item.item_label,
                    component_id=piece.component_id,
                    component_name=piece.component_name,
                    material_id=piece.material_id,
                    shape_type=piece.shape_type,
                    length_mm=piece.length_mm,
                    width_mm=piece.width_mm,
                    offcut_mm=piece.offcut_mm,
                ))
    return result


# ══════════════════════════════════════════════════════════════
# PROJECT CUTTING PLAN GENERATION (BFD)
# ══════════════════════════════════════════════════════════════

def generate_project_cutting_plan(
    labeled_pieces: List[LabeledPiece],
    stock_lengths: Dict[str, int],
) -> Dict[str, CuttingPlan]:
    """
    Generate a cutting plan for the whole project using BFD optimization.

    For CUT_SHAPE: runs Best-Fit Decreasing across ALL items' pieces,
        producing bars with ItemID-labeled allocations.
    For FILL_AREA/FILL_CUT: packs pieces into sheets by area (largest-first).

    Args:
        labeled_pieces: All individual pieces with ItemID labels
                        (from compute_project_pieces)
        stock_lengths: {material_id: stock_length_mm}

    Returns:
        {material_id: CuttingPlan}
    """
    by_material: Dict[str, List[LabeledPiece]] = {}
    for p in labeled_pieces:
        by_material.setdefault(p.material_id, []).append(p)

    plans: Dict[str, CuttingPlan] = {}

    for mat_id, pieces in by_material.items():
        shape_type = pieces[0].shape_type
        stock_len = stock_lengths.get(mat_id, 6000)

        if shape_type == ShapeType.CUT_SHAPE:
            bars, total_waste = _bfd_pack_1d(pieces, stock_len)
            total_used = len(bars) * stock_len
            waste_pct = int(total_waste * 100 // total_used) if total_used > 0 else 0
            plans[mat_id] = CuttingPlan(
                material_id=mat_id,
                shape_type=shape_type,
                stock_length_mm=stock_len,
                bars=tuple(bars),
                total_pieces=len(pieces),
                total_waste_mm=total_waste,
                waste_pct=waste_pct,
            )
        else:
            # FILL_AREA / FILL_CUT: area-based sheet packing
            sheet_area = stock_len * stock_len
            sheets = _pack_2d_labeled(pieces, sheet_area, stock_len)
            total_piece_area = sum(
                p.length_mm * (p.width_mm or p.length_mm) for p in pieces
            )
            total_used_area = len(sheets) * sheet_area
            waste_mm = max(0, total_used_area - total_piece_area)
            waste_pct = int(waste_mm * 100 // total_used_area) if total_used_area > 0 else 0
            plans[mat_id] = CuttingPlan(
                material_id=mat_id,
                shape_type=shape_type,
                stock_length_mm=stock_len,
                bars=tuple(sheets),
                total_pieces=len(pieces),
                total_waste_mm=waste_mm,
                waste_pct=waste_pct,
            )

    return plans


# ══════════════════════════════════════════════════════════════
# CHARGE COMPUTATION
# ══════════════════════════════════════════════════════════════

def compute_charge_rate_based(
    items: List[ProjectItem],
    style_rates: Dict[str, int],
) -> int:
    """
    Rate-based pricing: sum(rate_per_unit × unit_quantity) for each item.

    Args:
        items: Project items (each has style.style_id and unit_quantity)
        style_rates: {style_id: rate in minor currency units per unit}
                     Items whose style_id is not in style_rates contribute 0.

    Returns:
        Total cost in minor currency units (e.g. cents or TZS).
    """
    total = 0
    for item in items:
        rate = style_rates.get(item.style.style_id, 0)
        total += rate * item.unit_quantity
    return total


def compute_charge_cost_based(
    cutting_plans: Dict[str, CuttingPlan],
    material_cost_rates: Dict[str, int],
    labor_cost: int = 0,
) -> int:
    """
    Cost-based pricing: sum(bars_used × cost_per_bar) for each material
    plus a flat labor cost.

    The workshop buys whole bars/sheets, so cost is based on the number of
    bars consumed (not just net piece lengths). Waste is the workshop's cost.

    Args:
        cutting_plans: Output of generate_project_cutting_plan()
        material_cost_rates: {material_id: cost_per_bar/sheet in minor units}
                             Materials not in rates contribute 0.
        labor_cost: Additional labor cost in minor currency units (default 0).

    Returns:
        Total cost in minor currency units.
    """
    total = labor_cost
    for mat_id, plan in cutting_plans.items():
        cost_per_bar = material_cost_rates.get(mat_id, 0)
        total += len(plan.bars) * cost_per_bar
    return total
