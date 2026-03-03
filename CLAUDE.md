# BOS — Gap Registry (Claude Working Notes)

## Session: Document & POS Gap Analysis
**Date:** 2026-03-03
**Branch:** claude/explain-codebase-mlsfr9vu6lpytugq-0E7ZN

---

## GAP SET 1: Wiring / Infrastructure Gaps (Critical — System Broken)

| ID | Gap | File | Severity |
|----|-----|------|----------|
| W-01 | `RetailSubscriptionHandler` not registered in bootstrap — cart_qr→POS handoff silently broken | `core/bootstrap/subscription_wiring.py` | CRITICAL |
| W-02 | `actor_type="System"` (wrong case) in retail subscriptions — all commands from handler fail | `engines/retail/subscriptions.py:70` | CRITICAL |
| W-03 | No `DocumentSubscriptionHandler` class exists — receipt/invoice/quote never auto-generated after any event | Missing file | CRITICAL |
| W-04 | `DocumentIssuanceService` only wired to HTTP API — no event-driven document generation | `adapters/django_api/wiring.py:308` | CRITICAL |

---

## GAP SET 2: Retail POS Document Gaps

| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| R-01 | No auto-receipt after `retail.sale.completed.v1` | Receipt must fire on sale close | CRITICAL |
| R-02 | `customer_id` not included in `build_sale_completed_payload` | Receipt can't address customer | HIGH |
| R-03 | No sequential receipt number — only UUID `sale_id` | Legal receipts need e.g. RCP-2024-0001 | HIGH |
| R-04 | Business info (name, address, TIN/VAT) not in any retail event payload | Required for tax-compliant receipts | HIGH |
| R-05 | No auto-refund note after `retail.refund.issued.v1` | Customer needs proof of refund | MEDIUM |
| R-06 | `build_sale_voided_payload` has no lines or amount | Void receipt cannot be generated | MEDIUM |
| R-07 | No `cashier_name` on receipt payload — only `actor_id` (UUID) | Receipt should show cashier name | LOW |

---

## GAP SET 3: Restaurant / Hotel / Bar / BBQ Document Gaps

| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| RE-01 | No auto-receipt/bill after `restaurant.bill.settled.v1` | Bill document must auto-generate on settlement | CRITICAL |
| RE-02 | `build_bill_settled_payload` missing order line items | Bill has no itemised list of what was consumed | CRITICAL |
| RE-03 | No `bill.presented.v1` event — customer can't "see" bill before paying | Gap between "check please" and settlement | HIGH |
| RE-04 | `build_bill_split_payload` — no per-split receipts | Each party in a split needs their own receipt | HIGH |
| RE-05 | Kitchen ticket (`restaurant.kitchen.ticket.sent.v1`) never produces a formal KOT document | Kitchen Order Ticket needed for stations | MEDIUM |
| RE-06 | `covers` and `table_name` not carried into `build_bill_settled_payload` | Bill should show table name and number of covers | MEDIUM |
| RE-07 | No `server_id`/server name on bill/receipt | Restaurant receipt should show which server | LOW |

---

## GAP SET 4: Workshop Document Gaps

| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| WS-01 | No auto-quote document after `workshop.quote.generated.v1` | Quote event fires but no `doc.quote.issue.request` follows | CRITICAL |
| WS-02 | No auto-invoice document after `workshop.job.invoiced.v1` | Accounting records debt, customer gets no document | CRITICAL |
| WS-03 | `build_quote_generated_payload` has NO price/cost | Quote has pieces & materials but no `total_price` or `currency` | CRITICAL |
| WS-04 | `customer_id` not in quote payload — quote is addressed to nobody | Quote can't name the customer | HIGH |
| WS-05 | No `valid_until` date on quotes | Quotes must have an expiry for legal validity | HIGH |
| WS-06 | No `workshop.quote.accepted.v1` event — acceptance not tracked | When customer approves quote, system is blind | HIGH |
| WS-07 | No `workshop.quote.rejected.v1` event | Rejected quotes not tracked | MEDIUM |
| WS-08 | `build_job_invoiced_payload` too minimal — no line breakdown | Invoice only has total `amount`, no labor/parts split | HIGH |
| WS-09 | No `tax_amount` or `discount_amount` in invoice payload | Tax invoice compliance requires tax line | HIGH |
| WS-10 | No Job Sheet / Work Order document when job assigned | Technician needs a printable work order | MEDIUM |
| WS-11 | No Job Completion Certificate event/document | Formal handover document for customer missing | MEDIUM |
| WS-12 | No `payment_terms` / `due_date` in invoice payload | Invoice must specify when payment is due | MEDIUM |

---

## GAP SET 5: Cross-Cutting Document Gaps (All Engines)

| ID | Gap | Detail | Severity |
|----|-----|--------|----------|
| X-01 | No business info resolver — name, address, TIN/VAT absent from all payloads | All legal documents need issuer info | HIGH |
| X-02 | No customer detail resolver — only `customer_id` (UUID) in payloads | Documents need customer name, address | HIGH |
| X-03 | No sequential document numbering linked to business type | Each engine needs its own counter (RCP-, INV-, QT-) | HIGH |
| X-04 | No document template per business type (retail vs restaurant vs workshop) | Same receipt template can't serve all contexts | MEDIUM |
| X-05 | `FLAG_ENABLE_DOCUMENT_DESIGNER` required for all documents — no default templates active | Documents blocked even for standard receipts | MEDIUM |
| X-06 | No PDF/print output renderer — only render_plan JSON stored | Documents exist as data but can't be printed | HIGH |
| X-07 | No document delivery mechanism (email, SMS, WhatsApp) | Documents generated but not sent to customer | MEDIUM |

---

## Next Steps (Priority Order)

1. Fix W-01, W-02 (bootstrap wiring + actor_type bug)
2. Create `DocumentSubscriptionHandler` (W-03)
3. Fix retail payload — add `customer_id` to sale_completed (R-02)
4. Fix bill_settled payload — add line items (RE-02)
5. Fix workshop quote payload — add pricing (WS-03), `customer_id` (WS-04)
6. Fix workshop invoice payload — add line breakdown, tax, terms (WS-08, WS-09, WS-12)
7. Add missing events: `quote.accepted`, `quote.rejected`, `bill.presented` (WS-06, WS-07, RE-03)
