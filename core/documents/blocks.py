"""
BOS Documents - Block System
=============================
Defines the allowed block types for document templates.

Blocks are the named, typed sections of a document.
Each block type has a canonical identifier, allowed fields, and render semantics.

Doctrine:
- No raw HTML injection.
- Block order is declared by the template; renderer honours it.
- User may toggle or reorder within constraints (see scope-policy).
- Same block spec → same rendered output (deterministic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Block type identifiers (canonical, immutable)
# ---------------------------------------------------------------------------

BLOCK_HEADER = "HEADER"          # Document title, number, date, branch/business info
BLOCK_PARTY = "PARTY"            # Seller / Buyer parties
BLOCK_META = "META"              # Document metadata (ref numbers, PO, etc.)
BLOCK_ITEM_TABLE = "ITEM_TABLE"  # Line items table
BLOCK_TOTALS = "TOTALS"          # Subtotal, taxes, discounts, grand total
BLOCK_PAYMENT = "PAYMENT"        # Payment details, method, due date
BLOCK_COMPLIANCE = "COMPLIANCE"  # Fiscal/compliance fields (QR, fiscal no, etc.)
BLOCK_NOTES = "NOTES"            # Free notes / terms (structured text, not HTML)
BLOCK_QR = "QR"                  # QR code block (content is a URL or structured string)

VALID_BLOCK_TYPES = frozenset({
    BLOCK_HEADER,
    BLOCK_PARTY,
    BLOCK_META,
    BLOCK_ITEM_TABLE,
    BLOCK_TOTALS,
    BLOCK_PAYMENT,
    BLOCK_COMPLIANCE,
    BLOCK_NOTES,
    BLOCK_QR,
})

# ---------------------------------------------------------------------------
# Block field descriptors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BlockField:
    """Declares one field within a block."""
    key: str           # field key in the render_plan payload
    required: bool = True
    label: str = ""    # human-readable label (optional, used by renderer)


# ---------------------------------------------------------------------------
# Block definitions per block type
# ---------------------------------------------------------------------------

BLOCK_FIELD_DEFINITIONS: dict[str, tuple[BlockField, ...]] = {
    BLOCK_HEADER: (
        BlockField("doc_type", required=True, label="Document Type"),
        BlockField("doc_number", required=True, label="Number"),
        BlockField("issued_at", required=True, label="Date"),
        BlockField("business_name", required=False, label="Business"),
        BlockField("branch_name", required=False, label="Branch"),
    ),
    BLOCK_PARTY: (
        BlockField("seller_name", required=False, label="From"),
        BlockField("seller_address", required=False, label="Address"),
        BlockField("seller_tax_id", required=False, label="Tax ID"),
        BlockField("buyer_name", required=False, label="To"),
        BlockField("buyer_address", required=False, label="Address"),
        BlockField("buyer_tax_id", required=False, label="Tax ID"),
    ),
    BLOCK_META: (
        BlockField("reference", required=False, label="Reference"),
        BlockField("purchase_order", required=False, label="PO Number"),
        BlockField("currency", required=False, label="Currency"),
    ),
    BLOCK_ITEM_TABLE: (
        BlockField("line_items", required=True, label="Items"),
    ),
    BLOCK_TOTALS: (
        BlockField("subtotal", required=False, label="Subtotal"),
        BlockField("discount_total", required=False, label="Discount"),
        BlockField("tax_total", required=False, label="Tax"),
        BlockField("grand_total", required=True, label="Total"),
        BlockField("currency", required=False, label="Currency"),
    ),
    BLOCK_PAYMENT: (
        BlockField("payment_method", required=False, label="Method"),
        BlockField("payment_terms", required=False, label="Terms"),
        BlockField("due_date", required=False, label="Due Date"),
        BlockField("amount_paid", required=False, label="Paid"),
        BlockField("amount_due", required=False, label="Amount Due"),
    ),
    BLOCK_COMPLIANCE: (
        BlockField("fiscal_number", required=False, label="Fiscal Number"),
        BlockField("compliance_profile_id", required=False, label="Compliance Profile"),
        BlockField("compliance_notes", required=False, label="Compliance Notes"),
    ),
    BLOCK_NOTES: (
        BlockField("notes", required=False, label="Notes"),
        BlockField("terms", required=False, label="Terms & Conditions"),
    ),
    BLOCK_QR: (
        BlockField("qr_content", required=True, label="QR Content"),
        BlockField("qr_label", required=False, label="QR Label"),
    ),
}


# ---------------------------------------------------------------------------
# Block instance (as declared in a template)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BlockSpec:
    """
    Declares a block's presence and configuration within a template.

    block_type: one of VALID_BLOCK_TYPES
    enabled: if False, block is skipped during rendering
    label_override: optional custom label for this block
    field_overrides: optional per-field label overrides
    data_key: optional key into render_plan to find this block's data
              (defaults to block_type.lower())
    """
    block_type: str
    enabled: bool = True
    label_override: str = ""
    field_overrides: dict[str, str] = field(default_factory=dict)
    data_key: str = ""

    def __post_init__(self):
        if self.block_type not in VALID_BLOCK_TYPES:
            raise ValueError(
                f"block_type '{self.block_type}' is not valid. "
                f"Must be one of: {sorted(VALID_BLOCK_TYPES)}"
            )
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be bool.")
        if not isinstance(self.label_override, str):
            raise ValueError("label_override must be str.")
        if not isinstance(self.field_overrides, dict):
            raise ValueError("field_overrides must be dict.")

    def effective_data_key(self) -> str:
        return self.data_key if self.data_key else self.block_type.lower()

    def field_definitions(self) -> tuple[BlockField, ...]:
        return BLOCK_FIELD_DEFINITIONS.get(self.block_type, ())


# ---------------------------------------------------------------------------
# Block spec parsing from layout_spec dict
# ---------------------------------------------------------------------------

def parse_blocks_from_layout_spec(layout_spec: dict) -> tuple[BlockSpec, ...]:
    """
    Parse a 'blocks' list from layout_spec into BlockSpec instances.

    layout_spec may contain an optional 'blocks' key:
      {
        "blocks": [
          {"block_type": "HEADER", "enabled": true},
          {"block_type": "ITEM_TABLE"},
          {"block_type": "TOTALS"},
          ...
        ],
        ...
      }

    If 'blocks' is absent, returns an empty tuple (caller uses legacy layout).
    """
    raw_blocks = layout_spec.get("blocks")
    if not isinstance(raw_blocks, (list, tuple)):
        return ()

    result: list[BlockSpec] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_blocks):
        if not isinstance(raw, dict):
            raise ValueError(f"blocks[{index}] must be a dict.")
        block_type = raw.get("block_type")
        if not isinstance(block_type, str) or not block_type:
            raise ValueError(f"blocks[{index}].block_type must be a non-empty string.")
        if block_type not in VALID_BLOCK_TYPES:
            raise ValueError(
                f"blocks[{index}].block_type '{block_type}' is not valid."
            )
        if block_type in seen:
            raise ValueError(
                f"blocks[{index}].block_type '{block_type}' is declared more than once."
            )
        seen.add(block_type)

        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"blocks[{index}].enabled must be bool.")

        label_override = raw.get("label_override", "")
        if not isinstance(label_override, str):
            raise ValueError(f"blocks[{index}].label_override must be str.")

        field_overrides = raw.get("field_overrides", {})
        if not isinstance(field_overrides, dict):
            raise ValueError(f"blocks[{index}].field_overrides must be dict.")

        data_key = raw.get("data_key", "")
        if not isinstance(data_key, str):
            raise ValueError(f"blocks[{index}].data_key must be str.")

        result.append(BlockSpec(
            block_type=block_type,
            enabled=enabled,
            label_override=label_override,
            field_overrides=dict(field_overrides),
            data_key=data_key,
        ))

    return tuple(result)


def extract_block_data(
    render_plan: dict,
    block_spec: BlockSpec,
) -> dict[str, Any]:
    """
    Extract data for a specific block from the render_plan.

    Convention: render_plan stores block data under 'blocks.<block_type.lower()>'
    or under block_spec.effective_data_key().
    Falls back to top-level render_plan keys for legacy plans.
    """
    # Try structured blocks data first
    blocks_section = render_plan.get("blocks")
    if isinstance(blocks_section, dict):
        key = block_spec.effective_data_key()
        data = blocks_section.get(key)
        if isinstance(data, dict):
            return data

    # Legacy fallback: use header/totals/footer top-level keys
    fallback_map = {
        BLOCK_HEADER: render_plan.get("header", {}),
        BLOCK_TOTALS: render_plan.get("totals", {}),
        BLOCK_NOTES: render_plan.get("footer", {}),
        BLOCK_ITEM_TABLE: {"line_items": render_plan.get("line_items", [])},
    }
    return fallback_map.get(block_spec.block_type, {})
