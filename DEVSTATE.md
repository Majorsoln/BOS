# BOS — Developer State File
> Maintained by: Codex (Claude AI Engineer)
> Last updated: Phase 8 Security & Isolation built — tenant isolation, rate limiting, anomaly detection, guard pipeline — 903+ tests passing
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
Phase 4  ✅ Business Primitives  (ledger, item, inventory, party, obligation, actor, approval, workflow, document)
Phase 5  ✅ Enterprise Engines   (accounting, cash, inventory, procurement — subscriptions wired, reporting engine built)
Phase 6  ✅ Vertical Modules     (retail ✅, restaurant ✅ kitchen+split, workshop ✅ parametric geometry+cutlist)
Phase 7  ✅ AI & Decision Intel  (promotion ✅, HR ✅ payroll+ledger, AI advisory system ✅ guardrails+journal+advisors+simulation)
Phase 8  ✅ Security & Isolation (tenant isolation, rate limiting, anomaly detection, guard pipeline)
Phase 9  ❌ Integration Layer    (not started)
Phase 10 ❌ Performance & Scale  (not started)
Phase 11 ❌ Enterprise Admin     (not started)
Phase 12 ❌ SaaS Productization  (not started)
Phase 13 ❌ Documentation        (not started)
```

---

## ENGINES IMPLEMENTED (10/10)

All 10 engines have full structure: `events.py`, `commands/`, `services/`, `policies/`, `subscriptions.py`

| Engine | Phase | Event Types | Tests | Feature Flag | Subscription Wired | Scope Guard |
|--------|-------|-------------|-------|--------------|-------------------|-------------|
| accounting | 5 | 5 | ✅ | ✅ | ✅ | ✅ |
| inventory | 5 | 6 | ✅ | ✅ | ✅ | ✅ |
| cash | 5 | 5 | ✅ | ✅ | ✅ | ✅ |
| procurement | 6 | 8 | ✅ | ✅ | N/A | ✅ |
| retail | 6 | 7 | ✅ | ✅ | N/A | ✅ |
| restaurant | 7 | 8 | ✅ | ✅ | N/A | ✅ |
| workshop | 7 | 8 | ✅ | ✅ | N/A | ✅ |
| promotion | 7 | 5 | ✅ | ✅ | N/A | ✅ |
| hr | 7 | 5 | ✅ | ✅ | N/A | ✅ |
| reporting | 5.5 | 3 | ✅ | ✅ | ✅ subscribes to 8 events | ✅ |
| **TOTAL** | | **60** | **847** | **10/10** | **4/4 + reporting** | **10/10** |

Test commands (always run before commit):
```bash
python -m pytest tests/engines/ -v                    # engine tests
python -m pytest tests/core/ tests/ai/ -v             # core + AI tests
python -m pytest tests/ -v --ignore=tests/core/test_event_store_pg.py --ignore=tests/core/test_event_store_postgres_contract.py --ignore=tests/core/test_http_api_auth_db_integration.py --ignore=tests/core/test_http_api_identity_admin.py --ignore=tests/core/test_identity_store_bootstrap.py --ignore=tests/core/test_permissions_db_provider.py  # skip DB tests
```

---

## CORE INFRASTRUCTURE (GAP-11 — All Implemented)

| Module | Status | Key Components |
|--------|--------|---------------|
| `core/time/` | ✅ | Clock protocol, FixedClock, SystemClock, TimeWindow, is_expired |
| `core/audit/` | ✅ | AuditEntry, ConsentRecord, grant/revoke consent (append-only) |
| `core/business/` | ✅ | Business, Branch, BusinessState, lifecycle validation policies |
| `core/config/` | ✅ | TaxRule, ComplianceRule, InMemoryConfigStore (no hardcoded codes) |
| `core/resilience/` | ✅ | ResilienceMode (NORMAL/DEGRADED/READ_ONLY), SystemHealth |
| `core/security/` | ✅ | TenantScope, RateLimiter (sliding window), AnomalyDetector, SecurityGuardPipeline |

---

## AI ADVISORY SYSTEM (Phase 7 — Fully Implemented)

| Module | Status | Key Components |
|--------|--------|---------------|
| `ai/guardrails.py` | ✅ | AIActionType, GuardrailResult, check_ai_guardrail, FORBIDDEN_OPERATIONS |
| `ai/journal/` | ✅ | DecisionEntry, DecisionMode, DecisionOutcome, DecisionJournal (append-only) |
| `ai/advisors/` | ✅ | Advisor base, InventoryAdvisor, CashAdvisor, ProcurementAdvisor |
| `ai/decision_simulation/` | ✅ | SimulationScenario, SimulationResult, Simulator, price/reorder simulations |

AI Guardrail Rules Enforced:
- AI is advisory only — never commits state autonomously
- Tenant-scoped — cross-tenant access denied
- 9 forbidden operations (approve_purchase, sign_contract, borrow_funds, etc.)
- Command preparation requires human approval
- Autonomous execution requires explicit policy grant
- Full audit trail via Decision Journal

---

## ALL GAPS — RESOLVED

| Gap | Severity | Description | Status |
|-----|----------|-------------|--------|
| GAP-01 | ⛔ CRITICAL | Feature flags wrapping all 10 engines | ✅ Complete |
| GAP-02 | ⛔ CRITICAL | Workshop parametric geometry + cut list | ✅ Complete |
| GAP-03 | ⚠️ HIGH | Cross-engine subscriptions wired | ✅ Complete |
| GAP-04 | ⚠️ HIGH | Missing primitives (actor, approval, workflow, document) | ✅ Complete |
| GAP-05 | ⚠️ HIGH | Reporting/BI engine with KPI projections | ✅ Complete |
| GAP-06 | ⚠️ MEDIUM | Procurement: Requisition + Payment steps | ✅ Complete |
| GAP-07 | ⚠️ MEDIUM | Inventory FIFO/LIFO lot tracking | ✅ Complete |
| GAP-08 | ⚠️ MEDIUM | HR payroll + accounting ledger integration | ✅ Complete |
| GAP-09 | ⚠️ MEDIUM | Restaurant kitchen workflow + split billing | ✅ Complete |
| GAP-10 | ⚠️ LOW | Scope guards enforcement in all 10 engines | ✅ Complete |
| GAP-11 | ℹ️ LOW | Core stubs (time, audit, business, config, resilience, security) | ✅ Complete |
| GAP-12 | ℹ️ LOW | Invariant tests (11 architectural invariants) | ✅ Complete |
| GAP-13 | ℹ️ INFO | Naming drift — structure.md updated to match repo | ✅ Complete |

---

## EXECUTION ORDER (Next Sessions)

```
COMPLETED ✅:
  GAP-01 through GAP-13 — All resolved
  Phase 7 — AI advisory system fully built

COMPLETED ✅:
  Phase 8 — Security & Isolation
  - Tenant isolation: TenantScope, check_tenant_isolation, build_tenant_scope
  - Rate limiting: sliding window per-actor per-business, configurable tiers (HUMAN/SYSTEM/DEVICE/AI)
  - Anomaly detection: high velocity, rapid branch switching, repeated rejections
  - Security guard pipeline: orchestrates all checks, fail-safe on errors
  - 56 security tests passing

NEXT:
  Phase 9  — Integration Layer (external systems gateway)
  Phase 10 — Performance & Scale (caching, read models, projections)
  Phase 11 — Enterprise Admin (admin dashboard, config management)
  Phase 12 — SaaS Productization (multi-tenant billing, onboarding)
  Phase 13 — Documentation (API docs, developer guide)
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
python -m pytest tests/ -v --ignore=tests/core/test_event_store_postgres_contract.py  # skip DB tests

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
7. AI is advisory only — never commits state autonomously
8. All core models are frozen (immutable dataclasses)
9. Audit entries are append-only (no deletion)
10. Scope guards enforced as first statement in every engine's `_execute_command()`

---

## MASTER REFERENCE

Full BOS specification synthesized from all 18 PDFs:
→ **`BOS_MASTER_REFERENCE.md`** (root of repo)

Read this at the start of any session to understand:
- BOS identity and doctrine
- All engine specifications (including Workshop formula engine in full detail)
- AI guardrails and Decision Journal schema
- Scope policy matrix
- Phase map and gaps

---
*"BOS is not an ERP. It is a deterministic, legally defensible business kernel."*
