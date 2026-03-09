"""
BOS Documents - Deterministic Default Templates
===============================================
Default layout specs used when no effective stored template exists.
"""

from __future__ import annotations

import uuid
from typing import Optional

from core.documents.models import (
    DOCUMENT_CANCELLATION_NOTE,
    DOCUMENT_COMPLETION_CERTIFICATE,
    DOCUMENT_CREDIT_NOTE,
    DOCUMENT_CUTTING_LIST,
    DOCUMENT_DEBIT_NOTE,
    DOCUMENT_DELIVERY_NOTE,
    DOCUMENT_FOLIO,
    DOCUMENT_GOODS_RECEIPT_NOTE,
    DOCUMENT_INVOICE,
    DOCUMENT_KITCHEN_ORDER_TICKET,
    DOCUMENT_MATERIAL_REQUISITION,
    DOCUMENT_PAYMENT_VOUCHER,
    DOCUMENT_PETTY_CASH_VOUCHER,
    DOCUMENT_PROFORMA_INVOICE,
    DOCUMENT_PURCHASE_ORDER,
    DOCUMENT_QUOTE,
    DOCUMENT_RECEIPT,
    DOCUMENT_REFUND_NOTE,
    DOCUMENT_REGISTRATION_CARD,
    DOCUMENT_RESERVATION_CONFIRMATION,
    DOCUMENT_SALES_ORDER,
    DOCUMENT_CASH_SESSION_RECONCILIATION,
    DOCUMENT_STATEMENT,
    DOCUMENT_STOCK_ADJUSTMENT_NOTE,
    DOCUMENT_STOCK_TRANSFER_NOTE,
    DOCUMENT_WORK_ORDER,
    TEMPLATE_ACTIVE,
    DocumentTemplate,
)


DEFAULT_LAYOUT_SPECS = {
    DOCUMENT_RECEIPT: {
        "header_fields": ("receipt_no", "issued_at", "cashier", "customer_name", "payment_method"),
        "line_items_path": "line_items",
        "line_item_fields": ("name", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "discount_total", "tax_total", "grand_total"),
        "footer_fields": ("notes",),
    },
    DOCUMENT_QUOTE: {
        "header_fields": ("quote_no", "issued_at", "customer_name", "valid_until"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "discount_total", "tax_total", "grand_total"),
        "footer_fields": ("valid_until", "notes"),
    },
    DOCUMENT_INVOICE: {
        "header_fields": ("invoice_no", "issued_at", "customer_name", "due_date", "payment_terms"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "tax", "line_total"),
        "total_fields": ("subtotal", "tax_total", "discount_total", "grand_total"),
        "footer_fields": ("payment_terms", "bank_details", "notes"),
    },
    DOCUMENT_PROFORMA_INVOICE: {
        "header_fields": ("proforma_no", "issued_at", "customer_name", "valid_until"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("valid_until", "notes"),
    },
    DOCUMENT_DELIVERY_NOTE: {
        "header_fields": ("dn_no", "issued_at", "customer_name", "delivery_address"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit"),
        "total_fields": (),
        "footer_fields": ("received_by", "notes"),
    },
    DOCUMENT_CREDIT_NOTE: {
        "header_fields": ("cn_no", "issued_at", "customer_name", "original_ref"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("reason", "notes"),
    },
    DOCUMENT_DEBIT_NOTE: {
        "header_fields": ("dn_no", "issued_at", "customer_name", "original_ref"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "amount"),
        "total_fields": ("grand_total",),
        "footer_fields": ("reason", "notes"),
    },
    DOCUMENT_PURCHASE_ORDER: {
        "header_fields": ("po_no", "issued_at", "supplier_name", "delivery_date"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("payment_terms", "delivery_address", "notes"),
    },
    DOCUMENT_GOODS_RECEIPT_NOTE: {
        "header_fields": ("grn_no", "issued_at", "supplier_name", "po_ref"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "qty_ordered", "qty_received", "unit"),
        "total_fields": (),
        "footer_fields": ("received_by", "notes"),
    },
    DOCUMENT_SALES_ORDER: {
        "header_fields": ("so_no", "issued_at", "customer_name"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("notes",),
    },
    DOCUMENT_REFUND_NOTE: {
        "header_fields": ("ref_no", "issued_at", "customer_name", "original_receipt_ref"),
        "line_items_path": "line_items",
        "line_item_fields": ("name", "quantity", "unit_price", "line_total"),
        "total_fields": ("grand_total",),
        "footer_fields": ("reason", "notes"),
    },
    DOCUMENT_WORK_ORDER: {
        "header_fields": ("wo_no", "issued_at", "customer_name", "technician", "priority"),
        "line_items_path": "line_items",
        "line_item_fields": ("task", "description", "estimated_time"),
        "total_fields": (),
        "footer_fields": ("estimated_completion", "notes"),
    },
    DOCUMENT_MATERIAL_REQUISITION: {
        "header_fields": ("mrn_no", "issued_at", "job_ref", "requested_by"),
        "line_items_path": "line_items",
        "line_item_fields": ("material", "quantity", "unit", "purpose"),
        "total_fields": (),
        "footer_fields": ("approved_by", "notes"),
    },
    DOCUMENT_CUTTING_LIST: {
        "header_fields": ("cl_no", "issued_at", "job_ref", "style"),
        "line_items_path": "line_items",
        "line_item_fields": ("component", "material", "length_mm", "width_mm", "quantity"),
        "total_fields": (),
        "footer_fields": ("notes",),
    },
    DOCUMENT_COMPLETION_CERTIFICATE: {
        "header_fields": ("cc_no", "issued_at", "customer_name", "job_ref"),
        "line_items_path": "line_items",
        "line_item_fields": ("description",),
        "total_fields": (),
        "footer_fields": ("customer_signature", "notes"),
    },
    DOCUMENT_KITCHEN_ORDER_TICKET: {
        "header_fields": ("kot_no", "issued_at", "table", "station", "priority"),
        "line_items_path": "line_items",
        "line_item_fields": ("item", "quantity", "notes"),
        "total_fields": (),
        "footer_fields": ("order_ref",),
    },
    DOCUMENT_FOLIO: {
        "header_fields": ("folio_no", "issued_at", "guest_name", "room", "arrival", "departure", "nights"),
        "line_items_path": "line_items",
        "line_item_fields": ("date", "description", "amount"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("payment_method", "notes"),
    },
    DOCUMENT_RESERVATION_CONFIRMATION: {
        "header_fields": ("resv_no", "issued_at", "guest_name", "arrival_date", "departure_date", "nights"),
        "line_items_path": "line_items",
        "line_item_fields": ("room_type", "rate_plan", "nightly_rate", "nights", "total"),
        "total_fields": ("total_amount", "deposit_due"),
        "footer_fields": ("special_requests", "cancellation_policy", "notes"),
    },
    DOCUMENT_REGISTRATION_CARD: {
        "header_fields": ("reg_no", "issued_at", "guest_name", "room_number", "arrival_date", "departure_date"),
        "line_items_path": "line_items",
        "line_item_fields": (),
        "total_fields": (),
        "footer_fields": ("guest_signature", "id_number", "notes"),
    },
    DOCUMENT_CANCELLATION_NOTE: {
        "header_fields": ("cxl_no", "issued_at", "guest_name", "original_resv_ref"),
        "line_items_path": "line_items",
        "line_item_fields": (),
        "total_fields": ("cancellation_charge", "refund_amount"),
        "footer_fields": ("reason", "notes"),
    },
    DOCUMENT_PAYMENT_VOUCHER: {
        "header_fields": ("pv_no", "issued_at", "payee_name", "payment_method"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "amount"),
        "total_fields": ("grand_total",),
        "footer_fields": ("approved_by", "notes"),
    },
    DOCUMENT_PETTY_CASH_VOUCHER: {
        "header_fields": ("pcv_no", "issued_at", "received_by"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "amount"),
        "total_fields": ("grand_total",),
        "footer_fields": ("approved_by", "notes"),
    },
    DOCUMENT_STOCK_TRANSFER_NOTE: {
        "header_fields": ("stn_no", "issued_at", "from_location", "to_location"),
        "line_items_path": "line_items",
        "line_item_fields": ("item", "sku", "quantity", "unit"),
        "total_fields": (),
        "footer_fields": ("transferred_by", "received_by", "notes"),
    },
    DOCUMENT_STOCK_ADJUSTMENT_NOTE: {
        "header_fields": ("san_no", "issued_at", "adjustment_type", "location"),
        "line_items_path": "line_items",
        "line_item_fields": ("item", "sku", "qty_before", "qty_after", "variance"),
        "total_fields": (),
        "footer_fields": ("reason", "approved_by", "notes"),
    },
    DOCUMENT_STATEMENT: {
        "header_fields": ("stmt_no", "issued_at", "customer_name", "period_from", "period_to"),
        "line_items_path": "line_items",
        "line_item_fields": ("date", "description", "debit", "credit", "balance"),
        "total_fields": ("opening_balance", "total_debit", "total_credit", "closing_balance"),
        "footer_fields": ("notes",),
    },
    DOCUMENT_CASH_SESSION_RECONCILIATION: {
        "header_fields": ("session_id", "issued_at", "drawer_id"),
        "line_items_path": "line_items",
        "line_item_fields": (),
        "total_fields": ("expected_balance", "closing_balance", "variance"),
        "footer_fields": ("closed_by", "closed_at", "notes"),
    },
}


# ══════════════════════════════════════════════════════════════
# ENGINE-SPECIFIC LAYOUT OVERRIDES
# ══════════════════════════════════════════════════════════════
# Key: (source_engine, doc_type) → layout_spec
# When a document is issued from a specific engine context, use
# the engine-specific layout if available, else fall back to the
# generic DEFAULT_LAYOUT_SPECS.
# ══════════════════════════════════════════════════════════════

ENGINE_LAYOUT_OVERRIDES: dict[tuple[str, str], dict] = {
    # Retail receipt — cashier-centric, payment method prominent
    ("retail", DOCUMENT_RECEIPT): {
        "header_fields": ("receipt_no", "issued_at", "cashier_id", "customer_name", "payment_method"),
        "line_items_path": "line_items",
        "line_item_fields": ("name", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "discount_total", "tax_total", "grand_total"),
        "footer_fields": ("notes",),
    },
    # Restaurant receipt — table, covers, server, tip
    ("restaurant", DOCUMENT_RECEIPT): {
        "header_fields": ("receipt_no", "issued_at", "table_name", "covers", "server_id", "customer_name"),
        "line_items_path": "line_items",
        "line_item_fields": ("item", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "discount_total", "tax_total", "tip", "grand_total"),
        "footer_fields": ("payment_method", "notes"),
    },
    # Hotel receipt (folio settlement) — guest, room, stay dates
    ("hotel", DOCUMENT_RECEIPT): {
        "header_fields": ("receipt_no", "issued_at", "guest_name", "room_number", "arrival_date", "departure_date"),
        "line_items_path": "line_items",
        "line_item_fields": ("date", "description", "amount"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("payment_method", "notes"),
    },
    # Workshop invoice — labour/materials breakdown, payment terms
    ("workshop", DOCUMENT_INVOICE): {
        "header_fields": ("invoice_no", "issued_at", "customer_name", "job_id", "due_date", "payment_terms"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "discount_total", "grand_total"),
        "footer_fields": ("payment_terms", "bank_details", "notes"),
    },
    # Hotel invoice — corporate billing, folio reference
    ("hotel", DOCUMENT_INVOICE): {
        "header_fields": ("invoice_no", "issued_at", "customer_name", "reservation_id", "folio_id"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("payment_terms", "bank_details", "notes"),
    },
    # Restaurant invoice — on-account corporate dining
    ("restaurant", DOCUMENT_INVOICE): {
        "header_fields": ("invoice_no", "issued_at", "customer_name", "bill_id", "table_name"),
        "line_items_path": "line_items",
        "line_item_fields": ("item", "quantity", "unit_price", "line_total"),
        "total_fields": ("subtotal", "discount_total", "tax_total", "grand_total"),
        "footer_fields": ("payment_terms", "notes"),
    },
    # Workshop quote — valid_until, labour/material split
    ("workshop", DOCUMENT_QUOTE): {
        "header_fields": ("quote_no", "issued_at", "customer_name", "job_id", "valid_until"),
        "line_items_path": "line_items",
        "line_item_fields": ("description", "quantity", "unit_price", "line_total"),
        "total_fields": ("labour_cost", "subtotal", "discount_total", "tax_total", "grand_total"),
        "footer_fields": ("valid_until", "deposit_terms", "notes"),
    },
}
    if isinstance(value, dict):
        return {key: _clone_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_clone_value(item) for item in value)
    if isinstance(value, list):
        return [_clone_value(item) for item in value]
    return value


def get_default_layout_spec(doc_type: str, source_engine: Optional[str] = None) -> Optional[dict]:
    """
    Return layout spec for doc_type, preferring engine-specific override if available.

    Args:
        doc_type: Document type constant (e.g. DOCUMENT_RECEIPT)
        source_engine: Optional engine name (e.g. "retail", "restaurant", "workshop", "hotel")
                       When provided, returns engine-specific layout if one exists.
    """
    if source_engine:
        engine_layout = ENGINE_LAYOUT_OVERRIDES.get((source_engine, doc_type))
        if engine_layout is not None:
            return _clone_value(engine_layout)
    layout = DEFAULT_LAYOUT_SPECS.get(doc_type)
    if layout is None:
        return None
    return _clone_value(layout)


def build_default_template(
    business_id: uuid.UUID,
    doc_type: str,
    source_engine: Optional[str] = None,
) -> Optional[DocumentTemplate]:
    layout = get_default_layout_spec(doc_type, source_engine=source_engine)
    if layout is None:
        return None

    template_id = f"default.{doc_type.lower()}.v1"
    if source_engine:
        template_id = f"default.{doc_type.lower()}.{source_engine}.v1"

    return DocumentTemplate(
        template_id=template_id,
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
