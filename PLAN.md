# BOS Frontend Architecture Plan

## Tech Stack
- **Web:** Next.js 14 (App Router) + React 18
- **Mobile:** React Native (Expo) — Phase 2
- **State:** Zustand (global) + TanStack Query (server state)
- **UI:** shadcn/ui + Tailwind CSS
- **Forms:** React Hook Form + Zod validation
- **HTTP:** Axios with interceptors (API key injection)

## Directory Structure

```
frontend/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── components.json              # shadcn/ui config
├── public/
│   └── logo.svg
├── src/
│   ├── app/                     # Next.js App Router
│   │   ├── layout.tsx           # Root layout (providers, sidebar)
│   │   ├── page.tsx             # Dashboard home
│   │   ├── login/
│   │   │   └── page.tsx         # API key entry screen
│   │   ├── dashboard/
│   │   │   └── page.tsx         # Overview KPIs
│   │   ├── settings/
│   │   │   ├── business/
│   │   │   │   └── page.tsx     # Business profile editor
│   │   │   ├── branches/
│   │   │   │   └── page.tsx     # Branch management
│   │   │   ├── users/
│   │   │   │   └── page.tsx     # Actors + role assignment
│   │   │   ├── api-keys/
│   │   │   │   └── page.tsx     # API key management
│   │   │   ├── tax-rules/
│   │   │   │   └── page.tsx     # Tax rate configuration
│   │   │   ├── feature-flags/
│   │   │   │   └── page.tsx     # Feature flag toggles
│   │   │   └── layout.tsx       # Settings sidebar
│   │   ├── customers/
│   │   │   ├── page.tsx         # Customer list
│   │   │   └── [id]/
│   │   │       └── page.tsx     # Customer detail/edit
│   │   ├── documents/
│   │   │   ├── page.tsx         # Document list (all types)
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx     # Document detail + render
│   │   │   └── templates/
│   │   │       └── page.tsx     # Template management
│   │   └── migration/
│   │       └── page.tsx         # Data migration wizard
│   │
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── select.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── app-shell.tsx    # Main layout: sidebar + topbar + content
│   │   │   ├── sidebar.tsx      # Navigation sidebar
│   │   │   ├── topbar.tsx       # Top bar (business name, branch selector)
│   │   │   └── breadcrumbs.tsx
│   │   ├── auth/
│   │   │   └── auth-guard.tsx   # Redirect to login if no API key
│   │   └── shared/
│   │       ├── data-table.tsx   # Reusable table with pagination
│   │       ├── page-header.tsx  # Page title + actions
│   │       ├── empty-state.tsx  # Empty list placeholder
│   │       └── loading.tsx      # Skeleton loader
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts        # Axios instance with API key interceptor
│   │   │   ├── admin.ts         # Admin endpoints (business, roles, flags)
│   │   │   ├── customers.ts     # Customer CRUD
│   │   │   ├── documents.ts     # Document issuance + rendering
│   │   │   └── migration.ts     # Migration endpoints
│   │   ├── utils.ts             # Formatters (currency, date, etc.)
│   │   └── constants.ts         # Enums, valid permissions, doc types
│   │
│   ├── stores/
│   │   ├── auth-store.ts        # API key, business_id, branch_id, actor
│   │   ├── ui-store.ts          # Sidebar state, theme, locale
│   │   └── business-store.ts    # Cached business profile, branches, roles
│   │
│   └── types/
│       ├── api.ts               # Request/response types
│       ├── business.ts          # Business, Branch, Actor, Role
│       ├── document.ts          # DocumentType, Template, RenderPlan
│       └── customer.ts          # CustomerProfile
│
└── .env.local                   # API base URL
```

## Phase 1 Implementation Steps (App Shell)

### Step 1: Project scaffolding
- `npx create-next-app@latest frontend` with TypeScript, Tailwind, App Router
- Install: zustand, @tanstack/react-query, axios, react-hook-form, zod
- Init shadcn/ui: `npx shadcn-ui@latest init`
- Add base components: button, input, card, table, dialog, badge, select, toast, dropdown-menu, sheet

### Step 2: API client (`src/lib/api/client.ts`)
- Axios instance pointing to `http://localhost:8000` (Django backend)
- Request interceptor: inject `Authorization: Bearer {apiKey}` header
- Response interceptor: handle errors (401 → redirect to login)
- Auto-inject `business_id` + `branch_id` from auth store

### Step 3: Auth store + login page
- Zustand store: `apiKey`, `businessId`, `branchId`, `actor`
- Persist to localStorage
- Login page: simple form — enter API key → call `GET /admin/business` to validate
- On success → store key + business data → redirect to dashboard
- Auth guard component wrapping all protected routes

### Step 4: App shell layout
- `app-shell.tsx`: sidebar (left) + topbar (top) + content area
- Sidebar navigation grouped by section:
  - **Overview**: Dashboard
  - **Operations**: (placeholder for engine-specific pages)
  - **Documents**: Document list, Templates
  - **People**: Customers
  - **Settings**: Business, Branches, Users, API Keys, Tax, Flags
  - **Migration**: Data import wizard
- Topbar: business name, branch selector dropdown, theme toggle
- Responsive: sidebar collapses on mobile (hamburger → sheet)

### Step 5: Dashboard page
- Placeholder cards for KPIs (will connect to reporting engine later)
- Quick actions: "New Customer", "Issue Document", "View Documents"
- Recent activity feed (placeholder)

### Step 6: Settings pages (CRUD wired to real API)
- **Business profile**: GET + POST `/admin/business/update` — name, address, tax_id, logo
- **Branches**: GET `/admin/branches` — list with name, timezone
- **Users & Roles**: GET `/admin/actors` + `/admin/roles` — list actors, assign/revoke roles
- **API Keys**: GET + POST `/admin/api-keys/*` — create, list, revoke, rotate
- **Tax Rules**: GET + POST `/admin/tax-rules/*` — configure rates
- **Feature Flags**: GET + POST `/admin/feature-flags/*` — toggle flags

### Step 7: Customer management
- List page with search/filter
- Create dialog (name, phone, email, address)
- Edit page
- All wired to `/admin/customers/*` endpoints

### Step 8: Document views
- Document list with type filter, date range, search
- Document detail: render plan JSON + "View HTML" / "Download PDF" buttons
- Template list (admin only)
