"""
BOS Documents - i18n / Locale Translation System
==================================================
Provides translation key registry, default locale bundles, and a resolver
for translating document labels at render time.

Architecture:
- All hardcoded labels are mapped to canonical translation keys.
- Default bundles ship for en, sw (Swahili), fr (French), ar (Arabic).
- At render time, the renderer calls ``resolve_label(key, translations)``
  which returns the translated string or falls back to English.
- Business.default_language determines which locale is used.
- Fallback chain: locale (e.g. sw_KE) -> language (sw) -> en.

Doctrine:
- Translation keys are dot-separated, lowercase.
- All system-internal keys remain English (event types, constants).
- Only human-visible document labels are translated.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Translation key -> English default label
# ---------------------------------------------------------------------------

LABEL_KEYS: dict[str, str] = {
    # Section headings
    "section.header": "Header",
    "section.items": "Items",
    "section.totals": "Totals",
    "section.notes": "Notes",
    "section.parties": "Parties",
    "section.reference": "Reference",
    "section.payment": "Payment",
    "section.compliance": "Compliance",
    "section.qr_code": "QR Code",

    # Header block fields
    "header.doc_type": "Type",
    "header.doc_number": "Number",
    "header.date": "Date",
    "header.business": "Business",
    "header.branch": "Branch",

    # Party block
    "party.from": "From",
    "party.to": "To",
    "party.name": "Name",
    "party.address": "Address",
    "party.tax_id": "Tax ID",

    # Item table
    "items.no_items": "No items.",
    "items.description": "Description",
    "items.item": "Item",
    "items.name": "Name",
    "items.qty": "Quantity",
    "items.unit_price": "Unit Price",
    "items.total": "Total",
    "items.date": "Date",
    "items.amount": "Amount",
    "items.notes": "Notes",

    # Totals
    "totals.subtotal": "Subtotal",
    "totals.discount": "Discount",
    "totals.discount_total": "Discount Total",
    "totals.tax": "Tax",
    "totals.tax_total": "Tax Total",
    "totals.grand_total": "Total",
    "totals.currency": "Currency",
    "totals.labour": "Labour",
    "totals.materials": "Materials",

    # Payment
    "payment.method": "Payment Method",
    "payment.terms": "Payment Terms",
    "payment.due_date": "Due Date",
    "payment.amount_paid": "Amount Paid",
    "payment.amount_due": "Amount Due",

    # Compliance
    "compliance.fiscal_number": "Fiscal Number",
    "compliance.profile": "Compliance Profile",
    "compliance.notes": "Compliance Notes",

    # Notes / footer
    "notes.notes": "Notes",
    "notes.terms": "Terms & Conditions",

    # QR
    "qr.content": "QR Content",
    "qr.label": "QR Label",
    "qr.code": "QR Code",

    # Common document labels
    "doc.receipt": "Receipt",
    "doc.invoice": "Invoice",
    "doc.quote": "Quote",
    "doc.credit_note": "Credit Note",
    "doc.debit_note": "Debit Note",
    "doc.purchase_order": "Purchase Order",
    "doc.delivery_note": "Delivery Note",
    "doc.goods_receipt_note": "Goods Receipt Note",
    "doc.sales_order": "Sales Order",
    "doc.refund_note": "Refund Note",
    "doc.proforma_invoice": "Proforma Invoice",
    "doc.work_order": "Work Order",
    "doc.cutting_list": "Cutting List",
    "doc.completion_certificate": "Completion Certificate",
    "doc.material_requisition": "Material Requisition",
    "doc.kitchen_order_ticket": "Kitchen Order Ticket",
    "doc.folio": "Folio",
    "doc.reservation_confirmation": "Reservation Confirmation",
    "doc.registration_card": "Registration Card",
    "doc.cancellation_note": "Cancellation Note",
    "doc.payment_voucher": "Payment Voucher",
    "doc.petty_cash_voucher": "Petty Cash Voucher",
    "doc.statement": "Statement",
    "doc.stock_transfer_note": "Stock Transfer Note",
    "doc.stock_adjustment_note": "Stock Adjustment Note",
    "doc.cash_session_reconciliation": "Cash Session Reconciliation",

    # Receipt-specific
    "receipt.cashier": "Cashier",
    "receipt.customer": "Customer",
    "receipt.walk_in": "Walk-in Customer",
    "receipt.thank_you": "Thank you for your purchase!",

    # Invoice-specific
    "invoice.due_date": "Due Date",
    "invoice.payment_terms": "Payment Terms",
    "invoice.bank_details": "Bank Details",

    # Quote-specific
    "quote.valid_until": "Valid Until",
    "quote.prepared_by": "Prepared By",

    # Hotel-specific
    "hotel.guest": "Guest",
    "hotel.room": "Room",
    "hotel.arrival": "Arrival",
    "hotel.departure": "Departure",
    "hotel.nights": "Nights",
    "hotel.folio_no": "Folio No",

    # Restaurant-specific
    "restaurant.table": "Table",
    "restaurant.covers": "Covers",
    "restaurant.server": "Server",
    "restaurant.kot_no": "KOT No",
    "restaurant.station": "Station",
    "restaurant.priority": "Priority",

    # Workshop-specific
    "workshop.job_description": "Job Description",
    "workshop.technician": "Technician",
    "workshop.estimated_completion": "Estimated Completion",

    # Common footer
    "footer.template": "Template",
    "footer.hash": "Hash",
    "footer.thank_you": "Thank you for your business!",
}


# ---------------------------------------------------------------------------
# Default locale bundles
# ---------------------------------------------------------------------------

_BUNDLE_SW: dict[str, str] = {
    # Section headings
    "section.header": "Kichwa",
    "section.items": "Bidhaa",
    "section.totals": "Jumla",
    "section.notes": "Maelezo",
    "section.parties": "Wahusika",
    "section.reference": "Rejea",
    "section.payment": "Malipo",
    "section.compliance": "Utiifu",
    "section.qr_code": "Msimbo wa QR",

    # Header
    "header.doc_type": "Aina",
    "header.doc_number": "Namba",
    "header.date": "Tarehe",
    "header.business": "Biashara",
    "header.branch": "Tawi",

    # Party
    "party.from": "Kutoka",
    "party.to": "Kwa",
    "party.name": "Jina",
    "party.address": "Anwani",
    "party.tax_id": "Namba ya Kodi",

    # Items
    "items.no_items": "Hakuna bidhaa.",
    "items.description": "Maelezo",
    "items.item": "Bidhaa",
    "items.name": "Jina",
    "items.qty": "Kiasi",
    "items.unit_price": "Bei ya Kitu",
    "items.total": "Jumla",
    "items.date": "Tarehe",
    "items.amount": "Kiasi",
    "items.notes": "Maelezo",

    # Totals
    "totals.subtotal": "Jumla Ndogo",
    "totals.discount": "Punguzo",
    "totals.discount_total": "Jumla ya Punguzo",
    "totals.tax": "Kodi",
    "totals.tax_total": "Jumla ya Kodi",
    "totals.grand_total": "Jumla Kuu",
    "totals.currency": "Sarafu",
    "totals.labour": "Kazi",
    "totals.materials": "Vifaa",

    # Payment
    "payment.method": "Njia ya Malipo",
    "payment.terms": "Masharti ya Malipo",
    "payment.due_date": "Tarehe ya Mwisho",
    "payment.amount_paid": "Kiasi Kilicholipwa",
    "payment.amount_due": "Kiasi Kinachostahili",

    # Notes
    "notes.notes": "Maelezo",
    "notes.terms": "Masharti na Vigezo",

    # Common document names
    "doc.receipt": "Risiti",
    "doc.invoice": "Ankara",
    "doc.quote": "Nukuu",
    "doc.credit_note": "Noti ya Mkopo",
    "doc.debit_note": "Noti ya Deni",
    "doc.purchase_order": "Agizo la Ununuzi",
    "doc.delivery_note": "Noti ya Uwasilishaji",
    "doc.refund_note": "Noti ya Kurudishiwa",
    "doc.work_order": "Agizo la Kazi",
    "doc.payment_voucher": "Hati ya Malipo",
    "doc.folio": "Folio",
    "doc.statement": "Taarifa",

    # Receipt
    "receipt.cashier": "Karani",
    "receipt.customer": "Mteja",
    "receipt.walk_in": "Mteja wa Kawaida",
    "receipt.thank_you": "Asante kwa ununuzi wako!",

    # Hotel
    "hotel.guest": "Mgeni",
    "hotel.room": "Chumba",
    "hotel.arrival": "Kuwasili",
    "hotel.departure": "Kuondoka",
    "hotel.nights": "Usiku",

    # Restaurant
    "restaurant.table": "Meza",
    "restaurant.covers": "Wageni",
    "restaurant.server": "Mhudumu",

    # Footer
    "footer.template": "Kiolezo",
    "footer.hash": "Hashi",
    "footer.thank_you": "Asante kwa biashara yako!",
}

_BUNDLE_FR: dict[str, str] = {
    "section.header": "En-tete",
    "section.items": "Articles",
    "section.totals": "Totaux",
    "section.notes": "Remarques",
    "section.parties": "Parties",
    "section.payment": "Paiement",

    "header.doc_type": "Type",
    "header.doc_number": "Numero",
    "header.date": "Date",
    "header.business": "Entreprise",
    "header.branch": "Succursale",

    "party.from": "De",
    "party.to": "A",
    "party.name": "Nom",
    "party.address": "Adresse",
    "party.tax_id": "Numero fiscal",

    "items.no_items": "Aucun article.",
    "items.description": "Description",
    "items.qty": "Quantite",
    "items.unit_price": "Prix unitaire",
    "items.total": "Total",

    "totals.subtotal": "Sous-total",
    "totals.discount": "Remise",
    "totals.tax": "Taxe",
    "totals.tax_total": "Total Taxe",
    "totals.grand_total": "Total General",
    "totals.currency": "Devise",

    "payment.method": "Mode de paiement",
    "payment.terms": "Conditions de paiement",
    "payment.due_date": "Date d'echeance",

    "notes.notes": "Remarques",
    "notes.terms": "Conditions generales",

    "doc.receipt": "Recu",
    "doc.invoice": "Facture",
    "doc.quote": "Devis",
    "doc.credit_note": "Avoir",
    "doc.purchase_order": "Bon de commande",
    "doc.delivery_note": "Bon de livraison",
    "doc.refund_note": "Note de remboursement",
    "doc.payment_voucher": "Bon de paiement",
    "doc.statement": "Releve",

    "receipt.cashier": "Caissier",
    "receipt.customer": "Client",
    "receipt.walk_in": "Client de passage",
    "receipt.thank_you": "Merci pour votre achat!",
    "footer.thank_you": "Merci pour votre confiance!",
}

_BUNDLE_AR: dict[str, str] = {
    "section.header": "الرأس",
    "section.items": "العناصر",
    "section.totals": "المجاميع",
    "section.notes": "ملاحظات",
    "section.parties": "الأطراف",
    "section.payment": "الدفع",

    "header.doc_type": "النوع",
    "header.doc_number": "الرقم",
    "header.date": "التاريخ",
    "header.business": "المنشأة",
    "header.branch": "الفرع",

    "items.qty": "الكمية",
    "items.unit_price": "سعر الوحدة",
    "items.total": "المجموع",

    "totals.subtotal": "المجموع الفرعي",
    "totals.discount": "الخصم",
    "totals.tax": "الضريبة",
    "totals.grand_total": "المجموع الكلي",

    "doc.receipt": "إيصال",
    "doc.invoice": "فاتورة",
    "doc.quote": "عرض سعر",
    "doc.credit_note": "إشعار دائن",

    "receipt.customer": "العميل",
    "receipt.thank_you": "!شكرا لتسوقكم معنا",
    "footer.thank_you": "!شكرا لتعاملكم معنا",
}


# ---------------------------------------------------------------------------
# Bundle registry
# ---------------------------------------------------------------------------

DEFAULT_BUNDLES: dict[str, dict[str, str]] = {
    "en": dict(LABEL_KEYS),  # English is the complete set
    "sw": _BUNDLE_SW,
    "fr": _BUNDLE_FR,
    "ar": _BUNDLE_AR,
}


# ---------------------------------------------------------------------------
# Locale resolution
# ---------------------------------------------------------------------------

def resolve_locale(locale: str | None) -> str:
    """
    Normalise a locale string and return the best available language code.

    Fallback chain: locale (e.g. 'sw_KE') -> language ('sw') -> 'en'.
    """
    if not locale:
        return "en"
    locale = locale.strip().lower().replace("-", "_")
    # Try exact match first (e.g. 'sw_ke')
    if locale in DEFAULT_BUNDLES:
        return locale
    # Try language prefix (e.g. 'sw' from 'sw_ke')
    lang = locale.split("_")[0]
    if lang in DEFAULT_BUNDLES:
        return lang
    return "en"


def get_translations(
    locale: str | None,
    *,
    custom_translations: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Return a merged translation dict for a given locale.

    Priority: custom_translations > locale bundle > English defaults.
    """
    resolved = resolve_locale(locale)
    # Start from English defaults, overlay locale, overlay custom
    result = dict(LABEL_KEYS)
    if resolved != "en":
        bundle = DEFAULT_BUNDLES.get(resolved, {})
        result.update(bundle)
    if custom_translations:
        result.update(custom_translations)
    return result


def resolve_label(
    key: str,
    translations: dict[str, str] | None = None,
) -> str:
    """
    Resolve a translation key to its label string.

    Falls back to the English default if not found in translations.
    If the key is not in the registry at all, returns the key
    formatted as a human-readable string (title-cased, underscores to spaces).
    """
    if translations and key in translations:
        return translations[key]
    if key in LABEL_KEYS:
        return LABEL_KEYS[key]
    # Not a registered key — format as human-readable fallback
    return key.replace("_", " ").replace(".", " ").title()


# ---------------------------------------------------------------------------
# Field key -> translation key mapping
# ---------------------------------------------------------------------------

# Maps render_plan field names to their translation keys.
# Used by renderers to translate k/v labels in header, totals, footer sections.
FIELD_TRANSLATION_KEYS: dict[str, str] = {
    # Header fields
    "doc_type": "header.doc_type",
    "doc_number": "header.doc_number",
    "receipt_no": "header.doc_number",
    "invoice_no": "header.doc_number",
    "quote_no": "header.doc_number",
    "folio_no": "hotel.folio_no",
    "kot_no": "restaurant.kot_no",
    "issued_at": "header.date",
    "date": "header.date",
    "business_name": "header.business",
    "branch_name": "header.branch",

    # Party/customer fields
    "customer_name": "receipt.customer",
    "guest_name": "hotel.guest",
    "seller_name": "party.from",
    "seller_address": "party.address",
    "seller_tax_id": "party.tax_id",
    "buyer_name": "party.to",
    "buyer_address": "party.address",

    # Totals fields
    "subtotal": "totals.subtotal",
    "discount_total": "totals.discount_total",
    "tax_total": "totals.tax_total",
    "tax": "totals.tax",
    "tax_amount": "totals.tax",
    "grand_total": "totals.grand_total",
    "labour": "totals.labour",
    "materials": "totals.materials",
    "currency": "totals.currency",

    # Payment fields
    "payment_method": "payment.method",
    "payment_terms": "payment.terms",
    "due_date": "payment.due_date",

    # Table column fields
    "description": "items.description",
    "item": "items.item",
    "name": "items.name",
    "qty": "items.qty",
    "quantity": "items.qty",
    "unit_price": "items.unit_price",
    "price": "items.unit_price",
    "total": "items.total",
    "amount": "items.amount",

    # Notes
    "notes": "notes.notes",
    "terms": "notes.terms",

    # Restaurant
    "table": "restaurant.table",
    "table_name": "restaurant.table",
    "covers": "restaurant.covers",
    "server": "restaurant.server",
    "station": "restaurant.station",
    "priority": "restaurant.priority",

    # Hotel
    "room": "hotel.room",
    "room_number": "hotel.room",
    "arrival": "hotel.arrival",
    "arrival_date": "hotel.arrival",
    "departure": "hotel.departure",
    "departure_date": "hotel.departure",
    "nights": "hotel.nights",

    # Workshop
    "job_description": "workshop.job_description",
    "technician": "workshop.technician",
    "estimated_completion": "workshop.estimated_completion",

    # Receipt
    "cashier": "receipt.cashier",

    # Quote
    "valid_until": "quote.valid_until",
    "prepared_by": "quote.prepared_by",

    # Invoice
    "bank_details": "invoice.bank_details",
}


def translate_field_label(
    field_key: str,
    translations: dict[str, str] | None = None,
) -> str:
    """
    Translate a render_plan field key to its localised label.

    Looks up the field_key in FIELD_TRANSLATION_KEYS to find the
    translation key, then resolves via the translations dict.
    Falls back to Title Case of the field key if no mapping exists.
    """
    translation_key = FIELD_TRANSLATION_KEYS.get(field_key)
    if translation_key:
        return resolve_label(translation_key, translations)
    # No mapping — format as human-readable
    return field_key.replace("_", " ").title()
