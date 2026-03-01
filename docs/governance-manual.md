# BOS Governance & Authorization Manual

> Version: 1.0
> Audience: Administrators and developers managing access control

---

## 1. Actor Model

Every operation in BOS is performed by an **actor**. Actors are classified by type:

| Actor Type | Description | Rate Limit Tier |
|------------|-------------|-----------------|
| `HUMAN` | Human user (admin, cashier, manager) | Standard |
| `SYSTEM` | Internal system process | Elevated |
| `DEVICE` | Hardware device (POS terminal, EFD) | Standard |
| `AI` | AI advisory component | Restricted |

### 1.1 AI Actor Restrictions

AI actors are **advisory only** and are subject to guardrails:

- Cannot approve purchases
- Cannot sign contracts
- Cannot borrow funds
- Cannot create actors
- Cannot modify permissions
- Cannot override policies
- Cannot delete data
- Cannot access cross-tenant data
- Cannot bypass compliance

All AI actions are logged in the Decision Journal (`ai/journal/`).

---

## 2. Identity & Authentication

### 2.1 API Key Authentication

All HTTP requests require authentication via API key:

```
X-API-KEY: <api-key>
X-BUSINESS-ID: <business-uuid>
X-BRANCH-ID: <branch-uuid>  (optional, depends on operation scope)
```

### 2.2 Identity Bootstrap

First-time setup creates the initial admin actor:

```bash
POST /v1/admin/identity/bootstrap
{
    "business_id": "...",
    "admin_actor_id": "admin-1",
    "admin_actor_type": "HUMAN"
}
```

### 2.3 API Key Lifecycle

| Endpoint | Description |
|----------|-------------|
| `POST /v1/admin/api-keys/create` | Create new API key |
| `POST /v1/admin/api-keys/revoke` | Revoke an API key |
| `POST /v1/admin/api-keys/rotate` | Rotate (revoke old + create new) |
| `GET /v1/admin/api-keys` | List all API keys |

---

## 3. Role-Based Access Control (RBAC)

### 3.1 Role Assignment

```bash
POST /v1/admin/roles/assign
{
    "business_id": "...",
    "actor_id": "user-42",
    "role": "cashier"
}
```

### 3.2 Role Revocation

```bash
POST /v1/admin/roles/revoke
{
    "business_id": "...",
    "actor_id": "user-42",
    "role": "cashier"
}
```

### 3.3 Standard Roles

Roles are admin-configurable, not hardcoded. Common roles:

| Role | Typical Permissions |
|------|-------------------|
| `admin` | Full access to all operations |
| `manager` | Business-wide read + write for enabled engines |
| `cashier` | Branch-scoped retail/cash operations |
| `accountant` | Accounting engine + reporting read |
| `warehouse` | Inventory engine operations |
| `kitchen` | Restaurant kitchen workflow |
| `hr_admin` | HR engine operations |

---

## 4. Permission Evaluation Pipeline

When a command enters the Command Bus, it passes through multiple authorization layers:

```
Command arrives
    │
    ▼
┌─────────────────────────────┐
│ 1. Actor Scope Guard        │  Is actor valid? Has business access?
├─────────────────────────────┤
│ 2. Permission Guard         │  Does role allow this command type?
├─────────────────────────────┤
│ 3. Feature Flag Guard       │  Is the engine enabled for this tenant?
├─────────────────────────────┤
│ 4. Compliance Guard         │  Does operation comply with regulations?
├─────────────────────────────┤
│ 5. Document Guard           │  (For doc operations) Template valid?
└─────────────────────────────┘
    │
    ▼
  ACCEPTED or REJECTED (with structured RejectionReason)
```

### 4.1 Rejection Codes

| Code | Meaning |
|------|---------|
| `ACTOR_REQUIRED_MISSING` | No actor provided in request |
| `PERMISSION_DENIED` | Role does not allow this operation |
| `FEATURE_DISABLED` | Engine not enabled for this business |
| `COMPLIANCE_VIOLATION` | Operation violates compliance rules |
| `BUSINESS_SUSPENDED` | Business is in SUSPENDED state |
| `BUSINESS_CLOSED` | Business is in CLOSED state |
| `BRANCH_REQUIRED_MISSING` | Branch scope required but not provided |
| `BRANCH_NOT_IN_BUSINESS` | Branch does not belong to this business |
| `AI_EXECUTION_FORBIDDEN` | AI actor attempted forbidden operation |
| `INVALID_COMMAND_STRUCTURE` | Command failed validation |

---

## 5. Multi-Tenant Isolation

### 5.1 Scope Model

Every command and event MUST contain:
- `business_id` — **mandatory** (tenant identifier)
- `branch_id` — **optional** (physical location within tenant)

### 5.2 Scope Enforcement

```
business_id = X, branch_id = None     → Business Scope (administrative)
business_id = X, branch_id = Y        → Branch Scope (operational)
business_id = None                     → REJECTED (always)
```

### 5.3 Tenant Isolation Guarantees

- **Event Store**: Events are scoped to `business_id`. Cross-tenant queries are impossible.
- **Projections**: Rebuilt per business. No shared state between tenants.
- **Rate Limiting**: Per-actor, per-business sliding window.
- **Anomaly Detection**: Monitors for rapid branch switching, high velocity commands.

### 5.4 Security Guard Pipeline

The `SecurityGuardPipeline` (`core/security/`) orchestrates:

1. **Tenant Isolation Check** — Verify actor belongs to business
2. **Rate Limit Check** — Sliding window per actor/business
3. **Anomaly Detection** — Flag suspicious patterns
4. Fail-safe: On internal error, guards **fail closed** (deny access)

---

## 6. Business Lifecycle

Businesses (tenants) follow a strict lifecycle:

```
CREATED  ──→  ACTIVE  ──→  SUSPENDED  ──→  CLOSED
  │              │              │
  └──→ CLOSED    └──→ CLOSED   └──→ ACTIVE (reactivate)
```

| State | Can Accept Commands? | Can Add Branches? |
|-------|---------------------|-------------------|
| CREATED | Yes (setup only) | Yes |
| ACTIVE | Yes | Yes |
| SUSPENDED | No | No |
| CLOSED | No (terminal) | No |

---

## 7. Audit Trail

### 7.1 Event Store as Audit

Every state change produces an immutable event with:
- `event_id` — Unique identifier
- `actor_id` + `actor_type` — Who performed the action
- `business_id` + `branch_id` — Scope
- `created_at` — When it happened
- `event_hash` — SHA-256 hash-chain integrity
- `correlation_id` — Groups related operations
- `status` — FINAL / PROVISIONAL / REVIEW_REQUIRED

### 7.2 Consent Records

The audit module (`core/audit/`) maintains append-only consent records:
- `grant_consent()` — Record consent given
- `revoke_consent()` — Record consent withdrawn (does not delete grant)
- All consent records are immutable and timestamped

### 7.3 AI Decision Journal

AI advisory actions are logged in `ai/journal/`:
- `DecisionEntry` — Records AI recommendation
- `DecisionMode` — ADVISORY / AUTONOMOUS
- `DecisionOutcome` — ACCEPTED / REJECTED / OVERRIDDEN
- Append-only, tenant-scoped

---

## 8. Compliance Configuration

Compliance rules are **data-driven, not hardcoded**:

```
# WRONG (never do this):
if country == "TZ":
    apply_vat(18)

# CORRECT:
tax_rule = config_store.get_tax_rule(business_id, "VAT")
apply_tax(tax_rule.rate)
```

Compliance profiles are managed via admin API:
- `POST /v1/admin/compliance-profiles/upsert`
- `POST /v1/admin/compliance-profiles/deactivate`
- `GET /v1/admin/compliance-profiles`

---

*"Governance is not optional. Every action is auditable, every boundary is enforced."*
