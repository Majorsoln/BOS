"""
BOS Core Primitives — Reusable Business Building Blocks
========================================================
Phase 4: Business Primitive Layer

Primitives are the shared, engine-agnostic building blocks that
all BOS engines consume. They are:

- Pure Python (no Django dependency)
- Immutable (frozen dataclasses)
- Deterministic (same input → same output)
- Multi-tenant aware (business_id scoped)
- Event-sourced (state derived from events only)

Primitives:
    ledger      — Double-entry accounting entries & balance computation
    item        — Catalog item / product / service definition
    inventory   — Stock movement abstraction (in/out/transfer/adjust)
    party       — Customer, vendor, staff party abstraction
    obligation  — Payment/delivery obligation lifecycle tracking
"""
