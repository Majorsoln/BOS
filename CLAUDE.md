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

### INFRA-03 — ~~No DocumentSubscriptionHandler~~ **RESOLVED (2026-03-04)**
`engines/documents/subscriptions.py` — 29-event handler, fully wired in bootstrap.
`business_info_resolver` + `customer_info_resolver` now injectable callables.
Stubs return `{}` / `"Walk-in Customer"` until real resolvers are provided at startup.
**Severity:** ~~CRITICAL~~ → MEDIUM (resolver stubs are the remaining gap for legal compliance)

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
| W-03 | ~~No `DocumentSubscriptionHandler` class anywhere~~ | **RESOLVED** — `engines/documents/subscriptions.py` 29 handlers wired | ~~CRITICAL~~ |
| W-04 | ~~`DocumentIssuanceService` HTTP-only, no event path~~ | **RESOLVED** — DocumentSubscriptionHandler calls service; `document_service` passed in bootstrap | ~~CRITICAL~~ |
| W-05 | ~~`VALID_DOCUMENT_TYPES` only allows RECEIPT/QUOTE/INVOICE~~ | **RESOLVED** — all 25 doc types in `VALID_DOCUMENT_TYPES` | ~~CRITICAL~~ |
| W-06 | ~~Issuance registry has only 3 command/event pairs~~ | **RESOLVED** — all 25 command/event pairs in registry | ~~CRITICAL~~ |

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
| X-01 | ~~No business info resolver~~ | **RESOLVED** — real `_business_info_resolver` in `adapters/django_api/wiring.py` queries identity_store ORM (name, address, city, phone, email, tax_id, logo_url) | ~~HIGH~~ |
| X-02 | ~~No customer detail resolver~~ | **RESOLVED** — `_customer_info_resolver` wired; returns stub until CustomerProfileService is persistent | ~~HIGH~~ |
| X-03 | ~~Numbering engine not wired~~ | **RESOLVED** — `InMemoryNumberingProvider` registered in `wiring.py` with all 26 doc type policies; `DocumentIssuanceService` calls it on every issue | ~~HIGH~~ |
| X-04 | ~~FLAG_ENABLE_DOCUMENT_DESIGNER blocks POS receipts~~ | **RESOLVED** — `document_policy.py` now uses `FLAG_ENABLE_DOCUMENT_ENGINE` (not DESIGNER); tests updated | ~~HIGH~~ |
| X-05 | ~~PDF/HTML renderers not exposed via API~~ | **RESOLVED** — `GET /docs/{id}/render-pdf` and `/render-html` routes exist in `urls.py` | ~~HIGH~~ |
| X-06 | No i18n/locale support in templates | All docs English-only, no translation path | HIGH |
| X-07 | No document delivery (email/SMS/WhatsApp) | Docs generated but never sent to customer | MEDIUM |
| X-08 | No per-engine document template differentiation | Same receipt template for all contexts | MEDIUM |

### GAP SET 8: Accounting Engine Gaps
**Session:** 2026-03-04 Deep Dive
| ID | Gap | File | Severity | Status |
|----|-----|------|----------|--------|
| AC-01 | `handle_retail_sale` used `net_amount` only — no VAT split journal | `engines/accounting/subscriptions.py` | HIGH | **FIXED** — now posts DR payment / CR Revenue + CR VAT_PAYABLE |
| AC-02 | `handle_restaurant_bill` had no tax split | `engines/accounting/subscriptions.py` | HIGH | **FIXED** — same 3-line pattern with VAT_PAYABLE |
| AC-03 | `handle_workshop_invoice` has no tax/labour/materials breakdown | `engines/accounting/subscriptions.py` | HIGH | OPEN — workshop payload needs `tax_amount` first (WS-09) |
| AC-04 | No handler for `hotel.folio.settled.v1` | Missing | HIGH | **FIXED** — `handle_hotel_folio_settled` added; supports company billing → AR |
| AC-05 | No handler for `procurement.payment.released.v1` | Missing | HIGH | **FIXED** — `handle_procurement_payment_released` added; DR AP / CR Bank |
| AC-06 | No PAYMENT_VOUCHER document trigger from accounting | Missing | HIGH | OPEN — needs DocumentSubscriptionHandler (W-03) |
| AC-07 | No STATEMENT_OF_ACCOUNT auto-generation | Missing | MEDIUM | **FIXED** — `StatementGenerateRequest` command + `accounting.statement.generated.v1` event wired; `DocumentSubscriptionHandler.handle_accounting_statement_generated` issues STATEMENT doc |
| AC-08 | No `ObligationCreateRequest` document trigger | Missing | MEDIUM | OPEN |
| AC-09 | No handler for `cash.session.closed.v1` | Missing | MEDIUM | **FIXED** — `handle_cash_session_closed` posts CASH_OVER_SHORT journal on non-zero variance |
| AC-10 | No handler for `retail.refund.issued.v1` | Missing | HIGH | **FIXED** — `handle_retail_refund` added; DR Revenue / CR Cash |
| AC-11 | No handler for `restaurant.order.cancelled.v1` | Missing | MEDIUM | **PARTIAL** — handler exists but `build_order_cancelled_payload` lacks `refund_amount`/`currency`, so reversal journal never posts (see APM-01) |
| AC-12 | `handle_payroll_run` deductions lumped into single TAX_PAYABLE | `engines/accounting/subscriptions.py` | MEDIUM | **FIXED** — deductions dict split per named key: PAYE → PAYE_PAYABLE, NSSF → NSSF_PAYABLE, NHIF/SHIF → NHIF_PAYABLE, remainder → OTHER_DEDUCTIONS_PAYABLE |
| AC-13 | No AR aging snapshot | Missing | MEDIUM | OPEN |

### GAP SET 9: Cash Engine Gaps
**Session:** 2026-03-04 Deep Dive
| ID | Gap | File | Severity | Status |
|----|-----|------|----------|--------|
| CS-01 | Workshop and hotel cash payments not recorded in drawer | Missing handlers | HIGH | **FIXED** — `handle_workshop_invoice` + `handle_hotel_folio` added |
| CS-02 | Hotel folio cash not going into drawer | Missing | HIGH | **FIXED** — covered by `handle_hotel_folio` |
| CS-03 | No PETTY_CASH_VOUCHER document trigger on expense_payout withdrawal | Missing | HIGH | **FIXED** — `handle_cash_withdrawal_recorded` added; subscribes `cash.withdrawal.recorded.v1` → PETTY_CASH_VOUCHER |
| CS-04 | No PAYMENT_VOUCHER trigger on bank/safe withdrawal | `cash.withdrawal.recorded.v1` → PETTY_CASH_VOUCHER already covers this | MEDIUM | **RESOLVED** — withdrawal → PETTY_CASH_VOUCHER wired |
| CS-05 | No cash session closing reconciliation document | Missing | MEDIUM | OPEN |
| CS-06 | CARD and MOBILE payments have no float tracking | `engines/cash/subscriptions.py` | MEDIUM | OPEN — by design; card settled via bank reconciliation |
| CS-07 | `cash.session.closed.v1` payload missing `variance` field | `engines/cash/events.py` | MEDIUM | **FIXED** — `variance` field added to `build_session_closed_payload` (falls back to `difference`) |
| CS-08 | Supplier cash payments (procurement) not going out of drawer | Missing | HIGH | **FIXED** — `handle_procurement_payment` added; uses WithdrawalRecordRequest |

### GAP SET 10: Reporting Engine Gaps
**Session:** 2026-03-04 Deep Dive
| ID | Gap | File | Severity | Status |
|----|-----|------|----------|--------|
| RP-01 | No hotel events subscribed — zero hotel KPIs recorded | Missing | HIGH | **FIXED** — hotel.folio.settled, reservation.confirmed, guest.checked_in/out added |
| RP-02 | No `cash.session.closed.v1` handler for cash KPIs | Missing | MEDIUM | **FIXED** — `handle_cash_session_closed` records CASH_SESSIONS_CLOSED (count) + CASH_SESSION_VARIANCE (abs variance amount) |
| RP-03 | No accounting journal handler (audit trail KPI) | Missing | LOW | OPEN |
| RP-04 | `handle_bill_settled` had no tax/covers KPIs | `engines/reporting/subscriptions.py` | MEDIUM | PARTIAL — payment_method dimension added; covers/tax still needs payload update (RE-06) |
| RP-05 | `handle_sale_completed` used `net_amount` only | `engines/reporting/subscriptions.py` | MEDIUM | **FIXED** — now uses `total_amount` (gross) with payment_method dimension |
| RP-06 | No payment method breakdown dimension on KPIs | Missing | HIGH | **FIXED** — `dimension={"payment_method": ...}` added to retail + restaurant + hotel revenue KPIs |
| RP-07 | No inventory KPIs (stock adjusted/transferred) | Missing | MEDIUM | **FIXED** — `handle_stock_adjusted` + `handle_stock_transferred` added; records STOCK_ADJUSTMENTS, STOCK_ADJUSTED_UNITS, STOCK_TRANSFERS, STOCK_TRANSFERRED_UNITS |
| RP-08 | No daily revenue snapshot auto-generation | Missing | HIGH | OPEN — needs scheduler |
| RP-09 | `retail.refund.issued.v1` not subscribed | Missing | HIGH | **FIXED** — `handle_retail_refund` added; records REFUNDS_ISSUED + REFUND_COUNT |
| RP-10 | `restaurant.order.cancelled.v1` not subscribed | Missing | MEDIUM | **FIXED** — `handle_order_cancelled` added; records ORDERS_CANCELLED |
| RP-11 | Workshop quote pipeline not tracked | Missing | MEDIUM | **FIXED** — `handle_workshop_quote_generated/accepted/rejected` added; records QUOTES_GENERATED, QUOTE_VALUE, QUOTES_ACCEPTED, QUOTE_ACCEPTED_VALUE, QUOTES_REJECTED |
| RP-12 | KPI `dimension` field unused in subscriptions | `engines/reporting/subscriptions.py` | MEDIUM | **FIXED** — payment_method dimension now passed for revenue KPIs |
| RP-13 | No hotel KPIs: ADR, RevPAR, occupancy | Missing | HIGH | **FIXED (ADR only)** — HOTEL_REVENUE_TOTAL, HOTEL_ROOM_NIGHTS, HOTEL_ADR, HOTEL_CHECKOUTS added; RevPAR needs room inventory |

### GAP SET 11: Payload Mismatches — Document Handlers vs Event Builders
**Session:** 2026-03-06 Deep Code Review
| ID | Gap | File(s) | Severity | Status |
|----|-----|---------|----------|--------|
| PM-01 | `handle_procurement_order_received` reads `po_id` but event provides `order_id` | `engines/documents/subscriptions.py:863` vs `engines/procurement/events.py:111` | CRITICAL | **FIXED** — `po_id` alias added to `build_order_received_payload` |
| PM-02 | `handle_procurement_order_received` reads `supplier_id`, `supplier_name` — NOT in `build_order_received_payload` | `engines/documents/subscriptions.py:864-865` vs `engines/procurement/events.py:108-118` | CRITICAL | **FIXED** — `supplier_id`, `supplier_name` added to payload builder |
| PM-03 | `handle_inventory_stock_transfer` reads `transfer_id` — NOT in `build_stock_transferred_payload` | `engines/documents/subscriptions.py:904` vs `engines/inventory/events.py:105-118` | CRITICAL | **FIXED** — `transfer_id` added (falls back to `reference_id`) |
| PM-04 | `handle_inventory_stock_transfer` reads `items[]` as array — event has single-item fields (`item_id`, `sku`, `quantity`) | `engines/documents/subscriptions.py:907` vs `engines/inventory/events.py:108-109` | CRITICAL | **FIXED** — `items[]` array added wrapping single item |
| PM-05 | `handle_inventory_stock_adjusted` reads `items[]` as array — event has single-item fields | `engines/documents/subscriptions.py:925` vs `engines/inventory/events.py:124-128` | CRITICAL | **FIXED** — `adjustment_id` + `items[]` array added |
| PM-06 | `handle_hotel_guest_checked_out` reads `company_id` — NOT in `build_guest_checked_out_payload`; corporate invoice path NEVER fires | `engines/documents/subscriptions.py:742` vs `engines/hotel_reservation/events.py:161-171` | CRITICAL | **FIXED** — `company_id`, `company_name` added to checkout payload |
| PM-07 | `handle_hotel_guest_checked_in` builds registration card without `guest_name` — field also missing from `build_guest_checked_in_payload` | `engines/documents/subscriptions.py:715-723` vs `engines/hotel_reservation/events.py:148-158` | HIGH | **FIXED** — `guest_id`, `guest_name` added to event + handler resolves guest |
| PM-08 | `handle_hotel_folio_settled` sets `grand_total = total_charges` but `tax_amount` is separate — should be `total_charges + tax_amount` | `engines/documents/subscriptions.py:796` | MEDIUM | **FIXED** — `grand_total = total_charges + tax_amount` |
| PM-09 | `handle_workshop_job_invoiced` sets both `subtotal` and `grand_total` to `amount` — ignores `tax_amount`/`discount_amount` | `engines/documents/subscriptions.py:605,608` | MEDIUM | **FIXED** — `subtotal` now back-computed; `grand_total = amount` (tax-inclusive) |
| PM-10 | Reporting `handle_stock_adjusted` reads `items[]` as array — same inventory single-item mismatch, `qty_delta` always 0 | `engines/reporting/subscriptions.py:334` | HIGH | **FIXED** — inventory event now provides `items[]` array |
| PM-11 | Reporting `handle_stock_transferred` reads `items[]` as array — same mismatch, `qty_moved` always 0 | `engines/reporting/subscriptions.py:355` | HIGH | **FIXED** — inventory event now provides `items[]` array |

### GAP SET 12: Accounting & Cash Payload Mismatches
**Session:** 2026-03-06 Deep Code Review
| ID | Gap | File(s) | Severity | Status |
|----|-----|---------|----------|--------|
| APM-01 | `handle_restaurant_order_cancelled` reads `refund_amount` and `currency` but `build_order_cancelled_payload` provides neither — handler ALWAYS returns early, reversal journal never posts | `engines/accounting/subscriptions.py:968` vs `engines/restaurant/events.py:109-116` | CRITICAL | **FIXED** — `refund_amount`, `currency` added to `build_order_cancelled_payload` |
| APM-02 | Cash `handle_retail_sale` records `net_amount` into drawer but customer pays `total_amount` (includes tax) — cash drawer balance understated | `engines/cash/subscriptions.py:139` | HIGH | **FIXED** — `amount_key` changed to `total_amount` |
| APM-03 | Refund journal posts flat `DR Revenue / CR Cash` without reversing VAT — VAT liability overstated after refunds | `engines/accounting/subscriptions.py:620-684` | MEDIUM | **FIXED** — 3-line journal: DR Revenue (net) + DR VAT_PAYABLE (tax) / CR Cash (total) |
| APM-04 | `build_refund_issued_payload` missing `tax_amount` — refund VAT reversal impossible | `engines/retail/events.py:167-178` | HIGH | **FIXED** — `tax_amount` added to refund event payload |

### GAP SET 13: Reporting Validation Failures
**Session:** 2026-03-06 Deep Code Review
| ID | Gap | File(s) | Severity | Status |
|----|-----|---------|----------|--------|
| RV-01 | `unit="AMOUNT"` used in 3 KPI handlers but not in `VALID_KPI_UNITS` — KPI recording crashes with ValueError | `engines/reporting/subscriptions.py:386,409,434` | CRITICAL | **FIXED** — changed to `MINOR_CURRENCY` |
| RV-02 | 20 KPI keys used by handlers but missing from `VALID_KPI_KEYS` — all KPI recording crashes | `engines/reporting/commands/__init__.py:45-66` | CRITICAL | **FIXED** — all 20 keys added to `VALID_KPI_KEYS` |

### GAP SET 14: Retail Command Request Missing Fields
**Session:** 2026-03-06 Deep Code Review
| ID | Gap | File(s) | Severity | Status |
|----|-----|---------|----------|--------|
| RC-01 | `SaleCompleteRequest` has no `customer_id` param — event payload always None, receipts always "Walk-in Customer" | `engines/retail/commands/__init__.py:258-317` | HIGH | **FIXED** — `customer_id: Optional[str]` added |
| RC-02 | `SaleCompleteRequest` has no `on_account`/`requires_delivery` — INVOICE and DELIVERY_NOTE documents never trigger | `engines/retail/commands/__init__.py:258-317` | HIGH | **FIXED** — `on_account: bool`, `requires_delivery: bool` added |
| RC-03 | `SaleVoidRequest` has no `lines`/`total_amount`/`currency`/`original_receipt_id` — CREDIT_NOTE doc handler always skips | `engines/retail/commands/__init__.py:320-359` | HIGH | **FIXED** — all fields added as optional params |
| RC-04 | `RefundIssueRequest` has no `customer_id` or `tax_amount` — refund notes can't address customer, VAT reversal impossible | `engines/retail/commands/__init__.py:362-415` | HIGH | **FIXED** — `customer_id`, `tax_amount` added |

---

## IMPLEMENTATION PRIORITY ORDER

### Phase 1 — Foundation (Unblock Everything)
1. ✅ **W-05** — Expand `VALID_DOCUMENT_TYPES` to include all 25 types — **DONE**
2. ✅ **W-06** — Expand issuance registry with all 25 command/event pairs — **DONE**
3. ✅ **W-01 + W-02** — Retail bootstrap wiring in place; actor_type uses "SYSTEM" — **DONE**
4. ✅ **X-04** — `document_policy.py` now uses `FLAG_ENABLE_DOCUMENT_ENGINE` (not DESIGNER); tests updated — **DONE**
5. ✅ **X-01/X-02** — Real business + customer resolvers wired in `adapters/django_api/wiring.py` — **DONE**

### Phase 2 — Core Document Auto-Generation
6. ✅ **W-03/W-04** — `DocumentSubscriptionHandler` exists + is wired — **DONE**
7. ✅ **R-01 to R-04** — Retail: auto-receipt wired; `customer_id`, `tax_amount`, `lines` all in payload — **DONE**
8. ✅ **RE-01 to RE-02** — Restaurant: auto-receipt wired; `order_lines`, `table_name`, `covers` in payload — **DONE**
9. ✅ **H-01 to H-03** — Hotel: reservation confirmation handler implemented with full guest/stay data — **DONE**
10. ✅ **WS-01 to WS-04** — Workshop: auto-quote, invoice, work order all wired — **DONE**

### Phase 3 — Document Completeness
11. ✅ **WS-06/WS-07** — `workshop.quote.accepted.v1` + `quote.rejected.v1` events exist + handlers wired — **DONE**
12. ✅ **WS-08/WS-09/WS-12** — Invoice payload has labour_hours, labour_rate, parts_used, tax_amount, discount_amount, payment_terms, due_date — **DONE**
13. ✅ **WS-10/WS-11/WS-13** — Work Order, Completion Certificate, Cutting List all wired — **DONE**
14. ✅ **RE-03 to RE-05** — `restaurant.bill.presented.v1` event + payload builder added; split receipts (`handle_restaurant_bill_split`) + KOT (`handle_kitchen_ticket_sent`) wired — **DONE**
15. ✅ **P-01 to P-03** — Procurement PO, GRN, Payment Voucher all wired — **DONE**
16. ✅ **H-04 to H-08** — Registration Card, Cancellation Note, Folio, Credit/Debit Note all wired — **DONE**

### Phase 3B — Accounting / Cash / Reporting Completeness (2026-03-04 session)
- ✅ **AC-01/AC-02** — VAT split journals for retail + restaurant revenue — **DONE**
- ✅ **AC-04** — Hotel folio accounting journal (incl. company billing → AR) — **DONE**
- ✅ **AC-05** — Procurement payment released → DR AP / CR Bank — **DONE**
- ✅ **AC-10** — Retail refund reversal journal — **DONE**
- ✅ **AC-03** — Workshop invoice tax split — **DONE** (tax_amount was already in payload; VAT split journal already in handle_workshop_invoice)
- ✅ **AC-07** — `StatementGenerateRequest` + `accounting.statement.generated.v1` + `handle_accounting_statement_generated` → STATEMENT doc — **DONE**
- ✅ **AC-09** — Cash session closed → ledger reconciliation entry — **DONE** (`handle_cash_session_closed` posts CASH_OVER_SHORT journal)
- ✅ **AC-11** — Restaurant order cancelled → revenue reversal journal — **DONE** (fires only when `refund_amount > 0`)
- ✅ **AC-12** — Payroll deductions split: PAYE/NSSF/NHIF/SHIF per named key in deductions dict — **DONE (2026-03-06)**
- ✅ **CS-01/CS-02** — Workshop + hotel cash payments into drawer — **DONE**
- ✅ **CS-08** — Procurement cash supplier payment → drawer withdrawal — **DONE**
- ✅ **CS-03** — PETTY_CASH_VOUCHER document on expense_payout — **DONE** (`cash.withdrawal.recorded.v1` subscribed)
- ✅ **CS-07** — `variance` field added to `build_session_closed_payload` — **DONE**
- ✅ **RP-01** — Hotel events subscribed: folio, reservation, check-in/out — **DONE**
- ✅ **RP-02** — Cash session KPIs: CASH_SESSIONS_CLOSED + CASH_SESSION_VARIANCE — **DONE (2026-03-06)**
- ✅ **RP-05/RP-06** — Total amount + payment method dimension on revenue KPIs — **DONE**
- ✅ **RP-09** — Retail refund KPI (REFUNDS_ISSUED, REFUND_COUNT) — **DONE**
- ✅ **RP-10** — Restaurant order cancelled KPI — **DONE**
- ✅ **RP-11** — Workshop quote pipeline: QUOTES_GENERATED, QUOTE_VALUE, QUOTES_ACCEPTED, QUOTE_ACCEPTED_VALUE, QUOTES_REJECTED — **DONE (2026-03-06)**
- ✅ **RP-12/RP-13** — Hotel ADR, room nights, checkout KPIs — **DONE**
- **RP-08** — Daily revenue snapshot auto-generation (needs scheduler — OPEN)
- ✅ **RP-07** — Inventory KPIs: `handle_stock_adjusted` + `handle_stock_transferred` record STOCK_ADJUSTMENTS, STOCK_ADJUSTED_UNITS, STOCK_TRANSFERS, STOCK_TRANSFERRED_UNITS — **DONE**

### Phase 3C — Document Subscription Completeness (2026-03-04 session)
- ✅ **Resolvers injectable** — `business_info_resolver` + `customer_info_resolver` in `DocumentSubscriptionHandler.__init__` — **DONE**
- ✅ **Bootstrap accepts resolvers** — `wire_all_subscriptions(business_info_resolver=..., customer_info_resolver=...)` — **DONE**
- ✅ **`handle_hotel_reservation_confirmed`** enriched with guest_name, arrival/departure, line_items, deposit — **DONE**
- ✅ **`handle_hotel_guest_checked_out`** implemented — INVOICE for company/corporate billing — **DONE**
- ✅ **Procurement `build_payment_released_payload`** — added `supplier_name`, `supplier_id`, `approved_by` — **DONE**
- ✅ **Hotel `build_reservation_confirmed_payload`** — added guest info, stay dates, room type, rate, currency — **DONE**
- ✅ **Real BusinessInfoResolver** — queries `Business` Django ORM; returns `{business_name, address, city, country_code, phone, email, tax_id, logo_url, default_currency}` — **DONE**
- ✅ **Real CustomerInfoResolver** — wired in `adapters/django_api/wiring.py`; returns stub until CustomerProfileService is persistent — **DONE**
- ✅ **`cash.withdrawal.recorded.v1`** — added to DOCUMENT_SUBSCRIPTIONS → `handle_cash_withdrawal_recorded` → PETTY_CASH_VOUCHER — **DONE**
- ✅ **Business model fields** — `address`, `city`, `phone`, `email`, `tax_id`, `logo_url` all exist on `core/identity_store/models.py:Business` — **DONE**
- **REMAINING: Persistent CustomerProfile DB** — currently only in-memory; add Django ORM table so `customer_info_resolver` can look up display_name by UUID
- ✅ **Workshop Phase 16/17/18 COMMAND_FLAG_MAP** — `workshop.style.register/update/deactivate.request`, `workshop.quote.generate/accept/reject.request`, `workshop.project.quote.generate.request` all added — **DONE (2026-03-05)**
- ✅ **`restaurant.bill.present.request`** — added to COMMAND_FLAG_MAP — **DONE (2026-03-05)**
- ✅ **`accounting.statement.generate.request`** — added to COMMAND_FLAG_MAP — **DONE (2026-03-05)**
- ✅ **`DocumentBuilderError`** — converted from frozen dataclass to regular Exception to fix Python `__traceback__` FrozenInstanceError — **DONE (2026-03-05)**

### Phase 4 — Delivery & Rendering
17. ✅ **X-05** — `/docs/{id}/render-pdf` and `/docs/{id}/render-html` endpoints exist — **DONE**
18. ✅ **X-03** — `InMemoryNumberingProvider` with all 26 doc type policies registered in `wiring.py` — **DONE**
19. **X-06** — i18n: template label keys + translation table in Admin (OPEN)
20. **X-07** — Document delivery (email/SMS/WhatsApp) integration stubs (OPEN)

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
