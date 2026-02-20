# BOS — Developer State File
> Maintained by: Codex (Claude AI Engineer)
> Last updated: Phase 7 complete
> Read this file at the start of every session before touching any code.

---

## WHO I AM IN THIS PROJECT

I am the implementing engineer of BOS (Business Operating System).
I work from the `Roadmap`, `AGENTS.md`, `structure.md`, and `scope-policy.md` as law.
I do not invent architecture — I execute the doctrine faithfully.

Branch: `claude/explain-codebase-mlsfr9vu6lpytugq-0E7ZN`
Push to this branch. Never to `main` unless explicitly merged.

---

## CURRENT POSITION — PHASE MAP

```
Phase 0  ✅ Core Kernel         (event store, hash-chain, command bus, engine registry, replay)
Phase 1  ✅ Governance           (policy engine, compliance, admin layer)
Phase 2  ✅ HTTP API             (contracts, handlers, auth middleware, Django adapter)
Phase 3  ✅ Document Engine      (builder, HTML+PDF renderer, numbering, verification, hash)
Phase 4  ⚠️ Business Primitives  (ledger, item, inventory, party, obligation — 4 missing, see GAP-04)
Phase 5  ⚠️ Enterprise Engines   (accounting, cash, inventory, procurement — all wired but subscriptions pass, see GAP-03)
Phase 6  ⚠️ Vertical Modules     (retail ✅, restaurant ⚠️, workshop ⚠️ — critical gaps, see GAP-02 & GAP-09)
Phase 7  ⏳ AI & Decision Intel  (promotion ✅ done, HR ✅ done — but AI advisory system = empty stubs)
Phase 8  ❌ Security & Isolation (not started)
Phase 9  ❌ Integration Layer    (not started)
Phase 10 ❌ Performance & Scale  (not started)
Phase 11 ❌ Enterprise Admin     (not started)
Phase 12 ❌ SaaS Productization  (not started)
Phase 13 ❌ Documentation        (not started)
```

---

## ENGINES IMPLEMENTED (9/9)

All 9 engines have full structure: `events.py`, `commands/`, `services/`, `policies/`, `subscriptions.py`

| Engine | Phase | Event Types | Tests | Feature Flag | Subscription Wired |
|--------|-------|-------------|-------|--------------|-------------------|
| accounting | 5 | 5 | ✅ 53 tests (phase5) | ❌ MISSING | ❌ pass stubs |
| inventory | 5 | 6 | ✅ | ❌ MISSING | ❌ pass stubs |
| cash | 5 | 5 | ✅ | ❌ MISSING | ❌ pass stubs |
| procurement | 6 | 5 | ✅ 41 tests (phase6) | ❌ MISSING | ❌ pass stubs |
| retail | 6 | 7 | ✅ | ❌ MISSING | N/A (emitter only) |
| restaurant | 7 | 6 | ✅ 19 tests (phase7) | ❌ MISSING | N/A |
| workshop | 7 | 5 | ✅ | ❌ MISSING | N/A |
| promotion | 7 | 5 | ✅ | ❌ MISSING | N/A |
| hr | 7 | 5 | ✅ | ❌ MISSING | N/A |
| **TOTAL** | | **49** | **113** | **0/9** | **0/4** |

Test commands (always run before commit):
```bash
python -m pytest tests/engines/ -v          # 113 engine tests
python -m pytest tests/core/test_commands.py tests/core/test_policy.py tests/core/test_engine_registry.py -v
python -m pytest tests/ -v --ignore=tests/core/test_event_store_postgres_contract.py  # skip DB tests
```

---

## KNOWN GAPS — PRIORITIZED BACKLOG

### GAP-01 ⛔ CRITICAL — Feature Flags Not Wrapping Engines
**Doctrine:** AGENTS.md Rule 14 — "All new major engines must be wrapped behind feature flags. Default to OFF unless activated."
**Status:** `core/feature_flags/` is fully implemented. Zero engines check it.
**Fix:** Each engine's `services/__init__.py` must check `feature_flags.is_enabled("<engine>_engine", business_id)` at command dispatch time.
**Files to touch:** `engines/*/services/__init__.py` (all 9), `core/engines/contracts.py` (add flag_key to EngineContract)
**Priority:** MUST FIX before Phase 8.

---

### GAP-02 ⛔ CRITICAL — Workshop Engine Missing Parametric Geometry
**Doctrine:** AGENTS.md Rule 12 — "Parametric geometry only. No randomness. Same input → same cutting list."
**Roadmap:** "Style-driven costing, Cutting optimization engine (line + area), Offcut reuse logic, Material consumption events"
**Status:** Workshop only tracks job lifecycle. No geometry, no cut list, no offcut.
**Missing commands:** `GenerateCutListRequest`, `MaterialConsumeRequest`, `OffcutRecordRequest`
**Missing events:** `workshop.cutlist.generated.v1`, `workshop.material.consumed.v1`, `workshop.offcut.recorded.v1`
**Fix:** Extend workshop engine with parametric geometry layer.
**Priority:** MUST FIX — core doctrine violation.

---

### GAP-03 ⚠️ HIGH — Cross-Engine Subscriptions All `pass`
**Doctrine:** AGENTS.md Rule 4 — "Engines communicate ONLY via events."
**Status:** Subscription handlers exist in code but all contain `pass`. Nothing actually reacts to events.
**Broken flows:**
```
procurement.order.received  → inventory.handle_procurement_received  (pass)
retail.sale.completed       → cash.handle_retail_sale               (pass)
inventory.stock.received.v1 → accounting.handle_stock_received      (pass)
cash.payment.recorded.v1    → accounting.handle_payment_recorded    (pass)
```
**Fix:** Wire the event dispatcher to call SubscriptionHandlers, implement each handler body.
**Priority:** HIGH — engines are islands, no inter-engine intelligence.

---

### GAP-04 ⚠️ HIGH — Phase 4 Primitives Incomplete
**Roadmap:** Actor, Document, Approval, Workflow primitives.
**Status:** `core/primitives/` has: ledger, item, inventory, party, obligation.
**Missing:**
- `core/primitives/actor.py` — Actor primitive (reusable identity building block for engines)
- `core/primitives/approval.py` — Approval lifecycle (used by procurement, HR, workshop)
- `core/primitives/workflow.py` — Generic state machine primitive (CREATED→...→DONE)
- `core/primitives/document.py` — Lightweight document reference primitive
**Fix:** Add missing primitives. Refactor engines to use `workflow.py` state machine pattern (DRY).
**Priority:** HIGH — will reduce duplication across all lifecycle engines.

---

### GAP-05 ⚠️ HIGH — No Reporting/BI Engine
**Roadmap 5.5:** "Event-driven projections, Snapshot reporting, KPI calculators"
**Status:** `engines/` has no reporting engine. `projections/bi/__init__.py` is empty.
**Missing:** `engines/reporting/` or `engines/bi/` with event-driven KPI projection.
**Priority:** HIGH — mentioned in Phase 5 which is supposedly done.

---

### GAP-06 ⚠️ MEDIUM — Procurement Missing Requisition + Payment
**Roadmap 5.3:** `Requisition → PO → GRN → Invoice → Payment`
**Status:** We have: `Create → Approve → Receive → InvoiceMatch`. Missing start (Requisition) and end (Payment).
**Missing commands:** `RequisitionCreateRequest`, `RequisitionApproveRequest`, `PaymentReleaseRequest`
**Missing events:** `procurement.requisition.created.v1`, `procurement.payment.released.v1`
**Priority:** MEDIUM.

---

### GAP-07 ⚠️ MEDIUM — Inventory Missing FIFO/LIFO Strategy
**Roadmap 5.2:** "FIFO/LIFO strategy plugin"
**Status:** `InventoryProjectionStore` tracks `{(item_id, location_id): qty}` only. No lot tracking, no valuation.
**Fix:** Add lot-based stock tracking with FIFO/LIFO cost computation.
**Priority:** MEDIUM.

---

### GAP-08 ⚠️ MEDIUM — HR Missing Payroll + Ledger Integration
**Roadmap 5.6:** "Payroll ledger integration, Permission binding"
**Status:** HR has shifts and leave. No payroll computation, no accounting journal link, no role→permission binding.
**Fix:** Add `PayrollRunRequest`, `PayrollJournalPostRequest`, link shift data to ledger primitive.
**Priority:** MEDIUM.

---

### GAP-09 ⚠️ MEDIUM — Restaurant Missing Kitchen Workflow + Split Billing
**Roadmap 6.2:** "Kitchen workflow engine, Split billing, QR per table, Self-service ordering"
**Status:** Restaurant has table open/order/bill. No kitchen tickets, no bill splitting.
**Missing events:** `restaurant.kitchen.ticket.sent.v1`, `restaurant.bill.split.v1`
**Priority:** MEDIUM.

---

### GAP-10 ⚠️ LOW — scope-policy.md Scope Guards Not Enforced in Engines
**Doctrine:** `scope-policy.md` — many operations require `branch_id` (e.g. cash drawer ops, inventory moves, POS sales).
**Status:** Engine commands accept `branch_id=None`. No hard rejection for "branch required" ops.
**Fix:** Add scope guard policies per engine matching the scope-policy matrix.
**Reference:** `scope-policy.md` sections 7-12.
**Priority:** LOW (structure exists via policy layer, but not enforced at engine level).

---

### GAP-11 ℹ️ LOW — Core Stubs Empty
Modules in `core/` defined in `structure.md` that are completely empty:
- `core/audit/` — Evidence, consent, access logs (Phase 0 said "audit trail" complete, but module is empty)
- `core/time/` — Explicit clock (important for determinism rules)
- `core/business/` — Business lifecycle management
- `core/resilience/` — NORMAL/DEGRADED/READ_ONLY modes
- `core/config/` — Country rules, tax rules, config flags

---

### GAP-12 ℹ️ LOW — Test Gaps
- `tests/invariants/` — Empty. AGENTS.md Rule 8 requires invariant tests (boundary, determinism, replay, tenant isolation).
- `tests/core/test_admin_data_layer.py` — 0 lines. Stub never filled.
- `tests/security/` — Empty (acceptable until Phase 8).
- `tests/projections/` — Empty (acceptable until Phase 10).

---

### GAP-13 ℹ️ INFO — Naming Mismatch: structure.md vs Repo
`structure.md` says `core/rules/` — repo has `core/policy/`. Not a bug, just docs drift.
`structure.md` says `docs/doctrine/` subdir — actual `docs/` is flat.

---

## EXECUTION ORDER (Next Sessions)

```
IMMEDIATE (doctrine compliance):
  1. GAP-01 — Feature flags in all 9 engines
  2. GAP-02 — Workshop parametric geometry + cutting engine
  3. GAP-03 — Wire cross-engine subscriptions

NEXT (roadmap completeness):
  4. GAP-04 — Add missing primitives (actor, approval, workflow, document)
  5. GAP-05 — Build Reporting/BI engine (engines/reporting/)
  6. GAP-06 — Procurement: add Requisition + Payment steps

THEN:
  7. GAP-07 — Inventory FIFO/LIFO lot tracking
  8. GAP-08 — HR payroll + ledger integration
  9. GAP-09 — Restaurant kitchen workflow + split billing

THEN PHASES:
  Phase 8 — Security & Isolation
  Phase 9 — Integration Layer
  Phase 10 — Performance (projections, read models)
```

---

## CANONICAL ENGINE PATTERN (for all new engines)

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

Event naming: `engine.domain.action.vN` (e.g. `retail.sale.completed.v1`)
Command naming: `engine.domain.action.request` (e.g. `retail.sale.complete.request`)
All commands: `source_engine = "<engine>"`, `@dataclass(frozen=True)`
All RejectionReason: MUST include `policy_name="function_name"` — will fail tests without it.

---

## TEST DOUBLE PATTERN (used in all engine tests)

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

---

## SCOPE POLICY QUICK REF (from scope-policy.md)

Operations that REQUIRE `branch_id` (cannot be business-scope):
- Cash: drawer create, CashIn/CashOut, reconciliation, adjustments
- Inventory: stock movements, transfers
- Procurement: Goods Receipt
- Retail: POS sale, refund
- Restaurant: table/order/kitchen/split billing
- Workshop: cutting optimization, material consumption, offcut tracking

Operations OK at business-scope (branch optional):
- Accounting: journal entries, trial balance, corrections
- Procurement: supplier registry, requisition, invoice matching
- Documents: template create/activate, verification
- Compliance: profile assign/validate

---

## GIT WORKFLOW

```bash
# Start session:
git status
git log --oneline -5

# After changes:
python -m pytest tests/engines/ -v
python -m pytest tests/core/test_commands.py tests/core/test_policy.py tests/core/test_engine_registry.py -v

# Commit format:
git commit -m "codex phase X — Short description"

# Push:
git push -u origin claude/explain-codebase-mlsfr9vu6lpytugq-0E7ZN
```

---

## INVARIANTS — NEVER BREAK

1. Hash-chain integrity (do not touch `core/event_store/hashing/`)
2. Replay determinism (no `datetime.now()` inside engine logic)
3. Engine isolation (no direct cross-engine calls)
4. Multi-tenant safety (every event has `business_id`)
5. Additive only (no removing events, commands, or contracts)
6. `policy_name` required in every `RejectionReason()` call

---
*"BOS is not an ERP. It is a deterministic, legally defensible business kernel."*
