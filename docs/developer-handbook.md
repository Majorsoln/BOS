# BOS Developer Handbook

> Version: 1.0
> Audience: Developers building on or extending BOS

---

## 1. What Is BOS?

BOS (Business Operating System) is a **deterministic, event-sourced, multi-tenant business kernel**.

It is NOT a traditional Django application. It is NOT an ERP. BOS is a **legally defensible business kernel** where:

- All state derives from immutable events
- Every mutation is auditable and reproducible
- Engines are isolated — they communicate via events only
- AI components are advisory only — never state-authoritative

---

## 2. Architecture Overview

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────┐
│  Django Adapter (thin HTTP shell)   │
│  adapters/django_api/views.py       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  HTTP API Handlers                  │
│  core/http_api/handlers.py          │
│  Parse contract → Build command     │
└──────────────┬──────────────────────┘
               │ Command
               ▼
┌─────────────────────────────────────┐
│  Command Bus + Dispatcher           │
│  core/commands/bus.py               │
│  Evaluate policies → ACCEPT/REJECT  │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
   ACCEPTED         REJECTED
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ Engine       │ │ Rejection    │
│ Service      │ │ Event        │
│ Execute +    │ └──────────────┘
│ Emit Event   │
└──────┬───────┘
       │ Event
       ▼
┌─────────────────────────────────────┐
│  Event Store (PostgreSQL)           │
│  Append-only, hash-chained          │
│  core/event_store/                  │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
  Persisted        Projection
  (immutable)      (in-memory)
                   Rebuilt on load
```

### Key Concepts

| Concept | Traditional Django | BOS Equivalent |
|---------|-------------------|----------------|
| Database tables | `models.py` with ORM | Event Store (append-only events) |
| Business logic | `views.py` | Engine Services + Command Bus |
| HTML output | `templates/` | JSON API responses + Document Engine (PDF/HTML) |
| State queries | `SELECT * FROM ...` | Projections (in-memory, rebuilt from events) |
| Data changes | `model.save()` | Command → Event → Projection |

---

## 3. Getting Started

### 3.1 Prerequisites

- Python 3.11+
- PostgreSQL (for event store persistence)
- Django 5.x (as HTTP container only)

### 3.2 Project Structure

```
BOS/
├── core/                  # System kernel (immutable truth)
│   ├── event_store/       # Append-only event persistence
│   ├── commands/          # Command bus, dispatcher, outcomes
│   ├── http_api/          # HTTP handlers and contracts
│   ├── admin/             # Admin service (feature flags, compliance, tenants)
│   ├── saas/              # SaaS modules (plans, subscriptions, onboarding)
│   ├── security/          # Tenant isolation, rate limiting, anomaly detection
│   ├── feature_flags/     # Engine-level feature flag system
│   ├── business/          # Business & Branch lifecycle models
│   ├── documents/         # Document builder & rendering
│   └── ...                # Other core modules
│
├── engines/               # 10 business engines
│   ├── accounting/        # Journal entries, trial balance
│   ├── cash/              # Cash drawer, reconciliation
│   ├── inventory/         # Stock movements, FIFO/LIFO
│   ├── procurement/       # PO lifecycle, supplier registry
│   ├── retail/            # POS sale lifecycle
│   ├── restaurant/        # Table/order/kitchen workflow
│   ├── workshop/          # Parametric geometry, cut optimization
│   ├── promotion/         # Campaigns, loyalty programs
│   ├── hr/                # Employee lifecycle, payroll
│   └── reporting/         # KPI snapshots, BI projections
│
├── adapters/              # Framework adapters (Django HTTP)
├── ai/                    # Advisory system (guardrails, advisors)
├── integration/           # Inbound/outbound adapters
├── projections/           # Cross-engine read models
├── tests/                 # Test suite (1135+ tests)
├── config/                # Django configuration
└── docs/                  # Documentation
```

### 3.3 Running the Server

```bash
python manage.py runserver 127.0.0.1:8000
```

### 3.4 Running Tests

```bash
# All tests (excluding DB-dependent tests)
python -m pytest tests/ -v \
  --ignore=tests/core/test_event_store_pg.py \
  --ignore=tests/core/test_event_store_postgres_contract.py \
  --ignore=tests/core/test_http_api_auth_db_integration.py \
  --ignore=tests/core/test_http_api_identity_admin.py \
  --ignore=tests/core/test_identity_store_bootstrap.py \
  --ignore=tests/core/test_permissions_db_provider.py

# Engine tests only
python -m pytest tests/engines/ -v

# Core + AI tests only
python -m pytest tests/core/ tests/ai/ -v

# SaaS module tests
python -m pytest tests/saas/ -v

# Admin module tests
python -m pytest tests/admin/ -v
```

---

## 4. Core Patterns

### 4.1 Frozen Dataclasses

All data structures are immutable:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CreateOrderRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    items: tuple  # tuples, not lists
```

Why frozen? Determinism. Immutable data can be replayed safely.

### 4.2 Command → Event → Projection

**Step 1: Command** — Express intent

```python
command = Command(
    command_id=uuid.uuid4(),
    command_type="retail.sale.complete.request",
    business_id=business_id,
    branch_id=branch_id,
    payload={"items": [...]},
    ...
)
```

**Step 2: Event** — Record fact

```python
event = {
    "event_type": "retail.sale.completed.v1",
    "business_id": str(business_id),
    "payload": {"sale_id": "...", "total": "1500.00"},
    "status": "FINAL",
}
persist_event(event)  # Append-only, hash-chained
```

**Step 3: Projection** — Derive state

```python
class SaleProjection:
    def apply(self, event_type, payload):
        if event_type == "retail.sale.completed.v1":
            self._sales[payload["sale_id"]] = SaleRecord(...)
```

### 4.3 RejectionReason

All rejections are structured:

```python
from core.commands.rejection import RejectionReason

rejection = RejectionReason(
    code="INSUFFICIENT_STOCK",
    message="Not enough stock for item X.",
    policy_name="check_stock_availability",  # REQUIRED
)
```

The `policy_name` field is mandatory — tests will fail without it.

### 4.4 Feature Flags

Every engine is wrapped behind a feature flag:

```python
from core.feature_flags.models import FeatureFlag, FEATURE_ENABLED

flag = FeatureFlag(
    flag_key="ENABLE_RETAIL_ENGINE",
    business_id=business_id,
    status=FEATURE_ENABLED,
)
```

---

## 5. Dev Credentials (Smoke Testing)

Seeded in `adapters/django_api/wiring.py`:

| Credential | Value |
|------------|-------|
| Admin API Key | `dev-admin-key` |
| Cashier API Key | `dev-cashier-key` |
| Business ID | `11111111-1111-1111-1111-111111111111` |
| Admin Branch | `22222222-2222-2222-2222-222222222222` |
| Cashier Branch | `33333333-3333-3333-3333-333333333333` |

### Headers

```
X-API-KEY: dev-admin-key
X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111
X-BRANCH-ID: 22222222-2222-2222-2222-222222222222  (optional)
```

---

## 6. Invariants — Never Break These

1. **Hash-chain integrity** — Never modify `core/event_store/hashing/`
2. **Replay determinism** — No `datetime.now()` inside engine logic
3. **Engine isolation** — No direct cross-engine calls
4. **Multi-tenant safety** — Every event has `business_id`
5. **Additive only** — No removing events, commands, or contracts
6. **`policy_name` required** — Every `RejectionReason()` must include it
7. **AI is advisory** — Never commits state autonomously
8. **All core models frozen** — Immutable dataclasses
9. **Audit entries append-only** — No deletion
10. **Scope guards enforced** — First statement in every engine's `_execute_command()`

---

## 7. Test Doubles

All engine tests use in-memory stubs:

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
    def dispatch(self, command):
        self.dispatched.append(command)
        return MagicMock(status="ACCEPTED")
```

---

## 8. Commit Workflow

```bash
# 1. Run tests
python -m pytest tests/ -v --ignore=tests/core/test_event_store_pg.py ...

# 2. Commit with descriptive message
git commit -m "Phase X — Short description of changes"

# 3. Push to feature branch
git push -u origin <branch-name>
```

Never push to `main` directly.

---

*"BOS is not an ERP. It is a deterministic, legally defensible business kernel."*
