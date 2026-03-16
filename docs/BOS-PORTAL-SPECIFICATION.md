# BOS Platform — Portal & Operations Specification

**Version:** 1.0
**Date:** 2026-03-16
**Status:** Approved Doctrine
**Scope:** Global Admin Portal + Agent Portal — full feature specification with permissions

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [User Roles & Permissions](#2-user-roles--permissions)
3. [Global Admin Portal — Feature Specification](#3-global-admin-portal)
4. [Agent Portal — Feature Specification](#4-agent-portal)
5. [Pricing Model](#5-pricing-model)
6. [Agent Commission & Payout](#6-agent-commission--payout)
7. [Tenant Lifecycle](#7-tenant-lifecycle)
8. [Compliance Model](#8-compliance-model)
9. [SaaS Compliance Standard](#9-saas-compliance-standard)
10. [Data & Privacy](#10-data--privacy)

---

## 1. System Overview

BOS operates two portals serving different user groups:

```
┌──────────────────────────────────────────────────────────────────┐
│                    BOS GLOBAL ADMIN PORTAL                       │
│  Technology owner · Pricing authority · Compliance verifier      │
│  URL: /platform/*                                                │
│  Users: Platform administrators, support staff                   │
└──────────────────────────────────────────────────────────────────┘
         │
         │  Manages
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      BOS AGENT PORTAL                            │
│  Tenant acquisition · Onboarding · L1 support · Commissions     │
│  URL: /agent/*                                                   │
│  Users: Global Agents, Regional Agents                           │
└──────────────────────────────────────────────────────────────────┘
         │
         │  Serves
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      TENANT DASHBOARD                            │
│  Business operations · POS · Restaurant · Hotel · Workshop       │
│  URL: /dashboard, /*, etc.                                       │
│  Users: Tenant business owners, staff, cashiers                  │
└──────────────────────────────────────────────────────────────────┘
```

**Critical rule:** Tenants cannot sign up directly. Every tenant must come through an agent. The BOS website displays verified agents per region for prospective customers to contact.

---

## 2. User Roles & Permissions

### 2.1 Global Admin Portal Roles

| Role | Code | Description |
|------|------|-------------|
| **Super Admin** | `PLATFORM_SUPER_ADMIN` | Full access to all platform features. Can create other admins. |
| **Platform Admin** | `PLATFORM_ADMIN` | Full access except creating other Super Admins. |
| **Finance Admin** | `PLATFORM_FINANCE` | Billing, commissions, payouts, rate governance. Read-only on agents and tenants. |
| **Agent Manager** | `PLATFORM_AGENT_MANAGER` | Manages agents: registration, promotion, suspension, termination. Read-only on billing. |
| **Support Staff** | `PLATFORM_SUPPORT` | Tenant and agent support tickets. Read-only on everything else. |
| **Viewer** | `PLATFORM_VIEWER` | Read-only access to all dashboards and reports. No write actions. |

### 2.2 Global Admin Permission Matrix

| Feature Area | Super Admin | Admin | Finance | Agent Mgr | Support | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Dashboard (view) | YES | YES | YES | YES | YES | YES |
| Engine catalog (manage) | YES | YES | — | — | — | — |
| Combos (create/edit/deactivate) | YES | YES | — | — | — | — |
| Plan Builder (configure pricing) | YES | YES | YES | — | — | — |
| Billing & Tax Governance | YES | YES | YES | — | — | VIEW |
| Trial Policy (set/update) | YES | YES | YES | — | — | VIEW |
| Active Trials (manage) | YES | YES | YES | — | — | VIEW |
| Expansion Gates (configure) | YES | YES | YES | — | — | VIEW |
| Agent Registration | YES | YES | — | YES | — | — |
| Agent Promotion (Remote → Regional) | YES | YES | — | YES | — | — |
| Agent Suspension / Termination | YES | YES | — | YES | — | — |
| Agent Agreements (view/edit) | YES | YES | YES | YES | — | VIEW |
| Commission Ranges (set) | YES | YES | YES | — | — | VIEW |
| Commission Payouts (approve) | YES | YES | YES | — | — | — |
| Promotions (create platform promos) | YES | YES | YES | — | — | VIEW |
| Promotion Cost-Share Requests | YES | YES | YES | — | — | VIEW |
| Subscriptions (manage) | YES | YES | YES | — | YES | VIEW |
| Tenant Transfers (arbitrate) | YES | YES | — | YES | YES | — |
| Support Tickets (L2) | YES | YES | — | — | YES | — |
| Onboarding Policy (set days) | YES | YES | — | — | — | — |
| Platform Users (create/manage) | YES | — | — | — | — | — |
| Audit Log (view) | YES | YES | YES | YES | YES | YES |

### 2.3 Agent Portal Roles

| Role | Code | Description |
|------|------|-------------|
| **Agent Owner** | `AGENT_OWNER` | Full access to their agent portal. The registered agent. |
| **Agent Staff** | `AGENT_STAFF` | Can manage tenants and support tickets. Cannot view financials or agreements. |
| **Agent Viewer** | `AGENT_VIEWER` | Read-only access to agent dashboard. |

### 2.4 Agent Permission Matrix

| Feature Area | Owner | Staff | Viewer |
|---|:---:|:---:|:---:|
| Agent Dashboard (view) | YES | YES | YES |
| Onboard Tenant | YES | YES | — |
| My Tenants (view) | YES | YES | YES |
| My Tenants (support actions) | YES | YES | — |
| Commission History | YES | — | — |
| Payout Requests | YES | — | — |
| My Promotions (create) | YES | — | — |
| Cost-Share Requests (submit) | YES | — | — |
| Support Tickets (L1) | YES | YES | — |
| Compliance Docs (Regional only) | YES | — | — |
| Training Materials | YES | YES | YES |
| My Agreement (view) | YES | — | — |
| Agent Staff (invite/manage) | YES | — | — |
| Market Intelligence | YES | YES | YES |

---

## 3. Global Admin Portal

### 3.1 Dashboard (`/platform/dashboard`)

**Purpose:** Overview of the entire BOS platform at a glance.

**KPI Cards:**

| Metric | Source | Description |
|--------|--------|-------------|
| Total Active Tenants | Subscription store | Count of tenants with status ACTIVE or TRIAL |
| Tenants on Trial | Subscription store | Count of TRIAL status subscriptions |
| Active Agents | Agent store | Count of agents with status ACTIVE |
| Global Agents | Agent store | Count of type GLOBAL with status ACTIVE |
| Regional Agents | Agent store | Count of type REGIONAL with status ACTIVE |
| Active Promotions | Promotion store | Count of promos with status ACTIVE |
| Monthly Revenue | Billing store | Sum of all paid subscriptions this month |
| Trial Conversion Rate | Subscription store | Converted trials / total expired trials |
| Pending Payouts | Commission store | Total unpaid agent commissions |
| Pending Transfers | Transfer store | Tenant transfer requests awaiting decision |

**Quick Actions:**

| Action | Target Page | Description |
|--------|-------------|-------------|
| Register New Agent | `/platform/agents` | Register a new Global Agent |
| Create Promotion | `/platform/promotions` | Create a platform-wide promotion |
| Define New Combo | `/platform/combos` | Create a new engine combo |
| Review Payouts | `/platform/agents` → Payouts tab | Approve pending commission payouts |

**Permissions:** All roles can view. Quick actions visible based on write permissions.

---

### 3.2 Engine Catalog (`/platform/engines`)

**Purpose:** View and register all BOS backend engines in the SaaS catalog.

**Features:**
- Display all 22 backend engines (4 FREE, 18 PAID)
- Show registration status (registered in SaaS catalog or not)
- Register individual engine or "Register All" bulk action
- Cannot unregister an engine that is part of an active combo

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN` — full access. Others — read-only.

---

### 3.3 Combos (`/platform/combos`)

**Purpose:** Define engine combo packages that agents offer to tenants.

**Features:**
- List all combos with status (ACTIVE, INACTIVE)
- Create new combo: name, description, business model (B2B/B2C/BOTH), select paid engines
- Edit existing combo (name, description, engines)
- Set regional rate: combo × region → monthly amount in local currency
- Deactivate combo (existing tenants unaffected, no new signups)

**Business rules:**
- A combo must include at least one paid engine
- Free engines (cash, documents, reporting, customer) are automatically included in every combo
- Deactivation is soft — combo remains in system for existing tenants

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN` — full access. Others — read-only.

---

### 3.4 Plan Builder (`/platform/pricing`)

**Purpose:** Configure and preview pricing for tenants. This is the pricing calculator that shows how the 4-dimension pricing model works.

**Pricing dimensions:**

| Dimension | Description | Configured By |
|-----------|-------------|---------------|
| Service Category | Business type → engine package | Tenant selects at onboarding |
| Document Volume | Monthly documents across all engines | Usage-tracked, billed per tier |
| AI Token Usage | AI feature consumption per month | Usage-tracked, billed per tier |
| Branch Count | Number of business branches | Set at onboarding, adjustable |

**Document Volume Tiers (set by Global Admin per region):**

| Tier | Range | Description |
|------|-------|-------------|
| Tier 1 | 0 – 150 documents/month | Starter |
| Tier 2 | 151 – 500 documents/month | Growing |
| Tier 3 | 501 – 2,000 documents/month | Business |
| Tier 4 | 2,000+ documents/month | Enterprise |

**AI Token Tiers (set by Global Admin per region):**

| Tier | Range | Description |
|------|-------|-------------|
| Tier 1 | 0 – 2,000 tokens/month | Basic |
| Tier 2 | 2,001 – 10,000 tokens/month | Standard |
| Tier 3 | 10,000+ tokens/month | Power |

**Branch Multiplier:**

| Range | Multiplier |
|-------|------------|
| 1 – 2 branches | 1.0× |
| 3 – 5 branches | 0.9× per branch (10% volume discount) |
| 6 – 10 branches | 0.85× per branch |
| 11+ branches | 0.8× per branch |

**Pricing formula:**
```
Monthly Price = (CategoryBasePrice + DocTierPrice + AITierPrice) × Branches × BranchMultiplier
```

All prices are set per region by Global Admin. The Plan Builder page lets admins preview pricing for any combination and region.

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — full access. Others — read-only.

---

### 3.5 Billing & Tax Governance (`/platform/rates`)

**Purpose:** Manage pricing doctrine, tax rules, rate changes, and billing policy.

**Tabs:**

#### Tab 1: Billing Doctrine
Displays the immutable billing rules:
- Billing country determines tax (not branch footprint)
- B2B → Reverse Charge where applicable
- B2C → VAT always charged
- Safe default: charge VAT when verification is pending, correct later via credit note
- No silent edits or backdating — corrections via credit note + adjustment invoice only
- Rate changes require 90-day advance notice
- Increases >25% trigger double notification
- 4-gate region expansion required before country goes live

#### Tab 2: Tax Rules by Country
Table showing per-country tax configuration:
- VAT/GST rate
- Digital services tax rate
- Tax name (VAT, TVA, GST)
- B2B reverse charge availability
- Registration requirements
- Ability to edit tax rules per country

#### Tab 3: Check Effective Rate
Look up the current effective rate for a specific tenant:
- Input: Business ID
- Output: Monthly amount, currency, rate guaranteed until date, trial/active status

#### Tab 4: Publish Rate Change
Publish a rate change with governance controls:
- Select combo and region
- Enter old amount and new amount
- Effective date (minimum 90 days from today)
- System enforces: increases >25% trigger elevated notifications to all affected tenants

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — full access. `PLATFORM_VIEWER` — read-only.

---

### 3.6 Trial Policy (`/platform/trial-policy`)

**Purpose:** Set platform-wide trial policy. Affects new tenants only — existing trials are immutable.

**Fields:**

| Field | Description | Default |
|-------|-------------|---------|
| Default Trial Days | Trial duration for new tenants | 180 |
| Max Trial Days | Maximum including any bonuses | 365 |
| Grace Period Days | Days after trial expires before suspension | 14 |
| Rate Notice Days | Minimum notice before rate changes (min 90) | 90 |

**Business rules:**
- Changes only affect future trials
- Existing trial agreements are immutable (locked at creation time)
- Trial agreement stores a rate snapshot — tenant pays this rate for the first billing cycle

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — full access. Others — read-only.

---

### 3.7 Active Trials (`/platform/trials`)

**Purpose:** Search and manage active trial agreements.

**Features:**
- Search by Business ID
- View trial agreement details: trial days, bonus days, rate snapshot, billing start date, combo
- Extend trial (add days, must not exceed max)
- Convert trial to paying subscription
- All actions are logged in audit trail

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — full access. Others — read-only.

---

### 3.8 Expansion Gates (`/platform/expansion-gates`)

**Purpose:** 4-gate readiness check before a country goes live for billing.

**Gates:**

| Gate | Requirement | Who Configures |
|------|-------------|----------------|
| 1. Country Logic Locked | Currency, affordability weight, USD conversion rate | Global Admin |
| 2. B2B/B2C Qualification Locked | Tax rules, reverse charge, registration requirements | Global Admin (from agent compliance docs) |
| 3. Registration Path Exists | Digital tax registration or subsidiary pathway documented | Regional Agent submits, Admin verifies |
| 4. Reporting & Correction Path | Credit note, adjustment invoice, tax correction workflows | Global Admin |

**Display:** Grid showing all countries with pass/fail per gate and overall status (LIVE / PARTIAL / BLOCKED). Click a country to see gate details.

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — full access. Others — read-only.

---

### 3.9 Agent Management (`/platform/agents`)

**Purpose:** Register, manage, promote, suspend, and terminate agents. Replaces the old Resellers and Referrals pages.

#### Tab 1: Agent List

| Column | Description |
|--------|-------------|
| Agent Name | Display name |
| Type | GLOBAL or REGIONAL |
| Territory | Region/country (Regional agents only) |
| Status | ACTIVE, PROBATION, SUSPENDED, TERMINATED |
| Tenants | Count of attributed tenants |
| Commission Range | Current tier based on tenant count |
| Joined | Date registered |

**Filters:** By type, status, territory.

#### Tab 2: Register Agent

**Form fields:**

| Field | Required | Description |
|-------|----------|-------------|
| Agent Name | YES | Individual or company name |
| Contact Email | YES | Primary contact |
| Contact Phone | YES | Primary phone |
| Country | YES | Agent's country of residence/operation |
| Agent Type | YES | GLOBAL (default for new agents) |
| Commission Range Override | NO | If blank, uses default volume-based ranges |
| Notes | NO | Internal notes |

**On registration:**
- Agent starts in PROBATION status
- Probation period: 90 days
- Must onboard minimum 5 tenants during probation
- After probation: automatically promoted to ACTIVE
- If probation fails: Admin can extend or terminate

#### Tab 3: Promote to Regional

**Only for ACTIVE Global Agents.**

**Additional fields:**

| Field | Required | Description |
|-------|----------|-------------|
| Territory | YES | Country or region this agent will cover |
| Regional Override Share | YES | Additional % commission on all tenants in their territory (e.g., 5-10%) |
| Office Address | YES | Physical office address (required for Regional) |
| Compliance Obligations | YES | Checkbox acknowledgment of regional legal obligations |
| Agreement Start Date | YES | When regional agreement begins |
| Agreement Duration | YES | Months or years |

**Business rules:**
- Regional override applies ONLY to tenants within the assigned territory
- On tenants outside their territory, Regional Agent earns standard commission (same as Global)
- Multiple Regional Agents can exist for the same country (non-exclusive)
- Regional Agent agreement is a new contract on top of the existing agent agreement

#### Tab 4: Commission Settings

**Volume-based commission ranges (set by Global Admin):**

| Setting | Description |
|---------|-------------|
| Range tiers | Define tenant count ranges (e.g., 1-20, 21-50, 51-100, 100+) |
| Commission rate per tier | Percentage for each range |
| Regional override range | Min/max % for regional override share |
| Residual rate | Permanent small % when tenant transfers away from agent |
| First-year bonus | Additional % during tenant's first 12 months (if any) |

#### Tab 5: Payouts

**Commission payout management:**
- List of pending payouts per agent
- Payout calculation: Agent commission = tenant payment × commission rate
- **Critical rule:** Admin collects payment from tenant FIRST, then pays agent
- Payout status: ACCRUED → APPROVED → PAID
- Payout methods: M-Pesa, Mobile Money, Bank Transfer
- Payout frequency: Monthly (configurable per agent agreement)
- Each payout generates a payout record with: agent ID, period, amount, method, reference

#### Tab 6: Agreements

- List all agent agreements (current and historical)
- View agreement terms: commission rates, territory, obligations
- Agreement status: DRAFT → ACTIVE → EXPIRED → TERMINATED
- Download agreement as PDF

#### Tab 7: Promotion Cost-Share Requests

- Agent submits a request to share promotion costs with platform
- Request includes: promotion description, cost amount, requested platform share
- Admin can: APPROVE (as-is), ADJUST (change amounts), REJECT
- Decision is recorded and visible to both parties
- Approved cost-sharing adjusts platform margin, not agent margin

#### Tab 8: Tenant Transfers

- List pending transfer requests
- Show: tenant, current agent, requested new agent, reason, date
- Admin actions: APPROVE transfer, DENY transfer
- On approval:
  - Original agent continues earning until agreement period expires
  - After expiry, new agent gets full commission
  - Residual share (set by Admin at original onboarding) continues to original agent permanently
- All transfer records are permanent and auditable

#### Tab 9: Agent Suspension / Termination

**Suspension:**
- Agent cannot access dashboard
- Agent's tenants are NOT affected — service continues
- Agent's commission continues to accrue (frozen, not paid out until reinstated)
- Can be reinstated by Admin

**Termination:**
- Agent's tenants are notified
- Tenants choose a new agent (or Admin assigns one)
- New agent inherits full commission share
- Terminated agent loses all future commission
- Accrued unpaid commission up to termination date is paid out
- Termination is permanent — cannot be reversed

**Permissions:**

| Action | Super Admin | Admin | Agent Mgr | Finance | Support | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| View agent list | YES | YES | YES | YES | YES | YES |
| Register agent | YES | YES | YES | — | — | — |
| Promote to Regional | YES | YES | YES | — | — | — |
| Set commission ranges | YES | YES | — | YES | — | — |
| Approve payouts | YES | YES | — | YES | — | — |
| Manage agreements | YES | YES | YES | YES | — | — |
| Cost-share decisions | YES | YES | — | YES | — | — |
| Arbitrate transfers | YES | YES | YES | — | YES | — |
| Suspend agent | YES | YES | YES | — | — | — |
| Terminate agent | YES | YES | — | — | — | — |

---

### 3.10 Promotions (`/platform/promotions`)

**Purpose:** Create and manage platform-wide promotions.

**Promotion types:**

| Type | Description | Who Bears Cost |
|------|-------------|----------------|
| DISCOUNT | Percentage off monthly rate | Platform — agent margin NOT affected |
| CREDIT | Account credit in local currency | Platform — agent margin NOT affected |
| EXTENDED_TRIAL | Extra trial days | Platform — no direct cost, delayed revenue |
| ENGINE_BONUS | Free engine for limited time | Platform |
| BUNDLE_DISCOUNT | Discount for specific engine bundle | Platform |

**Features:**
- Create promotion: type, code, value, start/end date, max redemptions, applicable regions
- View active/expired/upcoming promotions
- Redeem a promo code for a tenant
- Track redemption count and remaining uses

**Critical rule:** Platform-created promotions are funded by the platform. Agent commission is calculated on the ORIGINAL price, not the discounted price. The platform absorbs the discount.

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — full access. Others — read-only.

---

### 3.11 Subscriptions (`/platform/subscriptions`)

**Purpose:** Search and manage tenant subscriptions.

**Features:**
- Search by Business ID
- View subscription details: status, combo, plan, billing dates, renewal count, attributed agent
- Actions:
  - Activate (trial → paying) — triggers first billing
  - Cancel — permanent, cannot be reversed
  - Change combo — switch engine package
  - Start trial — create new trial subscription (must be through an agent)

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN`, `PLATFORM_FINANCE` — manage. `PLATFORM_SUPPORT` — view + activate/cancel only. `PLATFORM_VIEWER` — read-only.

---

### 3.12 Onboarding Policy (`/platform/settings/onboarding`)

**Purpose:** Configure onboarding and training policy for new tenants.

**Settings:**

| Setting | Description | Default |
|---------|-------------|---------|
| Free Onboarding Days | Number of days of free onboarding/training included | 30 |
| Onboarding Includes | What's covered: setup assistance, data migration, basic training | All |
| Extended Onboarding Rate | Daily rate for onboarding beyond free period | Set per region |
| Onboarding Provider | Who delivers: Platform team (not agents) | Platform |

**Critical rule:** First onboarding/training for new tenants is FREE. The duration is set by Global Admin. Agents receive NOTHING for onboarding — it is a platform responsibility. Agents only earn commission after the tenant completes payment and the platform collects.

**Permissions:** `PLATFORM_SUPER_ADMIN`, `PLATFORM_ADMIN` only.

---

### 3.13 Audit Log (`/platform/audit`)

**Purpose:** Immutable log of all administrative actions.

**Logged events:**
- Agent registered / promoted / suspended / terminated
- Commission ranges changed
- Payout approved / executed
- Promotion created / redeemed
- Rate change published
- Trial extended / converted
- Subscription activated / cancelled / combo changed
- Tenant transfer approved / denied
- Tax rules updated
- Expansion gate status changed
- Agreement created / modified
- Cost-share request approved / adjusted / rejected

**Fields per entry:** timestamp, actor (who did it), action, target, details, IP address.

**Permissions:** All roles can view. No one can edit or delete.

---

## 4. Agent Portal

### 4.1 Agent Dashboard (`/agent/dashboard`)

**Purpose:** Agent's home screen — overview of their business.

**KPI Cards:**

| Metric | Description |
|--------|-------------|
| My Total Tenants | Count of tenants attributed to this agent |
| Active Tenants | Tenants with ACTIVE or TRIAL subscriptions |
| This Month's Revenue | Total payments from my tenants this month |
| My Commission (This Month) | Calculated commission for current month |
| Pending Payout | Accrued commission not yet paid out |
| Tenants on Trial | My tenants still in trial period |
| Trial Conversion Rate | My converted / total expired trials |
| Regional Override Tenants | (Regional agents only) Tenants in my territory from other agents |

**Notifications area:**
- New tenant signup confirmations
- Commission payout notifications
- Platform promotion announcements
- Transfer requests requiring action
- Compliance document status updates (Regional)

**Permissions:** `AGENT_OWNER` — full view. `AGENT_STAFF` — tenants and support metrics only (no financials). `AGENT_VIEWER` — read-only.

---

### 4.2 Onboard Tenant (`/agent/onboard`)

**Purpose:** Sign up a new tenant under this agent's attribution.

**Form (multi-step wizard):**

**Step 1: Business Information**

| Field | Required | Description |
|-------|----------|-------------|
| Business Name | YES | Tenant's business name |
| Business Type | YES | Retail, Restaurant, Hotel, Workshop, Mixed, Services |
| Country | YES | Business headquarters country |
| City | YES | City of operation |
| Contact Name | YES | Primary contact person |
| Contact Email | YES | Primary email |
| Contact Phone | YES | Primary phone |

**Step 2: Plan Selection**

| Field | Required | Description |
|-------|----------|-------------|
| Service Category | YES | Matches business type — auto-suggested |
| Estimated Document Volume | YES | Select tier (affects pricing preview) |
| AI Usage | YES | None / Basic / Advanced |
| Number of Branches | YES | 1+ |
| Billing Model | YES | HQ Pays / Branch Pays |
| Buyer Type | YES | B2C / B2B (if B2B: tax registration number) |

**Step 3: Review & Confirm**
- Shows pricing summary: base + document tier + AI tier × branches × multiplier
- Shows trial period (from current platform policy)
- Shows billing start date
- Agent confirms onboarding
- System creates: tenant account + subscription (TRIAL) + agent attribution

**After onboarding:**
- Tenant receives welcome email with login credentials
- Free onboarding/training period begins (duration set by Global Admin)
- Agent is attributed — commission starts accruing when tenant starts paying

**Permissions:** `AGENT_OWNER`, `AGENT_STAFF` — can onboard. `AGENT_VIEWER` — cannot.

---

### 4.3 My Tenants (`/agent/tenants`)

**Purpose:** View and manage all tenants attributed to this agent.

**Table columns:**

| Column | Description |
|--------|-------------|
| Business Name | Tenant business name |
| Business Type | Retail, Hotel, etc. |
| Country | Tenant country |
| Status | TRIAL, ACTIVE, SUSPENDED, CANCELLED |
| Monthly Amount | Current subscription amount |
| My Commission | Agent's commission on this tenant |
| Onboarding Date | When tenant was onboarded |
| Trial Expires | When trial ends (if TRIAL) |
| Last Active | Last activity timestamp |

**Actions per tenant:**
- View details (full tenant info, usage stats, billing history)
- Create support ticket (L1)
- Escalate to platform (L2)

**Filters:** By status, business type, country, date range.

**Permissions:** `AGENT_OWNER`, `AGENT_STAFF` — full view + actions. `AGENT_VIEWER` — view only.

---

### 4.4 Commission History (`/agent/commissions`)

**Purpose:** View commission earnings and payout history.

**Sections:**

#### Current Month Summary
| Metric | Description |
|--------|-------------|
| Gross Tenant Payments | Total payments from my tenants this month |
| My Commission Rate | Current rate based on tenant volume |
| Earned Commission | Gross × rate |
| Regional Override | (Regional only) Override earnings from territory tenants |
| Total Earned | Commission + override |
| Status | ACCRUING / PENDING APPROVAL / APPROVED / PAID |

#### Monthly History Table
| Column | Description |
|--------|-------------|
| Month | Billing month |
| Tenant Payments | Total collected from my tenants |
| Commission Rate | Rate that applied |
| Commission Amount | Calculated amount |
| Override Amount | Regional override (if applicable) |
| Total | Commission + override |
| Payout Status | ACCRUED → APPROVED → PAID |
| Payout Date | When paid out |
| Payout Method | M-Pesa, Bank Transfer, etc. |
| Reference | Payment reference number |

#### Request Payout
- Agent can request payout of accrued commission
- Request goes to Global Admin for approval
- Admin approves → system processes payout
- **Critical rule:** Platform collects from tenant FIRST, then pays agent. Agent never receives money before tenant pays.

**Permissions:** `AGENT_OWNER` only. Staff and viewers cannot see financial data.

---

### 4.5 My Promotions (`/agent/promotions`)

**Purpose:** Manage agent's own promotions and request cost-sharing from platform.

**Sections:**

#### My Active Promotions
- Agent can create promotions from their own margin
- Types: discount (% off), free trial extension, bonus training
- Agent sets: promo code, value, duration, max uses
- **Limits:** Cannot exceed the discount authority limits set by Global Admin (e.g., max 10% discount without approval)

#### Request Cost-Share from Platform
- Agent submits a request for platform to share promotion costs
- Form fields:
  - Promotion description
  - Total cost
  - Requested platform share (% or fixed amount)
  - Justification (why this helps the market)
- Status: PENDING → APPROVED / ADJUSTED / REJECTED
- If APPROVED: platform absorbs their share, agent absorbs remainder
- If ADJUSTED: platform proposes different terms, agent can accept or withdraw
- If REJECTED: agent can still run the promo at their own cost

**Permissions:** `AGENT_OWNER` only.

---

### 4.6 Support Tickets (`/agent/support`)

**Purpose:** Manage L1 support tickets from tenants and escalate to platform when needed.

**L1 tickets (Agent handles):**

| Category | Examples |
|----------|----------|
| Onboarding | Setup questions, initial configuration |
| Training | How to use features, best practices |
| Billing | Subscription questions, payment issues |
| General Usage | Day-to-day operation help |

**Ticket fields:**
- Tenant (select from my tenants)
- Category
- Subject
- Description
- Priority: LOW / MEDIUM / HIGH / URGENT
- Status: OPEN → IN_PROGRESS → RESOLVED / ESCALATED

**Escalation to L2 (Platform):**
- Agent clicks "Escalate to Platform"
- Adds escalation reason
- Ticket moves to platform support queue
- Agent and tenant can see status updates from platform

**Permissions:** `AGENT_OWNER`, `AGENT_STAFF` — full access. `AGENT_VIEWER` — cannot create or respond.

---

### 4.7 Compliance (Regional Agents Only) (`/agent/compliance`)

**Purpose:** Submit and track compliance documentation for the agent's territory.

**Document types:**

| Document | Description | Frequency |
|----------|-------------|-----------|
| Tax Rules Summary | Local VAT/GST rates, registration requirements | On change |
| Business Regulations | Local business licensing requirements | Annual |
| Data Residency | Data storage requirements in the region | On change |
| Payment Processor Requirements | Approved local payment methods | On change |
| Regulatory Updates | New laws or regulation changes | As needed |

**Workflow:**
```
Agent researches local laws
    → Agent uploads documentation + summary
        → Platform legal team reviews
            → Status: PENDING → UNDER_REVIEW → APPROVED / REJECTED / REVISION_NEEDED
                → If APPROVED: Platform implements in system
                    → Agent confirms implementation matches local reality
```

**Critical rule:** No law enters the system directly through agent submission. Platform always verifies and implements independently. This limits Global Admin's liability.

**Permissions:** `AGENT_OWNER` only (Regional agents only — not visible for Global agents).

---

### 4.8 Training (`/agent/training`)

**Purpose:** Product knowledge and sales materials provided by the platform.

**Content categories:**

| Category | Description |
|----------|-------------|
| Product Training | How each engine works, feature walkthroughs |
| Sales Training | How to pitch BOS, competitive positioning |
| Onboarding Guides | Step-by-step tenant onboarding procedures |
| Compliance Guides | Regional compliance requirements checklists |
| Release Notes | New features, updates, changes |
| Marketing Materials | Brochures, one-pagers, demo videos |

**Permissions:** All agent roles can view.

---

### 4.9 My Agreement (`/agent/agreement`)

**Purpose:** View the agent's current agreement terms.

**Displayed information:**

| Field | Description |
|-------|-------------|
| Agreement ID | Unique reference |
| Agent Type | GLOBAL or REGIONAL |
| Status | ACTIVE, EXPIRED |
| Start Date | When agreement began |
| Duration | Agreement term |
| Expiry Date | When agreement ends |
| Commission Rate | Current tier and rate |
| Regional Override | (Regional only) Override % and territory |
| Residual Rate | Permanent % after tenant transfer |
| Territory | (Regional only) Assigned region |
| Obligations | List of agent's obligations |
| Terms | Full agreement text |

**Actions:**
- Download agreement as PDF
- Request amendment (creates a request to Global Admin)

**Permissions:** `AGENT_OWNER` only.

---

### 4.10 Market Intelligence (`/agent/market`)

**Purpose:** Anonymized market data for the agent's operating regions.

**Available data:**

| Metric | Scope | Detail Level |
|--------|-------|-------------|
| Total Tenants in Region | Agent's territory (or country) | Count only |
| Market Growth Rate | Monthly % change in tenant count | Trend |
| Business Type Distribution | % breakdown by business type | Aggregate |
| Average Revenue per Tenant | For the region | Average only |
| Churn Rate | Regional tenant churn | Percentage |

**NOT shown (privacy protection):**
- Individual tenant names or details
- Other agents' client lists
- Other agents' commission data
- Individual tenant revenue

**Permissions:** All agent roles can view.

---

## 5. Pricing Model

### 5.1 Pricing Dimensions

```
Monthly Price = (CategoryBase + DocumentTier + AITier) × Branches × BranchMultiplier
```

All prices are set by Global Admin per region in local currency.

### 5.2 Service Categories (Engine Packages)

| Category | Included Paid Engines | Use Case |
|----------|----------------------|----------|
| Retail | retail, inventory, procurement | Shop, duka, supermarket |
| Restaurant | restaurant, inventory | Restaurant, bar, BBQ, cafe |
| Hotel | hotel_reservation, hotel_folio, hotel_property, hotel_housekeeping | Hotel, lodge, guest house |
| Workshop | workshop, inventory, procurement | Fabrication, garage, fundi |
| Services | accounting, hr | Professional services, consultancy |
| Mixed | Combination of above | Hotel + Restaurant, Retail + Workshop |

Every category automatically includes FREE engines: cash, documents, reporting, customer.

### 5.3 Document Volume Tiers

| Tier | Documents/Month | Description |
|------|----------------|-------------|
| 1 | 0 – 150 | Starter — small business |
| 2 | 151 – 500 | Growing — medium business |
| 3 | 501 – 2,000 | Business — active operation |
| 4 | 2,000+ | Enterprise — high volume |

### 5.4 AI Usage Tiers

| Tier | Tokens/Month | Description |
|------|-------------|-------------|
| 1 | 0 – 2,000 | Basic — reports, simple automation |
| 2 | 2,001 – 10,000 | Standard — predictions, analysis |
| 3 | 10,000+ | Power — full AI suite |

### 5.5 Branch Multiplier

| Branches | Multiplier | Effective Discount |
|----------|------------|-------------------|
| 1 – 2 | 1.0× | None |
| 3 – 5 | 0.9× per branch | 10% volume discount |
| 6 – 10 | 0.85× per branch | 15% volume discount |
| 11+ | 0.8× per branch | 20% volume discount |

### 5.6 Regional Pricing Authority

- Global Admin sets all prices per region
- Prices are in local currency
- Internal calculation uses: Global Reference Price × Region Affordability Weight × USD-to-Local conversion
- Affordability weights are INTERNAL — never shown to agents or tenants
- Agents can advise on local market conditions but cannot set prices

---

## 6. Agent Commission & Payout

### 6.1 Commission Flow

```
Tenant uses BOS
    → Tenant's subscription payment is due
        → Platform billing system charges tenant
            → Payment collected into platform account
                → Commission calculated: payment × agent's rate
                    → Commission accrues to agent's balance
                        → Agent requests payout (or auto-payout on schedule)
                            → Global Admin approves payout
                                → Payout processed (M-Pesa / Bank / Mobile Money)
```

**Critical rule:** Agent NEVER receives money before the platform collects from the tenant. Commission is calculated and accrued AFTER successful payment collection.

### 6.2 Volume-Based Commission Ranges

| Tenant Count | Commission Rate |
|---|---|
| 1 – 20 active tenants | 20% |
| 21 – 50 active tenants | 25% |
| 51 – 100 active tenants | 28% |
| 100+ active tenants | 30% |

These ranges are configurable by Global Admin and apply to all agents uniformly.

### 6.3 Regional Override (Regional Agents Only)

- Set per agreement (typically 5-10%)
- Applies to ALL tenants within the Regional Agent's territory, regardless of which agent brought them
- If a Global Agent brings a tenant in a Regional Agent's territory:
  - Global Agent gets their commission (e.g., 25%)
  - Regional Agent gets their override (e.g., 7%)
  - Platform gets remainder (68%)
- If Regional Agent brings a tenant in their own territory:
  - They get commission (25%) + override (7%) = 32%
  - Platform gets 68%

### 6.4 Transfer Residual

When a tenant transfers from Agent A to Agent B:
- Agent A continues earning full commission until the original agreement period expires
- After expiry, Agent B gets full commission
- Agent A receives a permanent residual share (set by Global Admin at onboarding, typically 2-5%)
- This residual is deducted from Agent B's commission, not from the platform

### 6.5 Promotion Impact on Commission

| Promotion Source | Commission Calculation |
|---|---|
| Platform promotion | Commission calculated on ORIGINAL price (before discount). Platform absorbs discount. |
| Agent promotion (own margin) | Commission calculated on DISCOUNTED price. Agent absorbs discount from their share. |
| Cost-shared promotion | Commission calculated on ORIGINAL price. Shared cost deducted per agreement. |

---

## 7. Tenant Lifecycle

### 7.1 Signup Flow

```
Prospective customer visits BOS website
    → Sees list of verified agents per region
        → Contacts an agent
            → Agent onboards tenant via Agent Portal
                → Tenant account created (TRIAL status)
                    → Free onboarding period begins (days set by Global Admin)
                        → Trial period runs (days from trial policy)
                            → Trial expires → tenant pays → ACTIVE
                                → Agent starts earning commission
```

**No direct signups.** Every tenant must come through an agent.

### 7.2 Agent Switch

```
Tenant requests to leave Agent A
    ├─► Tenant provides reason to Agent A
    │     └─► Agent A gives "Go-Ahead"
    │           └─► Transfer completes immediately
    │
    └─► If Agent A refuses:
          └─► Tenant escalates to Global Admin
                └─► Global Admin reviews and decides
                      └─► If approved:
                            ├─ Agent A earns until agreement period expires
                            ├─ Residual share continues permanently
                            └─ Agent B starts earning after agreement period
```

### 7.3 Tenant Cancellation

- Tenant can cancel subscription at any time
- Cancellation is permanent
- Agent stops earning commission on cancelled tenant
- Tenant data retained per data retention policy (typically 90 days)

---

## 8. Compliance Model

### 8.1 Responsibility Split

| Area | Responsible Party |
|------|-------------------|
| Local tax laws research | Regional Agent |
| Business regulation awareness | Regional Agent |
| Compliance documentation | Regional Agent submits |
| Verification of compliance docs | Global Admin legal team |
| System implementation | Global Admin engineering |
| Final approval | Global Admin |
| Ongoing monitoring | Both (agent monitors, platform audits) |

### 8.2 Workflow

```
Regional Agent studies local laws
    → Agent uploads compliance summary + supporting documents
        → Global Admin legal reviews
            → APPROVED: Platform implements (tax rules, payment processors, etc.)
            → REJECTED: Agent revises and resubmits
            → REVISION_NEEDED: Specific changes requested
                → Agent confirms implementation matches local requirements
```

### 8.3 Liability Protection

- Global Admin is the **technology provider and system regulator**
- Regional Agent holds **primary compliance responsibility** for their territory
- No law enters the system directly from agent — always verified by platform
- Agent agreements include compliance obligations and indemnification clauses
- Platform maintains right to audit agent compliance at any time

---

## 9. SaaS Compliance Standard

BOS operates under a **service-from-origin-country** model:

| Principle | Implementation |
|-----------|---------------|
| **No Permanent Establishment** | No offices in customer countries. Regional Agents are independent contractors, not branch offices or subsidiaries. |
| **B2B Reverse Charge** | Business customers with verified tax registration handle their own VAT. Platform issues invoices without VAT (reverse charge notation). |
| **B2C VAT Collection** | Individual customers are charged VAT at the rate of their billing country. Platform collects and remits. |
| **EU OSS (future)** | When EU customer thresholds are reached, One-Stop Shop registration for simplified VAT compliance. |
| **GDPR-level Privacy** | Applied globally (not just EU). All tenant and customer data meets GDPR standards. |
| **Digital Tax Systems** | Dashboard designed to plug in country-specific digital tax systems as BOS expands. |
| **Safe Default** | When B2B/B2C status is unclear: charge VAT provisionally, verify later, issue credit note if overpaid. |

---

## 10. Data & Privacy

### 10.1 Data Visibility Rules

| Data | Global Admin | Agent (own tenants) | Agent (other tenants) |
|------|:---:|:---:|:---:|
| Tenant business name | YES | YES | NO |
| Tenant contact details | YES | YES | NO |
| Tenant usage data | YES | YES | NO |
| Tenant billing amount | YES | YES | NO |
| Tenant transaction data | YES | NO | NO |
| Other agent's client list | YES | NO | NO |
| Other agent's commission | YES | NO | NO |
| Regional aggregate stats | YES | YES (own region) | NO |
| Agent performance metrics | YES | Own only | NO |

### 10.2 Agent Data Restrictions

- Agents can ONLY see data for tenants attributed to them
- Regional Agents can see aggregated (anonymized) market data for their territory
- Agents cannot export bulk tenant data without platform approval
- Agent's access is immediately revoked upon termination
- All agent portal access is logged in audit trail

---

## Appendix A: Removed Features

The following features are replaced by the Agent model and should be removed from the platform:

| Feature | Replacement |
|---------|-------------|
| Reseller Program (`/platform/resellers`) | Agent Management (`/platform/agents`) |
| Referral Program (`/platform/referrals`) | Agent-based tenant acquisition |
| Direct tenant signup | All signups through agents |

---

## Appendix B: Future Enhancements (Not in Scope Now)

| Feature | Description | Priority |
|---------|-------------|----------|
| BOS Website Agent Directory | Public page showing verified agents per region | HIGH (needed for tenant acquisition) |
| Agent Mobile App | Mobile version of Agent Portal | MEDIUM |
| White-Label Option | Gold-tier agents can brand the tenant dashboard | LOW |
| Automated Compliance Monitoring | AI-assisted regulation tracking per country | LOW |
| Agent Leaderboard | Gamified performance ranking (opt-in) | LOW |
