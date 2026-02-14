bos/
├── core/                           # 🔐 SYSTEM LAW & TRUTH
│   ├── context/                    # Business / Branch / Request context
│   ├── event_store/                # Canonical events (immutable truth)
│   ├── events/                     # Event bus, dispatcher, registry
│   ├── replay/                     # Replay & rebuild
│   ├── engines/                    # Engine registry & contracts
│   ├── rules/                      # Generic policy / rule engine
│   ├── time/                       # Clock & temporal rules
│   ├── security/                   # Access, anomaly, rate limits
│   ├── audit/                      # Evidence, consent, access logs
│   ├── resilience/                 # NORMAL / DEGRADED / READ_ONLY
│   ├── business/                   # Business lifecycle
│   └── config/                     # Country rules, tax rules, flags
│
├── engines/                        # 🏭 BUSINESS ENGINES (WRITE EVENTS ONLY)
│   ├── retail/                     # 🛒 RETAIL ENGINE
│   │   ├── commands/               # Intent (SellItem, OpenCart)
│   │   ├── services/               # Retail business logic
│   │   ├── policies/               # Discounts, eligibility rules
│   │   ├── events.py               # retail.* event declarations
│   │   └── subscriptions.py        # reacts to other engines (read-only)
│   │
│   ├── restaurant/                 # 🍽️ RESTAURANT ENGINE
│   │   ├── commands/               # OpenTable, PlaceOrder
│   │   ├── services/               # Order lifecycle, kitchen flow
│   │   ├── policies/               # Table rules, service rules
│   │   ├── events.py               # restaurant.* events
│   │   └── subscriptions.py
│   │
│   ├── workshop/                   # 🪟 WORKSHOP / CONSTRUCTION ENGINE
│   │   ├── commands/               # CreateProject, GenerateCutList
│   │   ├── services/               # Style logic, optimization
│   │   ├── policies/               # Material usage, waste rules
│   │   ├── events.py               # workshop.* events
│   │   └── subscriptions.py
│   │
│   ├── inventory/                  # 📦 INVENTORY ENGINE
│   │   ├── commands/
│   │   ├── services/
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
│   │   ├── commands/
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
│   └── hr/                          # 👥 HR & ATTENDANCE ENGINE
│       ├── commands/
│       ├── services/
│       ├── policies/
│       ├── events.py               # hr.* events
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
│   ├── advisors/
│   ├── decision_simulation/
│   ├── journal/
│   └── guardrails.py
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
│   ├── security/
│   └── invariants/
│
└── docs/
    ├── doctrine/
    ├── architecture/
    ├── implementation/
    └── ownership