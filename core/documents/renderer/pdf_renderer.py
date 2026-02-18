"""
BOS Documents - PDF Renderer
==============================
Generates a minimal, deterministic PDF from a render_plan dict.

Implementation: pure Python stdlib — no external dependencies.
Generates a valid PDF 1.4 file with Helvetica text (built-in PDF font).

Doctrine:
- Same render_plan → same PDF bytes (deterministic, given same timestamp arg).
- All content is escaped for PDF string encoding.
- No arbitrary code execution from template content.
- PDF is derived from the same render_plan as the HTML renderer.
- Hash of render_plan (not PDF bytes) is the canonical artifact identifier.
"""

from __future__ import annotations

import io
from typing import Any


# ---------------------------------------------------------------------------
# PDF string encoding
# ---------------------------------------------------------------------------

def _pdf_str(value: Any) -> str:
    """Encode a value as a PDF literal string (parentheses form)."""
    text = str(value) if value is not None else ""
    # Escape backslash and parentheses as required by PDF spec
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # Limit line length by replacing non-ASCII with '?'
    safe = "".join(c if ord(c) < 128 else "?" for c in text)
    return f"({safe})"


def _fmt(value: Any) -> str:
    """Format a value for display in the PDF (plain text)."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_fmt(item) for item in value)
    if isinstance(value, dict):
        return " | ".join(f"{k}: {_fmt(v)}" for k, v in sorted(value.items()))
    return str(value)


# ---------------------------------------------------------------------------
# Minimal PDF writer
# ---------------------------------------------------------------------------

class _PdfWriter:
    """
    Writes a minimal, valid PDF 1.4 file.

    Page size: A4 (595 x 842 pts)
    Font: Helvetica (built-in, no embedding required)
    Content model: lines of text, auto-pagination.
    """

    PAGE_W = 595
    PAGE_H = 842
    MARGIN_LEFT = 50
    MARGIN_RIGHT = 50
    MARGIN_TOP = 790
    MARGIN_BOTTOM = 50
    LINE_HEIGHT_NORMAL = 16
    LINE_HEIGHT_HEADING = 20
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_HEADING = 13
    FONT_SIZE_TITLE = 16

    def __init__(self):
        self._objects: list[bytes] = []  # raw PDF objects (excluding header)
        self._offsets: list[int] = []
        self._pages: list[int] = []     # object IDs of page objects
        self._current_stream_lines: list[str] = []
        self._y: float = self.MARGIN_TOP
        self._buf = io.BytesIO()

    # -- low-level object management ----------------------------------------

    def _add_object(self, content: str) -> int:
        """Add a PDF object and return its 1-based object ID."""
        obj_id = len(self._objects) + 1
        self._objects.append(content.encode("latin-1"))
        return obj_id

    # -- stream line helpers -------------------------------------------------

    def _push_line(self, text: str, *, bold: bool = False, size: int | None = None, y: float | None = None) -> None:
        """Add a text line to the current page stream."""
        if y is None:
            y = self._y
        font = "/F2" if bold else "/F1"
        sz = size or self.FONT_SIZE_NORMAL
        self._current_stream_lines.append(
            f"BT {font} {sz} Tf {self.MARGIN_LEFT} {y:.2f} Td {_pdf_str(text)} Tj ET"
        )

    def _push_hline(self, y: float) -> None:
        """Draw a horizontal rule."""
        x1 = self.MARGIN_LEFT
        x2 = self.PAGE_W - self.MARGIN_RIGHT
        self._current_stream_lines.append(
            f"{x1} {y:.2f} m {x2} {y:.2f} l S"
        )

    # -- page management -----------------------------------------------------

    def _flush_page(self) -> int:
        """Serialise the current page stream to a PDF content stream object."""
        stream_text = "\n".join(self._current_stream_lines)
        stream_bytes = stream_text.encode("latin-1")
        length = len(stream_bytes)
        stream_obj = (
            f"<< /Length {length} >>\nstream\n"
            + stream_text
            + "\nendstream"
        )
        stream_id = self._add_object(stream_obj)
        self._current_stream_lines = []
        self._y = self.MARGIN_TOP
        return stream_id

    def _finish_page(self) -> None:
        """Flush content stream and register a page object."""
        stream_id = self._flush_page()
        page_id = self._add_object(
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {self.PAGE_W} {self.PAGE_H}] "
            f"/Contents {stream_id} 0 R "
            f"/Resources << /Font << "
            f"/F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> "
            f"/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> "
            f">> >> >>"
        )
        self._pages.append(page_id)

    def _ensure_space(self, needed: float) -> None:
        """Start a new page if there is not enough vertical space."""
        if self._y - needed < self.MARGIN_BOTTOM:
            self._finish_page()

    # -- content helpers -----------------------------------------------------

    def add_title(self, text: str) -> None:
        self._ensure_space(self.LINE_HEIGHT_TITLE if hasattr(self, "LINE_HEIGHT_TITLE") else 28)
        self._push_line(text, bold=True, size=self.FONT_SIZE_TITLE, y=self._y)
        self._y -= self.LINE_HEIGHT_HEADING
        self._push_hline(self._y)
        self._y -= 4

    def add_heading(self, text: str) -> None:
        self._ensure_space(self.LINE_HEIGHT_HEADING + 8)
        self._y -= 6
        self._push_line(text, bold=True, size=self.FONT_SIZE_HEADING, y=self._y)
        self._y -= self.LINE_HEIGHT_HEADING

    def add_kv(self, label: str, value: Any, *, indent: int = 0) -> None:
        self._ensure_space(self.LINE_HEIGHT_NORMAL)
        x = self.MARGIN_LEFT + indent
        label_text = f"{label}:"
        value_text = _fmt(value)
        # Label at x, value at x+120
        self._current_stream_lines.append(
            f"BT /F2 {self.FONT_SIZE_NORMAL} Tf {x} {self._y:.2f} Td {_pdf_str(label_text)} Tj ET"
        )
        self._current_stream_lines.append(
            f"BT /F1 {self.FONT_SIZE_NORMAL} Tf {x + 120} {self._y:.2f} Td {_pdf_str(value_text)} Tj ET"
        )
        self._y -= self.LINE_HEIGHT_NORMAL

    def add_text(self, text: str) -> None:
        self._ensure_space(self.LINE_HEIGHT_NORMAL)
        self._push_line(text, y=self._y)
        self._y -= self.LINE_HEIGHT_NORMAL

    def add_separator(self) -> None:
        self._ensure_space(8)
        self._y -= 4
        self._push_hline(self._y)
        self._y -= 4

    def add_table_header(self, columns: list[str], col_widths: list[float]) -> None:
        self._ensure_space(self.LINE_HEIGHT_NORMAL + 4)
        x = self.MARGIN_LEFT
        for col_text, width in zip(columns, col_widths):
            self._current_stream_lines.append(
                f"BT /F2 {self.FONT_SIZE_NORMAL} Tf {x:.2f} {self._y:.2f} Td {_pdf_str(col_text)} Tj ET"
            )
            x += width
        self._y -= self.LINE_HEIGHT_NORMAL
        self._push_hline(self._y)
        self._y -= 2

    def add_table_row(self, cells: list[Any], col_widths: list[float]) -> None:
        self._ensure_space(self.LINE_HEIGHT_NORMAL)
        x = self.MARGIN_LEFT
        for cell_value, width in zip(cells, col_widths):
            text = _fmt(cell_value)
            # Truncate to fit column (rough approximation: ~6px per char)
            max_chars = max(4, int(width / 6))
            if len(text) > max_chars:
                text = text[: max_chars - 1] + "…"
            self._current_stream_lines.append(
                f"BT /F1 {self.FONT_SIZE_NORMAL} Tf {x:.2f} {self._y:.2f} Td {_pdf_str(text)} Tj ET"
            )
            x += width
        self._y -= self.LINE_HEIGHT_NORMAL

    def add_vspace(self, pts: float = 8) -> None:
        self._y -= pts

    # -- finalise ------------------------------------------------------------

    def build(self) -> bytes:
        """Flush remaining content, build xref table, return PDF bytes."""
        if self._current_stream_lines:
            self._finish_page()

        if not self._pages:
            # Ensure at least one page
            self._finish_page()

        # Now we have:
        # objects 1..N already in self._objects
        # We need to prepend:
        #   obj 1 = Catalog
        #   obj 2 = Pages
        # These are inserted at position 0 and 1 (prepend), but IDs were already
        # assigned during add_object calls. We need a different approach.
        # Reset and rebuild properly.
        return self._serialise()

    def _serialise(self) -> bytes:
        """
        Serialise all objects, build xref, return complete PDF bytes.
        Object layout:
          1: Catalog
          2: Pages
          3..N: content streams + page objects (already in self._objects at 0-based indices)
        """
        # Recalculate: objects are already in order, page IDs are 1-based
        # We need to shift: prepend catalog (id=1) and pages (id=2)
        # Total objects = 2 + len(self._objects)

        all_page_ids = []
        # self._pages contains the 1-based IDs of page objects within self._objects
        # After prepending 2 objects, each id shifts by 2
        shifted_page_ids = [pid + 2 for pid in self._pages]
        kids_str = " ".join(f"{pid} 0 R" for pid in shifted_page_ids)

        catalog_str = "<< /Type /Catalog /Pages 2 0 R >>"
        pages_str = (
            f"<< /Type /Pages /Kids [{kids_str}] /Count {len(shifted_page_ids)} >>"
        )

        # Now we also need to shift all "X 0 R" references inside existing objects
        # by +2. We do this with simple string replacement.
        shifted_objects: list[bytes] = []
        for i, obj_bytes in enumerate(self._objects):
            obj_str = obj_bytes.decode("latin-1")
            # Replace all "N 0 R" with "(N+2) 0 R"
            import re
            def _shift_ref(m):
                original_id = int(m.group(1))
                return f"{original_id + 2} 0 R"
            obj_str = re.sub(r"(\d+) 0 R", _shift_ref, obj_str)
            shifted_objects.append(obj_str.encode("latin-1"))

        # Build PDF body
        out = io.BytesIO()
        out.write(b"%PDF-1.4\n")
        out.write(b"%\xe2\xe3\xcf\xd3\n")  # binary comment (signals binary file)

        offsets: list[int] = []

        def write_obj(obj_id: int, content: str) -> None:
            offsets.append(out.tell())
            out.write(f"{obj_id} 0 obj\n".encode("latin-1"))
            out.write(content.encode("latin-1"))
            out.write(b"\nendobj\n")

        write_obj(1, catalog_str)
        write_obj(2, pages_str)
        for i, obj_bytes in enumerate(shifted_objects):
            obj_id = i + 3
            offsets.append(out.tell())
            out.write(f"{obj_id} 0 obj\n".encode("latin-1"))
            out.write(obj_bytes)
            out.write(b"\nendobj\n")

        # xref
        xref_offset = out.tell()
        total_objects = 2 + len(shifted_objects)
        out.write(f"xref\n0 {total_objects + 1}\n".encode("latin-1"))
        out.write(b"0000000000 65535 f \n")
        for offset in offsets:
            out.write(f"{offset:010d} 00000 n \n".encode("latin-1"))

        # trailer
        out.write(
            f"trailer\n<< /Size {total_objects + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
        )
        return out.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_pdf(
    render_plan: dict,
    *,
    doc_hash: str | None = None,
) -> bytes:
    """
    Render a render_plan dict to PDF bytes.

    Args:
        render_plan: the render plan produced by DocumentBuilder
        doc_hash: optional document hash to embed in the footer

    Returns:
        PDF file as bytes.

    Raises:
        ValueError: if render_plan is not a dict.
    """
    if not isinstance(render_plan, dict):
        raise ValueError("render_plan must be a dict.")

    writer = _PdfWriter()

    doc_type = render_plan.get("doc_type", "DOCUMENT")
    template_id = render_plan.get("template_id", "")
    template_version = render_plan.get("template_version", "")

    # Title
    title_text = f"{doc_type}"
    if template_id:
        title_text += f"  |  {template_id}"
    writer.add_title(title_text)
    writer.add_vspace(4)

    # Header section
    header = render_plan.get("header", {})
    if header:
        writer.add_heading("Header")
        for key, value in sorted(header.items()):
            writer.add_kv(key.replace("_", " ").title(), value)
        writer.add_vspace()

    # Line items
    line_items = render_plan.get("line_items", [])
    if isinstance(line_items, (list, tuple)) and line_items:
        writer.add_heading("Items")
        # Discover columns
        all_keys: list[str] = []
        seen_keys: set[str] = set()
        for item in line_items:
            if isinstance(item, dict):
                for key in item:
                    if key not in seen_keys:
                        all_keys.append(key)
                        seen_keys.add(key)

        available_width = (
            _PdfWriter.PAGE_W - _PdfWriter.MARGIN_LEFT - _PdfWriter.MARGIN_RIGHT
        )
        col_count = len(all_keys)
        if col_count:
            col_width = available_width / col_count
            col_widths = [col_width] * col_count
            headers = [k.replace("_", " ").title() for k in all_keys]
            writer.add_table_header(headers, col_widths)
            for item in line_items:
                if not isinstance(item, dict):
                    continue
                cells = [item.get(k) for k in all_keys]
                writer.add_table_row(cells, col_widths)
        writer.add_vspace()

    # Totals
    totals = render_plan.get("totals", {})
    if totals:
        writer.add_heading("Totals")
        currency = totals.get("currency", "")
        priority = ("subtotal", "discount_total", "tax_total", "grand_total")
        seen: set[str] = set()
        for key in priority:
            if key in totals and totals[key] is not None:
                value_str = f"{currency} {_fmt(totals[key])}" if currency else _fmt(totals[key])
                writer.add_kv(key.replace("_", " ").title(), value_str)
                seen.add(key)
        for key, value in sorted(totals.items()):
            if key not in seen and key != "currency" and value is not None:
                value_str = f"{currency} {_fmt(value)}" if currency else _fmt(value)
                writer.add_kv(key.replace("_", " ").title(), value_str)
        writer.add_vspace()

    # Footer / notes
    footer = render_plan.get("footer", {})
    if footer:
        writer.add_heading("Notes")
        for key, value in sorted(footer.items()):
            if value is not None:
                writer.add_kv(key.replace("_", " ").title(), value)
        writer.add_vspace()

    # Metadata footer
    writer.add_separator()
    meta_parts = []
    if template_id:
        meta_parts.append(f"Template: {template_id}")
    if template_version:
        meta_parts.append(f"v{template_version}")
    if doc_hash:
        meta_parts.append(f"Hash: {doc_hash[:16]}...")
    if meta_parts:
        writer.add_text(" | ".join(meta_parts))

    return writer.build()
