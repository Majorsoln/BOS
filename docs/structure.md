bos/
├── core/                           # 🔐 SYSTEM LAW & TRUTH
│   ├── context/                    # Business / Branch / Request context
│   ├── event_store/                # Canonical events (immutable truth)
│   ├── events/                     # Event bus, dispatcher, registry
│   ├── replay/                     # Replay & rebuild
│   ├── engines/                    # Engine registry & contracts
│   ├── commands/                   # Command base, outcomes, rejection, bus
│   ├── primitives/                 # Shared value objects (Money, Quantity, etc.)
│   ├── policy/                     # Generic policy / rule engine
│   ├── feature_flags/              # Engine-level feature flag system
│   ├── time/                       # Clock protocol & temporal rules
│   ├── security/                   # Access, anomaly, rate limits (Phase 8)
│   ├── audit/                      # Evidence, consent, access logs
│   ├── resilience/                 # NORMAL / DEGRADED / READ_ONLY
│   ├── business/                   # Business & branch lifecycle
│   ├── config/                     # Country rules, tax rules, compliance
│   ├── admin/                      # Admin command handling
│   ├── auth/                       # Authentication primitives
│   ├── bootstrap/                  # System initialization
│   ├── compliance/                 # Compliance rule engine
│   ├── documents/                  # Document templates & rendering
│   ├── document_issuance/          # Document issuance workflow
│   ├── http_api/                   # HTTP API framework
│   ├── identity/                   # Identity resolution
│   ├── identity_store/             # Identity persistence
│   ├── permissions/                # Permission definitions
│   └── permissions_store/          # Permission persistence
│
├── engines/                        # 🏭 BUSINESS ENGINES (10 ENGINES)
│   ├── retail/                     # 🛒 RETAIL ENGINE
│   │   ├── commands/               # Intent (SaleOpen, AddLine, Complete)
│   │   ├── services/               # Retail business logic
│   │   ├── policies/               # Discounts, eligibility rules
│   │   ├── events.py               # retail.* event declarations
│   │   └── subscriptions.py        # reacts to other engines
│   │
│   ├── restaurant/                 # 🍽️ RESTAURANT ENGINE
│   │   ├── commands/               # TableOpen, OrderPlace, KitchenTicket
│   │   ├── services/               # Order lifecycle, kitchen flow
│   │   ├── policies/               # Table rules, service rules
│   │   ├── events.py               # restaurant.* events
│   │   └── subscriptions.py
│   │
│   ├── workshop/                   # 🪟 WORKSHOP / CONSTRUCTION ENGINE
│   │   ├── commands/               # JobCreate, CutlistGenerate
│   │   ├── services/               # Parametric geometry, cut optimization
│   │   ├── policies/               # Material usage, waste rules
│   │   ├── events.py               # workshop.* events
│   │   └── subscriptions.py
│   │
│   ├── inventory/                  # 📦 INVENTORY ENGINE
│   │   ├── commands/               # StockReceive, StockIssue, StockTransfer
│   │   ├── services/               # FIFO/LIFO lot tracking
│   │   ├── policies/
│   │   ├── events.py               # inventory.* events
│   │   └── subscriptions.py
│   │
│   ├── cash/                       # 💵 CASH MANAGEMENT ENGINE
│   │   ├── commands/
│   │   ├── services/
│   │   ├── policies/
│   │   ├── events.py               # cash.* events
│   │   └── subscriptions.py
│   │
│   ├── accounting/                 # 📊 ACCOUNTING ENGINE
│   │   ├── commands/
│   │   ├── services/
│   │   ├── policies/
│   │   ├── events.py               # accounting.* events
│   │   └── subscriptions.py
│   │
│   ├── procurement/                # 🧾 PROCUREMENT ENGINE
│   │   ├── commands/               # RequisitionCreate, OrderCreate, PaymentRelease
│   │   ├── services/
│   │   ├── policies/
│   │   ├── events.py               # procurement.* events
│   │   └── subscriptions.py
│   │
│   ├── promotion/                  # 🎯 PROMOTION & LOYALTY ENGINE
│   │   ├── commands/
│   │   ├── services/
│   │   ├── policies/
│   │   ├── events.py               # promotion.* events
│   │   └── subscriptions.py
│   │
│   ├── hr/                         # 👥 HR & ATTENDANCE ENGINE
│   │   ├── commands/               # EmployeeOnboard, PayrollRun
│   │   ├── services/               # Payroll computation + ledger integration
│   │   ├── policies/
│   │   ├── events.py               # hr.* events
│   │   └── subscriptions.py
│   │
│   └── reporting/                  # 📈 REPORTING & BI ENGINE
│       ├── commands/               # SnapshotRecord, KPIRecord
│       ├── services/               # KPI projections, dashboards
│       ├── policies/
│       ├── events.py               # reporting.* events
│       └── subscriptions.py
│
├── projections/                    # 📊 READ MODELS (DISPOSABLE)
│   ├── retail/
│   ├── restaurant/
│   ├── workshop/
│   ├── inventory/
│   ├── finance/
│   ├── bi/
│   └── guards/                     # Read-only enforcement
│
├── integration/                    # 🌐 EXTERNAL SYSTEMS
│   ├── inbound/
│   ├── outbound/
│   ├── adapters/
│   ├── permissions.py
│   └── audit_log.py
│
├── ai/                             # 🤖 ADVISORY ONLY
│   ├── advisors/                   # Domain-specific advisory modules
│   ├── decision_simulation/        # What-if outcome projections
│   ├── journal/                    # Decision Journal (append-only)
│   └── guardrails.py              # AI execution boundary enforcement
│
├── interfaces/                     # 🖥️ API / UI
│   ├── api/
│   ├── admin/
│   └── ui/
│
├── tests/
│   ├── core/
│   ├── engines/
│   ├── projections/
│   ├── ai/
│   └── integration/
│
└── docs/
    ├── AGENTS.md
    ├── BOS-Requirement.md
    ├── scope-policy.md
    ├── identity-actor-matrix.md
    ├── structure.md
    ├── live-smoke-tests.md
    └── live-smoke-tests-phase-2.7.md
