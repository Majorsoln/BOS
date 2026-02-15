"""
BOS Documents - Deterministic Default Templates
===============================================
Default layout specs used when no effective stored template exists.
"""

from __future__ import annotations

import uuid
from typing import Optional

from core.documents.models import (
    DOCUMENT_INVOICE,
    DOCUMENT_QUOTE,
    DOCUMENT_RECEIPT,
    TEMPLATE_ACTIVE,
    DocumentTemplate,
)


DEFAULT_LAYOUT_SPECS = {
    DOCUMENT_RECEIPT: {
        "header_fields": ("receipt_no", "issued_at", "cashier"),
        "line_items_path": "line_items",
        "line_item_fields": ("name", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("notes",),
    },
    DOCUMENT_QUOTE: {
        "header_fields": ("quote_no", "issued_at", "customer_name"),
        "line_items_path": "line_items",
        "line_item_fields": ("sku", "description", "quantity", "unit_price"),
        "total_fields": ("subtotal", "discount_total", "grand_total"),
        "footer_fields": ("valid_until", "notes"),
    },
    DOCUMENT_INVOICE: {
        "header_fields": ("invoice_no", "issued_at", "customer_name"),
        "line_items_path": "line_items",
        "line_item_fields": ("sku", "description", "quantity", "tax", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("payment_terms", "notes"),
    },
}


def _clone_value(value):
    if isinstance(value, dict):
        return {key: _clone_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_clone_value(item) for item in value)
    if isinstance(value, list):
        return [_clone_value(item) for item in value]
    return value


def get_default_layout_spec(doc_type: str) -> Optional[dict]:
    layout = DEFAULT_LAYOUT_SPECS.get(doc_type)
    if layout is None:
        return None
    return _clone_value(layout)


def build_default_template(
    business_id: uuid.UUID,
    doc_type: str,
) -> Optional[DocumentTemplate]:
    layout = get_default_layout_spec(doc_type)
    if layout is None:
        return None

    return DocumentTemplate(
        template_id=f"default.{doc_type.lower()}.v1",
        business_id=business_id,
        branch_id=None,
        doc_type=doc_type,
        version=1,
        status=TEMPLATE_ACTIVE,
        schema_version=1,
        layout_spec=layout,
        created_by_actor_id=None,
        created_at=None,
    )
