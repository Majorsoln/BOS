# BOS Platform Admin Frontend — Implementation Plan
## "Uongozi wa Mfumo" (System Governance)

**Tarehe:** 2026-03-15
**Scope:** Frontend ya utawala wa PLATFORM (sio tenant) — mahali leadership inasimamiia engines, combos, pricing, trials, promotions, referrals, resellers, na subscriptions.

---

## 1. BRAND & DESIGN SYSTEM (Msingi wa Rangi)

### 1.1 Color Palette — CSS Variables

```
Silver  #C4C4C4  →  Main: backgrounds, borders, muted text, cards
Purple  #7851A9  →  Primary: buttons, active nav, links, brand accent
Gold    #D4AF37  →  Accent: highlights, badges, premium, success indicators
```

**Derived shades (auto-generated via Tailwind):**

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `--bos-purple` | #7851A9 | #9B7BC7 | Primary buttons, active states |
| `--bos-purple-light` | #F3EEFA | #2D1F45 | Selected row bg, hover states |
| `--bos-purple-dark` | #5C3D87 | #B494DB | Text on light bg, links |
| `--bos-gold` | #D4AF37 | #E8C84A | Premium badges, revenue highlights |
| `--bos-gold-light` | #FDF8E8 | #3D3418 | Gold badge backgrounds |
| `--bos-silver` | #C4C4C4 | #6B6B6B | Borders, muted text, dividers |
| `--bos-silver-light` | #F5F5F5 | #1A1A1A | Page backgrounds, card fills |
| `--bos-silver-dark` | #8A8A8A | #9E9E9E | Secondary text |

**Status Colors (semantic — hazibadiliki):**

| Status | Color | Usage |
|--------|-------|-------|
| ACTIVE / Success | `#16A34A` (green-600) | Active badges, success toasts |
| TRIAL | `#7851A9` (purple) | Trial badges — matches brand |
| SUSPENDED | `#EA580C` (orange-600) | Warning states |
| CANCELLED / Error | `#DC2626` (red-600) | Destructive actions, errors |
| DEACTIVATED | `#8A8A8A` (silver-dark) | Muted, inactive items |
| PENDING | `#2563EB` (blue-600) | In-progress, awaiting action |
| GOLD tier | `#D4AF37` (gold) | Reseller GOLD badge |
| SILVER tier | `#C4C4C4` (silver) | Reseller SILVER badge |
| BRONZE tier | `#CD7F32` | Reseller BRONZE badge |

### 1.2 Typography

- Headings: `font-semibold`, sizes: page h1 = `text-2xl`, section h2 = `text-lg`, card h3 = `text-base`
- Body: `text-sm` (14px) — default for all content
- Small/muted: `text-xs` with `text-[--bos-silver-dark]`
- Monospace: `font-mono text-xs` for IDs, codes, API keys

### 1.3 Component Upgrades Required

| Component | Current | After |
|-----------|---------|-------|
| **Button** (primary) | `bg-neutral-900` | `bg-[--bos-purple] hover:bg-[--bos-purple-dark]` |
| **Button** (secondary) | `bg-neutral-100` | `bg-[--bos-silver-light] border-[--bos-silver]` |
| **Badge** (success) | `bg-green-*` | stays green (semantic) |
| **Badge** (new: gold) | N/A | `bg-[--bos-gold-light] text-[--bos-gold] border-[--bos-gold]` |
| **Badge** (new: trial) | N/A | `bg-[--bos-purple-light] text-[--bos-purple] border-[--bos-purple]` |
| **Sidebar** | `bg-white border-neutral-200` | `bg-white` with purple active indicator bar |
| **Topbar** | `bg-white` | `bg-white` with subtle gold bottom accent line |
| **Cards** | `border-neutral-200` | `border-[--bos-silver]/50` with hover shadow |
| **Tables** | `border-neutral-200` | `border-[--bos-silver]/30`, purple header accent |
| **Active nav** | `bg-neutral-100 text-neutral-900` | `bg-[--bos-purple-light] text-[--bos-purple] border-l-[--bos-purple]` |

### 1.4 Icons — Switch from Unicode to Lucide

lucide-react tayari imefungwa. Tutabadilisha Unicode symbols zote kwenye sidebar na pages kuwa Lucide icons.

---

## 2. NAVIGATION STRUCTURE — Platform Admin

Sidebar itabadilika kutoka tenant admin kwenda platform admin. Platform admin ina sections hizi:

```
┌─────────────────────────────┐
│  🟣  BOS Platform           │  ← Logo + "Platform" label
├─────────────────────────────┤
│                             │
│  OVERVIEW                   │
│    ▸ Dashboard              │  /platform/dashboard
│                             │
│  ENGINE CATALOG             │
│    ▸ Engines                │  /platform/engines
│    ▸ Combos (Plans)         │  /platform/combos
│    ▸ Pricing                │  /platform/pricing
│                             │
│  TRIALS & BILLING           │
│    ▸ Trial Policy           │  /platform/trial-policy
│    ▸ Active Trials          │  /platform/trials
│    ▸ Rate Governance        │  /platform/rates
│                             │
│  GROWTH                     │
│    ▸ Promotions             │  /platform/promotions
│    ▸ Referrals              │  /platform/referrals
│    ▸ Resellers              │  /platform/resellers
│                             │
│  TENANTS                    │
│    ▸ Subscriptions          │  /platform/subscriptions
│                             │
├─────────────────────────────┤
│  ← Back to Tenant Admin     │  → / (existing pages)
└─────────────────────────────┘
```

**Total: 11 pages mpya**

---

## 3. PAGE-BY-PAGE SPECIFICATION

### 3.1 Platform Dashboard (`/platform/dashboard`)

**Purpose:** Muhtasari wa hali ya mfumo mzima — KPIs za juu na vitendo vya haraka.

**Layout:** Grid ya stat cards (4 columns) + quick action cards (3 columns)

**Stat Cards (row 1):**
| Card | Data Source | Icon |
|------|-----------|------|
| Total Active Tenants | count subscriptions where status=ACTIVE | `Users` |
| Tenants on Trial | count subscriptions where status=TRIAL | `Clock` |
| Active Resellers | count resellers where status=ACTIVE | `Handshake` |
| Active Promotions | count promos where status=ACTIVE | `Tag` |

**Stat Cards (row 2):**
| Card | Data Source | Icon |
|------|-----------|------|
| Engine Combos | count combos where status=ACTIVE | `Layers` |
| Pending Referrals | count referrals where status=PENDING | `Gift` |
| Monthly Revenue (estimate) | sum active subscriptions × rate | `TrendingUp` |
| Trial Conversion Rate | (converted ÷ total trials) × 100 | `BarChart3` |

**Quick Actions (row 3):**
| Card | Link | Description |
|------|------|-------------|
| Define New Combo | /platform/combos | Tengeneza mpango mpya wa engine |
| Create Promotion | /platform/promotions | Unda promo code mpya |
| Register Reseller | /platform/resellers | Sajili wakala mpya |

**Data fetching:**
- GET `/saas/combos` → count active
- GET `/saas/promos` → count active
- GET `/saas/resellers` → count active
- GET `/saas/subscriptions?business_id=*` → hii hatuwezi kwa sasa (endpoint ni per-business). **NOTA:** Tutaonyesha "-" kwa sasa na kuongeza endpoint ya summary baadaye.

---

### 3.2 Engines Page (`/platform/engines`)

**Purpose:** Catalog ya engines zote za BOS. Leadership inaweza kuongeza engine mpya.

**Layout:**
- PageHeader: "Engine Catalog" + Button "Register Engine"
- Grid ya cards (3 columns): kila engine ni card

**Engine Card:**
```
┌──────────────────────────┐
│  ⚙️  retail               │  ← icon + engine_key
│  Retail (POS/Shop)       │  ← display_name
│  ─────────────────────── │
│  Category: [PAID]        │  ← badge (PAID=purple, FREE=gold)
│  Duka, POS, shop mgmt    │  ← description
└──────────────────────────┘
```

**Register Engine Dialog (modal):**
- Fields: `engine_key` (text, required), `display_name` (text, required), `category` (select: FREE/PAID), `description` (textarea)
- Submit → POST `/saas/engines/register`

**Data:** GET `/saas/engines`

---

### 3.3 Combos Page (`/platform/combos`)

**Purpose:** Kuunda na kusimamia engine combos (plans) ambazo tenants wanachagua.

**Layout:**
- PageHeader: "Engine Combos" + Button "Define Combo"
- Table ya combos

**Table Columns:**
| Column | Field | Notes |
|--------|-------|-------|
| Combo Name | `name` | Bold, primary text |
| Slug | `slug` | Monospace, muted |
| Business Model | `business_model` | Badge: B2B=blue, B2C=purple, BOTH=gold |
| Engines | `paid_engines[]` | Comma-joined badges |
| Quotas | `quota` | "5 branches, 20 users" summary |
| Status | `status` | Badge: ACTIVE=green, DEACTIVATED=gray |
| Actions | — | Edit, Set Rate, Deactivate buttons |

**Define Combo Dialog (modal/slide-over):**
- `name` (text, required) — e.g., "BOS Duka"
- `slug` (text, required, auto-generated from name) — e.g., "bos-duka"
- `description` (textarea)
- `business_model` (select: B2B / B2C / BOTH)
- `paid_engines` (multi-select checkboxes from engine catalog, PAID only)
- Quotas section:
  - `max_branches` (number)
  - `max_users` (number)
  - `max_api_calls_per_month` (number)
  - `max_documents_per_month` (number)
- Submit → POST `/saas/combos/define`

**Edit Combo Dialog:**
- Same fields, pre-filled
- Submit → POST `/saas/combos/update`

**Set Rate Dialog (per combo):**
- `region_code` (select: KE, TZ, UG, RW, NG, GH, CI, EG, ZA, etc.)
- `currency` (auto-filled from region: KE→KES, TZ→TZS, etc.)
- `monthly_amount` (number input, in major units e.g. 4500)
- Submit → POST `/saas/combos/set-rate`

**Deactivate:** Confirmation dialog → POST `/saas/combos/deactivate`

**Data:** GET `/saas/combos`

---

### 3.4 Pricing Page (`/platform/pricing`)

**Purpose:** Kuona bei za combos kwa kila region — mtazamo wa user/customer.

**Layout:**
- PageHeader: "Pricing Catalog"
- Filter bar: Region dropdown (KE, TZ, UG, etc.) + Business Model toggle (B2B / B2C / All)
- Grid ya pricing cards (3 columns)

**Pricing Card:**
```
┌────────────────────────────────┐
│  BOS Duka                      │  ← combo name
│  Perfect for retail shops      │  ← description
│  ──────────────────────────── │
│        KES 4,500               │  ← monthly_amount (big, gold text)
│        /month                  │
│  ──────────────────────────── │
│  ✓ Retail (POS)               │  ← paid engines list
│  ✓ Inventory                  │
│  ──── Plus Free ────           │
│  ✓ Cash                       │  ← free engines (muted)
│  ✓ Documents                  │
│  ✓ Reporting                  │
│  ✓ Customer                   │
│  ──────────────────────────── │
│  Quotas:                      │
│  5 branches · 20 users        │
│  ──────────────────────────── │
│  [B2C]                        │  ← business model badge
└────────────────────────────────┘
```

**Data:** GET `/saas/pricing?region_code={selected}&business_model={selected}`

---

### 3.5 Trial Policy Page (`/platform/trial-policy`)

**Purpose:** Kuweka sera ya trial kwa platform nzima.

**Layout:**
- PageHeader: "Trial Policy"
- Single form card (centered, max-w-lg)

**Form Fields:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_trial_days` | number | 180 | Siku za trial kwa tenant mpya |
| `max_trial_days` | number | 365 | Kiwango cha juu (pamoja na bonuses) |
| `grace_period_days` | number | 7 | Siku za neema baada ya trial kuisha |
| `rate_notice_days` | number | 90 | Siku za notisi kabla ya kubadilisha bei |

**Behavior:**
- On load: GET `/saas/trial-policy` → populate form
- On save: POST `/saas/trial-policy/set`
- Show "Current Version: v{n}" badge at top

---

### 3.6 Active Trials Page (`/platform/trials`)

**Purpose:** Kuona trials zote zinazoendelea na kuzisimamia.

**Layout:**
- PageHeader: "Active Trials" + stat badges (total, expiring soon)
- Table ya trials

**Table Columns:**
| Column | Field | Notes |
|--------|-------|-------|
| Business ID | `business_id` | Monospace, truncated UUID |
| Combo | `combo_id` → resolve name | Badge |
| Trial Days | `trial_days + bonus_days` | "180 + 30 bonus" format |
| Started | `trial_starts_at` | Formatted date |
| Ends | `trial_ends_at` | Formatted date, RED if < 7 days |
| Billing Starts | `billing_starts_at` | Formatted date |
| Status | `status` | Badge: ACTIVE=purple, CONVERTED=green, EXPIRED=gray |
| Rate | `rate_snapshot.monthly_amount` | Gold text, e.g. "KES 4,500" |
| Actions | — | Extend, Convert buttons |

**Extend Trial Dialog:**
- `extra_days` (number, required)
- `reason` (text)
- Submit → POST `/saas/trials/extend`

**Convert Trial:** Confirmation → POST `/saas/trials/convert`

**Data:** GET `/saas/trials/agreement?business_id={each}` — **NOTA:** Endpoint ni per-business. Kwa sasa tutaonyesha search-by-business-id. Baadaye tuongeze list endpoint.

**Workaround kwa sasa:** Input field ya Business ID + "Load" button → fetches single agreement.

---

### 3.7 Rate Governance Page (`/platform/rates`)

**Purpose:** Kusimamia mabadiliko ya bei na kulinda tenants.

**Layout:**
- PageHeader: "Rate Governance" + Button "Publish Rate Change"
- Tab: "Effective Rates" | "Rate Changes"

**Tab 1 — Effective Rates:**
- Input: Business ID → "Check Rate" button
- Shows: current effective rate, rate_guaranteed_until, is paying old rate or new

**Tab 2 — Publish Rate Change:**
- Form:
  - `combo_id` (select from active combos)
  - `region_code` (select)
  - `old_amount` (auto-filled from current rate)
  - `new_amount` (number input)
  - `currency` (auto-filled)
  - `effective_from` (date picker — must be ≥90 days from today)
- Submit → POST `/saas/rates/publish-change`
- Response shows: urgency level (STANDARD/ELEVATED), tenants_to_notify count

**Data:**
- GET `/saas/rates/effective?business_id={id}`
- POST `/saas/rates/publish-change`

---

### 3.8 Promotions Page (`/platform/promotions`)

**Purpose:** Kuunda na kusimamia promo codes.

**Layout:**
- PageHeader: "Promotions" + Button "Create Promotion"
- Table ya promos

**Table Columns:**
| Column | Field | Notes |
|--------|-------|-------|
| Code | `promo_code` | Monospace, bold, uppercase |
| Type | `promo_type` | Badge with color per type |
| Description | `description` | Truncated text |
| Valid Period | `valid_from` → `valid_until` | Date range |
| Redemptions | `current_redemptions / max_redemptions` | Progress bar or "3/50" |
| Status | `status` | Badge: ACTIVE=green, EXHAUSTED=gold, DEACTIVATED=gray |

**Promo Type Badge Colors:**
| Type | Color |
|------|-------|
| DISCOUNT | Purple |
| CREDIT | Gold |
| EXTENDED_TRIAL | Blue |
| ENGINE_BONUS | Green |
| BUNDLE_DISCOUNT | Orange |

**Create Promotion Dialog (large modal/page):**

Step 1 — Type Selection:
- Cards kwa kila type (DISCOUNT, CREDIT, EXTENDED_TRIAL, ENGINE_BONUS, BUNDLE_DISCOUNT)
- Kila card ina icon, name, na maelezo mafupi

Step 2 — Details (based on type):
- Common: `promo_code`, `description`, `valid_from`, `valid_until`, `max_redemptions`
- Optional filters: `region_codes[]` (multi-select), `combo_ids[]` (multi-select)
- Type-specific:
  - DISCOUNT: `discount_pct` (0-100), `discount_months`
  - CREDIT: `credit_amount`, `credit_currency`, `credit_expires_months`
  - EXTENDED_TRIAL: `extra_trial_days`
  - ENGINE_BONUS: `bonus_engine` (select), `bonus_months`
  - BUNDLE_DISCOUNT: `bundle_engines[]` (multi-select), `bundle_discount_pct`

Submit → POST `/saas/promos/create`

**Redeem Promo (admin action):**
- Small dialog: `promo_code`, `business_id`, `region_code`, `combo_id`
- Submit → POST `/saas/promos/redeem`

**Data:** GET `/saas/promos`

---

### 3.9 Referrals Page (`/platform/referrals`)

**Purpose:** Kusimamia programu ya "Alika Rafiki".

**Layout:**
- PageHeader: "Referral Program — Alika Rafiki"
- Section 1: Policy Card (current settings)
- Section 2: Actions (Generate Code, Submit Referral, Qualify)

**Policy Card:**
```
┌─────────────────────────────────────────────┐
│  📋 Referral Policy (v2)                     │
│  ──────────────────────────────────────────  │
│  Referrer Reward:      30 days              │
│  Referee Bonus:        30 days              │
│  Qualification:        30 days + 10 txns    │
│  Max Referrals/Year:   12                   │
│  Champion Threshold:   10 qualified         │
│  ──────────────────────────────────────────  │
│  [Update Policy]                            │
└─────────────────────────────────────────────┘
```

**Actions Section (3 cards side by side):**

Card 1 — Generate Code:
- Input: `business_id`, `business_name`
- Button: "Generate"
- Output: Shows generated code (e.g., "BOS-MAMA-7X3K") with copy button

Card 2 — Submit Referral:
- Input: `referral_code`, `referee_business_id`, `referee_phone` (optional)
- Button: "Submit"
- Output: `referral_id`, `referee_bonus_days`

Card 3 — Qualify Referral:
- Input: `referee_business_id`
- Button: "Qualify"
- Output: qualified status, referrer reward, is_champion badge

**Update Policy Dialog:**
- Fields: `referrer_reward_days`, `referee_bonus_days`, `qualification_days`, `qualification_min_transactions`, `max_referrals_per_year`, `champion_threshold`
- Submit → POST `/saas/referrals/set-policy`

---

### 3.10 Resellers Page (`/platform/resellers`)

**Purpose:** Kusimamia programu ya "Wakala wa BOS".

**Layout:**
- PageHeader: "Resellers — Wakala wa BOS" + Button "Register Reseller"
- Summary stat cards (3): Total Resellers, Total Tenants Linked, Pending Commissions
- Table ya resellers

**Table Columns:**
| Column | Field | Notes |
|--------|-------|-------|
| Company | `company_name` | Bold text |
| Contact | `contact_person` | Secondary text |
| Tier | `tier` | Badge: BRONZE=#CD7F32, SILVER=#C4C4C4, GOLD=#D4AF37 |
| Status | `status` | Badge: ACTIVE=green, SUSPENDED=orange, TERMINATED=red |
| Tenants | `active_tenant_count` | Number |
| Commission Rate | `commission_rate` | Percentage, e.g. "15%" |
| Earned | `total_commission_earned` | Currency format |
| Pending | `pending_commission` | Gold text if > 0 |
| Actions | — | Link Tenant, Accrue, Payout buttons |

**Register Reseller Dialog:**
- `company_name` (required)
- `contact_person`
- `phone`
- `email`
- `region_codes` (multi-select)
- Payout section:
  - `payout_method` (select: M-PESA, Mobile Money, Bank Transfer)
  - Conditional fields based on method:
    - M-PESA/Mobile: `payout_phone`
    - Bank: `bank_name`, `account_number`, `account_name`
- Submit → POST `/saas/resellers/register`

**Link Tenant Dialog:**
- `business_id` (text input)
- Shows: new tier, active tenant count after link
- Submit → POST `/saas/resellers/link-tenant`

**Accrue Commission Dialog:**
- `business_id` (tenant)
- `tenant_monthly_amount` (number)
- `currency` (select)
- `period` (text, e.g., "2026-03")
- Submit → POST `/saas/resellers/accrue-commission`

**Request Payout Dialog:**
- `amount` (number)
- `currency` (select)
- Shows: available pending_commission
- Submit → POST `/saas/resellers/request-payout`

**Data:** GET `/saas/resellers`

---

### 3.11 Subscriptions Page (`/platform/subscriptions`)

**Purpose:** Kuona na kusimamia subscriptions za tenants.

**Layout:**
- PageHeader: "Subscriptions"
- Search: Business ID input + "Search" button
- Result card (kama subscription inapatikana)

**Subscription Card:**
```
┌──────────────────────────────────────────────────┐
│  Subscription: sub_abc123...                      │
│  ────────────────────────────────────────────── │
│  Business:     11111111-1111-...                 │
│  Combo:        BOS Duka                          │
│  Status:       [TRIAL]                           │  ← purple badge
│  Activated:    15 Mar 2026                       │
│  Billing:      15 Sep 2026                       │
│  Renewals:     0                                 │
│  ────────────────────────────────────────────── │
│  [Activate]  [Change Combo]  [Cancel]            │
└──────────────────────────────────────────────────┘
```

**Actions:**
- Activate → POST `/saas/subscriptions/activate` (TRIAL → ACTIVE)
- Change Combo → Dialog with combo select → POST `/saas/subscriptions/change-combo`
- Cancel → Confirmation with reason → POST `/saas/subscriptions/cancel`
- Start Trial → Dialog with business_id, combo_id, etc. → POST `/saas/subscriptions/start-trial`

**Data:** GET `/saas/subscriptions?business_id={id}`

---

## 4. FILE STRUCTURE (Mpya)

```
frontend/src/
├── app/
│   ├── globals.css                    ← UPDATE: BOS color variables
│   ├── platform/                      ← NEW: Platform Admin section
│   │   ├── layout.tsx                 ← Platform-specific layout with PlatformSidebar
│   │   ├── dashboard/page.tsx
│   │   ├── engines/page.tsx
│   │   ├── combos/page.tsx
│   │   ├── pricing/page.tsx
│   │   ├── trial-policy/page.tsx
│   │   ├── trials/page.tsx
│   │   ├── rates/page.tsx
│   │   ├── promotions/page.tsx
│   │   ├── referrals/page.tsx
│   │   ├── resellers/page.tsx
│   │   └── subscriptions/page.tsx
├── components/
│   ├── layout/
│   │   ├── platform-sidebar.tsx       ← NEW: Platform admin sidebar
│   │   ├── platform-topbar.tsx        ← NEW: Platform admin topbar
│   │   ├── platform-shell.tsx         ← NEW: Platform app shell
│   │   ├── sidebar.tsx                ← UPDATE: BOS colors + Lucide icons
│   │   ├── topbar.tsx                 ← UPDATE: BOS colors
│   │   └── app-shell.tsx              ← unchanged
│   ├── shared/
│   │   ├── stat-card.tsx              ← NEW: Reusable KPI stat card
│   │   ├── status-badge.tsx           ← NEW: Status-aware badge (ACTIVE/TRIAL/etc.)
│   │   ├── confirm-dialog.tsx         ← NEW: Reusable confirmation modal
│   │   ├── form-dialog.tsx            ← NEW: Reusable form modal/slide-over
│   │   ├── page-header.tsx            ← unchanged
│   │   └── empty-state.tsx            ← unchanged
│   └── ui/
│       └── index.tsx                  ← UPDATE: BOS colors on Button, Badge, Card
├── lib/
│   └── api/
│       ├── admin.ts                   ← unchanged
│       └── saas.ts                    ← NEW: All 33 SaaS API methods
└── stores/
    └── auth-store.ts                  ← unchanged
```

---

## 5. API CLIENT — `lib/api/saas.ts`

Faili mpya yenye methods 33 za SaaS endpoints:

```typescript
// Engines
getEngines()                         → GET /saas/engines
registerEngine(data)                 → POST /saas/engines/register

// Combos
getCombos()                          → GET /saas/combos
defineCombo(data)                    → POST /saas/combos/define
updateCombo(data)                    → POST /saas/combos/update
deactivateCombo(data)                → POST /saas/combos/deactivate
setComboRate(data)                   → POST /saas/combos/set-rate

// Pricing
getPricing(regionCode, businessModel) → GET /saas/pricing?region_code=&business_model=

// Trial Policy
getTrialPolicy()                     → GET /saas/trial-policy
setTrialPolicy(data)                 → POST /saas/trial-policy/set

// Trials
getTrialAgreement(businessId)        → GET /saas/trials/agreement?business_id=
createTrial(data)                    → POST /saas/trials/create
extendTrial(data)                    → POST /saas/trials/extend
convertTrial(data)                   → POST /saas/trials/convert

// Rate Governance
getEffectiveRate(businessId)         → GET /saas/rates/effective?business_id=
publishRateChange(data)              → POST /saas/rates/publish-change

// Promotions
getPromos()                          → GET /saas/promos
createPromo(data)                    → POST /saas/promos/create
redeemPromo(data)                    → POST /saas/promos/redeem

// Referrals
setReferralPolicy(data)              → POST /saas/referrals/set-policy
generateReferralCode(data)           → POST /saas/referrals/generate-code
submitReferral(data)                 → POST /saas/referrals/submit
qualifyReferral(data)                → POST /saas/referrals/qualify

// Resellers
getResellers()                       → GET /saas/resellers
registerReseller(data)               → POST /saas/resellers/register
linkTenant(data)                     → POST /saas/resellers/link-tenant
accrueCommission(data)               → POST /saas/resellers/accrue-commission
requestPayout(data)                  → POST /saas/resellers/request-payout

// Subscriptions
getSubscription(businessId)          → GET /saas/subscriptions?business_id=
startTrial(data)                     → POST /saas/subscriptions/start-trial
activateSubscription(data)           → POST /saas/subscriptions/activate
cancelSubscription(data)             → POST /saas/subscriptions/cancel
changeCombo(data)                    → POST /saas/subscriptions/change-combo
```

---

## 6. IMPLEMENTATION ORDER (Hawamu)

### Hawamu 1: Design System + Navigation (Msingi)
1. Update `globals.css` — BOS color CSS variables
2. Update `components/ui/index.tsx` — Button, Badge, Card with BOS colors
3. Update existing `sidebar.tsx` — Lucide icons + BOS colors + "Platform Admin" link
4. Update `topbar.tsx` — BOS brand colors
5. Create `platform-shell.tsx`, `platform-sidebar.tsx`, `platform-topbar.tsx`
6. Create `app/platform/layout.tsx` — wraps all platform pages
7. Create shared components: `stat-card.tsx`, `status-badge.tsx`, `confirm-dialog.tsx`, `form-dialog.tsx`

### Hawamu 2: API Layer + Dashboard
8. Create `lib/api/saas.ts` — all 33 API methods
9. Build `/platform/dashboard` — stat cards + quick actions

### Hawamu 3: Engine Catalog + Combos
10. Build `/platform/engines` — engine list + register dialog
11. Build `/platform/combos` — combo table + define/edit/rate/deactivate dialogs
12. Build `/platform/pricing` — pricing catalog view with region filter

### Hawamu 4: Trials & Rates
13. Build `/platform/trial-policy` — policy form
14. Build `/platform/trials` — trial lookup + extend/convert
15. Build `/platform/rates` — effective rate checker + rate change publisher

### Hawamu 5: Growth (Promos, Referrals, Resellers)
16. Build `/platform/promotions` — promo table + create wizard
17. Build `/platform/referrals` — policy card + action cards
18. Build `/platform/resellers` — reseller table + register/link/accrue/payout

### Hawamu 6: Subscriptions
19. Build `/platform/subscriptions` — search + subscription card + actions

---

## 7. REGION/CURRENCY MAP (for dropdowns)

```typescript
const REGIONS = [
  { code: "KE", name: "Kenya", currency: "KES" },
  { code: "TZ", name: "Tanzania", currency: "TZS" },
  { code: "UG", name: "Uganda", currency: "UGX" },
  { code: "RW", name: "Rwanda", currency: "RWF" },
  { code: "NG", name: "Nigeria", currency: "NGN" },
  { code: "GH", name: "Ghana", currency: "GHS" },
  { code: "ZA", name: "South Africa", currency: "ZAR" },
  { code: "CI", name: "Côte d'Ivoire", currency: "XOF" },
  { code: "EG", name: "Egypt", currency: "EGP" },
  { code: "ET", name: "Ethiopia", currency: "ETB" },
];
```

---

## 8. DESIGN PRINCIPLES

1. **Professional & Clean** — Silver msingi, purple accent, gold highlight. Hakuna rangi nyingi kupita kiasi.
2. **Data-dense** — Tables na cards zionyeshe data muhimu bila scroll kupita kiasi.
3. **Status-clear** — Kila status ina rangi yake maalum. Mtumiaji aone hali kwa mtazamo wa kwanza.
4. **Consistent** — Kila page ina PageHeader + content area + action buttons location ile ile.
5. **Responsive** — Grid inajibadilisha: 3-col → 2-col → 1-col kwa screen ndogo.
6. **Dark mode** — Kila rangi ina dark variant. Inafuata OS preference.
7. **Accessible** — Contrast ratio ≥ 4.5:1 kwa text zote. Focus states visible.
