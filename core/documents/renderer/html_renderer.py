"""
BOS Documents - HTML Preview Renderer
======================================
Converts a render_plan dict into a safe, deterministic HTML string.

Doctrine:
- All user-supplied content is HTML-escaped (no XSS).
- No raw HTML injection from templates or payloads.
- Same render_plan → same HTML output (deterministic).
- Component-based: each block type renders independently.
- No external dependencies (stdlib html.escape only).
- PDF and HTML derived from the same render_plan snapshot.
"""

from __future__ import annotations

import html
from typing import Any

from core.documents.blocks import (
    BLOCK_COMPLIANCE,
    BLOCK_HEADER,
    BLOCK_ITEM_TABLE,
    BLOCK_META,
    BLOCK_NOTES,
    BLOCK_PARTY,
    BLOCK_PAYMENT,
    BLOCK_QR,
    BLOCK_TOTALS,
    BlockSpec,
    extract_block_data,
    parse_blocks_from_layout_spec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _e(value: Any) -> str:
    """HTML-escape any value to a safe string."""
    return html.escape(str(value) if value is not None else "", quote=True)


def _fmt_value(value: Any) -> str:
    """Format a value for display inside a table cell or paragraph."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_fmt_value(item) for item in value)
    if isinstance(value, dict):
        parts = []
        for k, v in sorted(value.items()):
            parts.append(f"{_e(k)}: {_e(v)}")
        return " | ".join(parts)
    return _e(value)


def _kv_table(rows: list[tuple[str, Any]], *, css_class: str = "") -> str:
    """Render a key-value table."""
    class_attr = f' class="{_e(css_class)}"' if css_class else ""
    lines = [f"<table{class_attr}>"]
    for label, value in rows:
        lines.append(
            f"  <tr>"
            f"<th>{_e(label)}</th>"
            f"<td>{_fmt_value(value)}</td>"
            f"</tr>"
        )
    lines.append("</table>")
    return "\n".join(lines)


def _section(title: str, body: str, *, css_class: str = "") -> str:
    class_attr = f' class="{_e(css_class)}"' if css_class else ""
    return (
        f'<section{class_attr}>\n'
        f'  <h2>{_e(title)}</h2>\n'
        f'{body}\n'
        f'</section>'
    )


# ---------------------------------------------------------------------------
# Block renderers
# ---------------------------------------------------------------------------

def _render_header_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Document"
    doc_number = data.get("doc_number") or data.get("receipt_no") or data.get("invoice_no") or data.get("quote_no") or ""
    issued_at = data.get("issued_at", "")
    doc_type = data.get("doc_type", "")
    business_name = data.get("business_name", "")
    branch_name = data.get("branch_name", "")

    rows = []
    if doc_type:
        rows.append(("Type", doc_type))
    if doc_number:
        rows.append(("Number", doc_number))
    if issued_at:
        rows.append(("Date", issued_at))
    if business_name:
        rows.append(("Business", business_name))
    if branch_name:
        rows.append(("Branch", branch_name))

    # Include any other header fields
    known = {"doc_number", "receipt_no", "invoice_no", "quote_no", "issued_at", "doc_type", "business_name", "branch_name"}
    for key, value in sorted(data.items()):
        if key not in known and value is not None:
            rows.append((_e(key).replace("_", " ").title(), value))

    body = _kv_table(rows, css_class="header-table") if rows else ""
    return _section(title, body, css_class="block-header")


def _render_party_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Parties"
    seller_rows = []
    buyer_rows = []
    other_rows = []
    seller_keys = {"seller_name", "seller_address", "seller_tax_id"}
    buyer_keys = {"buyer_name", "buyer_address", "buyer_tax_id"}

    for key, value in sorted(data.items()):
        if value is None:
            continue
        label = key.replace("_", " ").title()
        if key in seller_keys:
            seller_rows.append((label.replace("Seller ", ""), value))
        elif key in buyer_keys:
            buyer_rows.append((label.replace("Buyer ", ""), value))
        else:
            other_rows.append((label, value))

    parts = []
    if seller_rows:
        parts.append(f'<div class="party seller"><strong>From</strong>\n{_kv_table(seller_rows)}</div>')
    if buyer_rows:
        parts.append(f'<div class="party buyer"><strong>To</strong>\n{_kv_table(buyer_rows)}</div>')
    if other_rows:
        parts.append(_kv_table(other_rows))

    body = "\n".join(parts)
    return _section(title, body, css_class="block-party")


def _render_meta_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Reference"
    rows = []
    for key, value in sorted(data.items()):
        if value is not None:
            rows.append((key.replace("_", " ").title(), value))
    body = _kv_table(rows, css_class="meta-table") if rows else "<p>—</p>"
    return _section(title, body, css_class="block-meta")


def _render_item_table_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Items"
    line_items = data.get("line_items", [])
    if not isinstance(line_items, (list, tuple)) or not line_items:
        return _section(title, "<p>No items.</p>", css_class="block-item-table")

    # Collect all column headers deterministically
    all_keys: list[str] = []
    seen_keys: set[str] = set()
    for item in line_items:
        if isinstance(item, dict):
            for key in item:
                if key not in seen_keys:
                    all_keys.append(key)
                    seen_keys.add(key)

    header_cells = "".join(
        f"<th>{_e(k.replace('_', ' ').title())}</th>" for k in all_keys
    )
    rows_html = [f"<thead><tr>{header_cells}</tr></thead>"]
    rows_html.append("<tbody>")
    for item in line_items:
        if not isinstance(item, dict):
            continue
        cells = "".join(
            f"<td>{_fmt_value(item.get(k))}</td>" for k in all_keys
        )
        rows_html.append(f"<tr>{cells}</tr>")
    rows_html.append("</tbody>")

    body = f'<table class="item-table">\n' + "\n".join(rows_html) + "\n</table>"
    return _section(title, body, css_class="block-item-table")


def _render_totals_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Totals"
    currency = data.get("currency", "")
    rows = []
    priority_keys = ("subtotal", "discount_total", "tax_total", "grand_total")
    seen: set[str] = set()
    for key in priority_keys:
        if key in data and data[key] is not None:
            label = key.replace("_", " ").title()
            value = data[key]
            display = f"{currency} {_fmt_value(value)}" if currency else _fmt_value(value)
            rows.append((label, display))
            seen.add(key)
    for key, value in sorted(data.items()):
        if key not in seen and key != "currency" and value is not None:
            label = key.replace("_", " ").title()
            display = f"{currency} {_fmt_value(value)}" if currency else _fmt_value(value)
            rows.append((label, display))

    body = _kv_table(rows, css_class="totals-table") if rows else "<p>—</p>"
    return _section(title, body, css_class="block-totals")


def _render_payment_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Payment"
    rows = []
    for key, value in sorted(data.items()):
        if value is not None:
            rows.append((key.replace("_", " ").title(), value))
    body = _kv_table(rows, css_class="payment-table") if rows else "<p>—</p>"
    return _section(title, body, css_class="block-payment")


def _render_compliance_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Compliance"
    rows = []
    for key, value in sorted(data.items()):
        if value is not None:
            rows.append((key.replace("_", " ").title(), value))
    body = _kv_table(rows, css_class="compliance-table") if rows else "<p>—</p>"
    return _section(title, body, css_class="block-compliance")


def _render_notes_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "Notes"
    parts = []
    notes = data.get("notes")
    terms = data.get("terms")
    if notes:
        parts.append(f"<p>{_e(notes)}</p>")
    if terms:
        parts.append(f"<p><strong>Terms:</strong> {_e(terms)}</p>")
    for key, value in sorted(data.items()):
        if key not in {"notes", "terms"} and value is not None:
            parts.append(f"<p><strong>{_e(key.replace('_',' ').title())}:</strong> {_e(value)}</p>")
    body = "\n".join(parts) if parts else "<p>—</p>"
    return _section(title, body, css_class="block-notes")


def _render_qr_block(data: dict, spec: BlockSpec) -> str:
    title = spec.label_override or "QR Code"
    qr_content = data.get("qr_content", "")
    qr_label = data.get("qr_label", "")
    # In HTML preview we render the QR content as text and a placeholder
    body_parts = []
    if qr_content:
        body_parts.append(
            f'<div class="qr-placeholder">'
            f'<p class="qr-label">{_e(qr_label) if qr_label else "QR Code"}</p>'
            f'<p class="qr-content"><code>{_e(qr_content)}</code></p>'
            f'</div>'
        )
    else:
        body_parts.append("<p>—</p>")
    return _section(title, "\n".join(body_parts), css_class="block-qr")


_BLOCK_RENDERERS = {
    BLOCK_HEADER: _render_header_block,
    BLOCK_PARTY: _render_party_block,
    BLOCK_META: _render_meta_block,
    BLOCK_ITEM_TABLE: _render_item_table_block,
    BLOCK_TOTALS: _render_totals_block,
    BLOCK_PAYMENT: _render_payment_block,
    BLOCK_COMPLIANCE: _render_compliance_block,
    BLOCK_NOTES: _render_notes_block,
    BLOCK_QR: _render_qr_block,
}


# ---------------------------------------------------------------------------
# Legacy layout fallback renderer (for templates without blocks)
# ---------------------------------------------------------------------------

def _render_legacy_layout(render_plan: dict) -> str:
    """
    Render a render_plan that uses the legacy layout_spec format
    (header_fields / line_items / totals / footer) without a blocks list.
    """
    parts: list[str] = []

    # Header section
    header = render_plan.get("header", {})
    if header:
        rows = [(k.replace("_", " ").title(), v) for k, v in sorted(header.items())]
        parts.append(_section("Header", _kv_table(rows, css_class="header-table"), css_class="block-header"))

    # Line items
    line_items = render_plan.get("line_items", [])
    if line_items:
        parts.append(_render_item_table_block(
            {"line_items": line_items},
            BlockSpec(block_type=BLOCK_ITEM_TABLE),
        ))

    # Totals
    totals = render_plan.get("totals", {})
    if totals:
        parts.append(_render_totals_block(totals, BlockSpec(block_type=BLOCK_TOTALS)))

    # Footer (notes)
    footer = render_plan.get("footer", {})
    if footer:
        parts.append(_render_notes_block(footer, BlockSpec(block_type=BLOCK_NOTES)))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Embedded CSS
# ---------------------------------------------------------------------------

_DOCUMENT_CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 13px;
  color: #111;
  background: #fff;
  padding: 32px;
  max-width: 800px;
  margin: 0 auto;
}
h1.doc-title { font-size: 22px; margin-bottom: 24px; border-bottom: 2px solid #333; padding-bottom: 8px; }
section { margin-bottom: 20px; }
section h2 { font-size: 14px; font-weight: bold; color: #333; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 5px 8px; border: 1px solid #ddd; }
th { background: #f5f5f5; font-weight: bold; white-space: nowrap; width: 180px; }
table.item-table th { width: auto; }
.block-totals table { max-width: 360px; margin-left: auto; }
.block-totals tr:last-child td, .block-totals tr:last-child th { font-weight: bold; border-top: 2px solid #333; }
.party { display: inline-block; width: 48%; vertical-align: top; margin-right: 2%; }
.qr-placeholder { border: 1px dashed #aaa; padding: 12px; text-align: center; max-width: 200px; }
.qr-content code { font-size: 11px; word-break: break-all; }
footer.doc-footer { margin-top: 32px; font-size: 11px; color: #666; border-top: 1px solid #eee; padding-top: 8px; }
@media print {
  body { padding: 0; max-width: none; }
  section { page-break-inside: avoid; }
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_html(
    render_plan: dict,
    *,
    layout_spec: dict | None = None,
    doc_hash: str | None = None,
) -> str:
    """
    Render a render_plan dict to a complete, safe HTML document string.

    Args:
        render_plan: the render plan produced by DocumentBuilder
        layout_spec: optional template layout_spec dict (for block ordering)
        doc_hash: optional document hash to embed in the footer

    Returns:
        A complete HTML document string (DOCTYPE + html + head + body).
    """
    if not isinstance(render_plan, dict):
        raise ValueError("render_plan must be a dict.")

    doc_type = render_plan.get("doc_type", "DOCUMENT")
    template_id = render_plan.get("template_id", "")
    template_version = render_plan.get("template_version", "")

    # Determine block order from layout_spec
    blocks: tuple[BlockSpec, ...] = ()
    if isinstance(layout_spec, dict):
        try:
            blocks = parse_blocks_from_layout_spec(layout_spec)
        except ValueError:
            blocks = ()

    body_sections: list[str] = []

    if blocks:
        for block_spec in blocks:
            if not block_spec.enabled:
                continue
            renderer = _BLOCK_RENDERERS.get(block_spec.block_type)
            if renderer is None:
                continue
            data = extract_block_data(render_plan, block_spec)
            body_sections.append(renderer(data, block_spec))
    else:
        body_sections.append(_render_legacy_layout(render_plan))

    title_text = f"{_e(doc_type)}"
    if template_id:
        title_text += f" &mdash; {_e(str(template_id))}"

    footer_parts = []
    if template_version:
        footer_parts.append(f"Template v{_e(str(template_version))}")
    if doc_hash:
        footer_parts.append(f"Hash: {_e(doc_hash[:16])}…")

    footer_html = (
        f'<footer class="doc-footer">{" | ".join(footer_parts)}</footer>'
        if footer_parts
        else ""
    )

    html_doc = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"  <title>{_e(doc_type)}</title>\n"
        "  <style>\n"
        + _DOCUMENT_CSS
        + "\n  </style>\n"
        "</head>\n"
        "<body>\n"
        f'<h1 class="doc-title">{title_text}</h1>\n'
        + "\n".join(body_sections)
        + "\n"
        + footer_html
        + "\n</body>\n</html>"
    )
    return html_doc
