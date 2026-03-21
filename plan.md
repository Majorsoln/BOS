# BOS Regional Operations — Implementation Plan

## MUHTASARI (Executive Summary)

BOS inasajiliwa nchi **moja** (origin country) na kutoa huduma **globally online**.
Hakuna haja ya ofisi kila eneo — **isipokuwa kisheria kunahitajika**, ambapo
majukumu hayo yanapitishwa kwa **Regional Agent** (mtu/kampuni ya eneo hilo).

### Aina Mbili za Uendeshaji

| Mode | Maelezo | Mfano |
|------|---------|-------|
| **DIRECT** | BOS inatoa huduma online moja kwa moja. Agent (Global) anafanya marketing tu, hakuna ofisi. | Nchi ambayo hakuna sheria ya PE (permanent establishment) kwa digital services |
| **AGENT_MANAGED** | Kisheria inahitajika uwepo wa physical. Regional Agent anashikilia licenses, ofisi, compliance. | Nchi inayohitaji local business registration au data residency |

---

## FAILI MPYA: `core/saas/agents.py`

Inachukua nafasi ya `resellers.py` na `referrals.py` kulingana na Portal Spec.

### Data Models

```
AgentType:
  GLOBAL      — Remote agent, anafanya kazi popote duniani
  REGIONAL    — Promoted from Global, ana territory + office + compliance duties

AgentStatus:
  PROBATION   — Mpya, siku 90, lazima a-onboard tenants 5+
  ACTIVE      — Amepita probation
  SUSPENDED   — Frozen (tenants OK, commission accrues but no payout)
  TERMINATED  — Permanent, cannot reverse

AgentRecord (frozen dataclass):
  agent_id: UUID
  agent_name: str
  agent_type: GLOBAL | REGIONAL
  contact_email, contact_phone: str
  country_code: str (agent's own country)
  status: AgentStatus
  probation_start: datetime
  probation_end: datetime (+ 90 days)
  commission_rate_override: Optional[Decimal]  # None = use volume-based
  registered_at: datetime
  registered_by: str (platform admin actor_id)
  # ── Regional-only fields ──
  territory_codes: tuple[str, ...]   # e.g. ("KE",) or ("KE-047", "KE-030")
  regional_override_pct: Decimal     # 5-10% on ALL territory tenants
  office_address: str
  agreement_start: Optional[datetime]
  agreement_end: Optional[datetime]
  agreement_status: DRAFT | ACTIVE | EXPIRED | TERMINATED

AgentTenantLink (frozen dataclass):
  agent_id: UUID
  tenant_id: UUID (business_id)
  linked_at: datetime
  linked_by: str
  status: ACTIVE | TRANSFERRED | TERMINATED
  residual_rate: Decimal  # permanent % after transfer (2-5%)

CommissionTier (frozen dataclass):
  min_tenants: int
  max_tenants: Optional[int]
  rate_pct: Decimal

CommissionEntry (frozen dataclass):
  entry_id: UUID
  agent_id: UUID
  tenant_id: UUID
  period: str (YYYY-MM)
  tenant_payment_amount: Decimal
  commission_rate: Decimal
  commission_amount: Decimal
  override_amount: Decimal  # regional override
  total_earned: Decimal
  status: ACCRUED | APPROVED | PAID | CLAWED_BACK
  currency: str

PayoutRecord (frozen dataclass):
  payout_id: UUID
  agent_id: UUID
  period: str
  amount: Decimal
  currency: str
  method: MPESA | MOBILE_MONEY | BANK_TRANSFER
  status: PENDING | APPROVED | COMPLETED | FAILED
  requested_at, approved_at, completed_at: Optional[datetime]
  reference: str

TenantTransferRequest (frozen dataclass):
  transfer_id: UUID
  tenant_id: UUID
  from_agent_id: UUID
  to_agent_id: UUID
  reason: str
  status: PENDING | AGENT_APPROVED | ADMIN_APPROVED | DENIED | COMPLETED
  requested_at: datetime
  decided_at: Optional[datetime]
  decided_by: Optional[str]
  residual_rate: Decimal  # original agent keeps this permanently
```

### Event Types

```
saas.agent.registered.v1
saas.agent.promoted_to_regional.v1
saas.agent.suspended.v1
saas.agent.reinstated.v1
saas.agent.terminated.v1
saas.agent.updated.v1
saas.agent.tenant_linked.v1
saas.agent.tenant_unlinked.v1
saas.agent.commission_accrued.v1
saas.agent.commission_approved.v1
saas.agent.commission_clawback.v1
saas.agent.payout_requested.v1
saas.agent.payout_approved.v1
saas.agent.payout_completed.v1
saas.agent.transfer_requested.v1
saas.agent.transfer_agent_approved.v1
saas.agent.transfer_admin_approved.v1
saas.agent.transfer_denied.v1
saas.agent.transfer_completed.v1
saas.agent.commission_tiers_set.v1
```

### Projection: AgentProjection

```
- agents: Dict[UUID, AgentRecord]
- tenant_links: Dict[UUID, AgentTenantLink]  # tenant_id → link
- agent_tenants: Dict[UUID, Set[UUID]]  # agent_id → set of tenant_ids
- commissions: Dict[(UUID, str), CommissionEntry]  # (agent_id, period) → entry
- payouts: Dict[UUID, PayoutRecord]
- transfers: Dict[UUID, TenantTransferRequest]
- commission_tiers: List[CommissionTier]  # volume-based, platform-wide
- territory_map: Dict[str, Set[UUID]]  # territory_code → set of regional agent_ids
```

### Service: AgentService

```
Commands:
  register_agent(name, email, phone, country, type=GLOBAL, actor_id)
  promote_to_regional(agent_id, territory_codes, override_pct, office_address, agreement_months, actor_id)
  suspend_agent(agent_id, reason, actor_id)
  reinstate_agent(agent_id, actor_id)
  terminate_agent(agent_id, reason, actor_id)
  link_tenant(agent_id, tenant_id, actor_id)
  unlink_tenant(agent_id, tenant_id, actor_id)
  set_commission_tiers(tiers: list, actor_id)
  accrue_commission(agent_id, tenant_id, payment_amount, currency, period, actor_id)
  approve_commission(agent_id, period, actor_id)
  request_payout(agent_id, period, method, actor_id)
  approve_payout(payout_id, actor_id)
  complete_payout(payout_id, reference, actor_id)
  request_transfer(tenant_id, to_agent_id, reason, actor_id)
  agent_approve_transfer(transfer_id, actor_id)
  admin_approve_transfer(transfer_id, residual_rate, actor_id)
  deny_transfer(transfer_id, reason, actor_id)

Key Business Rules:
  - Agent starts PROBATION (90 days, min 5 tenants to auto-promote)
  - Commission = tenant_payment × volume_rate
  - Regional override = tenant_payment × regional_override_pct (for ALL territory tenants)
  - Platform promo → commission on ORIGINAL price (platform absorbs)
  - Agent promo → commission on DISCOUNTED price (agent absorbs)
  - Transfer: original agent keeps residual_rate permanently
  - Payment flow: Platform collects → commission accrues → agent requests → admin approves → payout
```

---

## FAILI MPYA: `core/saas/expansion_gates.py`

4-gate readiness check kabla nchi "kwenda live" kwa billing.

### Data Models

```
GateType:
  COUNTRY_LOGIC         — Currency, affordability weight, USD conversion
  B2B_B2C_QUALIFICATION — Tax rules, reverse charge, registration reqs
  REGISTRATION_PATH     — Digital tax registration or subsidiary pathway
  REPORTING_CORRECTION  — Credit note, adjustment invoice, tax correction

GateStatus:
  BLOCKED   — Gate not yet passed
  PARTIAL   — Some requirements met
  PASSED    — All requirements met

CountryExpansionRecord (frozen dataclass):
  country_code: str
  country_name: str
  operating_mode: DIRECT | AGENT_MANAGED
  gates: Dict[GateType, GateEntry]
  overall_status: BLOCKED | PARTIAL | LIVE
  activated_at: Optional[datetime]
  activated_by: Optional[str]

GateEntry (frozen dataclass):
  gate_type: GateType
  status: GateStatus
  details: dict  # gate-specific data
  verified_at: Optional[datetime]
  verified_by: Optional[str]
  notes: str
```

### Gate 1: COUNTRY_LOGIC details
```json
{
  "currency": "KES",
  "affordability_weight": 0.35,
  "usd_conversion_rate": 153.50,
  "tax_name": "VAT",
  "vat_rate": 0.16,
  "digital_tax_rate": 0.015,
  "b2b_reverse_charge": true
}
```

### Gate 2: B2B_B2C_QUALIFICATION details
```json
{
  "b2b_registration_required": true,
  "b2b_tax_id_format": "P0\\d{9}[A-Z]",
  "b2c_vat_rate": 0.16,
  "exemptions": ["education", "healthcare"],
  "registration_threshold": null
}
```

### Gate 3: REGISTRATION_PATH details
```json
{
  "pathway": "DIGITAL_TAX_REG",
  "authority": "KRA",
  "registration_url": "https://itax.kra.go.ke",
  "documentation_url": "/docs/compliance/KE-registration.pdf",
  "agent_submitted_at": "2026-03-15",
  "platform_verified_at": "2026-03-18"
}
```

### Gate 4: REPORTING_CORRECTION details
```json
{
  "credit_note_supported": true,
  "adjustment_invoice_supported": true,
  "tax_correction_workflow": "CN_THEN_NEW_INV",
  "fiscal_integration": "KRA_TIMS"
}
```

### Event Types
```
saas.expansion.gate_updated.v1
saas.expansion.country_activated.v1
saas.expansion.country_deactivated.v1
```

### Service: ExpansionGateService
```
Commands:
  update_gate(country_code, gate_type, status, details, actor_id)
  activate_country(country_code, operating_mode, actor_id)
    → validates ALL 4 gates are PASSED
  deactivate_country(country_code, reason, actor_id)
```

---

## FAILI MPYA: `core/saas/operating_licenses.py`

Hati za kisheria za BOS au Regional Agent katika nchi fulani.

### Data Models

```
LicenseType:
  BUSINESS_REGISTRATION    — Company registration in country
  DATA_PROTECTION         — Data protection authority registration
  PAYMENT_PROCESSOR       — License to handle payments
  TAX_AGENT               — Tax collection/remittance authorization
  DIGITAL_SERVICES        — Digital services provider license
  INDUSTRY_SPECIFIC       — E.g., hotel levy, tourism board

LicenseStatus:
  PENDING     — Applied, waiting
  ACTIVE      — Valid and current
  EXPIRING_SOON — Auto-set 60 days before expiry
  EXPIRED     — Past expiry date, not renewed
  SUSPENDED   — Suspended by authority
  REVOKED     — Permanently revoked

LicenseHolder:
  PLATFORM    — BOS itself holds this license
  AGENT       — Regional Agent holds this license

OperatingLicense (frozen dataclass):
  license_id: UUID
  country_code: str
  license_type: LicenseType
  holder: LicenseHolder
  holder_id: Optional[UUID]  # agent_id if AGENT
  issuing_authority: str  # "KRA", "ODPC", "CAK"
  license_number: str
  issued_date: date
  expiry_date: Optional[date]  # None = perpetual
  document_url: str  # URL to scanned document
  status: LicenseStatus
  renewal_reminder_days: int = 60
  notes: str = ""
  created_at: datetime
  created_by: str
```

### Event Types
```
saas.license.uploaded.v1
saas.license.renewed.v1
saas.license.expiring_soon.v1  (system-generated)
saas.license.expired.v1        (system-generated)
saas.license.suspended.v1
saas.license.revoked.v1
```

### Service: LicenseService
```
Commands:
  upload_license(country_code, license_type, holder, holder_id, authority, number, issued, expiry, doc_url, actor_id)
  renew_license(license_id, new_expiry, new_doc_url, actor_id)
  suspend_license(license_id, reason, actor_id)
  revoke_license(license_id, reason, actor_id)
  check_expiring_licenses()  → system job, flags EXPIRING_SOON

Business Rules:
  - Expiring license (60 days) → auto-alert to agent + platform
  - Expired license + no renewal → block new tenant signups in that country
  - Revoked license → immediate escalation to platform admin
  - Regional Agent must have at least BUSINESS_REGISTRATION license
```

---

## FAILI MPYA: `core/saas/compliance_workflow.py`

Mfumo wa Regional Agent kupendekeza sheria → Platform kukagua → Platform kutekeleza.

### Data Models

```
ComplianceSubmissionType:
  TAX_RULES              — VAT/GST rates, exemptions
  BUSINESS_REGULATIONS   — Local business licensing
  DATA_RESIDENCY         — Data storage requirements
  PAYMENT_PROCESSORS     — Approved local payment methods
  REGULATORY_UPDATE      — New laws/regulation changes
  FISCAL_DEVICE          — EFD/TIMS/EFRIS requirements

SubmissionStatus:
  PENDING          — Agent submitted, awaiting review
  UNDER_REVIEW     — Platform legal team reviewing
  REVISION_NEEDED  — Platform requests changes
  APPROVED         — Platform verified, ready to implement
  IMPLEMENTED      — Platform has coded changes into system
  CONFIRMED        — Agent confirms implementation matches reality
  REJECTED         — Platform rejects submission

ComplianceSubmission (frozen dataclass):
  submission_id: UUID
  country_code: str
  agent_id: UUID  # submitting Regional Agent
  submission_type: ComplianceSubmissionType
  title: str
  summary: str  # agent's description of the law/regulation
  supporting_documents: tuple[str, ...]  # URLs
  effective_date: Optional[date]  # when law takes effect
  status: SubmissionStatus
  submitted_at: datetime
  reviewed_at: Optional[datetime]
  reviewed_by: Optional[str]
  review_notes: str
  implemented_at: Optional[datetime]
  confirmed_at: Optional[datetime]
  confirmation_notes: str
```

### Event Types
```
saas.compliance.submitted.v1
saas.compliance.under_review.v1
saas.compliance.revision_needed.v1
saas.compliance.approved.v1
saas.compliance.implemented.v1
saas.compliance.confirmed.v1
saas.compliance.rejected.v1
```

### Workflow
```
Regional Agent studies local laws
  → Agent uploads via POST /agent/compliance/submit
    → Status: PENDING
      → Platform legal reviews → UNDER_REVIEW
        → If OK: APPROVED → Platform implements → IMPLEMENTED
          → Agent confirms → CONFIRMED
        → If needs changes: REVISION_NEEDED → Agent resubmits
        → If invalid: REJECTED

CRITICAL: No law enters the system through agent submission.
Platform ALWAYS verifies independently and implements.
```

---

## FAILI MPYA: `core/saas/fiscal_integration.py`

Stubs za fiscal device integration (KRA TIMS, TRA EFD, etc.)

### Data Models

```
FiscalSystem:
  KRA_TIMS     — Kenya Revenue Authority Tax Invoice Management System
  TRA_EFD      — Tanzania Revenue Authority Electronic Fiscal Device
  URA_EFRIS    — Uganda Revenue Authority Electronic Fiscal Receipting
  ZRA_VSDC     — Zambia Revenue Authority Virtual Sales Data Controller
  GENERIC      — Generic e-invoicing adapter

FiscalIntegrationStatus:
  CONFIGURED   — Settings saved but not tested
  TESTING      — In test/sandbox mode
  ACTIVE       — Live, sending real fiscal data
  INACTIVE     — Temporarily disabled
  FAILED       — Last health check failed

FiscalIntegrationRecord (frozen dataclass):
  integration_id: UUID
  country_code: str
  system: FiscalSystem
  api_endpoint: str
  credentials_ref: str  # vault reference, NEVER store raw credentials
  sandbox_mode: bool
  status: FiscalIntegrationStatus
  last_health_check: Optional[datetime]
  last_health_status: Optional[str]
  configured_by: str
  configured_at: datetime
```

### Event Types
```
saas.fiscal.configured.v1
saas.fiscal.activated.v1
saas.fiscal.deactivated.v1
saas.fiscal.health_check.v1
```

**NOTE:** This is STUB-only for now. Actual fiscal device API integration
will be built when specific countries require it. The data model is ready.

---

## MABADILIKO KWA FAILI ZILIZOPO

### 1. `core/saas/onboarding.py` — Add AGENT_ASSIGNED step

```python
class OnboardingStep(Enum):
    INITIATED = "INITIATED"
    AGENT_ASSIGNED = "AGENT_ASSIGNED"    # ← NEW
    BUSINESS_CREATED = "BUSINESS_CREATED"
    PLAN_SELECTED = "PLAN_SELECTED"
    BRANCH_CREATED = "BRANCH_CREATED"
    ADMIN_SETUP = "ADMIN_SETUP"
    COMPLETED = "COMPLETED"
```

OnboardingRecord gets new field:
```python
agent_id: Optional[str] = None  # assigned agent UUID
```

### 2. `core/platform/tenant_lifecycle.py` — New suspension reason

```python
class SuspensionReason(Enum):
    ...existing...
    REGIONAL_LICENSE_EXPIRED = "REGIONAL_LICENSE_EXPIRED"  # ← NEW
```

### 3. `core/saas/subscriptions.py` — Add agent_id tracking

SubscriptionRecord gets:
```python
agent_id: Optional[str] = None  # attributed agent
```

### 4. `core/saas/resellers.py` — DEPRECATED

Add deprecation notice at top:
```python
"""
DEPRECATED — replaced by core/saas/agents.py
See BOS-PORTAL-SPECIFICATION.md Appendix A.
Kept for migration compatibility only.
"""
```

### 5. `core/saas/referrals.py` — DEPRECATED

Same deprecation notice.

### 6. `adapters/django_api/urls.py` — New URL patterns

Agent Portal endpoints (replacing reseller/referral):
```
# Agent Management (Platform Admin)
POST  /platform/agents/register
POST  /platform/agents/promote-to-regional
POST  /platform/agents/suspend
POST  /platform/agents/reinstate
POST  /platform/agents/terminate
GET   /platform/agents
GET   /platform/agents/{id}
POST  /platform/agents/set-commission-tiers
POST  /platform/agents/approve-payout
POST  /platform/agents/complete-payout
POST  /platform/agents/approve-transfer
POST  /platform/agents/deny-transfer

# Agent Self-Service
GET   /agent/dashboard
POST  /agent/onboard-tenant
GET   /agent/tenants
GET   /agent/commissions
POST  /agent/request-payout
POST  /agent/request-transfer
GET   /agent/agreement

# Agent Compliance (Regional only)
POST  /agent/compliance/submit
GET   /agent/compliance/submissions

# Expansion Gates
GET   /platform/expansion-gates
POST  /platform/expansion-gates/update
POST  /platform/expansion-gates/activate-country
POST  /platform/expansion-gates/deactivate-country

# Operating Licenses
POST  /platform/licenses/upload
POST  /platform/licenses/renew
GET   /platform/licenses?country_code=
GET   /agent/licenses  (own licenses)

# Fiscal Integration
POST  /platform/fiscal/configure
GET   /platform/fiscal?country_code=
POST  /platform/fiscal/health-check
```

---

## MPANGILIO WA KAZI (Implementation Order)

### Phase 1: Core Agent Model (kubadilisha Reseller/Referral)
1. Create `core/saas/agents.py` — full data models + projection + service
2. Deprecate `resellers.py` and `referrals.py`
3. Update `onboarding.py` — add AGENT_ASSIGNED step
4. Update `subscriptions.py` — add agent_id
5. Update `tenant_lifecycle.py` — add REGIONAL_LICENSE_EXPIRED

### Phase 2: Expansion & Licensing
6. Create `core/saas/expansion_gates.py` — 4-gate system
7. Create `core/saas/operating_licenses.py` — license tracking
8. Create `core/saas/compliance_workflow.py` — submission workflow
9. Create `core/saas/fiscal_integration.py` — fiscal device stubs

### Phase 3: HTTP Wiring
10. Add all new views in `adapters/django_api/views.py`
11. Wire URL patterns in `adapters/django_api/urls.py`
12. Remove old reseller/referral endpoints

### Phase 4: Integration
13. Wire agent assignment into onboarding flow
14. Wire license expiry checking (background job stub)
15. Wire expansion gate validation into country activation

---

## KANUNI KUU (Doctrine)

1. **BOS = nchi moja, huduma globally** — hakuna subsidiary, hakuna branch office
2. **Agent ≠ employee** — ni independent contractor, ana makubaliano yake
3. **Hakuna direct signup** — kila tenant lazima apitie Agent
4. **GLOBAL → REGIONAL ni promotion** — si entity mpya, ni upgrade ya existing agent
5. **Commission baada ya Platform kucollect** — Agent haipati pesa kabla tenant hajalipa
6. **Sheria za eneo zinapitia verification** — Agent anapendekeza, Platform inakagua na kutekeleza
7. **4 gates kabla ya kwenda live** — nchi haiwezi ku-accept billing mpaka gates zote zimepita
8. **Immutable history** — kila action ni event, hakuna kufuta au kubadilisha nyuma
