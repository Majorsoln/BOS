# BOS — Master Reference Document
> Synthesized from all 18 official PDF specifications + doctrine files
> Purpose: Single authoritative reference for any Claude session working on BOS
> Last compiled: Phase 7 complete, 18 PDFs read

---

## PART 0 — BOS IDENTITY & DOCTRINE

### What BOS Is

> **"BOS is global by architecture, local by law, and neutral by design."**

BOS (Business Operating System) is a **deterministic, event-sourced, legally defensible business kernel**.

It is NOT:
- An ERP system
- A statutory accounting platform
- A point-of-sale app
- A country-specific compliance tool

It IS:
- A write-once, replay-forever event store
- A multi-tenant engine isolation platform
- A deterministic command processor
- An audit-complete financial and operational kernel
- A foundation that regional/vertical products build ON TOP OF

### The Three Laws of BOS

1. **State is derived from events only.** No hidden mutation ever.
2. **Engines are isolated.** No cross-engine direct calls — events only.
3. **AI is advisory only.** It never commits state, never writes events autonomously.

### Final Execution Doctrine

> *"BOS must be built from truth to operations, then insight, then intelligence, and finally scale. No phase should be skipped, merged, or rushed."*

> *"If an action cannot be explained as an event, corrected safely, and audited clearly — it does not belong in BOS."*

---

## PART 1 — SYSTEM ARCHITECTURE

### Event Sourcing Foundation

All state in BOS is derived from an **immutable, append-only event store**.

- Every event is permanently stored
- Events have SHA-256 hash-chain integrity
- Corrections = new events (never overwrite old ones)
- Replay must reproduce identical state (determinism)

### Mandatory Event Schema

Every event MUST have:

```
event_id          UUID (globally unique)
event_type        "engine.domain.action.vN" format
event_version     integer (increment for breaking changes)
business_id       UUID (always required — multi-tenant key)
branch_id         UUID or null (null = business scope, intentional)
source_engine     string (which engine emitted this)
actor             { type: Human|System|Device|AI, id, name }
reference         { object_type, object_id }  (what this event is about)
payload           { ...versioned data fields... }
occurred_at       ISO timestamp (passed explicitly, never datetime.now())
provisional       bool (true = offline event, awaiting sync)
correction_of     UUID or null (if this corrects a prior event)
```

### Command → Outcome → Event Pattern

```
Command (Intent)
    ↓ validation
    ↓ policy check
Outcome: ACCEPTED or REJECTED (binary, deterministic)
    ↓ if ACCEPTED
Event emitted → Event Store appended
    ↓
Subscribers react (other engines, projections)
```

**Never:**
- Modify DB directly from engine logic
- Skip the policy layer
- Allow partial acceptance

### Engine Isolation Rules

- Engines communicate ONLY via events
- No engine may call another engine's internals
- No engine may mutate another engine's state
- Cross-engine coordination = emit event → subscriber reacts

### Multi-Tenant Safety

- Every command executes within `BusinessContext`
- Every event contains `business_id`
- Cross-tenant access fails deterministically
- AI components are scoped to their tenant — never global

### Determinism Rules (NEVER VIOLATE)

DO NOT use inside outcome/engine logic:
- `random()` or any non-deterministic function
- `datetime.now()` or `time.time()`
- Non-deterministic ordering (e.g., unordered dict iteration)
- External state reads (no DB queries in engine logic)

If time is required → pass it explicitly as part of the command payload.

### Feature Flags

- All major engines must be behind feature flags
- Default: **OFF** unless explicitly activated per business
- Feature flag check happens at command dispatch time in `services/__init__.py`
- Uses `core/feature_flags/` module

### Offline-First Architecture

- Events created offline are marked `provisional = True`
- On sync, events are ordered chronologically and replayed
- Conflicts require **human review** — no silent merges
- No automatic conflict resolution

### Human Review States

Used whenever automated systems cannot resolve ambiguity:

| State | Meaning |
|-------|---------|
| `REVIEW_REQUIRED` | Automated system flagged — human must decide |
| `DISPUTED` | Human has challenged the result |
| `CONFIRMED` | Human confirmed correct |
| `REJECTED` | Human rejected — correction event issued |

Triggered by: cash difference on reconciliation, inventory variance, offline event conflict, AI advice flagged for review.

### Scope Policy (Universal Rules)

`business_id` is **always required** for every command/event.

`branch_id = None` is **valid and intentional** (business scope). Never guess a branch.

**Operations requiring `branch_id` (cannot be business-scope):**
- Cash: drawer ops (CashIn, CashOut, reconciliation, adjustments)
- Inventory: stock movements, transfers
- Procurement: Goods Receipt
- Retail: POS sale, refund
- Restaurant: table, order, kitchen, split billing
- Workshop: cutting optimization, material consumption, offcut tracking

**Operations OK at business-scope (branch optional):**
- Accounting: journal entries, trial balance, corrections
- Procurement: supplier registry, requisition, invoice matching
- Documents: template create/activate, verification
- Compliance: profile assign/validate
- Reporting: all views (branch as filter)

---

## PART 2 — PHASE MAP

```
Phase 0  ✅ Core Kernel         — event store, hash-chain, command bus, engine registry, replay
Phase 1  ✅ Governance          — policy engine, compliance, admin layer
Phase 2  ✅ HTTP API            — contracts, handlers, auth middleware, Django adapter
Phase 3  ✅ Document Engine     — builder, HTML+PDF renderer, numbering, verification, hash
Phase 4  ⚠️ Business Primitives — ledger✅ item✅ inventory✅ party✅ obligation✅ | actor❌ approval❌ workflow❌ document❌
Phase 5  ⚠️ Enterprise Engines  — accounting✅ cash✅ inventory✅ procurement✅ | subscriptions = pass stubs
Phase 6  ⚠️ Vertical Modules    — retail✅ restaurant⚠️(no kitchen/split) workshop⚠️(no geometry)
Phase 7  ⏳ AI & Decision Intel — promotion✅ hr✅ | AI advisory system = empty stubs
Phase 8  ❌ Security & Isolation
Phase 9  ❌ Integration Layer
Phase 10 ❌ Performance & Scale
Phase 11 ❌ Enterprise Admin
Phase 12 ❌ SaaS Productization
Phase 13 ❌ Documentation
```

---

## PART 3 — ENGINE SPECIFICATIONS

### CANONICAL ENGINE STRUCTURE

```
engines/<name>/
├── __init__.py              # empty
├── events.py                # constants, payload builders, register_*_event_types(), resolve_*_event_type()
├── commands/
│   └── __init__.py          # frozen dataclasses with __post_init__ validation, to_command() method
├── services/
│   └── __init__.py          # <Name>Service + <Name>ProjectionStore, check feature flag here
├── policies/
│   └── __init__.py          # functions returning Optional[RejectionReason(code, message, policy_name=...)]
└── subscriptions.py         # SUBSCRIPTIONS dict + <Name>SubscriptionHandler class
```

Naming conventions:
- Event types: `engine.domain.action.vN` (e.g. `retail.sale.completed.v1`)
- Command names: `engine.domain.action.request` (e.g. `retail.sale.complete.request`)
- All commands: `source_engine = "<engine>"`, `@dataclass(frozen=True)`
- All RejectionReason: MUST include `policy_name="function_name"` — tests will fail without it

---

### ENGINE 1: ACCOUNTING ENGINE

**What it is:** Management-first financial aggregator. Collects and journals financial events from ALL other engines.

**What it is NOT:** Statutory bookkeeping, tax filing, balance sheet for regulators.

**Core Principle:** BOS accounting aggregates management truth. It does not replace a chartered accountant.

**Event Types (5):**
- `accounting.journal.posted.v1` — double-entry journal
- `accounting.period.closed.v1` — period lock
- `accounting.correction.posted.v1` — correction (new event)
- `accounting.balance.snapshot.v1` — balance snapshot
- `accounting.trial.balance.produced.v1` — trial balance

**Key Rules:**
- Double-entry always: debit = credit
- Corrections are NEW events, never overwrites
- Branch is analytical dimension, not required for all entries
- Period close is business-level only (no branch-level period close)
- Tax-aware but does not file taxes

**Subscriptions (currently `pass` — needs implementation):**
- `inventory.stock.received.v1` → post inventory purchase journal
- `cash.payment.recorded.v1` → post payment journal

**Scope:** Business-scope OK for entries. Branch as analytical tag optional.

---

### ENGINE 2: CASH MANAGEMENT ENGINE (CME)

**What it is:** Physical cash tracking with location awareness, session/shift control.

**What it is NOT:** Payment gateway, bank API, treasury system.

**Core Principle:** Cash cannot exist without a physical location. Drawers are always branch-scoped.

**Event Types (5):**
- `cash.drawer.created.v1`
- `cash.transaction.recorded.v1` — CashIn or CashOut
- `cash.session.opened.v1` / `cash.session.closed.v1`
- `cash.reconciliation.posted.v1`
- `cash.transfer.recorded.v1`

**Key Rules:**
- Drawers MUST have branch_id — never business-scope
- Bank accounts CAN be business-scope
- CashIn/CashOut require branch_id
- Reconciliation (drawer close) requires branch_id
- Adjustments require branch_id + approval
- Cash vs non-cash separation enforced
- Session/shift control: opening float recorded, closing count recorded
- Differences → REVIEW_REQUIRED state → human confirms or rejects

**Subscriptions (currently `pass` — needs implementation):**
- `retail.sale.completed` → record sale cash transaction

**Scope:** Drawers = always branch. Bank/wallet = can be business-level.

---

### ENGINE 3: INVENTORY ENGINE

**What it is:** Physical stock tracking at branch level. Single truth of what stock exists where.

**What it is NOT:** Demand forecasting, purchase planning, warehouse management system.

**Core Principle:** Inventory truth happens at branch. Business-scope inventory is a view, not a source.

**Event Types (6):**
- `inventory.stock.received.v1` — goods received (from procurement GRN)
- `inventory.stock.issued.v1` — stock consumed/sold
- `inventory.stock.transferred.v1` — branch to branch move
- `inventory.stock.adjusted.v1` — correction (requires approval)
- `inventory.stock.reserved.v1` — reservation for pending order
- `inventory.stock.reservation.released.v1` — release reservation

**Key Rules:**
- All movements require branch_id
- Stock valuation (business-wide view) derived from branch movements
- Reservation: stock reserved before order confirmed, released on cancel
- Engines consume inventory through events (Workshop, Restaurant each emit consumption events)
- FIFO/LIFO: NOT yet implemented (GAP-07)
- Lot tracking: NOT yet implemented (GAP-07)

**Subscriptions (currently `pass` — needs implementation):**
- `procurement.order.received` → trigger stock received event

**Scope:** All movements = branch required. Valuation = business-scope view OK.

---

### ENGINE 4: PROCUREMENT ENGINE

**What it is:** Purchase lifecycle from request to payment reference. Controls what enters the business.

**What it is NOT:** Accounts payable system, budget management, supplier relationship management.

**Core Principle:** No inventory until goods physically received. Payment is a reference only.

**Full Lifecycle:**
```
Purchase Request → Approval → Purchase Order → Goods Receipt (GRN) → Invoice Match → Payment Reference
```

**Event Types (5):**
- `procurement.order.created.v1`
- `procurement.order.approved.v1`
- `procurement.order.received.v1` — GRN (triggers inventory update)
- `procurement.invoice.matched.v1`
- `procurement.order.cancelled.v1`

**Missing (GAP-06):**
- `procurement.requisition.created.v1`
- `procurement.requisition.approved.v1`
- `procurement.payment.released.v1`

**Key Rules:**
- GRN always requires branch_id (inventory impact)
- Supplier registry = business-scope
- Requisition = can be business or branch
- PO with branch delivery = requires branch_id
- Invoice matching = business-scope OK (depends on GRN)
- Approval chain configurable via policy

**Scope:** Supplier registry, requisitions = business OK. GRN = always branch.

---

### ENGINE 5: RETAIL ENGINE

**What it is:** Basket-based POS for physical/digital sales. Multi-price, multi-location.

**What it is NOT:** E-commerce platform, order management system, CRM.

**Core Principle:** Every sale is a branch event. Retail is the consumer-facing layer.

**Event Types (7):**
- `retail.sale.completed.v1`
- `retail.sale.refunded.v1`
- `retail.item.added.v1`
- `retail.cart.opened.v1`
- `retail.cart.abandoned.v1`
- `retail.discount.applied.v1`
- `retail.payment.split.v1`

**Key Rules:**
- POS sales always require branch_id
- Refunds always require branch_id
- Multi-price layers: business default + branch override
- Promotions reduce price BEFORE tax (see Promotion engine)
- Retail↔Workshop bridge: workshop items can appear in retail POS
- QR-based loyalty code scanned at POS
- Receipt = document engine output (hash-verified)

**Scope:** All POS ops = branch required. Item catalog management = business OK.

---

### ENGINE 6: RESTAURANT ENGINE

**What it is:** Order-centric table service lifecycle from open to close.

**What it is NOT:** Hotel PMS, reservation system, delivery platform.

**Core Principle:** The order is the central object. Every item on an order has its own lifecycle.

**Order Item Lifecycle:**
```
Created → Confirmed → In Preparation → Ready → Served → Closed
```

**Event Types (6):**
- `restaurant.table.opened.v1`
- `restaurant.order.placed.v1`
- `restaurant.order.item.status.updated.v1`
- `restaurant.bill.requested.v1`
- `restaurant.bill.paid.v1`
- `restaurant.table.closed.v1`

**Missing (GAP-09):**
- `restaurant.kitchen.ticket.sent.v1` — route to Kitchen Display System
- `restaurant.bill.split.v1` — split billing by guest/item

**Key Rules:**
- All restaurant ops require branch_id
- Kitchen/bar routing: items routed to preparation stations automatically
- Kitchen Display System (KDS) integration planned
- Self-service QR ordering: customer scans table QR, places own order
- Split billing: by guest count or item selection
- Per-item modifiers (add cheese, no onions) part of order item payload

**Scope:** All ops = branch required.

---

### ENGINE 7: WORKSHOP ENGINE

**What it is:** Style-driven custom manufacturing for windows, doors, and panels. Formula-based cut list generation.

**What it is NOT:** Generic project management, free-form design tool, CAD system.

**Core Principle:** Parametric geometry only. Same input → same cut list. No randomness. No free drawing.

**Project Lifecycle:**
```
Quote (style selection + measurements) → In Progress (cut list generated, materials reserved)
     → Completion (inventory consumed) → Invoiced → Closed
```

**Event Types (5):**
- `workshop.project.created.v1`
- `workshop.project.approved.v1`
- `workshop.job.started.v1`
- `workshop.job.completed.v1`
- `workshop.job.cancelled.v1`

**Missing (GAP-02 — CRITICAL):**
- `workshop.cutlist.generated.v1`
- `workshop.material.consumed.v1`
- `workshop.offcut.recorded.v1`

**Missing Commands (GAP-02):**
- `GenerateCutListRequest`
- `MaterialConsumeRequest`
- `OffcutRecordRequest`

**Scope:** Style catalog = business OK. Cut list, material consumption, offcut = always branch (inventory impact).

---

#### WORKSHOP FORMULA ENGINE (Complete Specification)

This is the most complex part of BOS. From `BOS_Workshop_HOW_Official.pdf` and `BOS_Workshop_Style_Examples.pdf`.

##### Shape Types

**Type 1 — Cut Shapes (Lines/1D):**
- Used for: frames, sashes, mullions, rails
- Unit: linear (meters or mm)
- Formula produces: a length
- Cut from: profiles (linear stock)

**Type 2 — Fill Shapes Area-Based (2D):**
- Used for: glass panes, solid panels, boards
- Unit: area (m² or mm²)
- Formula produces: width × height
- Cut from: sheets (2D stock)

**Type 3 — Fill Shapes Cut-Based:**
- Used for: mosquito nets, mesh
- Unit: area but cut like linear
- Formula produces: width × height but optimized differently

##### Formula Rules

Each line (component) in a style has a formula. Formulas reference:
- **W** — window/unit Width (user input at quote time)
- **H** — window/unit Height (user input at quote time)
- **X, Y, Z** — optional extra variables (user defines meaning per style, e.g. X = number of panes)
- **Other line IDs** — a formula can reference the computed length of another line

**Critical rule for `null` formula:**
- `null` formula means this line is a **frame component** — its length is determined by position
- Horizontal null lines → take Width (W)
- Vertical null lines → take Height (H)
- ONLY frame-level lines can have null formulas
- Non-frame lines MUST reference other lines or formulas

**Dependency chain:**
```
null lines (frames)
  ↓ referenced by
inner lines (sashes, rails)
  ↓ referenced by
deeper inner lines (sub-components)
  ↓ ... and so on
```

##### Endpoint Types

Determines how two adjacent cut pieces connect:

| Type | Name | Meaning | Effect on Length |
|------|------|---------|-----------------|
| MM | Mater-Mater | Frame-to-frame (both pieces are full) | Both take full dimension |
| MS | Mater-Square | Frame continues, inner piece fits between | Inner = outer - 2×frame_width |
| SS | Square-Square | Both inner pieces fit between frames | Both adjusted inward |

##### Variable Inputs

- **X, Y, Z** are defined per style in the style catalog
- Their meaning is style-specific (e.g., X = number of horizontal panes, Y = number of vertical panes)
- Become constants for all formula calculations for that unit
- Entered by user at quote/POS time

##### Offcut

- Offcut is added **AFTER** formula evaluation, not inside formulas
- Each material profile/sheet has an offcut setting (mm)
- Offcut is tracked per production run
- Offcut can be reused (offcut tracking = future inventory event)

##### Material Quantities

**Important:** Material quantities are determined ONLY after the cut list is generated.
- Do NOT sum formula totals directly
- The cut list optimization algorithm determines: how many pieces, in what order, with what waste
- Optimization profiles:
  - Linear (frames/profiles): 1D "fundi-first" logic — largest pieces first
  - Area (glass/panels): 2D sheet packing algorithm

##### Cut List Generation Flow

```
Style Definition
  + Window Measurements (W, H, X, Y, Z)
  ↓
Formula Evaluation (all lines calculated in dependency order)
  ↓
Piece List (component ID, qty, length or W×H)
  ↓
Optimization Algorithm (1D or 2D per material type)
  ↓
Cut List (which stick/sheet → which pieces → in what order)
  ↓
Material Quantities (sticks needed, sheets needed, waste %)
  ↓
Events: workshop.cutlist.generated.v1, then (on production) workshop.material.consumed.v1
```

##### Workshop Style Examples (from BOS_Workshop_Style_Examples.pdf)

**Example 1 — Casement Window (2 leaves):**
```
Variables: W (width), H (height), X (not used)
Frame lines (null formula):
  F-Top: null, horizontal → W
  F-Bottom: null, horizontal → W
  F-Left: null, vertical → H
  F-Right: null, vertical → H
  F-Center: W/2 (divider)

Sash lines (MS endpoint, fits between frame):
  S-Top-L: F-Center - frame_width (left sash top)
  S-Top-R: F-Center - frame_width (right sash top)
  ... etc.

Glass (2D fill):
  Glass-L: (F-Center - 2×frame - 2×glass_edge) × (H - 2×frame - 2×glass_edge)
  Glass-R: same formula
```

**Example 2 — Sliding Window (2 or more panels):**
```
Variables: W, H, X (number of panels)
Frame: null lines for perimeter
Track: W (full width, horizontal line, 2 required top+bottom)
Panel-Width: W/X - overlap (each panel width)
Panel-Height: H - 2×track_height - clearance
Glass per panel: (Panel-Width - 2×seal) × (Panel-Height - 2×seal)
```

**Example 3 — Fixed Window (no opening):**
```
Variables: W, H only
Frame only: null lines for all 4 sides
Glass: single pane (W - 2×frame - 2×glass_edge) × (H - 2×frame - 2×glass_edge)
No sash lines needed
```

**Example 4 — Door:**
```
Variables: W, H, X (number of panels/lights)
Frame: null perimeter
Panel rails: H/X - frame per section
Panel stiles: W - 2×frame
If glazed: glass per light = (W - 2×frame - 2×stile) × (H/X - 2×rail)
```

**Example 5 — Variable/Complex (multiple sashes, mullions):**
```
Variables: W, H, X (horizontal divisions), Y (vertical divisions)
Mullions horizontal: (X-1) pieces, formula: H - 2×frame (vertical mullion)
Mullions vertical: (Y-1) pieces, formula: W - 2×frame (horizontal mullion)
Pane width: W/X - frame_share
Pane height: H/Y - frame_share
Glass per pane: pane_width × pane_height
Total glass panes: X × Y
```

---

### ENGINE 8: PROMOTION ENGINE

**What it is:** Rule-driven discount and loyalty system. Customer-controlled via QR consent.

**What it is NOT:** Marketing campaign manager, CRM, coupon printer.

**Core Principle:** Promotions reduce price BEFORE tax. Customer must consent (QR scan). No invisible discounts.

**Event Types (5):**
- `promotion.rule.created.v1`
- `promotion.rule.activated.v1`
- `promotion.code.issued.v1`
- `promotion.redemption.recorded.v1`
- `promotion.rule.expired.v1`

**Key Rules:**
- Discount applied BEFORE tax calculation (price reduction, not tax exemption)
- Negative pricing prevented by design (floor = 0)
- Customer QR scan = consent to use promotion
- Invisible discounts NOT permitted (always visible on receipt)
- Multi-rule stacking: configurable (max one promotion, or stacking allowed)
- Promotions can be: business-wide or branch-specific
- Time-bound: start/end datetime in command payload (not `datetime.now()`)

**Scope:** Promotion rules = business OK. Application = branch where sale occurs.

---

### ENGINE 9: HR ENGINE

**What it is:** Workforce tracking — attendance, shifts, leave, and payroll reference figures.

**What it is NOT:** Statutory payroll, HR system of record, compliance filing system.

**Core Principle:** Biometric data is hashed and consent-gated. Payroll figures are reference-only.

**Event Types (5):**
- `hr.employee.registered.v1`
- `hr.shift.started.v1`
- `hr.shift.ended.v1`
- `hr.leave.requested.v1`
- `hr.leave.approved.v1`

**Missing (GAP-08):**
- Payroll computation events
- `hr.payroll.run.v1`
- `hr.payroll.journal.posted.v1` (links to accounting engine)
- Role→permission binding

**Key Rules:**
- Biometric data: stored as **hashed reference only** — never raw biometrics
- Consent required before biometric capture
- After employee exit + retention period: biometric reference deleted
- Payroll figures = management reference only (not statutory)
- Shift data feeds into payroll calculation but accounting journal is reference-only
- Leave approval follows configurable approval chain (same pattern as procurement)

**Scope:** Employee registry = business OK. Shift/attendance = branch where shift occurs.

---

## PART 4 — AI & DECISION SIMULATION

### AI Guardrails (Non-Negotiable Across ALL Engines)

AI components are **advisory only**. AI CANNOT:
- Commit state changes autonomously
- Sign contracts or approve purchases
- Borrow funds or authorize payments
- Dismiss staff or modify HR records
- Delete data or alter historical records
- Operate outside their tenant scope
- Take actions without explicit user consent for execution

AI CAN:
- Analyze events and provide recommendations
- Simulate decisions (show projected outcomes)
- Flag anomalies for human review
- Prepare draft commands for human approval
- Journal all advisory outputs

### Decision Simulation Modes

| Mode | Description | Consent Required |
|------|-------------|-----------------|
| Advisory | AI provides analysis, human decides and acts | No (reading only) |
| Assisted Execution | AI prepares command, human reviews and approves | Yes — before dispatch |
| Limited Automation | AI dispatches low-risk commands autonomously | Yes — explicit policy grant |

### Decision Journal

Every AI advisory output must be logged:
```
decision_id    UUID
tenant_id      business_id
engine         which engine the advice relates to
advice         structured recommendation payload
mode           advisory|assisted|limited_automation
outcome        ACCEPTED|REJECTED|PENDING (human review state)
actor          AI actor details
occurred_at    timestamp
```

### AI Scope

- Scoped to tenant (business_id) — never cross-tenant
- Read from projections/read models only — never from event store directly
- All commands go through the standard command pipeline
- Full audit trail of every AI interaction

---

## PART 5 — REPORTING & BI ENGINE

**Status:** Not yet built (GAP-05)

**What it is:** Event-driven KPI projection layer. Translates engine events into business metrics.

**What it is NOT:** Static report tables, data warehouse, BI visualization tool.

**Core Principle:** Reports are derived from events, not static tables. Metrics are versioned and reproducible.

**Key Concepts:**
- **Semantic Layer:** translates raw events into business metric events
  - `accounting.journal.posted.v1` → "Revenue" metric
  - `retail.sale.completed.v1` → "Daily sales" metric
- **Snapshot Reporting:** point-in-time snapshots generated by replaying events to a given timestamp
- **Versioned Metrics:** metric definitions have versions (so historical reports remain consistent)
- **Role-based Dashboards:** owner sees P&L, branch manager sees branch KPIs, cashier sees shift summary
- **Audit Explorer:** must scope queries strictly to tenant/branch

**Required Events:**
- `bi.kpi.computed.v1`
- `bi.snapshot.generated.v1`
- `bi.report.exported.v1`

**Scope:** Business-wide views + branch-filtered views both allowed.

---

## PART 6 — INTEGRATION ENGINE

**Status:** Not yet built (Phase 9)

**What it is:** Controlled gateway for external system communication.

**What it is NOT:** Direct database access, ETL pipeline, API proxy.

**Core Principle:** External systems NEVER write directly to BOS core data. All integration is event-driven and permission-based.

**Inbound (external → BOS):**
- External event → Integration adapter → validate → translate → Command to BOS command bus
- External system cannot bypass command validation

**Outbound (BOS → external):**
- BOS event → Integration subscriber → translate → push to external system
- Events emitted, never state snapshots

**Adapter Pattern:**
- Each external system has a dedicated adapter
- Adapters are stateless translators
- Failures logged, retried with backoff, never silently dropped

---

## PART 7 — DOCUMENT ENGINE

**Status:** Implemented (Phase 3)

**What it is:** Structured document builder producing hash-verified HTML and PDF outputs.

**Key Rules:**
- Templates are structured JSON (no raw HTML injection)
- Past documents are immutable
- Render must be reproducible (same event snapshot → same document)
- PDF + HTML derived from same snapshot
- Document hash stored in event for verification
- Numbering: configurable per-business or per-branch sequence

**Event Types:**
- `document.template.created.v1`
- `document.template.activated.v1`
- `document.issued.v1`
- `document.verified.v1`

---

## PART 8 — CORE PRIMITIVES

**Status:** Partially implemented (Phase 4)

Primitives = shared, engine-agnostic building blocks. Pure Python, immutable, deterministic, multi-tenant aware.

### Existing Primitives

| Primitive | File | Description |
|-----------|------|-------------|
| `ledger` | `core/primitives/ledger.py` | Double-entry accounting entries & balance computation |
| `item` | `core/primitives/item.py` | Catalog item / product / service definition |
| `inventory` | `core/primitives/inventory.py` | Stock movement abstraction (in/out/transfer/adjust) |
| `party` | `core/primitives/party.py` | Customer, vendor, staff party abstraction |
| `obligation` | `core/primitives/obligation.py` | Payment/delivery obligation lifecycle tracking |

### Missing Primitives (GAP-04)

| Primitive | File Needed | Purpose |
|-----------|-------------|---------|
| `actor` | `core/primitives/actor.py` | Reusable identity building block for all engines |
| `approval` | `core/primitives/approval.py` | Approval lifecycle (procurement, HR, workshop) |
| `workflow` | `core/primitives/workflow.py` | Generic state machine (CREATED→...→DONE) |
| `document` | `core/primitives/document.py` | Lightweight document reference primitive |

---

## PART 9 — GLOBAL ADMINISTRATION & GOVERNANCE

### Platform Governance Principles

- BOS is multi-tenant SaaS at platform level
- No country-specific code: `if country == "X"` is FORBIDDEN
- All regional differences = admin-configurable + policy-driven + data-defined
- Platform admin ≠ tenant admin ≠ branch manager (completely separate permission trees)

### Configuration vs Data vs Code

| Category | Examples | Where it lives |
|----------|---------|----------------|
| Configuration | Country VAT rules, compliance profiles, feature flags | Admin-configurable data |
| Operational Data | Events, commands, projections | Event store + read models |
| Code | Engines, validators, policy functions | Codebase |

**Never hardcode configuration in code.**

### Data Lifecycle

- Events: never deleted
- Financial data: immutable forever
- PII: masked after retention period
- Biometric references: deleted after employee exit + retention period
- Corrections: always new events (never modify old events)

### Permissions Model

- **Role** = responsibility (e.g., Branch Cashier, Procurement Manager)
- **Permission** = atomic action (e.g., `cash.cashin.create`, `inventory.stock.adjust`)
- **Scope** = data boundary (business | branch | project)
- Role → set of Permissions × Scope
- Permissions bind at command dispatch time

### Scaling: Golden Path Doctrine

- Scale by replicating identical hardened VMs (Golden Image)
- No containers in the canonical plan
- All nodes identical (no special nodes)
- Horizontal scaling via VM replication

---

## PART 10 — CURRENT KNOWN GAPS

Full gap list maintained in `DEVSTATE.md`. Summary:

| Gap | Severity | Description |
|-----|----------|-------------|
| GAP-01 | ⛔ CRITICAL | Feature flags missing from all 9 engines |
| GAP-02 | ⛔ CRITICAL | Workshop: no geometry, no cut list, no offcut |
| GAP-03 | ⚠️ HIGH | Cross-engine subscriptions all `pass` |
| GAP-04 | ⚠️ HIGH | Missing primitives: actor, approval, workflow, document |
| GAP-05 | ⚠️ HIGH | No Reporting/BI engine |
| GAP-06 | ⚠️ MEDIUM | Procurement: missing Requisition + Payment steps |
| GAP-07 | ⚠️ MEDIUM | Inventory: no FIFO/LIFO lot tracking |
| GAP-08 | ⚠️ MEDIUM | HR: no payroll computation, no accounting link |
| GAP-09 | ⚠️ MEDIUM | Restaurant: no kitchen workflow, no split billing |
| GAP-10 | ⚠️ LOW | scope-policy.md guards not enforced in engines |
| GAP-11 | ℹ️ LOW | Core stubs empty (audit, time, security, resilience, config, business) |
| GAP-12 | ℹ️ LOW | Test gaps (invariants, projections, security) |
| GAP-13 | ℹ️ INFO | Naming drift: structure.md says `core/rules/`, repo has `core/policy/` |

---

## PART 11 — TEST PATTERNS

### Test Double Pattern (Used in All Engine Tests)

```python
class StubEventTypeRegistry:
    def __init__(self): self._types = {}
    def register(self, name, factory): self._types[name] = factory
    def resolve(self, name): return self._types.get(name)

class StubEventFactory:
    def __init__(self, registry): self._registry = registry
    def create(self, event_type, payload, business_id, branch_id=None, actor_id=None):
        return {"event_type": event_type, "payload": payload, "business_id": business_id}

class StubPersistEvent:
    def __init__(self): self.events = []
    def __call__(self, event): self.events.append(event)

class StubCommandBus:
    def __init__(self): self.dispatched = []
    def dispatch(self, command): self.dispatched.append(command); return MagicMock(status="ACCEPTED")
```

### Required Test Commands

```bash
python -m pytest tests/engines/ -v                     # all engine tests (113)
python -m pytest tests/core/test_commands.py tests/core/test_policy.py tests/core/test_engine_registry.py -v
python -m pytest tests/ -v --ignore=tests/core/test_event_store_postgres_contract.py  # skip DB tests
```

### Current Test Coverage

| Engine | Tests | Status |
|--------|-------|--------|
| accounting | 53 | ✅ pass |
| inventory | part of phase5 | ✅ pass |
| cash | part of phase5 | ✅ pass |
| procurement | 41 | ✅ pass |
| retail | part of phase6 | ✅ pass |
| restaurant | 19 | ✅ pass |
| workshop | part of phase7 | ✅ pass |
| promotion | part of phase7 | ✅ pass |
| hr | part of phase7 | ✅ pass |
| **Total** | **113** | **all pass** |

### Missing Tests (GAP-12)

- `tests/invariants/` — Empty. Need: boundary, determinism, replay, tenant isolation tests
- `tests/core/test_admin_data_layer.py` — Empty stub
- `tests/security/` — Empty (acceptable until Phase 8)
- `tests/projections/` — Empty (acceptable until Phase 10)

---

## PART 12 — GIT & SESSION WORKFLOW

### Branch

```
claude/explain-codebase-mlsfr9vu6lpytugq-0E7ZN
```

Push ONLY to this branch. Never to `main` without explicit merge instruction.

### Session Start Checklist

```bash
git status
git log --oneline -5
# Read DEVSTATE.md
# Read BOS_MASTER_REFERENCE.md (this file)
```

### After Any Change

```bash
python -m pytest tests/engines/ -v
python -m pytest tests/core/test_commands.py tests/core/test_policy.py tests/core/test_engine_registry.py -v
git add <specific files>
git commit -m "codex phase X — Short description"
git push -u origin claude/explain-codebase-mlsfr9vu6lpytugq-0E7ZN
```

### Commit Message Format

```
codex phase X — Short clear description
```

Examples:
- `codex phase 7 — Restaurant, Workshop, Promotion, HR Engines`
- `codex — DEVSTATE.md developer memory file`
- `codex gap-01 — Feature flags wired to all 9 engines`

---

## PART 13 — INVARIANTS — NEVER BREAK

1. **Hash-chain integrity** — never touch `core/event_store/hashing/`
2. **Replay determinism** — no `datetime.now()` inside engine logic, ever
3. **Engine isolation** — no direct cross-engine calls
4. **Multi-tenant safety** — every event has `business_id`
5. **Additive only** — no removing events, commands, or contracts
6. **`policy_name` required** — every `RejectionReason()` call must include it
7. **AI advisory only** — AI never commits state, never autonomous writes
8. **No silent merges** — offline conflicts require human review
9. **No invisible discounts** — all promotions visible on receipt
10. **No country code in code** — all regional rules via config/policy

---

*"BOS is not an ERP. It is a deterministic, legally defensible business kernel."*
*"BOS is global by architecture, local by law, and neutral by design."*
*"If an action cannot be explained as an event, corrected safely, and audited clearly — it does not belong in BOS."*
