# BOS Certification Path

> Version: 1.0
> Audience: QA teams, auditors, and deployment engineers

---

## 1. Purpose

This document defines the certification checklist for verifying that a BOS deployment meets all architectural, security, and compliance requirements before production use.

---

## 2. Certification Levels

| Level | Name | Requirements |
|-------|------|-------------|
| L1 | **Core Certified** | Event store integrity, replay determinism, tenant isolation |
| L2 | **Engine Certified** | All enabled engines pass feature tests + policies |
| L3 | **Production Ready** | Security hardened, compliance configured, monitoring active |

---

## 3. Level 1: Core Certification

### 3.1 Event Store Integrity

- [ ] **Hash-chain verification passes** — No gaps or mismatches in SHA-256 chain
- [ ] **Append-only enforcement** — No UPDATE or DELETE on event tables
- [ ] **Idempotency check** — Duplicate event_id is rejected
- [ ] **Event schema validation** — All required fields present (event_type, business_id, payload, event_hash)

### 3.2 Replay Determinism

- [ ] **Replay produces identical state** — Clear projections, replay all events, verify state matches
- [ ] **No time-dependent logic** — No `datetime.now()` in engine code
- [ ] **No random values in logic** — No `random()` in engine code
- [ ] **Ordered event processing** — Events applied in `created_at` order

### 3.3 Tenant Isolation

- [ ] **business_id on every event** — No events without tenant scope
- [ ] **Cross-tenant query impossible** — Projections filtered by business_id
- [ ] **Scope guard enforced** — First statement in every engine's `_execute_command()`
- [ ] **Rate limiting active** — Per-actor, per-business sliding window

### 3.4 Command Pipeline

- [ ] **All commands produce deterministic outcomes** — ACCEPTED or REJECTED
- [ ] **Rejection reasons are structured** — `code`, `message`, `policy_name` present
- [ ] **No silent failures** — Every rejection is logged as an event

### 3.5 Test Coverage

- [ ] **Core tests pass** — `python -m pytest tests/core/ -v`
- [ ] **Invariant tests pass** — `python -m pytest tests/invariants/ -v`
- [ ] **Security tests pass** — `python -m pytest tests/security/ -v`

---

## 4. Level 2: Engine Certification

### 4.1 Per-Engine Checklist

For each enabled engine, verify:

- [ ] **Feature flag exists** — `ENABLE_<ENGINE>_ENGINE` flag defined
- [ ] **Event types registered** — All `*.v1` event types in registry
- [ ] **Commands have validation** — `__post_init__` on all frozen dataclasses
- [ ] **Scope guard enforced** — Branch requirement matches scope-policy.md
- [ ] **Policies return RejectionReason** — With `policy_name` field
- [ ] **Projection store has apply()** — Deterministic state rebuild
- [ ] **Engine tests pass** — `python -m pytest tests/engines/test_<name>*.py -v`

### 4.2 Engine Test Matrix

| Engine | Expected Tests | Scope |
|--------|---------------|-------|
| accounting | 30+ | BUSINESS_SCOPE |
| cash | 25+ | BRANCH_REQUIRED |
| inventory | 30+ | BRANCH_REQUIRED |
| procurement | 25+ | BUSINESS_SCOPE |
| retail | 25+ | BRANCH_REQUIRED |
| restaurant | 25+ | BRANCH_REQUIRED |
| workshop | 25+ | BRANCH_REQUIRED |
| promotion | 20+ | BUSINESS_SCOPE |
| hr | 20+ | BUSINESS_SCOPE |
| reporting | 15+ | BUSINESS_SCOPE |

### 4.3 Cross-Engine Integration

- [ ] **Subscriptions wired** — accounting, cash, inventory, procurement subscribe to events
- [ ] **Reporting engine receives** — Subscribes to 8+ event types from other engines
- [ ] **No direct cross-engine calls** — Engines communicate via events only

---

## 5. Level 3: Production Readiness

### 5.1 Security

- [ ] **API key authentication active** — All endpoints require `X-API-KEY`
- [ ] **Rate limiting configured** — Appropriate limits per actor type
- [ ] **Anomaly detection enabled** — High velocity, rapid branch switching, repeated rejections
- [ ] **Security guard pipeline active** — Fail-safe on errors (deny by default)
- [ ] **HTTPS enforced** — No plaintext HTTP in production
- [ ] **API keys rotated** — Default dev keys replaced with production keys
- [ ] **Dev credentials removed** — `dev-admin-key` and `dev-cashier-key` disabled

### 5.2 Compliance Configuration

- [ ] **Tax rules configured** — Per-business tax codes with correct rates
- [ ] **Compliance profile active** — Business-specific regulatory rules
- [ ] **Region pack applied** — Country defaults (currency, timezone, tax presets)
- [ ] **Document templates configured** — Receipt, invoice, quote templates
- [ ] **No hardcoded regional logic** — Verified via code review

### 5.3 Monitoring & Health

- [ ] **Health dashboard accessible** — Admin can view SystemOverview + HealthStatus
- [ ] **Metrics collection active** — Events/sec, rebuild duration, cache hit rate
- [ ] **Freshness guard configured** — SLA enforcement for projection staleness
- [ ] **Resilience mode monitorable** — NORMAL/DEGRADED/READ_ONLY state visible
- [ ] **Backup schedule configured** — Daily full + WAL archiving

### 5.4 SaaS Configuration

- [ ] **Subscription plan defined** — At least one active plan (STARTER/PROFESSIONAL/ENTERPRISE)
- [ ] **Plan quotas set** — Max branches, users, API calls, documents
- [ ] **Onboarding flow tested** — Full lifecycle: initiate → complete
- [ ] **Branding configured** — Logo, colors, support email (if white-label)

### 5.5 Documentation

- [ ] **API Reference available** — All 26+ endpoints documented
- [ ] **Developer Handbook available** — Setup, patterns, testing
- [ ] **Governance Manual available** — Roles, permissions, tenant isolation
- [ ] **Disaster Recovery Manual available** — Procedures and checklists

---

## 6. Certification Verification Script

Run the following to validate core certification:

```bash
# Step 1: Run full test suite
python -m pytest tests/ -v \
  --ignore=tests/core/test_event_store_pg.py \
  --ignore=tests/core/test_event_store_postgres_contract.py \
  --ignore=tests/core/test_http_api_auth_db_integration.py \
  --ignore=tests/core/test_http_api_identity_admin.py \
  --ignore=tests/core/test_identity_store_bootstrap.py \
  --ignore=tests/core/test_permissions_db_provider.py

# Step 2: Run invariant tests specifically
python -m pytest tests/invariants/ -v

# Step 3: Run security tests
python -m pytest tests/security/ -v

# Step 4: Run engine tests
python -m pytest tests/engines/ -v

# Step 5: Run SaaS module tests
python -m pytest tests/saas/ -v

# Step 6: Run admin module tests
python -m pytest tests/admin/ -v

# Step 7: Run AI advisory tests
python -m pytest tests/ai/ -v

# Step 8: Run performance tests
python -m pytest tests/performance/ -v

# Step 9: Run integration tests
python -m pytest tests/integration/ -v
```

**Expected result:** 1135+ tests passing

---

## 7. Certification Record

When certification is complete, record:

```
Certification Level: L1 / L2 / L3
Date: YYYY-MM-DD
Certified By: [Name]
Test Results: [total] passed, [0] failed
Hash-Chain: Verified / Not Verified
Tenant Isolation: Verified / Not Verified
Resilience Mode: NORMAL
Notes: [Any exceptions or waivers]
```

---

*"Certification is evidence. Every claim must be verifiable."*
