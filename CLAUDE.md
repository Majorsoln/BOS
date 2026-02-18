# CLAUDE.md — BOS (Business Operating System)

## PROJECT IDENTITY

BOS is an enterprise-grade, event-sourced Business Operating System built on Django.
Framework: Django 6.x | Python 3.12+ | Database: SQLite (dev), PostgreSQL (prod)
Architecture: Event-Sourced, Append-Only, Engine-Isolated
Phases: 0–13 | Engines: 9 | Architecture Freeze: v1.0.1

## YOUR ROLE

You are a **Junior Engineer with speed** working on BOS.
- You have **NO architectural authority**
- You have **NO security authority**
- You have **NO permission to change semantics**
- You follow BOS Master Doctrine, Implementation Guide, Technical Appendix, and AI Coding Ruleset
- If a task violates these rules: **STOP**, explain why, ask for clarification
- Never assume. Never simplify BOS rules. Never optimize away safety.

---

## FINAL EXECUTION DOCTRINE (NON-NEGOTIABLE)

> "If an action cannot be explained as an event, corrected safely, and audited clearly — it does not belong in BOS."

- BOS must be built from truth → operations → insight → intelligence → scale
- No phase should be skipped, merged, or rushed
- No breaking changes. Additive only.

---

## PROJECT STRUCTURE

```
bos/
├── manage.py                         # Django entry point (DJANGO_SETTINGS_MODULE=config.settings)
├── config/                           # Django infrastructure
│   ├── settings.py                   # INSTALLED_APPS, DB, middleware
│   ├── urls.py                       # Empty (no interfaces yet)
│   ├── wsgi.py / asgi.py
│
├── core/                             # 🔐 SYSTEM LAW & TRUTH
│   ├── event_store/                  # ✅ COMPLETE — Canonical events (immutable truth)
│   │   ├── models.py                 # Event model: 17 frozen fields
│   │   ├── validators/               # ✅ event_validator, errors, registry, context
│   │   ├── idempotency/              # ✅ guard, errors
│   │   ├── hashing/                  # ✅ hasher, verifier, errors
│   │   ├── persistence/              # ⚠️ service.py done, errors.py + repository.py + __init__.py MISSING
│   │   └── migrations/               # ✅ 0001_initial.py
│   │
│   ├── events/                       # ✅ COMPLETE — Event Bus (dispatcher + registry)
│   │   ├── dispatcher.py             # Routes events to subscribers
│   │   ├── registry.py               # SubscriberRegistry (thread-safe)
│   │   ├── errors.py                 # Bus error types
│   │   └── service.py                # ⚠️ DUPLICATE — should be deleted
│   │
│   ├── bootstrap/                    # ✅ COMPLETE — System self-check on startup
│   │   ├── apps.py                   # Runs self_check via ready()
│   │   ├── self_check.py             # Orchestrates 5 invariant checks
│   │   ├── invariants.py             # 5 checks: table, guards, hash, registry, persistence
│   │   └── errors.py                 # SystemBootstrapError
│   │
│   ├── replay/                       # ✅ COMPLETE — Replay engine
│   │   ├── event_replayer.py         # replay_events() — core replay
│   │   ├── projection_rebuilder.py   # rebuild_projection() + ProjectionProtocol
│   │   ├── checkpoints.py            # ReplayCheckpoint model + save/load/clear
│   │   ├── context.py                # ReplayContext + is_replay_active()
│   │   ├── errors.py                 # Replay error types
│   │   ├── models.py                 # Re-exports for Django discovery
│   │   ├── apps.py                   # ReplayConfig
│   │   ├── settings.py               # ⚠️ WRONG FILE — delete this
│   │   └── migrations/               # ✅ 0001_initial.py
│   │
│   ├── context/                      # 🔲 EMPTY — BusinessContext implementation pending
│   ├── commands/                     # 🔲 EMPTY — Command framework pending
│   ├── engines/                      # 🔲 EMPTY — Engine registry pending
│   ├── rules/                        # 🔲 EMPTY — Policy engine pending
│   ├── config/                       # 🔲 EMPTY — Feature flags, country config pending
│   ├── security/                     # 🔲 EMPTY — Permissions pending
│   ├── business/                     # 🔲 EMPTY — Business lifecycle pending
│   ├── audit/                        # 🔲 EMPTY
│   ├── resilience/                   # 🔲 EMPTY
│   └── time/                         # 🔲 EMPTY
│
├── engines/                          # 🔲 ALL EMPTY — 9 engines scaffolded
│   ├── retail/                       # commands/, services/, policies/, events.py, subscriptions.py
│   ├── restaurant/
│   ├── workshop/
│   ├── inventory/
│   ├── cash/
│   ├── accounting/
│   ├── procurement/
│   ├── promotion/
│   └── hr/
│
├── projections/                      # 🔲 ALL EMPTY — 7 projection dirs
├── integration/                      # 🔲 ALL EMPTY
├── ai/                               # 🔲 ALL EMPTY
├── interfaces/                       # 🔲 ALL EMPTY
└── tests/                            # 🔲 ALL EMPTY
```

---

## KNOWN ISSUES (FIX BEFORE NEW WORK)

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | **HIGH** | `config/settings.py` | `INSTALLED_APPS` missing `'core.replay'` — add before `'core.bootstrap'` |
| 2 | **HIGH** | `core/event_store/persistence/errors.py` | MISSING — needs `PersistenceRejectionCode` + `PersistenceViolatedRule` |
| 3 | **HIGH** | `core/event_store/persistence/repository.py` | MISSING — needs `save_event()` function |
| 4 | **HIGH** | `core/event_store/persistence/__init__.py` | MISSING — needs public API exports |
| 5 | **MED** | `core/events/service.py` | DUPLICATE of `persistence/service.py` — **DELETE** |
| 6 | **MED** | `core/replay/settings.py` | Wrong copy of `config/settings.py` — **DELETE** |

---

## CORE ARCHITECTURE RULES

### Event-First, Append-Only
- ALL truth is expressed as immutable events
- No deletes, no overwrites, no updates after persistence
- Corrections are NEW events with `correction_of` set
- If you cannot express it as an event → it does not belong in BOS

### ONE Lawful Write Path
Every event MUST pass through `persist_event()` in this exact order:
1. **Validate** event structure (schema, actor, context, type, status, correction)
2. **Check idempotency** (app-level query)
3. **Verify hash-chain** (chain continuity + hash computation)
4. **Atomic DB save** (inside `transaction.atomic()` with re-checks)
5. **Dispatch** to subscribers (AFTER commit only, via `on_commit`)
6. **Return** deterministic result (accepted or rejected)

If ANY step fails → deterministic rejection. No partial state. No silent retry.

### Engine Isolation
- Each engine writes ONLY its own events
- Cross-engine communication is read-only (via events or queries)
- BI and AI NEVER write operational data
- Self-subscription blocked unless explicitly allowed

---

## CANONICAL EVENT MODEL (17 Frozen Fields)

```python
# core/event_store/models.py — DO NOT MODIFY SCHEMA
event_id            UUID        PK, default=uuid4, idempotency key
event_type          CharField   engine.domain.action format (from registry)
event_version       PositiveSmallIntegerField
business_id         UUID        Tenant boundary (always required)
branch_id           UUID        Nullable (business-wide events)
source_engine       CharField   Engine that emitted this event
actor_type          CharField   HUMAN | SYSTEM | DEVICE | AI
actor_id            CharField   Actor identifier
correlation_id      UUID        Story/journey grouping (REQUIRED)
causation_id        UUID        Direct cause event_id (NULLABLE)
payload             JSONField   Versioned payload
reference           JSONField   Optional external references
created_at          DateTimeField  Source timestamp
received_at         DateTimeField  auto_now_add (Event Store timestamp)
status              CharField   FINAL | PROVISIONAL | REVIEW_REQUIRED
correction_of       UUID        Nullable (references corrected event_id)
previous_event_hash CharField   SHA-256 of previous event (or "GENESIS")
event_hash          CharField   SHA-256 of this event
```

**Immutability guards enforced in model:**
- `save()` blocks updates (only INSERT allowed)
- `delete()` raises PermissionError always

---

## KEY CONSTANTS & PATTERNS

### Hash-Chain
```python
GENESIS_HASH = "GENESIS"  # First event per business uses this
# Formula: event_hash = SHA256(canonical_json(payload) + previous_event_hash)
# canonical_json: sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str
```

### Two Registries (NEVER cross-call)
1. **EventTypeRegistry** (`core/event_store/validators/registry.py`) — persistence gate
   - Controls which event types CAN be persisted
   - Starts empty, engines register at bootstrap
   - Format: `engine.domain.action`
2. **SubscriberRegistry** (`core/events/registry.py`) — routing table
   - Controls which handlers LISTEN to dispatched events
   - Thread-safe, in-memory only

### Event Status Enum
```python
FINAL            # Confirmed, immutable, trusted
PROVISIONAL      # Created offline or pending sync
REVIEW_REQUIRED  # Needs human review
```

### Actor Types
```python
HUMAN | SYSTEM | DEVICE | AI
# AI is advisory only — flagged with advisory_actor=True in ValidationResult
# AI cannot execute operations
```

### Validation Result
```python
ValidationResult(accepted=True/False, rejection=Rejection|None, advisory_actor=bool)
Rejection(code=str, message=str, violated_rule=str)
```

---

## DJANGO CONFIGURATION

```python
# config/settings.py
DJANGO_SETTINGS_MODULE = "config.settings"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "core.event_store",    # label: event_store
    "core.replay",         # label: replay  ← MUST BE ADDED (currently missing!)
    "core.bootstrap",      # label: bootstrap — MUST be last (runs self-check)
]
ROOT_URLCONF = "config.urls"
DB: SQLite (dev), PostgreSQL (prod)
```

### Bootstrap Behavior
- `core.bootstrap` app runs `run_bootstrap_checks()` via `AppConfig.ready()`
- **Skips during**: migrate, makemigrations, showmigrations, test, shell, dbshell, etc.
- 5 invariant checks (if any fails → `SystemBootstrapError` → system refuses to start):
  1. Event Store table exists
  2. Immutability guards active (save/delete blocked)
  3. Hash-chain structural integrity
  4. EventTypeRegistry importable and instantiable
  5. `persist_event` importable and callable

---

## REPLAY ENGINE

### Purpose
Event Store = truth archive. Replay Engine = time machine. Time machine must NEVER change history.

### Key Rules
- READ events only — never write to Event Store during replay
- `is_replay_active()` → `persist_event()` raises `ReplayIsolationError`
- Deterministic order: `received_at ASC, event_id ASC`
- Composite cursor for checkpoint resume (no same-timestamp skipping)
- Support: full, business-scoped, time-scoped, checkpoint resume, dry run

### Key Functions
```python
from core.replay.event_replayer import replay_events
from core.replay.projection_rebuilder import rebuild_projection
from core.replay.context import ReplayContext, is_replay_active
```

---

## 9 BUSINESS ENGINES (ALL PENDING)

Each engine follows identical structure:
```
engines/{name}/
├── __init__.py
├── commands/          # Intent (CreateX, UpdateY)
├── services/          # Business logic
├── policies/          # Rules, eligibility
├── events.py          # {engine}.* event declarations
└── subscriptions.py   # Reacts to other engines (read-only)
```

### Engine Summaries

| Engine | Domain | Key Concept |
|--------|--------|-------------|
| **retail** | POS, baskets, pricing | Cash-flow engine, basket-based POS, multi-price layers |
| **restaurant** | Orders, kitchen, tables | Order-centric, lifecycle per item, kitchen display |
| **workshop** | Windows, doors, panels | Style-driven production, formula engine, cutting optimization |
| **inventory** | Stock movements | Event-based, movement-only (no direct mutation), location-aware |
| **cash** | Cash control, shifts | Every unit traceable, session/shift control, drawer/safe locations |
| **accounting** | Financial events | Management-first (not statutory), append-only ledger |
| **procurement** | Purchase flow | Request→Approval→PO→Receive→Payment, role-based approvals |
| **promotion** | Rules, loyalty | Rule-based pricing modification, customer-controlled loyalty |
| **hr** | Staff, attendance | Light HR, biometric-aware, labour cost reference only |

### Workshop Engine (Special Attention)
Workshop is style-driven. Style = single source of truth for design, costing, cutting, ordering.

**Style Creation Flow:**
1. Prerequisites: style type (window/door/fixed), material type, material group
2. Drawing: Lines (profiles) + Shape Areas (fills)
3. Lines have: name, profile, formula, offcut, position, endpoints, is_variable
4. **Frame ONLY** can have formula = null (fallback to W or H by position)
5. All other lines MUST have formulas referencing other lines (dependency chain)
6. Shapes: material, width formula, height formula, clearance
7. POS: select style → enter W×H (+ variables if any) → project auto-created
8. Project states: Quote → In Progress (only In Progress generates cutting lists)
9. Material quantities finalized AFTER cutting list generated (not from raw formulas)

**Line Endpoint Types:** Mater-Mater | Mater-Square | Square-Square

---

## AI BOUNDARIES (NON-NEGOTIABLE)

- AI is **advisory only** — flagged with `advisory_actor=True`
- AI cannot commit state, execute operations, or modify records
- AI actions go through command pipeline like everything else
- AI cannot: sign contracts, borrow funds, pay money, dismiss staff, delete data, alter history
- AI cannot activate/modify promotion rules, change integration configs
- Full journaling of all AI interactions required

---

## CODING RULES

### File Delivery
- Generate individual files with placement instructions (not full project zips)
- User integrates files locally

### Event Types
- Format: `engine.domain.action` (e.g., `inventory.stock.moved`, `cash.session.closed`)
- Must be registered in EventTypeRegistry before use
- Free-text event types are FORBIDDEN

### Dependency Injection
- Validators receive `BusinessContextProtocol` + `EventTypeRegistry` as parameters
- No global state, no singletons for business logic
- Thread-safe registries use `threading.Lock`

### Error Handling
- No silent failures, no exception swallowing
- Every rejection is deterministic, explicit, auditable
- Raw database exceptions never propagate to callers
- Subscriber failure must NOT affect persisted events or other subscribers

### Dispatch Rules
- Dispatch happens AFTER commit via `transaction.on_commit()`
- Dispatch failure is caught, logged, and reported — never rollback event
- Sequential handler execution with per-handler error catching

### Database Rules
- No direct DB writes outside `persist_event()`
- Events are NEVER deleted or updated
- Schema changes are additive only
- Corrections are new events with `correction_of` set

### Testing Patterns
- Pure functions for validators (no DB needed)
- Test immutability guards with `_state.adding = False`
- Test idempotency at both app and DB level
- Test hash-chain with GENESIS + chain continuation

---

## PHASE STATUS

| Phase | Name | Status |
|-------|------|--------|
| 0 | Core Kernel | ✅ ~90% COMPLETE (persistence package incomplete) |
| 1 | Governance & Policy | 🔲 PLANNED |
| 2 | Global Compliance | 🔲 PLANNED |
| 3 | Document Engine | 🔲 PLANNED |
| 4 | Business Primitives | 🔲 PLANNED |
| 5 | Enterprise Engines | 🔲 PLANNED |
| 6 | Vertical Modules | 🔲 PLANNED |
| 7 | AI & Intelligence | 🔲 PLANNED |
| 8 | Security & Isolation | 🔲 PLANNED |
| 9 | Integration Layer | 🔲 PLANNED |
| 10 | Performance & Scale | 🔲 PLANNED |
| 11 | Enterprise Admin | 🔲 PLANNED |
| 12 | SaaS Productization | 🔲 PLANNED |
| 13 | Documentation | 🔲 PLANNED |

### Phase 0 Gaps (Must resolve before Phase 1)
- Multi-tenant core (BusinessContextProtocol exists, concrete implementation pending)
- Identity & Actor model (enum exists, full identity management pending)
- Role-Permission-Scope engine (`core/security/` empty)
- Feature flags (`core/config/` empty)
- Country configuration loader (empty)

---

## COMMON COMMANDS

```bash
# From bos/ directory (where manage.py lives)
python manage.py migrate                    # Run migrations
python manage.py makemigrations             # Generate migrations
python manage.py shell                      # Django shell
python manage.py test                       # Run tests
python manage.py runserver                  # Dev server (bootstrap checks run!)
```

---

## CROSS-ENGINE DATA FLOW

```
Customer Action
    → Command (engines/{name}/commands/)
        → Validation (core/event_store/validators/)
            → Idempotency Check
                → Hash-Chain Verify
                    → Atomic Save (core/event_store/persistence/)
                        → on_commit: Dispatch (core/events/dispatcher.py)
                            → Subscribers (engines/{name}/subscriptions.py)
                                → Projections (projections/{name}/)
```

Events flow ONE direction: Engine → Event Store → Bus → Subscribers → Projections.
Never backward. Never circular. Never bypass.

---

## REFERENCE DOCUMENTS (in project)

| Document | Covers |
|----------|--------|
| BOS_Master_Roadmap.pdf | Phases 0-13, completion status |
| BOS_Implementation_Build_Plan_Official.pdf | Logical build order |
| BOS_Core_Technical_Appendix_Mandatory_for_Developers.pdf | Technical contracts (MUST READ) |
| BOS_System_Architecture_Recap.pdf | Golden Path, scaling, governance |
| BOS_Retail_HOW_Official.pdf | Retail engine design |
| BOS_Restaurant_HOW_Official.pdf | Restaurant engine design |
| BOS_Workshop_HOW_Official.pdf | Workshop style-driven production |
| BOS_Inventory_Engine_HOW_Official.pdf | Event-based stock control |
| BOS_Cash_Management_HOW_Official.pdf | Cash control doctrine |
| BOS_Accounting_Engine_HOW_Official.pdf | Management accounting |
| BOS_Procurement_Engine_HOW_Official.pdf | Purchase flow control |
| BOS_Promotion_Engine_HOW_Official.pdf | Rule-based promotions |
| BOS_HR_Payroll_Engine_HOW_Official.pdf | Light HR, biometric attendance |
| BOS_Reporting_BI_Engine_HOW_Official.pdf | Event-driven BI |
| BOS_Decision_Simulation_AI_Advisors_HOW_Official.pdf | AI advisory layer |
| BOS_Integration_Engine_HOW_Official.pdf | External connectivity |
| BOS_Global_Administration_Governance.pdf | Platform governance |
