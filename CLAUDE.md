# BOS — Master Gap Registry & Document Blueprint
## Session: Document & POS Gap Analysis (Deep Dive)
**Date:** 2026-03-03
**Branch:** claude/explain-codebase-mlsfr9vu6lpytugq-0E7ZN

---

## WHAT EXISTS (Infrastructure Inventory)

### Engines Present in Codebase
| Engine | Module | Doc Status |
|--------|--------|------------|
| Retail (POS/Shop) | `engines/retail/` | NO AUTO-DOCS |
| Restaurant (F&B) | `engines/restaurant/` | NO AUTO-DOCS |
| Workshop (Fabrication) | `engines/workshop/` | NO AUTO-DOCS |
| Procurement | `engines/procurement/` | NO AUTO-DOCS |
| Inventory | `engines/inventory/` | NO AUTO-DOCS |
| Accounting | `engines/accounting/` | NO AUTO-DOCS |
| Cash | `engines/cash/` | NO AUTO-DOCS |
| Reporting | `engines/reporting/` | — |
| Cart QR | `engines/cart_qr/` | — |
| Promotion | `engines/promotion/` | Partial (credit_note event only) |
| Customer | `engines/customer/` | — |
| Wallet | `engines/wallet/` | — |
| Loyalty | `engines/loyalty/` | — |
| QR Menu | `engines/qr_menu/` | — |
| HR | `engines/hr/` | — |
| Hotel Folio | `engines/hotel_folio/` | NO AUTO-DOCS |
| Hotel Reservation | `engines/hotel_reservation/` | NO AUTO-DOCS |
| Hotel Property | `engines/hotel_property/` | — |
| Hotel Housekeeping | `engines/hotel_housekeeping/` | — |
| Hotel Booking Engine | `engines/hotel_booking_engine/` | — |
| Hotel Channel | `engines/hotel_channel/` | — |

### Document Infrastructure — What Actually Exists
| Component | File | State |
|-----------|------|-------|
| DocumentType enum (13 types) | `core/primitives/document.py` | Defined but most blocked |
| Document template model | `core/documents/models.py` | Only 3 types in VALID_DOCUMENT_TYPES |
| Default templates | `core/documents/defaults.py` | 3 only: RECEIPT, QUOTE, INVOICE |
| Document builder | `core/documents/builder.py` | Functional |
| Numbering engine | `core/documents/numbering/engine.py` | Functional — NOT wired to events |
| PDF renderer | `core/documents/renderer/pdf_renderer.py` | Functional — NOT exposed via API |
| HTML renderer | `core/documents/renderer/html_renderer.py` | Functional — NOT exposed via API |
| Document hashing | `core/documents/hashing.py` | SHA-256, functional |
| Issuance commands | `core/document_issuance/commands.py` | 3 commands only |
| Issuance events | `core/document_issuance/events.py` | 3 events only |
| Issuance service | `core/document_issuance/service.py` | HTTP-only, no event subscription |
| Document policy | `core/policy/document_policy.py` | FLAG_ENABLE_DOCUMENT_DESIGNER required |

---

## CRITICAL INFRASTRUCTURE GAPS (Foundation — Fix First)

### INFRA-01 — VALID_DOCUMENT_TYPES blocks everything except 3 types
**File:** `core/documents/models.py:22`
```python
VALID_DOCUMENT_TYPES = frozenset({"RECEIPT", "QUOTE", "INVOICE"})
```
`DocumentType` enum has 13 values but template model rejects all others.
PURCHASE_ORDER, GOODS_RECEIPT_NOTE, CREDIT_NOTE, JOB_SHEET, REFUND_NOTE all fail.
**Severity:** CRITICAL — blocks all document type expansion.

### INFRA-02 — Document issuance registry has only 3 command/event pairs
**File:** `core/document_issuance/registry.py`
Only: `doc.receipt.issue.request`, `doc.quote.issue.request`, `doc.invoice.issue.request`
Every new document type needs its own command + event registered here.
**Severity:** CRITICAL — new doc types cannot be issued at all.

### INFRA-03 — No DocumentSubscriptionHandler exists anywhere
No class listens to engine events and calls DocumentIssuanceService automatically.
Documents can ONLY be issued via HTTP API (manual call required every time).
**Severity:** CRITICAL — entire auto-document pipeline is missing.

### INFRA-04 — PDF/HTML renderers exist but are NOT exposed
`pdf_renderer.py` and `html_renderer.py` are implemented but:
- Not wired to any API endpoint
- No `GET /docs/{id}/pdf` or `GET /docs/{id}/html` route exists
- Documents stored as JSON render_plan only — cannot be printed or downloaded
**Severity:** HIGH — documents cannot reach the printer or customer.

### INFRA-05 — FLAG_ENABLE_DOCUMENT_DESIGNER blocks standard POS receipts
`core/policy/document_policy.py:67` requires this flag for ALL documents.
A POS receipt should not require a "Document Designer" feature flag.
Standard receipts (RECEIPT, INVOICE, QUOTE) should work with a simpler flag.
**Severity:** HIGH — new businesses get zero documents until admin enables flag.

### INFRA-06 — No business info resolver
No mechanism injects business name, address, TIN/VAT number into render inputs.
All legal documents require issuer details. None are enriched automatically.
**Severity:** HIGH — all documents legally incomplete.

### INFRA-07 — No customer detail resolver
Only `customer_id` (UUID) in event payloads.
Documents need customer name and address — resolved at subscription/render time.
**Severity:** HIGH — documents cannot address customers.

### INFRA-08 — Numbering engine not wired to any engine event
`core/documents/numbering/engine.py` (SequenceState, period_key) is fully functional
but DocumentSubscriptionHandler (which doesn't exist yet) would need to call it.
**Severity:** HIGH — sequential document numbers are never assigned.

---

## DOCUMENT TYPE EXPANSION REQUIRED

`VALID_DOCUMENT_TYPES` in `core/documents/models.py` must be expanded.
Each new type needs: model constant, default template, issuance command+event in registry.

| Doc Type Constant | Used By | Trigger Event | Number Prefix | Reset |
|-------------------|---------|---------------|---------------|-------|
| `PROFORMA_INVOICE` | Retail, Workshop, Hotel | quote.accepted | PRO- | YEARLY |
| `DELIVERY_NOTE` | Retail, Procurement | stock dispatched | DN- | YEARLY |
| `CREDIT_NOTE` | Retail, Restaurant, Workshop | refund/adjustment | CN- | YEARLY |
| `DEBIT_NOTE` | Procurement, Workshop | charge addition | DBN- | YEARLY |
| `PURCHASE_ORDER` | Procurement | order.created | PO- | YEARLY |
| `GOODS_RECEIPT_NOTE` | Procurement, Inventory | order.received | GRN- | YEARLY |
| `SALES_ORDER` | Retail, Workshop | on-account order | SO- | YEARLY |
| `STATEMENT` | Accounting | scheduled/on-demand | STMT- | MONTHLY |
| `REFUND_NOTE` | Retail, Restaurant | refund.issued | REF- | YEARLY |
| `WORK_ORDER` | Workshop | job.assigned | WO- | YEARLY |
| `MATERIAL_REQUISITION` | Workshop | material request | MRN- | MONTHLY |
| `CUTTING_LIST` | Workshop | cutlist.generated | CL- | YEARLY |
| `COMPLETION_CERTIFICATE` | Workshop | job.completed | CC- | YEARLY |
| `KITCHEN_ORDER_TICKET` | Restaurant | kitchen.ticket.sent | KOT- | DAILY |
| `FOLIO` | Hotel Folio | folio.settled | FOL- | YEARLY |
| `RESERVATION_CONFIRMATION` | Hotel Reservation | reservation.confirmed | RESV- | YEARLY |
| `REGISTRATION_CARD` | Hotel Reservation | guest.checked_in | REG- | YEARLY |
| `CANCELLATION_NOTE` | Hotel Reservation | reservation.cancelled | CXL- | YEARLY |
| `PAYMENT_VOUCHER` | Accounting, Cash | payment.released | PV- | YEARLY |
| `PETTY_CASH_VOUCHER` | Cash | petty_cash disbursed | PCV- | MONTHLY |
| `STOCK_TRANSFER_NOTE` | Inventory | stock transferred | STN- | MONTHLY |
| `STOCK_ADJUSTMENT_NOTE` | Inventory | stock adjusted | SAN- | MONTHLY |

---

## CORRECT DOCUMENT FLOW — ENGINE BY ENGINE

### FLOW DESIGN PRINCIPLE
```
Engine Event
    └─► DocumentSubscriptionHandler.handle_{event}()
              └─► Resolve: business_info + customer_details + doc_number
                        └─► Build render_inputs dict
                                  └─► doc.{type}.issue.request command
                                            └─► DocumentIssuanceService
                                                      └─► Template → Builder → Hash
                                                                └─► doc.{type}.issued.v1
                                                                          └─► ProjectionStore
                                                                          └─► PDF/HTML (on GET)
                                                                          └─► Delivery [future]
```
**Language:** All internal keys in English. Admin configures locale per business.
Templates carry i18n label keys. BOS Admin ships translations. Fallback = `en`.

---

### A. RETAIL (Duka / Shop) — Document Flow

| Trigger Event | Document | Condition | Prefix |
|--------------|----------|-----------|--------|
| `retail.sale.completed.v1` | SALES_RECEIPT | Always | RCP- |
| `retail.sale.completed.v1` | INVOICE | `on_account=true` | INV- |
| `retail.sale.completed.v1` | DELIVERY_NOTE | `requires_delivery=true` | DN- |
| `retail.sale.opened.v1` | SALES_ORDER | `on_account=true` | SO- |
| `retail.refund.issued.v1` | REFUND_NOTE | Always | REF- |
| `retail.sale.voided.v1` | CREDIT_NOTE | Sale was already completed | CN- |

#### Payload Gaps — `engines/retail/events.py`

**`build_sale_completed_payload` must add:**
- `customer_id` — dropped from sale at completion (present in sale.opened)
- `on_account` (bool) — triggers INVOICE instead of/in addition to RECEIPT
- `requires_delivery` (bool) — triggers DELIVERY_NOTE

**`build_sale_voided_payload` must add:**
- `lines` — list of voided items (needed for credit note)
- `total_amount` — needed for credit note value
- `original_receipt_id` — reference to receipt being voided

**`build_refund_issued_payload` — adequate for REFUND_NOTE** (has lines, amount, reason)

#### Retail Receipt Render Plan Structure
```json
{
  "header": {
    "business_name": "[resolved]", "business_address": "[resolved]",
    "tax_number": "[resolved]", "receipt_no": "RCP-2024-0001",
    "cashier": "[resolved from actor_id]", "date": "2024-01-15",
    "payment_method": "CASH",
    "customer_name": "[resolved from customer_id, or WALK-IN]"
  },
  "line_items": [
    {"name": "Item", "qty": 2, "unit_price": 100, "total": 200}
  ],
  "totals": {
    "subtotal": 200, "discount": 0, "tax": 32, "grand_total": 232, "currency": "KES"
  },
  "footer": {"notes": "Thank you for shopping with us"}
}
```

---

### B. RESTAURANT / BAR / BBQ — Document Flow

| Trigger Event | Document | Condition | Prefix |
|--------------|----------|-----------|--------|
| `restaurant.kitchen.ticket.sent.v1` | KITCHEN_ORDER_TICKET | Always | KOT- |
| `restaurant.bill.settled.v1` | SALES_RECEIPT | Always | RCP- |
| `restaurant.bill.settled.v1` | INVOICE | Corporate/on-account | INV- |
| `restaurant.bill.split.v1` | SALES_RECEIPT (×N) | Per split party | RCP- |
| `restaurant.order.cancelled.v1` | CREDIT_NOTE | If already billed | CN- |

#### Missing Events to Add
| Event | When | Purpose |
|-------|------|---------|
| `restaurant.bill.presented.v1` | Waiter brings bill to table | Timing audit, no doc |
| `restaurant.void.slip.created.v1` | Manager voids item | CREDIT_NOTE / audit trail |

#### Payload Gaps — `engines/restaurant/events.py`

**`build_bill_settled_payload` must add (CRITICAL):**
- `order_lines` — aggregated items from all orders on this table
- `covers` — number of diners (available from table.opened)
- `table_name` — e.g. "Table 5"
- `server_id` — who served the table
- `tax_amount` — tax component
- `discount_amount` — any discount applied

**`build_bill_split_payload` must add:**
Each entry in `splits` must include full line items and amount for that party.

**`build_kitchen_ticket_sent_payload` — SUFFICIENT for KOT**
Has: `ticket_id`, `order_id`, `table_id`, `station`, `items`, `priority`. Just needs auto-trigger.

#### Restaurant Bill Render Plan Structure
```json
{
  "header": {
    "business_name": "[resolved]", "table": "Table 5", "covers": 4,
    "server": "[resolved]", "receipt_no": "RCP-2024-0042",
    "date": "2024-01-15 20:30"
  },
  "line_items": [
    {"item": "Nyama Choma 1kg", "qty": 1, "price": 1200, "total": 1200},
    {"item": "Tusker Beer", "qty": 4, "price": 350, "total": 1400}
  ],
  "totals": {
    "subtotal": 2600, "tax": 416, "tip": 260, "grand_total": 3276, "currency": "KES"
  },
  "footer": {"payment_method": "CARD", "notes": "Thank you!"}
}
```

#### Kitchen Order Ticket (KOT) Render Plan Structure
```json
{
  "header": {
    "kot_no": "KOT-0042", "table": "Table 5",
    "station": "GRILL", "priority": "NORMAL", "time": "20:15"
  },
  "line_items": [
    {"item": "Nyama Choma 1kg", "qty": 1, "notes": "well done"},
    {"item": "Chips", "qty": 2, "notes": ""}
  ],
  "totals": {},
  "footer": {"order_id": "ORD-001"}
}
```

---

### C. WORKSHOP (Fabrication / Fundi / Garage) — Document Flow

| Trigger Event | Document | Condition | Prefix |
|--------------|----------|-----------|--------|
| `workshop.quote.generated.v1` | QUOTE | Always | QT- |
| `workshop.project.quote.generated.v1` | QUOTE | Always | QT- |
| `workshop.quote.accepted.v1` (new) | PROFORMA_INVOICE | Always | PRO- |
| `workshop.job.assigned.v1` | WORK_ORDER | Always | WO- |
| `workshop.cutlist.generated.v1` | CUTTING_LIST | Always | CL- |
| `workshop.job.completed.v1` | COMPLETION_CERTIFICATE | Always | CC- |
| `workshop.job.invoiced.v1` | INVOICE | Always | INV- |

#### Missing Events to Add
| Event | When | Document |
|-------|------|----------|
| `workshop.quote.accepted.v1` | Customer approves quote | PROFORMA_INVOICE |
| `workshop.quote.rejected.v1` | Customer rejects quote | None (tracking only) |
| `workshop.installation.completed.v1` | On-site install done | INSTALLATION_REPORT |

#### Payload Gaps — `engines/workshop/events.py`

**`build_quote_generated_payload` must add (CRITICAL):**
- `customer_id` — quote is currently addressed to nobody
- `total_price` — in minor currency units (e.g. 87000 = KES 870.00)
- `currency` — e.g. "KES"
- `labour_cost` — breakdown: labour component
- `material_cost` — breakdown: materials component
- `valid_until` — ISO date string, e.g. "2024-02-15"

**`build_job_invoiced_payload` must add (HIGH):**
- `customer_id`
- `labour_hours`, `labour_rate`, `labour_total`
- `parts_used` — list of `{part_name, qty, unit_price, line_total}`
- `materials_total`
- `tax_amount`
- `discount_amount`
- `payment_terms` — e.g. "NET_30"
- `due_date` — ISO date string

**`build_job_assigned_payload` must add (for Work Order):**
- `job_description`
- `estimated_completion`
- `customer_id`
- `priority`

#### Workshop Quote Render Plan Structure
```json
{
  "header": {
    "quote_no": "QT-2024-0018", "customer_name": "[resolved]",
    "customer_address": "[resolved]", "valid_until": "2024-02-15",
    "date": "2024-01-15", "prepared_by": "[actor name]"
  },
  "line_items": [
    {"description": "Sliding Window 1200x1000mm", "qty": 3,
     "unit_price": 25000, "total": 75000}
  ],
  "totals": {
    "labour": 15000, "materials": 60000, "subtotal": 75000,
    "tax": 12000, "grand_total": 87000, "currency": "KES"
  },
  "footer": {
    "valid_until": "2024-02-15",
    "notes": "Price includes installation. 50% deposit required."
  }
}
```

#### Workshop Invoice Render Plan Structure
```json
{
  "header": {
    "invoice_no": "INV-2024-0009", "customer_name": "[resolved]",
    "invoice_date": "2024-01-30", "due_date": "2024-02-28",
    "payment_terms": "NET_30"
  },
  "line_items": [
    {"description": "Labour 12hrs @ KES 1,500/hr", "qty": 12,
     "unit_price": 1500, "total": 18000},
    {"description": "Aluminium Profile 6m", "qty": 5,
     "unit_price": 3200, "total": 16000}
  ],
  "totals": {
    "subtotal": 34000, "tax_total": 5440, "grand_total": 39440, "currency": "KES"
  },
  "footer": {
    "bank_details": "[configured by admin]",
    "notes": "Payment due within 30 days."
  }
}
```

---

### D. HOTEL (Rooms / Property) — Document Flow

All 6 hotel sub-engines exist in the codebase. ZERO document generation is wired.

#### hotel_reservation — Events → Documents
| Trigger Event | Document | Condition | Prefix |
|--------------|----------|-----------|--------|
| `hotel.reservation.confirmed.v1` | RESERVATION_CONFIRMATION | Always | RESV- |
| `hotel.guest.checked_in.v1` | REGISTRATION_CARD | Always | REG- |
| `hotel.reservation.cancelled.v1` | CANCELLATION_NOTE | Always | CXL- |
| `hotel.reservation.no_show.v1` | CANCELLATION_NOTE | If charge applied | CXL- |
| `hotel.guest.checked_out.v1` | INVOICE | Company billing | INV- |
| `hotel.guest.checked_out.v1` | SALES_RECEIPT | Individual/cash | RCP- |

#### hotel_folio — Events → Documents
| Trigger Event | Document | Condition | Prefix |
|--------------|----------|-----------|--------|
| `hotel.folio.settled.v1` | FOLIO (Guest Bill) | Always | FOL- |
| `hotel.folio.settled.v1` | INVOICE | Company / corporate | INV- |
| `hotel.folio.adjusted.v1` | CREDIT_NOTE | adjustment_type=CREDIT | CN- |
| `hotel.folio.adjusted.v1` | DEBIT_NOTE | adjustment_type=DEBIT | DBN- |
| `hotel.folio.split.v1` | FOLIO (×N) | Per split folio | FOL- |

#### Payload Gaps — `engines/hotel_folio/events.py`

**`build_folio_settled_payload` must add (CRITICAL):**
```python
# Current: totals only — no charge detail
"folio_id", "total_charges", "total_payments", "balance_due", "payment_method"

# Must add:
"charge_lines": [...],    # all posted charges: room nights, restaurant, minibar, etc.
"guest_name": str,        # from folio.opened
"room_number": str,       # from check-in
"arrival_date": str,
"departure_date": str,
"nights": int,
"tax_amount": int,
```

**`build_folio_opened_payload` — GOOD for REGISTRATION_CARD**
Already has: `guest_id`, `guest_name`, `room_id`, `currency`, `reservation_id`.

#### Hotel Folio Render Plan Structure
```json
{
  "header": {
    "business_name": "[Hotel name]", "folio_no": "FOL-2024-0088",
    "guest_name": "John Doe", "room": "204",
    "arrival": "2024-01-10", "departure": "2024-01-13", "nights": 3
  },
  "line_items": [
    {"date": "2024-01-10", "description": "Room Night - Deluxe", "amount": 8500},
    {"date": "2024-01-11", "description": "Room Night - Deluxe", "amount": 8500},
    {"date": "2024-01-11", "description": "Restaurant - Dinner", "amount": 3200},
    {"date": "2024-01-12", "description": "Room Night - Deluxe", "amount": 8500}
  ],
  "totals": {
    "subtotal": 28700, "tax": 4592, "grand_total": 33292, "currency": "KES"
  },
  "footer": {"payment_method": "CARD", "notes": "Thank you for staying with us"}
}
```

---

### E. PROCUREMENT — Document Flow

| Trigger Event | Document | Condition | Prefix |
|--------------|----------|-----------|--------|
| `procurement.order.created.v1` | PURCHASE_ORDER | Always | PO- |
| `procurement.order.received.v1` | GOODS_RECEIPT_NOTE | Always | GRN- |
| `procurement.invoice.matched.v1` | None (capture only) | Already a supplier doc | — |
| `procurement.payment.released.v1` | PAYMENT_VOUCHER | Always | PV- |

---

### F. COMMON FINANCIAL DOCUMENTS

| Document | Trigger | Engine | Prefix |
|----------|---------|--------|--------|
| STATEMENT_OF_ACCOUNT | Scheduled/on-demand | Accounting | STMT- |
| PAYMENT_VOUCHER | `procurement.payment.released.v1` | Cash/Accounting | PV- |
| PETTY_CASH_VOUCHER | Manual command | Cash | PCV- |
| CREDIT_NOTE | `retail.refund.issued.v1` / adjustments | Retail/Restaurant | CN- |
| STOCK_TRANSFER_NOTE | stock transfer command | Inventory | STN- |
| STOCK_ADJUSTMENT_NOTE | stock adjustment command | Inventory | SAN- |

---

## COMPLETE GAP REGISTRY

### GAP SET 1: Infrastructure / Wiring (CRITICAL — System Broken)
| ID | Gap | File | Severity |
|----|-----|------|----------|
| W-01 | `RetailSubscriptionHandler` not registered in bootstrap | `core/bootstrap/subscription_wiring.py` | CRITICAL |
| W-02 | `actor_type="System"` wrong case in retail subscriptions | `engines/retail/subscriptions.py:70` | CRITICAL |
| W-03 | No `DocumentSubscriptionHandler` class anywhere | Missing file | CRITICAL |
| W-04 | `DocumentIssuanceService` HTTP-only, no event path | `adapters/django_api/wiring.py:308` | CRITICAL |
| W-05 | `VALID_DOCUMENT_TYPES` only allows RECEIPT/QUOTE/INVOICE | `core/documents/models.py:22` | CRITICAL |
| W-06 | Issuance registry has only 3 command/event pairs | `core/document_issuance/registry.py` | CRITICAL |

### GAP SET 2: Retail POS Document Gaps
| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| R-01 | No auto-receipt after `retail.sale.completed.v1` | Receipt must fire on sale close | CRITICAL |
| R-02 | `customer_id` dropped from sale_completed payload | Receipt can't address customer | HIGH |
| R-03 | No sequential receipt number | Legal receipts need RCP-2024-0001 | HIGH |
| R-04 | Business info absent from all event payloads | Required for tax-compliant receipts | HIGH |
| R-05 | No auto-refund note after `retail.refund.issued.v1` | Customer needs proof of refund | MEDIUM |
| R-06 | `build_sale_voided_payload` has no lines or amount | Void/credit note cannot be generated | MEDIUM |
| R-07 | No `cashier_name` — only `actor_id` UUID | Receipt should show cashier name | LOW |
| R-08 | No SALES_ORDER for on-account sales | On-account workflow incomplete | MEDIUM |
| R-09 | No DELIVERY_NOTE trigger | Dispatched goods leave no document | MEDIUM |

### GAP SET 3: Restaurant / Bar / BBQ Document Gaps
| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| RE-01 | No auto-receipt after `restaurant.bill.settled.v1` | Bill document never auto-generated | CRITICAL |
| RE-02 | `build_bill_settled_payload` missing order line items | Bill has no itemised food/drinks list | CRITICAL |
| RE-03 | No `restaurant.bill.presented.v1` event | Gap between "check please" and settlement | HIGH |
| RE-04 | No per-split receipts after `restaurant.bill.split.v1` | Each party needs their own receipt | HIGH |
| RE-05 | No KOT document from kitchen ticket event | Kitchen lacks printable/displayable ticket | MEDIUM |
| RE-06 | `covers` and `table_name` absent from bill_settled | Bill doesn't show table or guest count | MEDIUM |
| RE-07 | No `server_id` on bill payload | Restaurant receipt should show server | LOW |
| RE-08 | No void/cancel slip document | Audit trail for voided items missing | MEDIUM |

### GAP SET 4: Workshop Document Gaps
| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| WS-01 | No auto-quote document after `workshop.quote.generated.v1` | Quote stored internally, no customer doc | CRITICAL |
| WS-02 | No auto-invoice document after `workshop.job.invoiced.v1` | Customer gets no invoice document | CRITICAL |
| WS-03 | `build_quote_generated_payload` has NO price | Quote has materials but zero cost data | CRITICAL |
| WS-04 | `customer_id` not in quote payload | Quote addressed to nobody | HIGH |
| WS-05 | No `valid_until` on quotes | Legal quotes must have an expiry | HIGH |
| WS-06 | No `workshop.quote.accepted.v1` event | Quote acceptance not tracked | HIGH |
| WS-07 | No `workshop.quote.rejected.v1` event | Quote rejection not tracked | MEDIUM |
| WS-08 | `build_job_invoiced_payload` has no line breakdown | Invoice shows total only, no labor/parts | HIGH |
| WS-09 | No `tax_amount` or `discount_amount` in invoice payload | Tax invoice compliance broken | HIGH |
| WS-10 | No WORK_ORDER document on job assignment | Technician has no formal work document | MEDIUM |
| WS-11 | No COMPLETION_CERTIFICATE event/document | No formal handover document | MEDIUM |
| WS-12 | No `payment_terms` / `due_date` in invoice payload | Invoice must specify payment deadline | MEDIUM |
| WS-13 | No CUTTING_LIST document trigger | Cutting list stored but not issued as doc | MEDIUM |
| WS-14 | No MATERIAL_REQUISITION event/document | No formal material pickup from store | MEDIUM |

### GAP SET 5: Hotel Document Gaps
| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| H-01 | No RESERVATION_CONFIRMATION after `hotel.reservation.confirmed.v1` | Guest has no booking confirmation doc | CRITICAL |
| H-02 | No FOLIO document after `hotel.folio.settled.v1` | Checkout gives no guest bill | CRITICAL |
| H-03 | `build_folio_settled_payload` missing charge line items | Folio bill has no itemised charges | CRITICAL |
| H-04 | No REGISTRATION_CARD after `hotel.guest.checked_in.v1` | Front desk check-in has no document | HIGH |
| H-05 | No CANCELLATION_NOTE after `hotel.reservation.cancelled.v1` | Guest has no cancellation confirmation | HIGH |
| H-06 | No INVOICE after checkout for company billing | Corporate bookings get no tax invoice | HIGH |
| H-07 | No CREDIT_NOTE after `hotel.folio.adjusted.v1` (credit) | Adjustment not documented for guest | MEDIUM |
| H-08 | No DEBIT_NOTE after `hotel.folio.adjusted.v1` (debit) | Extra charges not formally documented | MEDIUM |

### GAP SET 6: Procurement Document Gaps
| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| P-01 | No PURCHASE_ORDER document after `procurement.order.created.v1` | PO created but never sent to supplier | HIGH |
| P-02 | No GOODS_RECEIPT_NOTE after `procurement.order.received.v1` | Stock received without GRN | HIGH |
| P-03 | No PAYMENT_VOUCHER after `procurement.payment.released.v1` | Supplier payment lacks voucher | MEDIUM |

### GAP SET 7: Cross-Cutting Gaps (All Engines)
| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| X-01 | No business info resolver (name, address, TIN/VAT) | All legal documents missing issuer info | HIGH |
| X-02 | No customer detail resolver (name, address from UUID) | Documents cannot address customers | HIGH |
| X-03 | Numbering engine not wired to any engine event | Sequential doc numbers never assigned | HIGH |
| X-04 | FLAG_ENABLE_DOCUMENT_DESIGNER blocks POS receipts | Standard receipts blocked by wrong flag | HIGH |
| X-05 | PDF/HTML renderers not exposed via API endpoint | Documents cannot be downloaded/printed | HIGH |
| X-06 | No i18n/locale support in templates | All docs English-only, no translation path | HIGH |
| X-07 | No document delivery (email/SMS/WhatsApp) | Docs generated but never sent to customer | MEDIUM |
| X-08 | No per-engine document template differentiation | Same receipt template for all contexts | MEDIUM |

---

## IMPLEMENTATION PRIORITY ORDER

### Phase 1 — Foundation (Unblock Everything)
1. **W-05** — Expand `VALID_DOCUMENT_TYPES` to include all 22 new types
2. **W-06** — Expand issuance registry with all new command/event pairs
3. **W-01 + W-02** — Fix retail bootstrap wiring + actor_type bug
4. **X-04** — Separate standard-receipts flag from document-designer flag
5. **X-01/X-02** — Add business info + customer resolver stubs

### Phase 2 — Core Document Auto-Generation
6. **W-03/W-04** — Create `DocumentSubscriptionHandler` + wire to event bus
7. **R-01 to R-04** — Retail: auto-receipt, customer_id in payload, numbering
8. **RE-01 to RE-02** — Restaurant: auto-receipt, line items in bill_settled
9. **H-01 to H-03** — Hotel: reservation confirmation + folio with charge lines
10. **WS-01 to WS-04** — Workshop: auto-quote doc, price in payload, customer_id

### Phase 3 — Document Completeness
11. **WS-06/WS-07** — Add `workshop.quote.accepted.v1` + `quote.rejected.v1` events
12. **WS-08/WS-09/WS-12** — Fix invoice payload (lines, tax, terms)
13. **WS-10/WS-11/WS-13** — Add Work Order, Completion Certificate, Cutting List docs
14. **RE-03 to RE-05** — Restaurant: bill.presented, split receipts, KOT document
15. **P-01 to P-03** — Procurement: PO, GRN, Payment Voucher
16. **H-04 to H-08** — Hotel: Registration Card, Cancellation Note, Credit/Debit Notes

### Phase 4 — Delivery & Rendering
17. **X-05** — Expose `GET /docs/{id}/pdf` and `GET /docs/{id}/html` endpoints
18. **X-03** — Wire numbering engine inside DocumentSubscriptionHandler
19. **X-06** — i18n: template label keys + translation table in Admin
20. **X-07** — Document delivery (email/SMS/WhatsApp) integration stubs

---

## TEMPLATE NAMING CONVENTION
```
Default platform:     default.{doc_type_lower}.v1
Business override:    {business_id}.{doc_type_lower}.v{n}
Branch override:      {business_id}.{branch_id}.{doc_type_lower}.v{n}
```

## LANGUAGE / LOCALE ARCHITECTURE
- **System language:** English (all internal keys, event types, constants)
- **Document render language:** Configured per business in Admin settings
- **Translations:** Template label keys resolved by locale bundle at render time
- **Admin ships:** Default translations for major languages (sw, fr, ar, pt, etc.)
- **User can:** Customise label strings or add locales via Admin panel
- **Locale format:** `{language}_{country}` e.g. `sw_KE`, `en_KE`, `fr_CI`, `ar_EG`
- **Fallback chain:** `{locale}` → `{language}` → `en`
