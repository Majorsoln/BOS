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
    """
    if "W" not in dimensions or "H" not in dimensions:
        raise ValueError("dimensions must include W (width) and H (height).")

    # Build the variable scope, starting with W, H, X, Y, Z
    scope: Dict[str, int] = {k: v for k, v in dimensions.items()}

    pieces: List[ComputedPiece] = []

    for component in style.components:
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
        width_mm: Optional[int] = None
        if component.shape_type in (ShapeType.FILL_AREA, ShapeType.FILL_CUT):
            if component.formula_width is not None:
                width_mm = evaluate_formula(component.formula_width, scope)
            else:
                # If no width formula, use H (height dimension)
                width_mm = dimensions["H"]

        # Clamp to non-negative (negative cutting doesn't make sense)
        length_mm = max(0, length_mm)
        if width_mm is not None:
            width_mm = max(0, width_mm)

        # Register this component's computed value for subsequent formulas
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
    Greedy 1D bin-packing (largest-first).
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
